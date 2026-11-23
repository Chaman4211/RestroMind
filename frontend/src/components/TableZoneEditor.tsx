import { useEffect, useMemo, useState } from 'react'
import type { MouseEvent, RefObject } from 'react'
import { createPortal } from 'react-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, Eraser, RotateCcw, Save, Trash2 } from 'lucide-react'
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
  videoRef: RefObject<HTMLVideoElement | HTMLImageElement | null>
  previewElement: HTMLDivElement | null
  tables: RestaurantTable[]
  cameraSourceId: number | null
  cameraActive: boolean
  zoneMode?: 'camera' | 'upload'
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
  zoneMode = 'camera',
}: Props) {
  const queryClient = useQueryClient()
  const [selectedTableId, setSelectedTableId] = useState('')
  const [points, setPoints] = useState<Point[]>([])
  const [drawing, setDrawing] = useState(false)
  const [message, setMessage] = useState('')
  const [videoSize, setVideoSize] = useState({ width: 640, height: 480 })

  const availableTables = useMemo(
    () =>
      zoneMode === 'upload'
        ? tables
        : tables.filter(
            (table) =>
              table.camera_source_id === null ||
              table.camera_source_id === cameraSourceId,
          ),
    [tables, cameraSourceId, zoneMode],
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

  const selectedZone =
    zoneMode === 'upload'
      ? selectedTable?.upload_zone_coordinates
      : selectedTable?.zone_coordinates

  const hasSavedZone = readZonePoints(selectedZone).length >= 3

  useEffect(() => {
    // Load the saved zone when the selected table or zone mode changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPoints(readZonePoints(selectedZone))
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDrawing(false)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMessage('')
  }, [selectedTable?.id, selectedZone])

  useEffect(() => {
    const media = videoRef.current
    if (!media) return

    const updateSize = () => {
      const width =
        media instanceof HTMLVideoElement ? media.videoWidth : media.naturalWidth
      const height =
        media instanceof HTMLVideoElement ? media.videoHeight : media.naturalHeight

      if (width > 0 && height > 0) {
        setVideoSize({ width, height })
      }
    }

    if (media instanceof HTMLVideoElement) {
      media.addEventListener('loadedmetadata', updateSize)
      media.addEventListener('loadeddata', updateSize)
    } else {
      media.addEventListener('load', updateSize)
    }

    updateSize()

    return () => {
      media.removeEventListener('loadedmetadata', updateSize)
      media.removeEventListener('loadeddata', updateSize)
      media.removeEventListener('load', updateSize)
    }
  }, [videoRef, cameraActive])

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!selectedTable) {
        throw new Error('Select a table first.')
      }

      if (zoneMode === 'camera' && cameraSourceId === null) {
        throw new Error('Select an active camera source first.')
      }

      if (points.length < 3) {
        throw new Error('A table zone needs at least three points.')
      }

      const coordinates = points.map((point) => [point.x, point.y])

      return zoneMode === 'upload'
        ? updateRestaurantTable(selectedTable.id, {
            upload_zone_coordinates: coordinates,
            upload_camera_source_id: cameraSourceId,
          })
        : updateRestaurantTable(selectedTable.id, {
            zone_coordinates: coordinates,
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

  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!selectedTable) {
        throw new Error('Select a table first.')
      }

      return zoneMode === 'upload'
        ? updateRestaurantTable(selectedTable.id, {
            upload_zone_coordinates: null,
            upload_camera_source_id: null,
          })
        : updateRestaurantTable(selectedTable.id, {
            zone_coordinates: null,
          })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] })
      setPoints([])
      setDrawing(false)
      setMessage('Saved table zone deleted. The table was kept.')
    },
    onError: (error) => {
      setMessage(
        error instanceof Error ? error.message : 'Could not delete the table zone.',
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
            aria-label="All saved table zones and zone drawing overlay"
          >
            {availableTables.map((table) => {
              const isSelected = table.id === selectedTable?.id
              const savedPoints = readZonePoints(
                zoneMode === 'upload'
                  ? table.upload_zone_coordinates
                  : table.zone_coordinates,
              )
              const zonePoints =
                isSelected && (!drawing || points.length >= 3)
                  ? points
                  : savedPoints

              if (zonePoints.length < 3) return null

              const polygonPoints = zonePoints
                .map(
                  (point) =>
                    `${point.x * videoSize.width},${point.y * videoSize.height}`,
                )
                .join(' ')

              const labelPoint = zonePoints[0]

              return (
                <g key={table.id}>
                  <polygon
                    points={polygonPoints}
                    className={
                      isSelected
                        ? 'zone-polygon zone-polygon-selected'
                        : 'zone-polygon zone-polygon-other'
                    }
                  />
                  <text
                    x={labelPoint.x * videoSize.width}
                    y={labelPoint.y * videoSize.height - 10}
                    className={
                      isSelected
                        ? 'zone-label zone-label-selected'
                        : 'zone-label'
                    }
                  >
                    {table.table_number}
                  </text>
                </g>
              )
            })}

            {drawing && points.length > 0 && (
              <>
                <polyline
                  points={points
                    .map(
                      (point) =>
                        `${point.x * videoSize.width},${point.y * videoSize.height}`,
                    )
                    .join(' ')}
                  className="zone-line"
                />
                {points.map((point, index) => (
                  <circle
                    key={`${index}-${point.x}-${point.y}`}
                    cx={point.x * videoSize.width}
                    cy={point.y * videoSize.height}
                    r={Math.max(5, videoSize.width / 150)}
                    className="zone-point"
                  />
                ))}
              </>
            )}
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

          {!drawing && hasSavedZone && (
            <button
              type="button"
              className="zone-delete-button"
              onClick={() => {
                if (window.confirm(`Delete the saved zone for ${selectedTable?.table_number}?`)) {
                  deleteMutation.mutate()
                }
              }}
              disabled={deleteMutation.isPending || saveMutation.isPending}
            >
              <Trash2 size={14} />
              {deleteMutation.isPending ? 'Deleting...' : 'Delete zone'}
            </button>
          )}

          {!drawing && (
            <button
              type="button"
              className="zone-save-button"
              onClick={() => saveMutation.mutate()}
              disabled={
                points.length < 3 ||
                !selectedTable ||
                (zoneMode === 'camera' && cameraSourceId === null) ||
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
              : "All saved table zones are visible. The highlighted outline is selected; redraw or delete only this zone."}
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
