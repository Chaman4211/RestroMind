import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  CheckCircle2,
  Film,
  Upload,
  Users,
} from 'lucide-react'
import {
  createCameraSource,
  getCameraSources,
  getRestaurantTables,
  uploadVideoStream,
  type RestaurantTable,
  type VideoFrameEvent,
  type VideoFrameResult,
  type VideoProcessingSummary,
} from '../services/api'
import TableZoneEditor from './TableZoneEditor'
import './UploadVideo.css'

type ZonePoint = {
  x: number
  y: number
}

function readZonePoints(zone: unknown): ZonePoint[] {
  const raw =
    Array.isArray(zone)
      ? zone
      : zone && typeof zone === 'object' && 'points' in zone
        ? (zone as { points?: unknown }).points
        : null

  if (!Array.isArray(raw)) return []

  return raw.flatMap((point): ZonePoint[] => {
    if (
      Array.isArray(point) &&
      point.length === 2 &&
      typeof point[0] === 'number' &&
      typeof point[1] === 'number'
    ) {
      return [{ x: point[0], y: point[1] }]
    }

    return []
  })
}

function statusColor(status: string): string {
  switch (status) {
    case 'OCCUPIED':
      return '#f59e0b'
    case 'NEEDS_CLEANING':
      return '#d97706'
    case 'UNPAID_BILL':
    case 'NEEDS_ATTENTION':
      return '#dc2626'
    default:
      return '#22a06b'
  }
}

function UploadVideo() {
  const queryClient = useQueryClient()
  const videoRef = useRef<HTMLVideoElement>(null)

  const [previewElement, setPreviewElement] = useState<HTMLDivElement | null>(null)
  const [sourceName, setSourceName] = useState('Uploaded video camera')
  const [selectedSource, setSelectedSource] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [videoReady, setVideoReady] = useState(false)
  const [message, setMessage] = useState('')
  const [frameResults, setFrameResults] = useState<VideoFrameEvent[]>([])
  const [activeFrame, setActiveFrame] = useState<VideoFrameResult | null>(null)
  const [summary, setSummary] = useState<VideoProcessingSummary | null>(null)
  const [progress, setProgress] = useState(0)
  const [currentVideoTime, setCurrentVideoTime] = useState(0)

  const {
    data: cameraSources = [],
    isLoading: camerasLoading,
  } = useQuery({
    queryKey: ['camera-sources'],
    queryFn: getCameraSources,
  })

  const {
    data: tables = [],
  } = useQuery({
    queryKey: ['restaurant-tables'],
    queryFn: getRestaurantTables,
  })

  const uploadSources = cameraSources.filter(
    (source) => source.source_type === 'UPLOAD' && source.is_active,
  )

  const activeSource = uploadSources.some(
    (source) => String(source.id) === selectedSource,
  )
    ? selectedSource
    : uploadSources.length > 0
      ? String(uploadSources[0].id)
      : ''

  useEffect(() => {
    return () => {
      if (videoUrl) URL.revokeObjectURL(videoUrl)
    }
  }, [videoUrl])

  const createMutation = useMutation({
    mutationFn: () =>
      createCameraSource({
        name: sourceName.trim(),
        source_type: 'UPLOAD',
      }),
    onSuccess: async (source) => {
      await queryClient.invalidateQueries({ queryKey: ['camera-sources'] })
      setSelectedSource(String(source.id))
      setMessage(`Upload source "${source.name}" created.`)
    },
    onError: (error) => {
      setMessage(
        error instanceof Error ? error.message : 'Could not create upload source.',
      )
    },
  })

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file || !activeSource) {
        throw new Error('Select an upload source and a video first.')
      }

      return uploadVideoStream(
        Number(activeSource),
        file,
        (event) => {
          setFrameResults((current) => [...current, event])

          const video = videoRef.current
          if (video && video.currentTime >= event.video_time) {
            setActiveFrame(event.result)
          }

          if (video && video.duration > 0) {
            setProgress(
              Math.min(99, Math.round((event.video_time / video.duration) * 100)),
            )
          }
        },
      )
    },
    onSuccess: async (data) => {
      setSummary(data)
      setProgress(100)
      setMessage('Video processing completed successfully.')

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] }),
        queryClient.invalidateQueries({ queryKey: ['alerts'] }),
      ])
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : 'Video processing failed.')
    },
  })

  const handleFileChange = (selectedFile?: File) => {
    setFrameResults([])
    setActiveFrame(null)
    setSummary(null)
    setProgress(0)
    setCurrentVideoTime(0)
    setMessage('')
    setVideoReady(false)

    if (!selectedFile) {
      setFile(null)
      setVideoUrl('')
      return
    }

    const allowedExtensions = /\.(mp4|mov|avi|mkv|webm)$/i

    if (!allowedExtensions.test(selectedFile.name)) {
      setFile(null)
      setVideoUrl('')
      setMessage('Choose an MP4, MOV, AVI, MKV, or WEBM video.')
      return
    }

    if (selectedFile.size > 100 * 1024 * 1024) {
      setFile(null)
      setVideoUrl('')
      setMessage('Video exceeds the 100 MB upload limit.')
      return
    }

    setFile(selectedFile)
    setVideoUrl(URL.createObjectURL(selectedFile))
  }

  const syncFrameToPlayback = () => {
    const video = videoRef.current
    if (!video) return

    const time = video.currentTime
    setCurrentVideoTime(time)

    const matchingFrames = frameResults.filter(
      (event) => event.video_time <= time + 0.05,
    )

    if (matchingFrames.length > 0) {
      setActiveFrame(matchingFrames[matchingFrames.length - 1].result)
    }
  }

  const startProcessing = () => {
    setFrameResults([])
    setActiveFrame(null)
    setSummary(null)
    setProgress(0)
    setMessage('Uploading video and starting person detection...')

    void videoRef.current?.play().catch(() => {
      setMessage('Video preview could not start. Press play after processing begins.')
    })

    uploadMutation.mutate()
  }

  const frameWidth = activeFrame?.frame_width || 640
  const frameHeight = activeFrame?.frame_height || 480

  return (
    <section className="upload-workspace">
      <div className="upload-heading">
        <div>
          <div className="panel-title">Video intelligence</div>
          <p className="panel-caption">
            Upload a restaurant recording to detect people and monitor table activity.
          </p>
        </div>
        <Film size={22} color="#78917d" />
      </div>

      <div className="upload-controls">
        <label className="upload-field">
          <span>Registered upload source</span>
          <select
            value={activeSource}
            onChange={(event) => setSelectedSource(event.target.value)}
            disabled={camerasLoading || uploadMutation.isPending}
          >
            <option value="">Select an upload source</option>
            {uploadSources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name} · #{source.id}
              </option>
            ))}
          </select>
        </label>

        <div className="upload-create-source">
          <label className="upload-field">
            <span>New source name</span>
            <input
              value={sourceName}
              onChange={(event) => setSourceName(event.target.value)}
              maxLength={100}
              minLength={2}
              placeholder="e.g. Restaurant recording"
            />
          </label>
          <button
            type="button"
            className="upload-secondary-button"
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending || sourceName.trim().length < 2}
          >
            {createMutation.isPending ? 'Creating...' : 'Create source'}
          </button>
        </div>
      </div>

      <div className="upload-file-area">
        <label className="upload-field">
          <span>Select video file</span>
          <input
            type="file"
            accept=".mp4,.mov,.avi,.mkv,.webm,video/*"
            onChange={(event) => handleFileChange(event.target.files?.[0])}
            disabled={uploadMutation.isPending}
          />
        </label>
        <p className="upload-hint">
          Supported formats: MP4, MOV, AVI, MKV, WEBM. Maximum size: 100 MB.
        </p>
        {file && (
          <div className="upload-selected-file">
            <Film size={16} />
            <span>{file.name}</span>
            <span>{(file.size / (1024 * 1024)).toFixed(1)} MB</span>
          </div>
        )}
      </div>

      {videoUrl && (
        <div className="upload-preview-section">
          <div>
            <div className="panel-title">Detection preview</div>
            <p className="panel-caption">
              Play the video to see detected people, tracking IDs, and configured table zones.
            </p>
          </div>

          <div className="camera-preview upload-video-preview" ref={setPreviewElement}>
            <video
              ref={videoRef}
              src={videoUrl}
              controls
              playsInline
              onLoadedMetadata={() => setVideoReady(true)}
              onTimeUpdate={syncFrameToPlayback}
              onError={() => {
                setVideoReady(false)
                setMessage('This video could not be previewed by your browser.')
              }}
            />

            {activeFrame && (
              <svg
                className="upload-detection-overlay"
                viewBox={`0 0 ${frameWidth} ${frameHeight}`}
                preserveAspectRatio="xMidYMid meet"
                aria-label="Person detection and table status overlay"
              >
                {tables
                  .filter(
                    (table) =>
                      table.upload_zone_coordinates !== null &&
                      table.upload_camera_source_id === Number(activeSource),
                  )
                  .map((table: RestaurantTable) => {
                  const points = readZonePoints(table.upload_zone_coordinates)
                  if (points.length < 3) return null

                  const tableResult = activeFrame.tables.find(
                    (item) => item.table_id === table.id,
                  )
                  const color = statusColor(
                    tableResult?.status || table.status,
                  )

                  return (
                    <g key={table.id}>
                      <polygon
                        points={points
                          .map(
                            (point) =>
                              `${point.x * frameWidth},${point.y * frameHeight}`,
                          )
                          .join(' ')}
                        fill={color}
                        fillOpacity="0.16"
                        stroke={color}
                        strokeWidth="3"
                      />
                      <text
                        x={points[0].x * frameWidth}
                        y={Math.max(18, points[0].y * frameHeight - 8)}
                        className="upload-zone-label"
                      >
                        {table.table_number} · {tableResult?.status || table.status}
                      </text>
                    </g>
                  )
                })}

                {activeFrame.people.map((person, index) => {
                  const [x1, y1, x2, y2] = person.bbox

                  return (
                    <g key={`${person.track_id}-${index}`}>
                      <rect
                        x={x1}
                        y={y1}
                        width={x2 - x1}
                        height={y2 - y1}
                        className="upload-person-box"
                      />
                      <text
                        x={x1}
                        y={Math.max(16, y1 - 5)}
                        className="upload-person-label"
                      >
                        Person {person.track_id} · {Math.round(person.confidence * 100)}%
                      </text>
                    </g>
                  )
                })}
              </svg>
            )}

            <div className="upload-preview-indicator">
              {uploadMutation.isPending ? 'AI PROCESSING' : 'VIDEO PREVIEW'}
            </div>
          </div>

          <TableZoneEditor
            videoRef={videoRef}
            previewElement={previewElement}
            tables={tables}
            cameraSourceId={activeSource ? Number(activeSource) : null}
            cameraActive={videoReady && Boolean(activeSource) && !uploadMutation.isPending}
            zoneMode="upload"
          />

          <div className="upload-live-metrics">
            <div>
              <Users size={18} />
              <span>People detected</span>
              <strong>{activeFrame?.people_detected ?? 0}</strong>
            </div>
            <div>
              <span>Processed frames</span>
              <strong>{frameResults.length}</strong>
            </div>
            <div>
              <span>Video time</span>
              <strong>{currentVideoTime.toFixed(1)}s</strong>
            </div>
          </div>

          <div className="upload-progress">
            <div className="upload-progress-heading">
              <span>{uploadMutation.isPending ? 'Processing video' : summary ? 'Processing complete' : 'Ready to process'}</span>
              <strong>{progress}%</strong>
            </div>
            <div className="upload-progress-track">
              <div style={{ width: `${progress}%` }} />
            </div>
          </div>

          <div className="upload-table-results">
            <div className="panel-title">Table detection results</div>
            {tables.length === 0 ? (
              <p className="panel-caption">No restaurant tables are registered.</p>
            ) : (
              <div className="upload-table-grid">
                {tables.map((table: RestaurantTable) => {
                  const result = activeFrame?.tables.find(
                    (item) => item.table_id === table.id,
                  )
                  const status = result?.status || table.status

                  return (
                    <div className="upload-table-card" key={table.id}>
                      <div className="upload-table-card-top">
                        <strong>{table.table_number}</strong>
                        <span style={{ color: statusColor(status) }}>
                          {status.replaceAll('_', ' ')}
                        </span>
                      </div>
                      <span>{table.name}</span>
                      <small>
                        {result
                          ? `${result.person_count} people detected`
                          : 'Waiting for detection'}
                      </small>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="upload-submit-row">
        <button
          type="button"
          className="upload-primary-button"
          onClick={startProcessing}
          disabled={
            !file ||
            !activeSource ||
            uploadMutation.isPending ||
            !videoReady
          }
        >
          <Upload size={15} />
          {uploadMutation.isPending ? 'Processing video...' : 'Start automatic detection'}
        </button>
      </div>

      {message && (
        <div
          className={`upload-message ${summary ? 'success' : ''}`}
          role="status"
        >
          {summary ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{message}</span>
        </div>
      )}

      {summary && (
        <div className="upload-result">
          <strong>Video processing summary</strong>
          <div className="upload-summary-grid">
            <span>Total frames: <strong>{summary.total_frames}</strong></span>
            <span>Processed frames: <strong>{summary.processed_frames}</strong></span>
            <span>Video duration: <strong>{summary.duration_seconds}s</strong></span>
            <span>Maximum people detected: <strong>{summary.max_people_detected}</strong></span>
          </div>
        </div>
      )}
    </section>
  )
}

export default UploadVideo
