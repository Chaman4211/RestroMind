import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  Circle,
  MonitorPlay,
  Users,
  Wifi,
  WifiOff,
} from 'lucide-react'
import {
  getCameraSources,
  getRestaurantTables,
  type CameraSource,
  type RestaurantTable,
} from '../services/api'
import TableZoneEditor from './TableZoneEditor'
import './LiveMonitoring.css'

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'disconnected'

type ProcessedTable = {
  table_id: number
  occupied: boolean
  person_count: number
  track_ids: number[]
  status: string
  events: unknown[]
}

type FrameResult = {
  camera_source_id: number
  people_detected: number
  table_count: number
  assignments: Record<string, number[]>
  tables: ProcessedTable[]
}

function LiveMonitoring() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [previewElement, setPreviewElement] = useState<HTMLDivElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<number | null>(null)
  const awaitingFrameRef = useRef(false)

  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [selectedDevice, setSelectedDevice] = useState('')
  const [selectedSource, setSelectedSource] = useState('')
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [connection, setConnection] = useState<ConnectionStatus>('idle')
  const [message, setMessage] = useState('')
  const [latestResult, setLatestResult] = useState<FrameResult | null>(null)
  const [lastFrameTime, setLastFrameTime] = useState('')
  const [mirrorCamera, setMirrorCamera] = useState(false)

  const {
    data: cameraSources = [],
    isLoading: camerasLoading,
    isError: camerasError,
  } = useQuery({
    queryKey: ['camera-sources'],
    queryFn: getCameraSources,
  })

  const {
    data: tables = [],
    isLoading: tablesLoading,
  } = useQuery({
    queryKey: ['restaurant-tables'],
    queryFn: getRestaurantTables,
  })

  const liveSources = cameraSources.filter(
    (source: CameraSource) => source.source_type === 'LIVE' && source.is_active,
  )

  const configuredTables = tables.filter(
    (table: RestaurantTable) =>
      table.zone_coordinates !== null && table.camera_source_id !== null,
  )

  const activeSelectedSource = liveSources.some(
    (source) => String(source.id) === selectedSource,
  )
    ? selectedSource
    : liveSources.length > 0
      ? String(liveSources[0].id)
      : ''

  useEffect(() => {
    let mounted = true

    const loadDevices = async () => {
      if (!navigator.mediaDevices?.enumerateDevices) {
        setMessage('This browser does not support camera access.')
        return
      }

      try {
        const availableDevices = await navigator.mediaDevices.enumerateDevices()
        if (!mounted) return

        const videoDevices = availableDevices.filter(
          (device) => device.kind === 'videoinput',
        )

        setDevices(videoDevices)

        if (!selectedDevice && videoDevices.length > 0) {
          setSelectedDevice(videoDevices[0].deviceId)
        }
      } catch {
        if (mounted) setMessage('Could not list available cameras.')
      }
    }

    void loadDevices()
    navigator.mediaDevices?.addEventListener('devicechange', loadDevices)

    return () => {
      mounted = false
      navigator.mediaDevices?.removeEventListener('devicechange', loadDevices)
    }
  }, [selectedDevice])

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream
      void videoRef.current.play().catch(() => {
        setMessage('Camera preview could not start. Check browser permissions.')
      })
    }
  }, [stream])

  const stopCamera = () => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    awaitingFrameRef.current = false

    if (socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }

    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setStream(null)
    setConnection('idle')
    setLatestResult(null)
    setLastFrameTime('')
  }

  useEffect(() => {
    return () => {
      if (intervalRef.current !== null) {
        window.clearInterval(intervalRef.current)
      }

      socketRef.current?.close()
      streamRef.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])

  const startCamera = async () => {
    setMessage('')
    setLatestResult(null)

    if (!activeSelectedSource) {
      setMessage('Please select an active LIVE camera source first.')
      return
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setMessage('Camera access requires HTTPS or localhost in a supported browser.')
      return
    }

    setConnection('connecting')

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: selectedDevice
          ? {
              deviceId: { exact: selectedDevice },
              width: { ideal: 640 },
              height: { ideal: 480 },
            }
          : {
              width: { ideal: 640 },
              height: { ideal: 480 },
            },
      })

      const availableDevices = await navigator.mediaDevices.enumerateDevices()
      const videoDevices = availableDevices.filter(
        (device) => device.kind === 'videoinput',
      )
      setDevices(videoDevices)

      const activeDeviceId = mediaStream.getVideoTracks()[0]?.getSettings().deviceId
      if (activeDeviceId) setSelectedDevice(activeDeviceId)

      streamRef.current = mediaStream
      setStream(mediaStream)

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const socketUrl =
        `${protocol}//${window.location.host}/api/v1/camera-sources/${activeSelectedSource}/stream`

      const socket = new WebSocket(socketUrl)
      socket.binaryType = 'arraybuffer'
      socketRef.current = socket

      socket.onopen = () => {
        setConnection('connected')
        setMessage('Camera connected. Waiting for the first processed frame.')

        intervalRef.current = window.setInterval(() => {
          const video = videoRef.current
          const canvas = canvasRef.current

          if (
            !video ||
            !canvas ||
            video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
            socket.readyState !== WebSocket.OPEN ||
            awaitingFrameRef.current
          ) {
            return
          }

          const scale = Math.min(1, 640 / video.videoWidth)
          canvas.width = Math.round(video.videoWidth * scale)
          canvas.height = Math.round(video.videoHeight * scale)

          const context = canvas.getContext('2d')
          if (!context) return

          context.setTransform(
            mirrorCamera ? -1 : 1,
            0,
            0,
            1,
            mirrorCamera ? canvas.width : 0,
            0,
          )
          context.drawImage(video, 0, 0, canvas.width, canvas.height)
          context.setTransform(1, 0, 0, 1, 0, 0)
          awaitingFrameRef.current = true

          canvas.toBlob(
            (blob) => {
              if (!blob || socket.readyState !== WebSocket.OPEN) {
                awaitingFrameRef.current = false
                return
              }

              socket.send(blob)
            },
            'image/jpeg',
            0.75,
          )
        }, 1200)
      }

      socket.onmessage = (event: MessageEvent<string>) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'connected') {
            setMessage(data.message || 'Live camera connected.')
          }

          if (data.type === 'frame_processed') {
            awaitingFrameRef.current = false
            setLatestResult(data.result as FrameResult)
            setLastFrameTime(new Date().toLocaleTimeString())
            setMessage('')
          }

          if (data.type === 'error') {
            awaitingFrameRef.current = false
            setMessage(data.message || 'The server rejected a camera frame.')
          }
        } catch {
          awaitingFrameRef.current = false
          setMessage('Received an unreadable response from the server.')
        }
      }

      socket.onerror = () => {
        awaitingFrameRef.current = false
        setMessage('WebSocket connection failed. Check that the backend is running.')
        setConnection('disconnected')
      }

      socket.onclose = (event) => {
        if (intervalRef.current !== null) {
          window.clearInterval(intervalRef.current)
          intervalRef.current = null
        }

        awaitingFrameRef.current = false
        setConnection('disconnected')

        if (event.code !== 1000) {
          setMessage(event.reason || 'The camera connection was closed by the server.')
        }
      }
    } catch (error) {
      stopCamera()
      setConnection('disconnected')
      setMessage(
        error instanceof Error
          ? error.message
          : 'Could not start the browser camera.',
      )
    }
  }

  const connectionLabel: Record<ConnectionStatus, string> = {
    idle: 'Not connected',
    connecting: 'Connecting',
    connected: 'Live connection',
    disconnected: 'Disconnected',
  }

  return (
    <div className="content live-monitoring">
      <div className="live-heading">
        <div>
          <div className="eyebrow">CAMERA INTELLIGENCE</div>
          <h1 className="page-title">Live monitoring</h1>
          <p className="page-subtitle">
            Monitor people and table activity using your connected camera.
          </p>
        </div>
        <div className={`live-status ${connection}`}>
            {connection === 'connected' ? <Wifi size={14} /> : <WifiOff size={14} />}
            {connectionLabel[connection]}
          </div>
      </div>

      <>
      {message && (
        <div className="live-message" role="status">
          <AlertCircle size={16} />
          <span>{message}</span>
        </div>
      )}

      <div className="live-layout">
        <section className="panel live-camera-panel">
          <div className="panel-header">
            <div>
              <div className="panel-title">Camera preview</div>
              <div className="panel-caption">
                Browser camera frames are processed locally by the RestroMind backend.
              </div>
            </div>
            <div className="camera-preview-actions">
              <button
                type="button"
                className={`camera-mirror-toggle ${mirrorCamera ? 'active' : ''}`}
                aria-pressed={mirrorCamera}
                onClick={() => setMirrorCamera((current) => !current)}
              >
                {mirrorCamera ? 'Mirror on' : 'Mirror off'}
              </button>
              <MonitorPlay size={18} color="#78917d" />
            </div>
          </div>

          <div className="camera-preview" ref={setPreviewElement}>
            {stream ? (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={mirrorCamera ? 'mirrored' : ''}
              />
            ) : (
              <div className="camera-placeholder">
                <div className="camera-placeholder-icon"><Camera size={28} /></div>
                <strong>Your camera preview will appear here</strong>
                <span>Select a camera and start monitoring.</span>
              </div>
            )}
            <div className={`preview-indicator ${connection}`}>
              <Circle size={8} fill="currentColor" />
              {connection === 'connected' ? 'PROCESSING' : 'CAMERA PREVIEW'}
            </div>
          </div>

          <canvas ref={canvasRef} className="live-hidden-canvas" />
          <TableZoneEditor
            videoRef={videoRef}
            previewElement={previewElement}
            tables={tables}
            cameraSourceId={activeSelectedSource ? Number(activeSelectedSource) : null}
            cameraActive={stream !== null && connection === 'connected'}
          />

          <div className="camera-controls">
            <label className="live-field">
              <span>Registered camera source</span>
              <select
                value={activeSelectedSource}
                onChange={(event) => setSelectedSource(event.target.value)}
                disabled={connection === 'connected' || connection === 'connecting'}
              >
                <option value="">Select a LIVE source</option>
                {liveSources.map((source) => (
                  <option key={source.id} value={source.id}>
                    {source.name} · #{source.id}
                  </option>
                ))}
              </select>
            </label>

            <label className="live-field">
              <span>Browser camera</span>
              <select
                value={selectedDevice}
                onChange={(event) => setSelectedDevice(event.target.value)}
                disabled={connection === 'connected' || connection === 'connecting'}
              >
                {devices.length === 0 && <option value="">No camera found</option>}
                {devices.map((device, index) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Camera ${index + 1}`}
                  </option>
                ))}
              </select>
            </label>

            {connection === 'connected' || connection === 'connecting' ? (
              <button className="live-stop-button" onClick={stopCamera}>
                Stop monitoring
              </button>
            ) : (
              <button
                className="live-start-button"
                onClick={() => void startCamera()}
                disabled={!activeSelectedSource || camerasLoading}
              >
                <Camera size={15} />
                Start camera
              </button>
            )}
          </div>
        </section>

        <div className="live-side-column">
          <section className="panel live-metric-panel">
            <div className="panel-title">Detection results</div>
            <div className="live-detection-number">
              <Users size={20} />
              <strong>{latestResult?.people_detected ?? '—'}</strong>
            </div>
            <div className="panel-caption">People detected in the latest processed frame</div>
            <div className="live-metric-divider" />
            <div className="live-small-metrics">
              <div>
                <span>Configured tables</span>
                <strong>{latestResult?.table_count ?? configuredTables.length}</strong>
              </div>
              <div>
                <span>Last processed</span>
                <strong>{lastFrameTime || '—'}</strong>
              </div>
            </div>
          </section>

          <section className="panel live-source-panel">
            <div className="panel-header">
              <div>
                <div className="panel-title">Camera sources</div>
                <div className="panel-caption">Available monitoring devices</div>
              </div>
              <Camera size={17} color="#829386" />
            </div>
            {camerasLoading ? (
              <p className="panel-caption">Loading camera sources...</p>
            ) : camerasError ? (
              <p className="panel-caption">Could not load camera sources.</p>
            ) : liveSources.length === 0 ? (
              <p className="panel-caption">No active LIVE camera sources found.</p>
            ) : (
              liveSources.map((source) => (
                <div className="live-source-item" key={source.id}>
                  <div className="live-source-icon"><Camera size={15} /></div>
                  <div>
                    <strong>{source.name}</strong>
                    <span>Source #{source.id} · Active</span>
                  </div>
                  <CheckCircle2 size={15} color="#6b9a70" />
                </div>
              ))
            )}
          </section>
        </div>
      </div>

      <section className="panel live-tables-panel">
        <div className="panel-header">
          <div>
            <div className="panel-title">Table monitoring</div>
            <div className="panel-caption">
              Tables assigned to camera sources and their zone configuration.
            </div>
          </div>
          <span className="live-table-count">{tables.length} registered</span>
        </div>

        {tablesLoading ? (
          <p className="panel-caption">Loading restaurant tables...</p>
        ) : tables.length === 0 ? (
          <p className="panel-caption">No restaurant tables are registered yet.</p>
        ) : (
          <div className="live-table-grid">
            {tables.map((table) => {
              const result = latestResult?.tables.find(
                (item) => item.table_id === table.id,
              )
              const hasZone = table.zone_coordinates !== null

              return (
                <div className="live-table-item" key={table.id}>
                  <div className="live-table-top">
                    <strong>{table.table_number}</strong>
                    <span className={`zone-tag ${hasZone ? 'configured' : 'missing'}`}>
                      {hasZone ? 'Zone configured' : 'Zone required'}
                    </span>
                  </div>
                  <span className="live-table-name">{table.name}</span>
                  <div className="live-table-bottom">
                    <span>
                      {result
                        ? `${result.person_count} people detected`
                        : 'Waiting for detection'}
                    </span>
                    <span className="live-table-status">{table.status.replace('_', ' ')}</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {configuredTables.length === 0 && tables.length > 0 && (
          <div className="zone-notice">
            <AlertCircle size={16} />
            <span>
              Table zones are not configured yet. Person detection can run, but
              table occupancy will not update until each table has a polygon zone.
            </span>
          </div>
        )}
      </section>

      <div className="live-footer-note">
        <Wifi size={14} />
        Frame processing runs one frame at a time to avoid overloading the local CPU.
      </div>
      </>
    </div>
  )
}

export default LiveMonitoring
