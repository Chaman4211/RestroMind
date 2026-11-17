import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Check, Pencil, Plus, RefreshCw, Trash2, X } from 'lucide-react'
import {
  createRestaurantTable,
  deleteRestaurantTable,
  getCameraSources,
  getRestaurantTables,
  updateRestaurantTable,
  type RestaurantTable,
} from '../services/api'
import './TableManagement.css'

function hasZone(zone: RestaurantTable['zone_coordinates']): boolean {
  if (Array.isArray(zone)) return zone.length >= 3

  if (zone && typeof zone === 'object' && 'points' in zone) {
    const points = zone.points
    return Array.isArray(points) && points.length >= 3
  }

  return false
}

const statusLabels: Record<RestaurantTable['status'], string> = {
  FREE: 'Available',
  OCCUPIED: 'Occupied',
  NEEDS_CLEANING: 'Needs cleaning',
}

export default function TableManagement() {
  const queryClient = useQueryClient()
  const [tableNumber, setTableNumber] = useState('')
  const [tableName, setTableName] = useState('')
  const [newCameraId, setNewCameraId] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editCameraId, setEditCameraId] = useState('')
  const [message, setMessage] = useState('')

  const tablesQuery = useQuery({
    queryKey: ['restaurant-tables'],
    queryFn: getRestaurantTables,
  })

  const camerasQuery = useQuery({
    queryKey: ['camera-sources'],
    queryFn: getCameraSources,
  })

  const tables = tablesQuery.data ?? []
  const cameras = camerasQuery.data ?? []
  const activeCameras = cameras.filter((camera) => camera.is_active)

  const refreshTables = () =>
    queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] })

  const createMutation = useMutation({
    mutationFn: createRestaurantTable,
    onSuccess: async () => {
      setTableNumber('')
      setTableName('')
      setNewCameraId('')
      setMessage('Table added successfully.')
      await refreshTables()
    },
    onError: (error: Error) => setMessage(error.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      name,
      cameraId,
    }: {
      id: number
      name: string
      cameraId: string
    }) =>
      updateRestaurantTable(id, {
        name: name.trim(),
        camera_source_id: cameraId ? Number(cameraId) : null,
      }),
    onSuccess: async () => {
      setEditingId(null)
      setMessage('Table updated successfully.')
      await refreshTables()
    },
    onError: (error: Error) => setMessage(error.message),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteRestaurantTable,
    onSuccess: async () => {
      setMessage('Table deleted successfully.')
      await refreshTables()
    },
    onError: (error: Error) => setMessage(error.message),
  })

  function startEditing(table: RestaurantTable) {
    setEditingId(table.id)
    setEditName(table.name)
    setEditCameraId(table.camera_source_id?.toString() ?? '')
    setMessage('')
  }

  function saveEdit(id: number) {
    if (editName.trim().length < 2) {
      setMessage('Table name must contain at least 2 characters.')
      return
    }

    updateMutation.mutate({ id, name: editName, cameraId: editCameraId })
  }

  function removeTable(table: RestaurantTable) {
    const confirmed = window.confirm(
      `Delete ${table.name} (Table ${table.table_number})?`,
    )

    if (confirmed) {
      setMessage('')
      deleteMutation.mutate(table.id)
    }
  }

  return (
    <main className="table-management">
      <header className="table-management-header">
        <div>
          <p className="table-management-eyebrow">RESTAURANT SETUP</p>
          <h1>Table management</h1>
          <p>Manage your restaurant tables, camera assignments, and monitoring zones.</p>
        </div>
        <div className="table-total">
          <strong>{tables.length}</strong>
          <span>Total tables</span>
        </div>
      </header>

      <section className="table-management-panel">
        <div className="table-panel-heading">
          <div>
            <h2><Plus size={19} /> Add a table</h2>
            <p>Create a table and optionally assign an active camera.</p>
          </div>
        </div>

        <form
          className="add-table-form"
          onSubmit={(event) => {
            event.preventDefault()
            setMessage('')
            createMutation.mutate({
              table_number: tableNumber.trim(),
              name: tableName.trim(),
              camera_source_id: newCameraId ? Number(newCameraId) : null,
            })
          }}
        >
          <label>
            Table number
            <input
              value={tableNumber}
              onChange={(event) => setTableNumber(event.target.value)}
              placeholder="e.g. 07"
              maxLength={30}
              required
            />
          </label>

          <label>
            Table name
            <input
              value={tableName}
              onChange={(event) => setTableName(event.target.value)}
              placeholder="e.g. Window table"
              minLength={2}
              maxLength={100}
              required
            />
          </label>

          <label>
            Camera assignment
            <select
              value={newCameraId}
              onChange={(event) => setNewCameraId(event.target.value)}
            >
              <option value="">No camera assigned</option>
              {activeCameras.map((camera) => (
                <option key={camera.id} value={camera.id}>{camera.name}</option>
              ))}
            </select>
          </label>

          <button type="submit" disabled={createMutation.isPending}>
            <Plus size={17} />
            {createMutation.isPending ? 'Adding...' : 'Add table'}
          </button>
        </form>
      </section>

      {message && (
        <div className="table-management-message" role="status">
          <AlertCircle size={17} />
          <span>{message}</span>
          <button type="button" onClick={() => setMessage('')} aria-label="Dismiss message">
            <X size={16} />
          </button>
        </div>
      )}

      <section className="table-management-panel">
        <div className="table-panel-heading">
          <div>
            <h2>Restaurant tables</h2>
            <p>Your existing tables and their current monitoring setup.</p>
          </div>
          <button
            className="table-refresh-button"
            type="button"
            onClick={() => {
              void refreshTables()
              void queryClient.invalidateQueries({ queryKey: ['camera-sources'] })
            }}
            aria-label="Refresh tables"
          >
            <RefreshCw size={17} />
          </button>
        </div>

        {tablesQuery.isLoading && <p className="table-query-message">Loading tables...</p>}

        {tablesQuery.isError && (
          <p className="table-query-error">
            Could not load tables: {(tablesQuery.error as Error).message}
          </p>
        )}

        {!tablesQuery.isLoading && !tablesQuery.isError && tables.length === 0 && (
          <div className="table-empty-state">
            <p>No tables have been added yet.</p>
            <span>Use the form above to add your first table.</span>
          </div>
        )}

        <div className="managed-table-list">
          {tables.map((table) => {
            const camera = cameras.find((item) => item.id === table.camera_source_id)
            const zoneConfigured = hasZone(table.zone_coordinates)
            const isEditing = editingId === table.id

            return (
              <article className="managed-table-row" key={table.id}>
                <div className="managed-table-main">
                  <div className="managed-table-number">{table.table_number}</div>
                  <div className="managed-table-details">
                    {isEditing ? (
                      <input
                        className="managed-table-edit-name"
                        value={editName}
                        onChange={(event) => setEditName(event.target.value)}
                        minLength={2}
                        maxLength={100}
                        aria-label="Table name"
                      />
                    ) : (
                      <h3>{table.name}</h3>
                    )}
                    <span className={`table-status table-status-${table.status.toLowerCase()}`}>
                      <span />
                      {statusLabels[table.status]}
                    </span>
                  </div>
                </div>

                <div className="managed-table-info">
                  <span className="managed-table-info-label">Camera</span>
                  {isEditing ? (
                    <select
                      value={editCameraId}
                      onChange={(event) => setEditCameraId(event.target.value)}
                      aria-label="Camera assignment"
                    >
                      <option value="">No camera assigned</option>
                      {activeCameras.map((item) => (
                        <option key={item.id} value={item.id}>{item.name}</option>
                      ))}
                    </select>
                  ) : (
                    <span>{camera?.name ?? 'Not assigned'}</span>
                  )}
                </div>

                <div className="managed-table-info">
                  <span className="managed-table-info-label">Monitoring zone</span>
                  <span className={zoneConfigured ? 'zone-configured' : 'zone-missing'}>
                    {zoneConfigured ? <Check size={15} /> : <AlertCircle size={15} />}
                    {zoneConfigured ? 'Configured' : 'Not configured'}
                  </span>
                </div>

                <div className="managed-table-actions">
                  {isEditing ? (
                    <>
                      <button
                        type="button"
                        className="table-action-save"
                        onClick={() => saveEdit(table.id)}
                        disabled={updateMutation.isPending}
                        aria-label="Save table changes"
                      >
                        <Check size={17} />
                      </button>
                      <button
                        type="button"
                        className="table-action-cancel"
                        onClick={() => setEditingId(null)}
                        aria-label="Cancel editing"
                      >
                        <X size={17} />
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => startEditing(table)}
                        aria-label={`Edit ${table.name}`}
                      >
                        <Pencil size={17} />
                      </button>
                      <button
                        type="button"
                        className="table-action-delete"
                        onClick={() => removeTable(table)}
                        disabled={deleteMutation.isPending}
                        aria-label={`Delete ${table.name}`}
                      >
                        <Trash2 size={17} />
                      </button>
                    </>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <p className="table-management-tip">
        To draw or adjust a monitoring zone, open <strong>Live monitoring</strong> or
        <strong> Upload video</strong> and use the existing zone editor.
      </p>
    </main>
  )
}
