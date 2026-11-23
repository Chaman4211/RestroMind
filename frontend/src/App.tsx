import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  confirmTableCleaning,
  getAlerts,
  getOccupancyHistory,
  getRestaurantTables,
  getServiceRequests,
  type OccupancyHistoryEvent,
  type RestaurantAlert,
  type RestaurantTable as ApiRestaurantTable,
} from './services/api'
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowRight,
  Bell,
  CalendarDays,
  CheckCircle2,
  CircleHelp,
  ClipboardList,
  Clock3,
  Coffee,
  LayoutDashboard,
  Menu,
  MonitorPlay,
  Plus,
  Settings2,
  ShieldCheck,
  Sparkles,
  Table2,
  Users,
  Utensils,
  Video,
  Wifi,
  X,
} from 'lucide-react'
import LiveMonitoring from './components/LiveMonitoring'
import TableManagement from './components/TableManagement'
import CleaningTasks from './components/CleaningTasks'
import ServiceRequests from './components/ServiceRequests'
import Staff from './components/Staff'
import WifiSettings from './components/WifiSettings'
import { KitchenDisplay, MenuManagement, TableQRCodes } from './components/OrderingPages'
import { getAccessToken } from './services/auth'
import './App.css'

type TableStatus = 'free' | 'occupied' | 'cleaning'

type DashboardTable = {
  id: number
  tableNumber: string
  name: string
  status: TableStatus
  occupancyStartedAt: string | null
}

function mapTable(table: ApiRestaurantTable): DashboardTable {
  const status: TableStatus =
    table.status === 'FREE'
      ? 'free'
      : table.status === 'OCCUPIED'
        ? 'occupied'
        : 'cleaning'

  return {
    id: table.id,
    tableNumber: table.table_number,
    name: table.name,
    status,
    occupancyStartedAt:
      table.status === 'OCCUPIED' ? table.last_status_changed_at : null,
  }
}

const navItems = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Table management', icon: Table2 },
  { label: 'Live monitoring', icon: MonitorPlay },
  { label: 'Cleaning tasks', icon: ClipboardList },
  { label: 'Service requests', icon: Bell },
  { label: 'Kitchen display', icon: Utensils },
  { label: 'Menu management', icon: Menu },
  { label: 'Table QR codes', icon: Table2 },
  { label: 'Staff', icon: Users },
  { label: 'Settings', icon: Settings2 },
]

const statusLabels: Record<TableStatus, string> = {
  free: 'Available',
  occupied: 'Occupied',
  cleaning: 'Needs cleaning',
}

function formatOccupancyDuration(
  startedAt: string | null,
  now: Date | null,
): string {
  if (!startedAt || !now) return 'Timer unavailable'

  const startTime = new Date(startedAt).getTime()
  if (!Number.isFinite(startTime)) return 'Timer unavailable'

  const elapsed = Math.max(0, Math.floor((now.getTime() - startTime) / 1000))
  const hours = Math.floor(elapsed / 3600)
  const minutes = Math.floor((elapsed % 3600) / 60)
  const seconds = elapsed % 60

  return [hours, minutes, seconds]
    .map((value) => String(value).padStart(2, '0'))
    .join(':')
}

function formatAlertTime(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Recently'
  }

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatHistoryTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Time unavailable'

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatVisitDuration(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds))
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const remainingSeconds = safeSeconds % 60

  if (hours > 0) return `${hours}h ${minutes}m`
  if (minutes > 0) return `${minutes}m ${remainingSeconds}s`
  return `${remainingSeconds}s`
}

function getHistoryEventLabel(event: OccupancyHistoryEvent): string {
  if (event.description) return event.description

  switch (event.new_status) {
    case 'OCCUPIED':
      return 'became occupied'
    case 'NEEDS_CLEANING':
      return 'marked for cleaning'
    case 'FREE':
      return 'became available'
    default:
      return `status changed to ${event.new_status.toLowerCase().replaceAll('_', ' ')}`
  }
}

function App() {
  const [currentDate, setCurrentDate] = useState<Date | null>(null)

  useEffect(() => {
    const updateDate = () => setCurrentDate(new Date())
    updateDate()

    const interval = window.setInterval(updateDate, 1000)
    return () => window.clearInterval(interval)
  }, [])

  const greeting = !currentDate
    ? 'Good day.'
    : currentDate.getHours() < 12
      ? 'Good morning.'
      : currentDate.getHours() < 17
        ? 'Good afternoon.'
        : 'Good evening.'
  const [activeNav, setActiveNav] = useState('Overview')
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [filter, setFilter] = useState<'all' | TableStatus>('all')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const [floorPlanOpen, setFloorPlanOpen] = useState(false)

  const queryClient = useQueryClient()
  const {
    data: apiTables = [],
    isLoading,
    isError,
    error,
    isFetching,
  } = useQuery({
    queryKey: ['restaurant-tables'],
    queryFn: getRestaurantTables,
  })

  const {
    data: openAlerts = [],
    isLoading: alertsLoading,
    isError: alertsError,
    error: alertsQueryError,
  } = useQuery({
    queryKey: ['alerts', 'OPEN'],
    queryFn: () => getAlerts('OPEN'),
    refetchInterval: 10000,
  })

  const {
    data: occupancyHistory,
    isLoading: historyLoading,
    isError: historyError,
  } = useQuery({
    queryKey: ['restaurant-table-history'],
    queryFn: getOccupancyHistory,
    refetchInterval: 15000,
  })

  const {
    data: serviceRequests = [],
    isLoading: serviceRequestsLoading,
    isError: serviceRequestsError,
  } = useQuery({
    queryKey: ['service-requests'],
    queryFn: getServiceRequests,
    refetchInterval: 5000,
  })

  const activeServiceRequests = serviceRequests.filter(
    (request) => request.status !== 'COMPLETED',
  )
  const activeServiceRequestCount = activeServiceRequests.length

  const showNotice = (message: string) => {
    setNotice(message)
    window.setTimeout(() => setNotice(''), 3000)
  }


  // STAFF_NOTIFICATION_SOCKET: receive newly assigned alerts in real time.
  useEffect(() => {
    let active = true
    let socket: WebSocket | null = null
    let reconnectTimer: number | undefined

    const connect = async () => {
      try {
        const accessToken = getAccessToken()
        if (!accessToken) return

        const response = await fetch('/api/v1/alerts/notification-token', {
          method: 'POST',
          headers: { Authorization: `Bearer ${accessToken}` },
        })

        if (!response.ok) {
          throw new Error('Could not authenticate notification connection')
        }

        const result = await response.json() as { token: string }
        if (!active) return

        const wsUrl = new URL(
          '/api/v1/alerts/notifications',
          window.location.href,
        )
        wsUrl.protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        wsUrl.searchParams.set('token', result.token)

        socket = new WebSocket(wsUrl.toString())

        socket.onmessage = (event) => {
          let message: {
            type?: string
            alert_type?: string
            message?: string
            table_number?: string
          }

          try {
            message = JSON.parse(event.data)
          } catch {
            return
          }

          if (message.type !== 'alert') return

          void queryClient.invalidateQueries({ queryKey: ['alerts'] })

          setNotice(
            `New alert: ${message.alert_type ?? 'Alert'} — Table ${message.table_number ?? 'N/A'}. ${message.message ?? ''}`,
          )
          window.setTimeout(() => setNotice(''), 6000)

          if (
            typeof Notification !== 'undefined' &&
            Notification.permission === 'granted'
          ) {
            new Notification('RestroMind: New alert', {
              body: `Table ${message.table_number ?? 'N/A'} — ${message.message ?? 'A new alert needs attention.'}`,
            })
          }
        }

        socket.onclose = () => {
          if (active) {
            reconnectTimer = window.setTimeout(() => void connect(), 3000)
          }
        }

        socket.onerror = () => socket?.close()
      } catch {
        if (active) {
          reconnectTimer = window.setTimeout(() => void connect(), 5000)
        }
      }
    }

    void connect()

    return () => {
      active = false
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer)
      }
      socket?.close()
    }
  }, [queryClient])

  const cleaningMutation = useMutation({
    mutationFn: confirmTableCleaning,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] }),
        queryClient.invalidateQueries({ queryKey: ['alerts'] }),
      ])
      showNotice('Cleaning confirmation saved.')
    },
    onError: (mutationError) => {
      showNotice(
        mutationError instanceof Error
          ? mutationError.message
          : 'Could not confirm cleaning.',
      )
    },
  })

  const tables = apiTables.map(mapTable)
  const availableCount = tables.filter((table) => table.status === 'free').length
  const occupiedCount = tables.filter((table) => table.status === 'occupied').length
  const cleaningTables = tables.filter((table) => table.status === 'cleaning')
  const cleaningCount = cleaningTables.length
  const occupiedPercentage = tables.length
    ? Math.round((occupiedCount / tables.length) * 100)
    : 0

  const visibleTables = filter === 'all'
    ? tables
    : tables.filter((table) => table.status === filter)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Utensils size={20} strokeWidth={2.4} /></div>
          <div className="brand-copy">
            <div className="brand-name">RestroMind</div>
            <div className="brand-subtitle">Restaurant intelligence</div>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>
        <nav className="nav-list">
          {navItems.map(({ label, icon: Icon }) => (
            <button
              className={`nav-item ${activeNav === label ? 'active' : ''}`}
              key={label}
              onClick={() => {
                setActiveNav(label)
                setMobileNavOpen(false)
              }}
            >
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {label === 'Cleaning tasks' && cleaningCount > 0 && (
                <span className="nav-count">{cleaningCount}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="nav-label" style={{ marginTop: 34 }}>PREFERENCES</div>
        <nav className="nav-list">
          <button
            className={`nav-item ${activeNav === 'Help & support' ? 'active' : ''}`}
            onClick={() => {
              setActiveNav('Help & support')
              setMobileNavOpen(false)
            }}
          >
            <CircleHelp size={17} /><span>Help & support</span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="plan-card">
            <div className="plan-icon"><Sparkles size={15} /></div>
            <strong>Smarter service starts here</strong>
            <p>Keep your tables moving and your team one step ahead.</p>
            <button className="plan-link" onClick={() => setActiveNav('Help & support')}>
              Explore features <ArrowRight size={12} style={{ verticalAlign: 'middle' }} />
            </button>
          </div>
          <div className="profile">
            <div className="avatar">RM</div>
            <div className="profile-copy">
              <div className="profile-name">Demo Workspace</div>
              <div className="profile-role">Public Demo</div>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMobileNavOpen(!mobileNavOpen)} aria-label="Toggle navigation">
            {mobileNavOpen ? <X size={17} /> : <Menu size={17} />}
          </button>
          <div className="breadcrumb">
            <span>Workspace</span><span>/</span><strong>{activeNav}</strong>
          </div>
          <div className="topbar-actions">
            <div className="date-chip"><CalendarDays size={14} /> {currentDate?.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" }) ?? ""}</div>
            <div className="notification-wrapper">
              <button
                className="icon-button"
                aria-label={`Notifications, ${openAlerts.length} open alerts`}
                aria-expanded={notificationsOpen}
                onClick={() => setNotificationsOpen((open) => !open)}
              >
                <Bell size={16} />
                {openAlerts.length > 0 && <span className="notification-dot" />}
              </button>

              {notificationsOpen && (
                <div className="notification-panel">
                  <div className="notification-panel-header">
                    <div>
                      <strong>Notifications</strong>
                      <span>{openAlerts.length} open alerts</span>
                    </div>
                    <button
                      className="notification-close"
                      onClick={() => setNotificationsOpen(false)}
                      aria-label="Close notifications"
                    >
                      <X size={16} />
                    </button>
                  </div>

                  <div className="notification-panel-list">
                    {alertsLoading ? (
                      <p className="notification-empty">Loading alerts...</p>
                    ) : alertsError ? (
                      <p className="notification-empty">
                        Could not load alerts. Please try again.
                      </p>
                    ) : openAlerts.length === 0 ? (
                      <p className="notification-empty">
                        <CheckCircle2 size={18} />
                        All caught up. No open alerts.
                      </p>
                    ) : (
                      openAlerts.map((alert: RestaurantAlert) => (
                        <button
                          className="notification-entry"
                          key={alert.id}
                          onClick={() => {
                            setActiveNav('Cleaning tasks')
                            setNotificationsOpen(false)
                          }}
                        >
                          <span className="notification-entry-icon">
                            {alert.alert_type === 'CLEANING_REQUIRED'
                              ? <Coffee size={16} />
                              : <AlertCircle size={16} />}
                          </span>
                          <span className="notification-entry-copy">
                            <strong>
                              {alert.table_number} · {alert.alert_type.replace(/_/g, ' ').toLowerCase()}
                            </strong>
                            <span>{alert.table_name} · {alert.message}</span>
                            <small>{formatAlertTime(alert.created_at)}</small>
                          </span>
                        </button>
                      ))
                    )}
                  </div>

                  <button
                    className="notification-view-all"
                    onClick={() => {
                      setActiveNav('Cleaning tasks')
                      setNotificationsOpen(false)
                    }}
                  >
                    Open cleaning tasks <ArrowRight size={14} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {mobileNavOpen && (
          <div style={{ padding: '12px 16px', background: '#17271e', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {navItems.map(({ label, icon: Icon }) => (
              <button key={label} onClick={() => {
                setActiveNav(label)
                setMobileNavOpen(false)
              }} style={{ display: 'flex', gap: 6, alignItems: 'center', padding: '9px 11px', border: 0, borderRadius: 8, background: activeNav === label ? '#426348' : '#263a2d', color: '#fff', fontSize: 11 }}>
                <Icon size={14} />{label}
              </button>
            ))}
            <button
              onClick={() => {
                setActiveNav('Help & support')
                setMobileNavOpen(false)
              }}
              style={{ display: 'flex', gap: 6, alignItems: 'center', padding: '9px 11px', border: 0, borderRadius: 8, background: activeNav === 'Help & support' ? '#426348' : '#263a2d', color: '#fff', fontSize: 11 }}
            >
              <CircleHelp size={14} />Help & support
            </button>
          </div>
        )}

        <div style={{ display: activeNav === 'Table management' ? 'block' : 'none' }}>
          <TableManagement />
        </div>

        <div style={{ display: activeNav === 'Kitchen display' ? 'block' : 'none' }}>
          <KitchenDisplay />
        </div>

        <div style={{ display: activeNav === 'Menu management' ? 'block' : 'none' }}>
          <MenuManagement />
        </div>

        <div style={{ display: activeNav === 'Table QR codes' ? 'block' : 'none' }}>
          <TableQRCodes />
        </div>

        <div style={{ display: activeNav === 'Live monitoring' ? 'block' : 'none' }}>
          <LiveMonitoring />
        </div>

        <div style={{ display: activeNav === 'Cleaning tasks' ? 'block' : 'none' }}>
          <CleaningTasks />
        </div>

        <div style={{ display: activeNav === 'Service requests' ? 'block' : 'none' }}>
          <ServiceRequests />
        </div>

        <div style={{ display: activeNav === 'Staff' ? 'block' : 'none' }}>
          <Staff />
        </div>

        <div style={{ display: activeNav === 'Settings' ? 'block' : 'none' }}>
          <section className="content settings-workspace">
            <div className="welcome-row">
              <div>
                <div className="eyebrow">RESTAURANT PREFERENCES</div>
                <h1 className="page-title">Settings</h1>
                <p className="page-subtitle">Manage your restaurant Wi-Fi connection.</p>
              </div>
            </div>
            <WifiSettings />
          </section>
        </div>

        <div style={{ display: activeNav === 'Help & support' ? 'block' : 'none' }}>
          <section className="content help-workspace">
            <div className="eyebrow">RESTROMIND ASSISTANCE</div>
            <h1 className="page-title">Help & support</h1>
            <p className="page-subtitle">Quick guidance for managing your restaurant workspace.</p>

            <div className="help-grid">
              <article className="help-card">
                <Wifi size={21} />
                <h2>Restaurant Wi-Fi</h2>
                <p>Open Settings, select Wi-Fi settings, configure the network name and password, then save. Staff can scan the displayed QR code to connect.</p>
                <button onClick={() => {
                  setActiveNav('Settings')
                }}>Open Wi-Fi settings <ArrowRight size={14} /></button>
              </article>

              <article className="help-card">
                <Users size={21} />
                <h2>Staff and roles</h2>
                <p>Open Staff to add team members, update their roles and contact details, and review their assigned cleaning tasks.</p>
                <button onClick={() => setActiveNav('Staff')}>Open staff management <ArrowRight size={14} /></button>
              </article>

              <article className="help-card">
                <MonitorPlay size={21} />
                <h2>Cameras and monitoring</h2>
                <p>Use Live monitoring to check camera feeds. For an IP camera, verify its RTSP address, network connection, and camera credentials.</p>
                <button onClick={() => setActiveNav('Live monitoring')}>Open live monitoring <ArrowRight size={14} /></button>
              </article>

              <article className="help-card">
                <ClipboardList size={21} />
                <h2>Cleaning tasks</h2>
                <p>Review pending cleaning tasks, check their assignments, and update task status after the table has been cleaned.</p>
                <button onClick={() => setActiveNav('Cleaning tasks')}>Open cleaning tasks <ArrowRight size={14} /></button>
              </article>
            </div>

            <div className="help-note">
              <strong>Need technical support?</strong>
              <p>Keep the error message, the page where it occurred, and the time of the issue. Share these details with your RestroMind project administrator so the problem can be investigated.</p>
            </div>
          </section>
        </div>

        <div style={{ display: activeNav === 'Overview' ? 'block' : 'none' }}>
        <div className="content">
          <div className="welcome-row">
            <div>
              <div className="eyebrow">Daily service overview</div>
              <h1 className="page-title">{greeting}</h1>
              <p className="page-subtitle">Here’s what’s happening across your restaurant today.</p>
            </div>
            <button className="primary-button" onClick={() => showNotice('Table setup will be connected to the API next.')}>
              <Plus size={15} /> Add a table
            </button>
          </div>

          <div className="demo-banner" role="status">
            <AlertCircle size={14} />
            <span>
              {isLoading
                ? 'Connecting to the restaurant database...'
                : isError
                  ? `Could not load restaurant data: ${error instanceof Error ? error.message : 'Unknown API error'}`
                  : (
                    <>
                      <strong>Live database data</strong> — Table statuses and totals are loaded from RestroMind.
                      {isFetching ? ' Refreshing data...' : ''}
                      {' '}Recent activity is loaded from occupancy history.
                    </>
                  )}
            </span>
          </div>

          <section className="stats-grid" aria-label="Restaurant statistics">
            <StatCard
              label="Total tables"
              value={String(tables.length).padStart(2, '0')}
              foot="Registered restaurant tables"
              icon={<Table2 size={16} />}
              tint="#eaf1e8"
              color="#4d7954"
            />
            <StatCard
              label="Available now"
              value={String(availableCount).padStart(2, '0')}
              foot="Ready for new guests"
              icon={<CheckCircle2 size={16} />}
              tint="#eaf4ec"
              color="#4e8a5a"
            />
            <StatCard
              label="Currently occupied"
              value={String(occupiedCount).padStart(2, '0')}
              foot={<><span className="positive">{occupiedPercentage}%</span> of all tables</>}
              icon={<Users size={16} />}
              tint="#edf1ed"
              color="#607d67"
            />
            <StatCard
              label="Need attention"
              value={String(cleaningCount).padStart(2, '0')}
              foot="Cleaning action required"
              icon={<Clock3 size={16} />}
              tint="#fbf0df"
              color="#b58239"
            />
          </section>

          <div className="dashboard-grid">
            <div className="dashboard-left-column">
            <section className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Floor overview</div>
                  <div className="panel-caption">Live table status and customer requests · refreshes automatically</div>
                </div>
                <button className="text-action" onClick={() => setFloorPlanOpen(true)}>
                  View floor plan <ArrowRight size={12} style={{ verticalAlign: 'middle' }} />
                </button>
              </div>

              <div className="floor-summary">
                <FloorPill color="#6d9a70" label="Available" count={String(availableCount)} />
                <FloorPill color="#e69a38" label="Occupied" count={String(occupiedCount)} />
                <FloorPill color="#d1a052" label="Needs cleaning" count={String(cleaningCount)} />
                <FloorPill color="#c56d5e" label="Active requests" count={String(activeServiceRequestCount)} />
              </div>

              <div className="floor-grid">
                {isLoading ? (
                  <p className="panel-caption">Loading tables...</p>
                ) : visibleTables.length === 0 ? (
                  <p className="panel-caption">
                    {tables.length === 0
                      ? 'No restaurant tables found. Add tables to your database first.'
                      : 'No tables match this filter.'}
                  </p>
                ) : (
                  visibleTables.map((table) => {
                    const tableRequests = activeServiceRequests.filter(
                      (request) => request.table_id === table.id,
                    )
                    const hasUnpaidBill = (openAlerts ?? []).some(
                      (alert: RestaurantAlert) =>
                        alert.table_id === table.id &&
                        alert.alert_type === 'UNPAID_BILL',
                    )
                    const hasAttention = hasUnpaidBill || tableRequests.length > 0
                    const displayStatus = hasUnpaidBill
                      ? 'Unpaid bill'
                      : tableRequests.length > 0
                        ? 'Needs attention'
                        : statusLabels[table.status]

                    const statusColor = hasAttention
                      ? '#dc5555'
                      : table.status === 'cleaning'
                        ? '#d1a052'
                        : table.status === 'occupied'
                          ? '#e69a38'
                          : '#6d9a70'

                    return (
                      <button
                        className={`table-card ${table.status}${hasAttention ? ' attention' : ''}`}
                        key={table.id}
                        onClick={() => {
                          if (tableRequests.length > 0) {
                            setActiveNav('Service requests')
                          } else {
                            showNotice(`${table.tableNumber} · ${table.name} · ${displayStatus}`)
                          }
                        }}
                      >
                        <div className="table-top">
                          <span className="table-number">{table.tableNumber}</span>
                          <span className="table-seats">{table.name}</span>
                        </div>
                        <div className="table-status">
                          <span
                            className="legend-dot"
                            style={{ background: statusColor }}
                          />
                          {displayStatus}
                        </div>
                        <div className="table-location">Table ID: {table.id}</div>
                        {table.status === 'occupied' && (
                          <div
                            className="table-location"
                            style={{
                              color: '#b58239',
                              fontWeight: 700,
                              fontVariantNumeric: 'tabular-nums',
                            }}
                          >
                            <Clock3
                              size={12}
                              style={{ verticalAlign: 'middle', marginRight: 5 }}
                            />
                            Occupied for{' '}
                            {formatOccupancyDuration(
                              table.occupancyStartedAt,
                              currentDate,
                            )}
                          </div>
                        )}
                        <div className="table-service-requests">
                          {serviceRequestsLoading ? (
                            <span className="service-request-empty">Checking requests...</span>
                          ) : serviceRequestsError ? (
                            <span className="service-request-empty">Requests unavailable</span>
                          ) : tableRequests.length > 0 ? (
                            tableRequests.map((request) => (
                              <span
                                className={`service-request-chip ${request.status.toLowerCase()}`}
                                key={request.id}
                              >
                                {request.request_type.replace(/_/g, ' ').toLowerCase()}
                                <span>{request.status === 'OPEN' ? 'New' : 'In progress'}</span>
                              </span>
                            ))
                          ) : hasUnpaidBill ? (
                            <span className="service-request-empty">Payment required</span>
                          ) : (
                            <span className="service-request-empty">No active requests</span>
                          )}
                        </div>
                      </button>
                    )
                  })
                )}
              </div>
              <div style={{ padding: '0 20px 15px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {(['all', 'free', 'occupied', 'cleaning'] as const).map((item) => (
                  <button
                    key={item}
                    onClick={() => setFilter(item)}
                    style={{
                      border: '1px solid #e7ebe5',
                      borderRadius: 20,
                      padding: '6px 10px',
                      background: filter === item ? '#eaf2e9' : '#fff',
                      color: filter === item ? '#315b43' : '#8a948c',
                      fontSize: 9,
                      fontWeight: 700,
                      cursor: 'pointer',
                      textTransform: 'capitalize',
                    }}
                  >
                    {item === 'all' ? 'All tables' : item === 'free' ? 'Available' : item === 'cleaning' ? 'Needs cleaning' : 'Occupied'}
                  </button>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Recent table visits</div>
                  <div className="panel-caption">
                    {historyLoading
                      ? 'Loading customer visits...'
                      : historyError
                        ? 'Could not load customer visits'
                        : `${occupancyHistory?.visits.length ?? 0} recorded visits · Customer occupancy duration`}
                  </div>
                </div>
                <Clock3 size={15} color="#9aa49b" />
              </div>

              <div className="activity-list">
                {occupancyHistory?.visits.slice(0, 5).map((visit, index) => (
                  <div className="activity-item" key={`${visit.table_id}-${visit.started_at}-${index}`}>
                    <span
                      className="activity-marker"
                      style={{ background: visit.is_ongoing ? '#d1a052' : '#6c9b70' }}
                    />
                    <div className="activity-copy">
                      <strong>Table {visit.table_number}</strong>
                      <span>
                        {formatVisitDuration(visit.duration_seconds)}
                        {visit.is_ongoing ? ' · In progress' : ' · Completed'}
                      </span>
                      <time>{formatHistoryTime(visit.started_at)}</time>
                    </div>
                  </div>
                ))}

                {!historyLoading && !historyError && !occupancyHistory?.visits.length && (
                  <div className="panel-caption">No customer visits have been recorded yet.</div>
                )}

                {historyLoading && (
                  <div className="panel-caption">Loading recent visits...</div>
                )}

                {historyError && (
                  <div className="panel-caption">Please check the backend history endpoint.</div>
                )}
              </div>
            </section>
            </div>

            <div className="right-column">
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <div className="panel-title">Needs attention</div>
                    <div className="panel-caption">Tasks waiting for your team</div>
                  </div>
                  <span style={{ background: '#fbf0df', color: '#a8752e', borderRadius: 20, padding: '4px 8px', fontSize: 9, fontWeight: 700 }}>{openAlerts.length} open</span>
                </div>
                <div className="alert-list">
                  {alertsLoading ? (
                    <div className="alert-item">
                      <div className="alert-copy">
                        <p>Loading alerts...</p>
                      </div>
                    </div>
                  ) : alertsError ? (
                    <div className="alert-item">
                      <div className="alert-symbol"><AlertCircle size={15} /></div>
                      <div className="alert-copy">
                        <strong>Could not load alerts</strong>
                        <p>{alertsQueryError instanceof Error ? alertsQueryError.message : 'Please try again.'}</p>
                      </div>
                    </div>
                  ) : openAlerts.length === 0 ? (
                    <div className="alert-item">
                      <div className="alert-symbol"><CheckCircle2 size={15} /></div>
                      <div className="alert-copy">
                        <strong>All tables are up to date</strong>
                        <p>No open alerts are waiting.</p>
                      </div>
                    </div>
                  ) : (
                    openAlerts.map((alert: RestaurantAlert) => {
                      const isCleaningAlert = alert.alert_type === 'CLEANING_REQUIRED'

                      return (
                        <AlertItem
                          key={alert.id}
                          icon={isCleaningAlert ? <Coffee size={15} /> : <AlertCircle size={15} />}
                          title={
                            isCleaningAlert
                              ? `${alert.table_number} needs cleaning`
                              : `${alert.table_number} · ${alert.alert_type.replace(/_/g, ' ').toLowerCase()}`
                          }
                          description={`${alert.table_name} · ${alert.message}`}
                          time={formatAlertTime(alert.created_at)}
                          action={
                            isCleaningAlert ? (
                              <button
                                className="text-action"
                                disabled={cleaningMutation.isPending}
                                onClick={() => cleaningMutation.mutate(alert.table_id)}
                              >
                                {cleaningMutation.isPending ? 'Saving...' : 'Confirm cleaned'}
                              </button>
                            ) : undefined
                          }
                        />
                      )
                    })
                  )}
                </div>
                <div className="alert-footer">
                  <button className="text-action" onClick={() => setActiveNav('Cleaning tasks')}>
                    Open cleaning tasks <ArrowRight size={12} style={{ verticalAlign: 'middle' }} />
                  </button>
                </div>
              </section>

              <section className="panel">
                <div className="panel-header">
                  <div>
                    <div className="panel-title">Recent activity</div>
                    <div className="panel-caption">
                      {historyLoading
                        ? 'Loading occupancy history...'
                        : historyError
                          ? 'Could not load occupancy history'
                          : `${occupancyHistory?.events.length ?? 0} recent table events`}
                    </div>
                  </div>
                  <Activity size={15} color="#9aa49b" />
                </div>
                <div className="activity-list">
                  {occupancyHistory?.events.slice(0, 6).map((event) => (
                    <ActivityItem
                      key={event.id}
                      color={
                        event.new_status === 'OCCUPIED'
                          ? '#6c9b70'
                          : event.new_status === 'NEEDS_CLEANING'
                            ? '#d1a052'
                            : '#8b9b91'
                      }
                      text={
                        <>
                          <strong>Table {event.table_number}</strong>{' '}
                          {getHistoryEventLabel(event)}
                        </>
                      }
                      time={formatHistoryTime(event.created_at)}
                    />
                  ))}
                  {!historyLoading && !historyError && !occupancyHistory?.events.length && (
                    <div className="panel-caption">No table activity has been recorded yet.</div>
                  )}
                  {historyError && (
                    <div className="panel-caption">Please check the backend history endpoint.</div>
                  )}
                </div>


              </section>
            </div>
          </div>



          <div className="bottom-grid">
            <section className="camera-card">
              <div>
                <div className="camera-eyebrow"><Wifi size={11} style={{ verticalAlign: 'middle', marginRight: 5 }} /> Intelligent monitoring</div>
                <div className="camera-title">Your floor, in focus.</div>
                <div className="camera-description">Connect a camera to monitor table activity in real time.</div>
              </div>
              <button className="camera-action" onClick={() => { setActiveNav('Live monitoring'); showNotice('Live camera setup is the next integration step.') }}>
                <Video size={13} style={{ verticalAlign: 'middle', marginRight: 6 }} />Open live monitoring
              </button>
            </section>

            <section className="panel occupancy-card">
              <div className="occupancy-head">
                <div className="panel-title">Table occupancy</div>
                <ArrowDownRight size={15} color="#8e9a90" />
              </div>
              <div className="occupancy-number">{occupiedPercentage}% <span>occupied</span></div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${occupiedPercentage}%` }} />
              </div>
              <div className="occupancy-note">{occupiedCount} of {tables.length} tables currently in use</div>
            </section>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 24, color: '#a0a9a1', fontSize: 9 }}>
            <span>RESTROMIND · RESTAURANT OPERATIONS</span>
            <span><ShieldCheck size={11} style={{ verticalAlign: 'middle', marginRight: 4 }} />Built for smarter service</span>
          </div>
        </div>
        </div>
      {floorPlanOpen && (
        <div className="floor-plan-overlay">
          <section
            className="floor-plan-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="floor-plan-title"
          >
            <div className="floor-plan-header">
              <div>
                <div className="panel-title" id="floor-plan-title">Live floor view</div>
                <div className="panel-caption">All restaurant tables and their current status · arranged automatically</div>
              </div>
              <button
                className="floor-plan-close"
                onClick={() => setFloorPlanOpen(false)}
                aria-label="Close floor plan"
                type="button"
              >
                <X size={19} />
              </button>
            </div>

            <div className="floor-plan-summary">
              <FloorPill color="#6c9b70" label="Available" count={String(availableCount)} />
              <FloorPill color="#d1a052" label="Occupied" count={String(occupiedCount)} />
              <FloorPill color="#8b9b91" label="Cleaning" count={String(cleaningCount)} />
              <FloorPill color="#526057" label="Total tables" count={String(tables.length)} />
            </div>

            {tables.length > 0 ? (
              <div className="floor-plan-grid">
                {tables.map((table) => (
                  <div className={`floor-plan-card ${table.status}`} key={table.id}>
                    <div className="floor-plan-card-top">
                      <strong>Table {table.tableNumber}</strong>
                      <span className={`floor-plan-status ${table.status}`}>
                        {table.status === 'free'
                          ? 'Available'
                          : table.status === 'occupied'
                            ? 'Occupied'
                            : 'Cleaning'}
                      </span>
                    </div>
                    <div className="floor-plan-table-name">{table.name}</div>
                    <div className="floor-plan-table-id">Table ID: {table.id}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="floor-plan-empty">
                No restaurant tables have been added yet.
              </div>
            )}
          </section>
        </div>
      )}

      </main>

      {notice && (
        <div role="status" style={{ position: 'fixed', bottom: 22, right: 22, zIndex: 20, display: 'flex', alignItems: 'center', gap: 10, background: '#20392a', color: '#f5f7ef', borderRadius: 10, padding: '13px 16px', boxShadow: '0 10px 30px #14221b30', fontSize: 12 }}>
          <CheckCircle2 size={16} color="#c6dfb9" />{notice}
          <button onClick={() => setNotice('')} aria-label="Dismiss notification" style={{ border: 0, background: 'transparent', color: '#cbd6cc', cursor: 'pointer', padding: 0, display: 'grid' }}><X size={14} /></button>
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  foot,
  icon,
  tint,
  color,
}: {
  label: string
  value: string
  foot: React.ReactNode
  icon: React.ReactNode
  tint: string
  color: string
}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <span className="stat-icon" style={{ background: tint, color }}>{icon}</span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-foot">{foot}</div>
    </div>
  )
}

function FloorPill({ color, label, count }: { color: string; label: string; count: string }) {
  return (
    <div className="floor-pill">
      <span className="legend-dot" style={{ background: color }} />
      <strong style={{ color: '#526057' }}>{count}</strong> {label}
    </div>
  )
}

function AlertItem({
  icon,
  title,
  description,
  time,
  action,
}: {
  icon: React.ReactNode
  title: string
  description: string
  time: string
  action?: React.ReactNode
}) {
  return (
    <div className="alert-item">
      <div className="alert-symbol">{icon}</div>
      <div className="alert-copy">
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
      <div className="alert-time">
        {time}
        {action}
      </div>
    </div>
  )
}

function ActivityItem({
  color,
  text,
  time,
}: {
  color: string
  text: React.ReactNode
  time: string
}) {
  return (
    <div className="activity-item">
      <span className="activity-marker" style={{ background: color }} />
      <div className="activity-copy">
        {text}
        <time>{time}</time>
      </div>
    </div>
  )
}

export default App
