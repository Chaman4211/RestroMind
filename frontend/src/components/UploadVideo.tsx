import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Film, Upload } from 'lucide-react'
import {
  createCameraSource,
  getCameraSources,
  getRestaurantTables,
  uploadVideo,
} from '../services/api'
import TableZoneEditor from './TableZoneEditor'
import './UploadVideo.css'

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
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const { data: cameraSources = [], isLoading: camerasLoading } = useQuery({
    queryKey: ['camera-sources'],
    queryFn: getCameraSources,
  })

  const { data: tables = [] } = useQuery({
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
      setMessage(error instanceof Error ? error.message : 'Could not create upload source.')
    },
  })

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file || !activeSource) {
        throw new Error('Select an upload source and a video first.')
      }
      return uploadVideo(Number(activeSource), file)
    },
    onSuccess: async (data) => {
      setResult(data)
      setMessage('Video processing completed successfully.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] }),
        queryClient.invalidateQueries({ queryKey: ['alerts'] }),
      ])
    },
    onError: (error) => {
      setResult(null)
      setMessage(error instanceof Error ? error.message : 'Video processing failed.')
    },
  })

  const handleFileChange = (selectedFile?: File) => {
    setResult(null)
    setMessage('')
    setVideoReady(false)
    setVideoUrl('')

    if (!selectedFile) {
      setFile(null)
      return
    }

    const allowedExtensions = /\.(mp4|mov|avi|mkv|webm)$/i

    if (!allowedExtensions.test(selectedFile.name)) {
      setFile(null)
      setMessage('Choose an MP4, MOV, AVI, MKV, or WEBM video.')
      return
    }

    if (selectedFile.size > 100 * 1024 * 1024) {
      setFile(null)
      setMessage('Video exceeds the 100 MB upload limit.')
      return
    }

    setFile(selectedFile)
    setVideoUrl(URL.createObjectURL(selectedFile))
  }

  return (
    <section className="upload-workspace">
      <div className="upload-heading">
        <div>
          <div className="panel-title">Process an uploaded video</div>
          <p className="panel-caption">
            Upload a recorded restaurant video to detect people and update table occupancy.
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
          <div className="panel-title">Video preview and table zones</div>
          <p className="panel-caption">
            Play the video and mark each table boundary before processing.
          </p>
          <div className="camera-preview upload-video-preview" ref={setPreviewElement}>
            <video
              ref={videoRef}
              src={videoUrl}
              controls
              playsInline
              onLoadedMetadata={() => setVideoReady(true)}
              onError={() => {
                setVideoReady(false)
                setMessage('This video could not be previewed by your browser.')
              }}
            />
          </div>

          <TableZoneEditor
            videoRef={videoRef}
            previewElement={previewElement}
            tables={tables}
            cameraSourceId={activeSource ? Number(activeSource) : null}
            cameraActive={videoReady && Boolean(activeSource)}
          />
        </div>
      )}

      <div className="upload-submit-row">
        <button
          type="button"
          className="upload-primary-button"
          onClick={() => uploadMutation.mutate()}
          disabled={
            !file ||
            !activeSource ||
            uploadMutation.isPending ||
            !videoReady
          }
        >
          <Upload size={15} />
          {uploadMutation.isPending ? 'Processing video...' : 'Upload and process video'}
        </button>
      </div>

      {message && (
        <div className={`upload-message ${result ? 'success' : ''}`} role="status">
          {result ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{message}</span>
        </div>
      )}

      {result && (
        <div className="upload-result">
          <strong>Processing result</strong>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </section>
  )
}

export default UploadVideo
