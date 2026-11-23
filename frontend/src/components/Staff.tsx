import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Check,
  ClipboardList,
  Edit2,
  Mail,
  Phone,
  Plus,
  RefreshCw,
  Trash2,
  UserRound,
  Users,
  X,
} from 'lucide-react'
import {
  createStaffMember,
  deleteStaffMember,
  getAlerts,
  getStaffMembers,
  updateStaffMember,
  type StaffRole,
  type StaffUser,
} from '../services/api'
import './Staff.css'

const roleLabels: Record<StaffRole, string> = {
  OWNER: 'Owner',
  MANAGER: 'Manager',
  ASSISTANT_MANAGER: 'Assistant Manager',
  SUPERVISOR: 'Supervisor',
  HEAD_CHEF: 'Head Chef',
  SOUS_CHEF: 'Sous Chef',
  CHEF: 'Chef / Cook',
  KITCHEN_ASSISTANT: 'Kitchen Assistant',
  DISHWASHER: 'Dishwasher',
  WAITER: 'Waiter / Server',
  HOST: 'Host / Hostess',
  CASHIER: 'Cashier',
  BARTENDER: 'Bartender',
  BARISTA: 'Barista',
  CLEANING_STAFF: 'Cleaning Staff',
  INVENTORY_MANAGER: 'Inventory Manager',
  DELIVERY_STAFF: 'Delivery Staff',
  SECURITY_STAFF: 'Security Staff',
}

export default function Staff() {
  const queryClient = useQueryClient()

  const [editingId, setEditingId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [role, setRole] = useState<StaffRole>('CLEANING_STAFF')
  const [showForm, setShowForm] = useState(false)
  const [message, setMessage] = useState('')
  const [selectedStaffId, setSelectedStaffId] = useState<number | null>(null)
  const [roleFilter, setRoleFilter] = useState<'ALL' | StaffRole>('ALL')

  const staffQuery = useQuery({
    queryKey: ['staff'],
    queryFn: getStaffMembers,
  })

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

  const staff = staffQuery.data ?? []
  const pendingTasks = pendingQuery.data ?? []
  const completedTasks = completedQuery.data ?? []
  const allTasks = [...pendingTasks, ...completedTasks]

  const activeCount = staff.filter((member) => member.is_active).length
  const inactiveCount = staff.length - activeCount
  const assignedCount = pendingTasks.filter(
    (task) => task.assigned_staff_id !== null,
  ).length

  const refreshData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['staff'] }),
      queryClient.invalidateQueries({ queryKey: ['alerts'] }),
    ])
  }

  const createMutation = useMutation({
    mutationFn: createStaffMember,
    onSuccess: async () => {
      resetForm()
      setMessage('Staff member added successfully.')
      await refreshData()
    },
    onError: (error: Error) => setMessage(error.message),
  })

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      updates,
    }: {
      id: number
      updates: {
        name?: string
        email?: string | null
        phone?: string | null
        role?: StaffRole
        is_active?: boolean
      }
    }) => updateStaffMember(id, updates),
    onSuccess: async () => {
      resetForm()
      setMessage('Staff profile updated successfully.')
      await refreshData()
    },
    onError: (error: Error) => setMessage(error.message),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteStaffMember,
    onSuccess: async () => {
      setMessage('Staff profile removed. Any task assignments have been cleared.')
      setSelectedStaffId(null)
      await refreshData()
    },
    onError: (error: Error) => setMessage(error.message),
  })

  function resetForm() {
    setEditingId(null)
    setName('')
    setEmail('')
    setPhone('')
    setRole('CLEANING_STAFF')
    setShowForm(false)
  }

  function startEditing(member: StaffUser) {
    setEditingId(member.id)
    setName(member.name)
    setEmail(member.email ?? '')
    setPhone(member.phone ?? '')
    setRole(member.role)
    setShowForm(true)
    setMessage('')
  }

  function submitForm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage('')

    const payload = {
      name: name.trim(),
      email: email.trim() || null,
      phone: phone.trim() || null,
      role,
    }

    if (editingId !== null) {
      updateMutation.mutate({ id: editingId, updates: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  function removeMember(member: StaffUser) {
    const confirmed = window.confirm(
      `Remove ${member.name} from the staff directory? Any task assignments will be cleared.`,
    )

    if (confirmed) {
      setMessage('')
      deleteMutation.mutate(member.id)
    }
  }

  const visibleStaff = roleFilter === 'ALL'
    ? staff
    : staff.filter((member) => member.role === roleFilter)

  const selectedStaff = staff.find((member) => member.id === selectedStaffId)
  const selectedTasks = selectedStaff
    ? allTasks.filter((task) => task.assigned_staff_id === selectedStaff.id)
    : []

  return (
    <main className="staff-workspace">
      <header className="staff-workspace-header">
        <div>
          <p className="staff-eyebrow">RESTAURANT OPERATIONS</p>
          <h1>Staff management</h1>
          <p>Manage staff profiles, roles, and cleaning task responsibilities.</p>
        </div>

        <button
          className="staff-primary-button"
          type="button"
          onClick={() => {
            resetForm()
            setShowForm(true)
            setMessage('')
          }}
        >
          <Plus size={17} />
          Add staff member
        </button>
      </header>

      <section className="staff-summary-grid">
        <div className="staff-summary-card">
          <div className="staff-summary-icon staff-icon-total">
            <Users size={20} />
          </div>
          <div>
            <strong>{staff.length}</strong>
            <span>Total staff</span>
          </div>
        </div>

        <div className="staff-summary-card">
          <div className="staff-summary-icon staff-icon-active">
            <UserRound size={20} />
          </div>
          <div>
            <strong>{activeCount}</strong>
            <span>Active staff</span>
          </div>
        </div>

        <div className="staff-summary-card">
          <div className="staff-summary-icon staff-icon-tasks">
            <ClipboardList size={20} />
          </div>
          <div>
            <strong>{assignedCount}</strong>
            <span>Assigned pending tasks</span>
          </div>
        </div>
      </section>

      {message && (
        <div className="staff-message" role="status">
          <span>{message}</span>
          <button
            type="button"
            onClick={() => setMessage('')}
            aria-label="Dismiss message"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {showForm && (
        <section className="staff-panel">
          <div className="staff-panel-heading">
            <div>
              <h2>{editingId === null ? 'Add staff member' : 'Edit staff profile'}</h2>
              <p>Enter the staff member's contact details and restaurant role.</p>
            </div>
            <button
              className="staff-icon-button"
              type="button"
              onClick={resetForm}
              aria-label="Close staff form"
            >
              <X size={18} />
            </button>
          </div>

          <form className="staff-form" onSubmit={submitForm}>
            <label>
              Full name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Ali Ahmed"
                minLength={2}
                maxLength={150}
                required
              />
            </label>

            <label>
              Email address
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@example.com"
                maxLength={255}
              />
            </label>

            <label>
              Phone number
              <input
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                placeholder="e.g. 03001234567"
                maxLength={30}
              />
            </label>

            <label>
              Staff role
              <select
                value={role}
                onChange={(event) => setRole(event.target.value as StaffRole)}
              >
                {Object.entries(roleLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <div className="staff-form-actions">
              <button
                className="staff-primary-button"
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                <Check size={16} />
                {createMutation.isPending || updateMutation.isPending
                  ? 'Saving...'
                  : editingId === null
                    ? 'Save staff member'
                    : 'Save changes'}
              </button>
              <button
                className="staff-secondary-button"
                type="button"
                onClick={resetForm}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="staff-panel">
        <div className="staff-panel-heading staff-directory-heading">
          <div>
            <h2>Staff directory</h2>
            <p>Staff profiles and their current availability.</p>
          </div>

          <div className="staff-directory-controls">
            <select
              value={roleFilter}
              onChange={(event) =>
                setRoleFilter(event.target.value as 'ALL' | StaffRole)
              }
              aria-label="Filter staff by role"
            >
              <option value="ALL">All roles</option>
              {Object.entries(roleLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button
              className="staff-icon-button"
              type="button"
              onClick={() => void refreshData()}
              aria-label="Refresh staff and tasks"
            >
              <RefreshCw size={17} />
            </button>
          </div>
        </div>

        {staffQuery.isLoading && (
          <p className="staff-query-message">Loading staff directory...</p>
        )}

        {(staffQuery.isError || pendingQuery.isError || completedQuery.isError) && (
          <p className="staff-query-error">
            Could not load staff or task information. Please refresh and try again.
          </p>
        )}

        {!staffQuery.isLoading && !staffQuery.isError && visibleStaff.length === 0 && (
          <div className="staff-empty-state">
            <Users size={28} />
            <h3>{staff.length === 0 ? 'No staff members yet' : 'No matching staff'}</h3>
            <p>
              {staff.length === 0
                ? 'Add your first staff profile to start managing cleaning responsibilities.'
                : 'Try selecting a different role filter.'}
            </p>
          </div>
        )}

        <div className="staff-list">
          {visibleStaff.map((member) => {
            const memberPending = pendingTasks.filter(
              (task) => task.assigned_staff_id === member.id,
            ).length
            const memberCompleted = completedTasks.filter(
              (task) => task.assigned_staff_id === member.id,
            ).length
            const isSelected = selectedStaffId === member.id

            return (
              <article className="staff-member-card" key={member.id}>
                <div className="staff-member-main">
                  <div className="staff-avatar">
                    {member.name.trim().charAt(0).toUpperCase()}
                  </div>

                  <div className="staff-member-details">
                    <h3>{member.name}</h3>
                    <span className="staff-role">{roleLabels[member.role]}</span>
                    <div className="staff-contact-details">
                      {member.email && (
                        <span><Mail size={13} />{member.email}</span>
                      )}
                      {member.phone && (
                        <span><Phone size={13} />{member.phone}</span>
                      )}
                      {!member.email && !member.phone && (
                        <span>No contact details added</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="staff-member-task-counts">
                  <button
                    type="button"
                    className={isSelected ? 'selected' : ''}
                    onClick={() => setSelectedStaffId(isSelected ? null : member.id)}
                  >
                    <strong>{memberPending}</strong>
                    <span>Pending</span>
                  </button>
                  <button
                    type="button"
                    className={isSelected ? 'selected' : ''}
                    onClick={() => setSelectedStaffId(isSelected ? null : member.id)}
                  >
                    <strong>{memberCompleted}</strong>
                    <span>Completed</span>
                  </button>
                </div>

                <div className="staff-member-actions">
                  <span className={`staff-active-status ${member.is_active ? 'active' : 'inactive'}`}>
                    {member.is_active ? 'Active' : 'Inactive'}
                  </span>
                  {member.role !== 'OWNER' && (
                    <>
                      <button
                        className="staff-icon-button"
                        type="button"
                        onClick={() => startEditing(member)}
                        aria-label={`Edit ${member.name}`}
                      >
                        <Edit2 size={16} />
                      </button>
                      <button
                        className="staff-icon-button staff-delete-button"
                        type="button"
                        onClick={() => removeMember(member)}
                        disabled={deleteMutation.isPending}
                        aria-label={`Permanently remove ${member.name}`}
                      >
                        <Trash2 size={16} />
                      </button>
                    </>
                  )}
                </div>
              </article>
            )
          })}
        </div>

        {selectedStaff && (
          <div className="staff-assigned-tasks">
            <div className="staff-assigned-heading">
              <div>
                <h3>Tasks assigned to {selectedStaff.name}</h3>
                <p>Pending and completed cleaning alerts assigned to this staff member.</p>
              </div>
              <button
                className="staff-icon-button"
                type="button"
                onClick={() => setSelectedStaffId(null)}
                aria-label="Close assigned tasks"
              >
                <X size={17} />
              </button>
            </div>

            {selectedTasks.length === 0 ? (
              <p className="staff-query-message">No cleaning tasks are assigned to this staff member.</p>
            ) : (
              <div className="staff-task-list">
                {selectedTasks.map((task) => (
                  <div className="staff-task-row" key={task.id}>
                    <div>
                      <strong>{task.table_name}</strong>
                      <span>Table {task.table_number} · {task.message}</span>
                    </div>
                    <span className={`staff-task-status ${task.status === 'RESOLVED' ? 'completed' : 'pending'}`}>
                      {task.status === 'RESOLVED' ? 'Completed' : 'Pending'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      <p className="staff-footnote">
        {inactiveCount} inactive profile{inactiveCount === 1 ? '' : 's'} · Staff profiles are directory records and do not provide login access.
      </p>
    </main>
  )
}
