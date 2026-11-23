import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Camera, Play, Plus, Square, Wifi, WifiOff } from 'lucide-react'
import {
  createCameraSource,
  getCameraSources,
  getRTSPCameraStatus,
  getRTSPCameraFrame,
  getRestaurantTables,
  type RestaurantTable,
  startRTSPCamera,
  stopRTSPCamera,
} from '../services/api'
import TableZoneEditor from './TableZoneEditor'
import './RTSPCameraPanel.css'

function RTSPCameraPanel() {
  const imageRef = useRef<HTMLImageElement>(null)
  const [previewElement, setPreviewElement] = useState<HTMLDivElement | null>(null)
  const [frameUrl, setFrameUrl] = useState<{
    cameraId: number
    url: string
  } | null>(null)

  const queryClient = useQueryClient()

  const [name, setName] = useState('')
  const [rtspUrl, setRtspUrl] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const { data: sources = [], isLoading } = useQuery({
    queryKey: ['camera-sources'],
    queryFn: getCameraSources,
  })

  const rtspSources = sources.filter(
    (source) => source.source_type === 'RTSP',
  )

  const { data: tables = [] } = useQuery<RestaurantTable[]>({
    queryKey: ['restaurant-tables'],
    queryFn: getRestaurantTables,
  })

  const selectedSource = rtspSources.find(
    (source) => source.id === selectedId,
  )

  const { data: status, refetch: refreshStatus } = useQuery({
    queryKey: ['rtsp-camera-status', selectedId],
    queryFn: () => getRTSPCameraStatus(selectedId!),
    enabled: selectedId !== null,
    refetchInterval: selectedId !== null ? 2000 : false,
  })

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setBusy(true)
    setMessage('')

    try {
      const camera = await createCameraSource({
        name: name.trim(),
        source_type: 'RTSP',
        rtsp_url: rtspUrl.trim(),
      })

      await queryClient.invalidateQueries({ queryKey: ['camera-sources'] })
      setSelectedId(camera.id)
      setName('')
      setRtspUrl('')
      setMessage('CCTV / IP camera registered successfully.')
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not register camera.')
    } finally {
      setBusy(false)
    }
  }

  const handleStart = async () => {
    if (!selectedId) return
    setBusy(true)
    setMessage('')

    try {
      await startRTSPCamera(selectedId)
      await refreshStatus()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not start camera.')
      await refreshStatus()
    } finally {
      setBusy(false)
    }
  }

  const handleStop = async () => {
    if (!selectedId) return
    setBusy(true)
    setMessage('')

    try {
      await stopRTSPCamera(selectedId)
      await refreshStatus()
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Could not stop camera.')
    } finally {
      setBusy(false)
    }
  }

  const running = status?.status === 'RUNNING' ||
    status?.status === 'STARTING' ||
    status?.status === 'STOPPING'

  const { data: frameBlob } = useQuery({
    queryKey: ['rtsp-camera-frame', selectedId],
    queryFn: () => getRTSPCameraFrame(selectedId!),
    enabled: selectedId !== null && status?.status === 'RUNNING',
    refetchInterval: 1500,
    retry: false,
  })

  // Synchronize the fetched frame with a revocable browser object URL.
  useEffect(() => {
    if (!frameBlob || selectedId === null) return

    const nextUrl = URL.createObjectURL(frameBlob)
    const timeout = window.setTimeout(() => {
      setFrameUrl({ cameraId: selectedId, url: nextUrl })
    }, 0)

    return () => {
      window.clearTimeout(timeout)
      URL.revokeObjectURL(nextUrl)
    }
  }, [frameBlob, selectedId])

  const frameReady = Boolean(
    frameUrl?.cameraId === selectedId && status?.status === 'RUNNING',
  )

  return (
    <div className="rtsp-camera-layout">
      <section className="panel rtsp-camera-panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">Register CCTV / IP camera</div>
            <div className="panel-caption">
              Connect a network camera using its RTSP or RTSPS address.
            </div>
          </div>
          <Camera size={19} color="#78917d" />
        </div>

        <form className="rtsp-register-form" onSubmit={handleCreate}>
          <label className="live-field">
            <span>Camera name</span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Dining Area Camera"
              minLength={2}
              maxLength={100}
              required
            />
          </label>

          <label className="live-field">
            <span>RTSP camera address</span>
            <input
              type="password"
              value={rtspUrl}
              onChange={(event) => setRtspUrl(event.target.value)}
              placeholder="rtsp://username:password@camera-ip:554/stream"
              required
            />
          </label>

          <button className="live-start-button" type="submit" disabled={busy}>
            <Plus size={15} />
            Register camera
          </button>
        </form>

        <p className="rtsp-security-note">
          Camera credentials are sent to the backend and encrypted before storage.
          They are not displayed after registration.
        </p>
      </section>

      <section className="panel rtsp-camera-panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">CCTV connection</div>
            <div className="panel-caption">
              Start or stop processing from a registered network camera.
            </div>
          </div>
          {running
            ? <Wifi size={19} color="#54845d" />
            : <WifiOff size={19} color="#829386" />}
        </div>

        <label className="live-field rtsp-select-field">
          <span>Registered IP camera</span>
          <select
            value={selectedId ?? ''}
            onChange={(event) => {
              setSelectedId(event.target.value ? Number(event.target.value) : null)
              setMessage('')
            }}
            disabled={busy}
          >
            <option value="">Select a CCTV / IP camera</option>
            {rtspSources.map((source) => (
              <option key={source.id} value={source.id}>
                {source.name} · #{source.id}
                {!source.is_active ? ' · Inactive' : ''}
              </option>
            ))}
          </select>
        </label>

        {isLoading && <p className="panel-caption">Loading camera sources...</p>}

        {!isLoading && rtspSources.length === 0 && (
          <p className="rtsp-empty">
            No IP cameras registered yet. Register a camera above to get started.
          </p>
        )}

        {selectedSource && (
          <div className="rtsp-status-card">
            <div>
              <span className="rtsp-status-label">Connection status</span>
              <strong className={`rtsp-status-value ${(status?.status || 'STOPPED').toLowerCase()}`}>
                {status?.status || 'CHECKING'}
              </strong>
            </div>
            <div>
              <span className="rtsp-status-label">Processed frames</span>
              <strong>{status?.processed_frames ?? 0}</strong>
            </div>
          </div>
        )}

        {status?.error && (
          <div className="rtsp-error">{status.error}</div>
        )}

        {message && (
          <div className="live-message" role="status">{message}</div>
        )}

        <div className="rtsp-actions">
          {running ? (
            <button
              className="live-stop-button"
              onClick={() => void handleStop()}
              disabled={busy || !selectedSource}
            >
              <Square size={14} />
              Stop processing
            </button>
          ) : (
            <button
              className="live-start-button"
              onClick={() => void handleStart()}
              disabled={busy || !selectedSource || !selectedSource.is_active}
            >
              <Play size={15} />
              Start IP camera
            </button>
          )}
        </div>
      </section>

      <section className="panel rtsp-preview-panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">CCTV camera snapshot</div>
            <div className="panel-caption">
              Latest frame received from the backend RTSP stream.
            </div>
          </div>
          <Camera size={19} color="#78917d" />
        </div>

        <div className="camera-preview rtsp-snapshot-preview" ref={setPreviewElement}>
          {frameReady ? (
            <img
              ref={imageRef}
              src={frameUrl!.url}
              alt="Latest CCTV camera frame"
            />
          ) : (
            <div className="camera-placeholder">
              <div className="camera-placeholder-icon"><Camera size={28} /></div>
              <strong>
                {status?.status === 'RUNNING'
                  ? 'Waiting for camera frame...'
                  : 'Start the IP camera to view a snapshot'}
              </strong>
              <span>Snapshots refresh while the RTSP camera is processing.</span>
            </div>
          )}
          <div className={`preview-indicator ${frameReady ? 'connected' : 'idle'}`}>
            {frameReady ? 'LATEST FRAME' : 'NO FRAME'}
          </div>
        </div>

        <TableZoneEditor
          videoRef={imageRef}
          previewElement={previewElement}
          tables={tables}
          cameraSourceId={selectedId}
          cameraActive={frameReady}
          zoneMode="camera"
        />
      </section>

      <section className="panel rtsp-information-panel">
        <div className="panel-title">How CCTV monitoring works</div>
        <p>
          RestroMind connects to the camera stream on the backend. Frames are
          processed by the existing AI vision pipeline and can update assigned
          table occupancy and monitoring events.
        </p>
        <p>
          The browser does not display the live RTSP video preview in this version.
          It displays the connection status and processing information instead.
        </p>
      </section>
    </div>
  )
}

export default RTSPCameraPanel
