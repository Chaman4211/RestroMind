import { useEffect, useMemo, useState } from 'react'
import type { MouseEvent, RefObject } from 'react'
import { createPortal } from 'react-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, Eraser, RotateCcw, Save } from 'lucide-react'
import {
  updateRestaurantTable,
  type RestaurantTable,
} from '../services/api'
import './TableZoneEditor.css'

type Point = {
  x: number
  y: number
}

type Props = {
  videoRef: RefObject<HTMLVideoElement | null>
  previewElement: HTMLDivElement | null
  tables: RestaurantTable[]
  cameraSourceId: number | null
  cameraActive: boolean
}

function readZonePoints(zone: unknown): Point[] {
  const raw =
    Array.isArray(zone)
      ? zone
      : zone && typeof zone === 'object' && 'points' in zone
        ? (zone as { points?: unknown }).points
        : null

  if (!Array.isArray(raw)) return []

  return raw.flatMap((point): Point[] => {
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

function TableZoneEditor({
  videoRef,
  previewElement,
  tables,
  cameraSourceId,
  cameraActive,
}: Props) {
  const queryClient = useQueryClient()
  const [selectedTableId, setSelectedTableId] = useState('')
  const [points, setPoints] = useState<Point[]>([])
  const [drawing, setDrawing] = useState(false)
  const [message, setMessage] = useState('')
  const [videoSize, setVideoSize] = useState({ width: 640, height: 480 })

  const availableTables = useMemo(
    () =>
      tables.filter(
        (table) =>
          table.camera_source_id === null ||
          table.camera_source_id === cameraSourceId,
      ),
    [tables, cameraSourceId],
  )

  const effectiveSelectedTableId = availableTables.some(
    (table) => String(table.id) === selectedTableId,
  )
    ? selectedTableId
    : availableTables.length > 0
      ? String(availableTables[0].id)
      : ''

  const selectedTable = availableTables.find(
    (table) => String(table.id) === effectiveSelectedTableId,
  )

  useEffect(() => {
    // Load the saved zone when the selected table changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPoints(readZonePoints(selectedTable?.zone_coordinates))
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDrawing(false)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMessage('')
  }, [selectedTable?.id, selectedTable?.zone_coordinates])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const updateSize = () => {
      if (video.videoWidth > 0 && video.videoHeight > 0) {
        setVideoSize({
          width: video.videoWidth,
          height: video.videoHeight,
        })
      }
    }

    video.addEventListener('loadedmetadata', updateSize)
    video.addEventListener('loadeddata', updateSize)
    updateSize()

    return () => {
      video.removeEventListener('loadedmetadata', updateSize)
      video.removeEventListener('loadeddata', updateSize)
    }
  }, [videoRef, cameraActive])

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!selectedTable || cameraSourceId === null) {
        throw new Error('Select a table and an active camera source first.')
      }

      if (points.length < 3) {
        throw new Error('A table zone needs at least three points.')
      }

      return updateRestaurantTable(selectedTable.id, {
        zone_coordinates: points.map((point) => [point.x, point.y]),
        camera_source_id: cameraSourceId,
      })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] })
      setDrawing(false)
      setMessage('Table zone saved successfully.')
    },
    onError: (error) => {
      setMessage(
        error instanceof Error ? error.message : 'Could not save the table zone.',
      )
    },
  })

  const handleOverlayClick = (event: MouseEvent<SVGSVGElement>) => {
    if (!drawing || !cameraActive) return

    const rect = event.currentTarget.getBoundingClientRect()
    const videoAspect = videoSize.width / videoSize.height
    const containerAspect = rect.width / rect.height

    let contentWidth = rect.width
    let contentHeight = rect.height
    let offsetX = 0
    let offsetY = 0

    if (containerAspect > videoAspect) {
      contentWidth = rect.height * videoAspect
      offsetX = (rect.width - contentWidth) / 2
    } else {
      contentHeight = rect.width / videoAspect
      offsetY = (rect.height - contentHeight) / 2
    }

    const x = (event.clientX - rect.left - offsetX) / contentWidth
    const y = (event.clientY - rect.top - offsetY) / contentHeight

    if (x < 0 || x > 1 || y < 0 || y > 1) return

    setPoints((current) => [
      ...current,
      {
        x: Number(x.toFixed(5)),
        y: Number(y.toFixed(5)),
      },
    ])
    setMessage('')
  }

  const startDrawing = () => {
    setPoints([])
    setDrawing(true)
    setMessage('Click around the table to mark its boundary. Add at least three points.')
  }

  const overlay =
    previewElement && cameraActive
      ? createPortal(
          <svg
            className={`zone-overlay ${drawing ? 'drawing' : ''}`}
            viewBox={`0 0 ${videoSize.width} ${videoSize.height}`}
            preserveAspectRatio="xMidYMid meet"
            onClick={handleOverlayClick}
            aria-label="Table zone drawing overlay"
          >
            {points.length >= 3 && (
              <polygon
                points={points
                  .map(
                    (point) =>
                      `${point.x * videoSize.width},${point.y * videoSize.height}`,
                  )
                  .join(' ')}
                className="zone-polygon"
              />
            )}

            {points.length > 0 && (
              <polyline
                points={points
                  .map(
                    (point) =>
                      `${point.x * videoSize.width},${point.y * videoSize.height}`,
                  )
                  .join(' ')}
                className="zone-line"
              />
            )}

            {points.map((point, index) => (
              <circle
                key={`${index}-${point.x}-${point.y}`}
                cx={point.x * videoSize.width}
                cy={point.y * videoSize.height}
                r={Math.max(5, videoSize.width / 150)}
                className="zone-point"
              />
            ))}
          </svg>,
          previewElement,
        )
      : null

  return (
    <>
      {overlay}

      <div className="zone-editor-panel">
        <div className="zone-editor-heading">
          <div>
            <div className="zone-editor-title">Table zone setup</div>
            <p>
              Select a table and mark its boundary on the camera preview.
            </p>
          </div>
          <span className="zone-point-count">{points.length} points</span>
        </div>

        <label className="zone-editor-field">
          <span>Restaurant table</span>
          <select
            value={effectiveSelectedTableId}
            onChange={(event) => setSelectedTableId(event.target.value)}
            disabled={drawing || saveMutation.isPending}
          >
            {availableTables.length === 0 && (
              <option value="">No tables available for this camera</option>
            )}
            {availableTables.map((table) => (
              <option key={table.id} value={table.id}>
                {table.table_number} · {table.name}
              </option>
            ))}
          </select>
        </label>

        <div className="zone-editor-actions">
          {!drawing ? (
            <button
              type="button"
              className="zone-primary-button"
              onClick={startDrawing}
              disabled={!cameraActive || !selectedTable || saveMutation.isPending}
            >
              <Check size={15} />
              {points.length >= 3 ? 'Redraw zone' : 'Draw zone'}
            </button>
          ) : (
            <>
              <button
                type="button"
                className="zone-secondary-button"
                onClick={() => setPoints((current) => current.slice(0, -1))}
                disabled={points.length === 0}
              >
                <RotateCcw size={14} />
                Undo
              </button>
              <button
                type="button"
                className="zone-secondary-button"
                onClick={() => setPoints([])}
                disabled={points.length === 0}
              >
                <Eraser size={14} />
                Clear
              </button>
              <button
                type="button"
                className="zone-primary-button"
                onClick={() => setDrawing(false)}
              >
                Finish drawing
              </button>
            </>
          )}

          {!drawing && (
            <button
              type="button"
              className="zone-save-button"
              onClick={() => saveMutation.mutate()}
              disabled={
                points.length < 3 ||
                !selectedTable ||
                cameraSourceId === null ||
                saveMutation.isPending
              }
            >
              <Save size={14} />
              {saveMutation.isPending ? 'Saving...' : 'Save zone'}
            </button>
          )}
        </div>

        <div className="zone-editor-hint">
          {!cameraActive
            ? 'Load a live camera or video preview before drawing table zones.'
            : drawing
              ? 'Click at least three points around the table. Finish drawing when ready.'
              : 'The green outline shows the selected table zone. You can redraw it at any time.'}
        </div>

        {message && (
          <div
            className={`zone-editor-message ${
              message.includes('successfully') ? 'success' : ''
            }`}
            role="status"
          >
            {message}
          </div>
        )}
      </div>
    </>
  )
}

export default TableZoneEditor
