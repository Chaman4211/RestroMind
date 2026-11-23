import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Check,
  CheckCircle2,
  Clock3,
  ClipboardList,
  RefreshCw,
  Sparkles,
  UserRound,
} from 'lucide-react'
import {
  assignAlertToStaff,
  confirmTableCleaning,
  getAlerts,
  getStaffMembers,
  type RestaurantAlert,
} from '../services/api'
import './CleaningTasks.css'

type TaskTab = 'pending' | 'completed'

function formatTaskTime(value: string | null): string {
  if (!value) return 'Time unavailable'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return 'Time unavailable'

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function TaskCard({
  alert,
  completed,
  confirming,
  assigning,
  staff,
  onConfirm,
  onAssign,
}: {
  alert: RestaurantAlert
  completed: boolean
  confirming: boolean
  assigning: boolean
  staff: { id: number; name: string; is_active: boolean }[]
  onConfirm: (tableId: number) => void
  onAssign: (alertId: number, staffId: number | null) => void
}) {
  return (
    <article className="cleaning-task-card">
      <div className="cleaning-task-icon">
        {completed ? <CheckCircle2 size={21} /> : <ClipboardList size={21} />}
      </div>

      <div className="cleaning-task-main">
        <div className="cleaning-task-title-row">
          <div>
            <h3>{alert.table_name}</h3>
            <p className="cleaning-task-table">Table {alert.table_number}</p>
          </div>

          <span className={`cleaning-task-status ${completed ? 'completed' : 'pending'}`}>
            {completed ? 'Completed' : 'Pending'}
          </span>
        </div>

        <p className="cleaning-task-description">{alert.message}</p>

        <div className="cleaning-task-time">
          <Clock3 size={14} />
          <span>
            {completed
              ? `Completed ${formatTaskTime(alert.resolved_at)}`
              : `Created ${formatTaskTime(alert.created_at)}`}
          </span>
        </div>

        <div className="cleaning-assignment">
          <UserRound size={15} />
          {completed ? (
            <span>
              {alert.assigned_staff_name
                ? `Assigned to ${alert.assigned_staff_name}`
                : 'No staff member assigned'}
            </span>
          ) : (
            <label>
              <span className="cleaning-assignment-label">Assign to:</span>
              <select
                value={alert.assigned_staff_id?.toString() ?? ''}
                disabled={assigning}
                onChange={(event) => {
                  const value = event.target.value
                  onAssign(alert.id, value ? Number(value) : null)
                }}
                aria-label={`Assign cleaning task for ${alert.table_name}`}
              >
                <option value="">Unassigned</option>
                {staff.map((member) => (
                  <option
                    key={member.id}
                    value={member.id}
                    disabled={!member.is_active}
                  >
                    {member.name}{member.is_active ? '' : ' (Inactive)'}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </div>

      {!completed && (
        <button
          className="cleaning-confirm-button"
          type="button"
          disabled={confirming}
          onClick={() => onConfirm(alert.table_id)}
        >
          <Check size={16} />
          {confirming ? 'Saving...' : 'Confirm cleaned'}
        </button>
      )}
    </article>
  )
}

export default function CleaningTasks() {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<TaskTab>('pending')
  const [message, setMessage] = useState('')

  const pendingQuery = useQuery({
    queryKey: ['alerts', 'OPEN'],
    queryFn: () => getAlerts('OPEN'),
    refetchInterval: 10000,
  })

  const completedQuery = useQuery({
    queryKey: ['alerts', 'RESOLVED'],
    queryFn: () => getAlerts('RESOLVED'),
    refetchInterval: 10000,
  })

  const staffQuery = useQuery({
    queryKey: ['staff'],
    queryFn: getStaffMembers,
  })

  const cleaningMutation = useMutation({
    mutationFn: confirmTableCleaning,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] }),
        queryClient.invalidateQueries({ queryKey: ['alerts'] }),
      ])
      setMessage('Cleaning confirmation saved successfully.')
      setActiveTab('completed')
    },
    onError: (error: Error) => {
      setMessage(error.message || 'Could not confirm cleaning.')
    },
  })

  const assignmentMutation = useMutation({
    mutationFn: ({
      alertId,
      staffId,
    }: {
      alertId: number
      staffId: number | null
    }) => assignAlertToStaff(alertId, staffId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['alerts'] }),
        queryClient.invalidateQueries({ queryKey: ['staff'] }),
      ])
      setMessage('Task assignment updated successfully.')
    },
    onError: (error: Error) => {
      setMessage(error.message || 'Could not update task assignment.')
    },
  })

  const pendingTasks = pendingQuery.data ?? []
  const completedTasks = completedQuery.data ?? []
  const staff = staffQuery.data ?? []
  const activeStaff = staff.filter((member) => member.is_active)
  const isLoading = pendingQuery.isLoading || completedQuery.isLoading
  const isError = pendingQuery.isError || completedQuery.isError
  const currentTasks = activeTab === 'pending' ? pendingTasks : completedTasks

  function refreshTasks() {
    void queryClient.invalidateQueries({ queryKey: ['alerts'] })
    void queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] })
    void queryClient.invalidateQueries({ queryKey: ['staff'] })
  }

  return (
    <main className="cleaning-workspace">
      <header className="cleaning-workspace-header">
        <div>
          <p className="cleaning-workspace-eyebrow">RESTAURANT OPERATIONS</p>
          <h1>Cleaning tasks</h1>
          <p>Track tables that need cleaning and review completed cleaning tasks.</p>
        </div>

        <button
          className="cleaning-refresh-button"
          type="button"
          onClick={refreshTasks}
          aria-label="Refresh cleaning tasks"
        >
          <RefreshCw size={17} />
          Refresh
        </button>
      </header>

      <section className="cleaning-summary-grid">
        <div className="cleaning-summary-card">
          <div className="cleaning-summary-icon pending-icon">
            <ClipboardList size={20} />
          </div>
          <div>
            <strong>{pendingTasks.length}</strong>
            <span>Pending tasks</span>
          </div>
        </div>

        <div className="cleaning-summary-card">
          <div className="cleaning-summary-icon completed-icon">
            <CheckCircle2 size={20} />
          </div>
          <div>
            <strong>{completedTasks.length}</strong>
            <span>Completed tasks</span>
          </div>
        </div>

        <div className="cleaning-summary-card">
          <div className="cleaning-summary-icon total-icon">
            <Sparkles size={20} />
          </div>
          <div>
            <strong>{pendingTasks.length + completedTasks.length}</strong>
            <span>Total cleaning alerts</span>
          </div>
        </div>
      </section>

      {message && (
        <div className="cleaning-message" role="status">
          <span>{message}</span>
          <button type="button" onClick={() => setMessage('')} aria-label="Dismiss message">
            ×
          </button>
        </div>
      )}

      <section className="cleaning-tasks-panel">
        <div className="cleaning-tasks-panel-heading">
          <div>
            <h2>Cleaning activity</h2>
            <p>Tasks generated from your restaurant table monitoring system.</p>
          </div>

          <div className="cleaning-tabs">
            <button
              type="button"
              className={activeTab === 'pending' ? 'active' : ''}
              onClick={() => setActiveTab('pending')}
            >
              Pending <span>{pendingTasks.length}</span>
            </button>
            <button
              type="button"
              className={activeTab === 'completed' ? 'active' : ''}
              onClick={() => setActiveTab('completed')}
            >
              Completed <span>{completedTasks.length}</span>
            </button>
          </div>
        </div>

        {isLoading && <p className="cleaning-query-message">Loading cleaning tasks...</p>}

        {isError && (
          <p className="cleaning-query-error">
            Could not load cleaning tasks. Please refresh and try again.
          </p>
        )}

        {staffQuery.isError && (
          <p className="cleaning-query-error">
            Staff list could not be loaded. Task assignment may not be available.
          </p>
        )}

        {!staffQuery.isLoading && !staffQuery.isError &&
          activeStaff.length === 0 && activeTab === 'pending' && (
            <p className="cleaning-query-message">
              Add active staff members in the Staff workspace to assign cleaning tasks.
            </p>
          )}

        {!isLoading && !isError && currentTasks.length === 0 && (
          <div className="cleaning-empty-state">
            <div className="cleaning-empty-icon">
              <CheckCircle2 size={25} />
            </div>
            <h3>{activeTab === 'pending' ? 'No pending cleaning tasks' : 'No completed tasks yet'}</h3>
            <p>
              {activeTab === 'pending'
                ? 'All your tables are up to date. New cleaning tasks will appear here when generated by camera monitoring.'
                : 'Cleaning tasks confirmed by staff will appear here.'}
            </p>
          </div>
        )}

        {!isLoading && !isError && currentTasks.length > 0 && (
          <div className="cleaning-task-list">
            {currentTasks.map((alert: RestaurantAlert) => (
              <TaskCard
                key={alert.id}
                alert={alert}
                completed={activeTab === 'completed'}
                staff={staff}
                confirming={
                  cleaningMutation.isPending &&
                  cleaningMutation.variables === alert.table_id
                }
                assigning={
                  assignmentMutation.isPending &&
                  assignmentMutation.variables?.alertId === alert.id
                }
                onConfirm={(tableId) => {
                  setMessage('')
                  cleaningMutation.mutate(tableId)
                }}
                onAssign={(alertId, staffId) => {
                  setMessage('')
                  assignmentMutation.mutate({ alertId, staffId })
                }}
              />
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
