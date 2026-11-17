import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  confirmTableCleaning,
  getAlerts,
  getRestaurantTables,
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
  LogOut,
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
import Staff from './components/Staff'
import { useAuth } from './components/authContext'
import './App.css'

type TableStatus = 'free' | 'occupied' | 'cleaning'

type DashboardTable = {
  id: number
  tableNumber: string
  name: string
  status: TableStatus
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
  }
}

const navItems = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Table management', icon: Table2 },
  { label: 'Live monitoring', icon: MonitorPlay },
  { label: 'Cleaning tasks', icon: ClipboardList },
  { label: 'Staff', icon: Users },
]

const statusLabels: Record<TableStatus, string> = {
  free: 'Available',
  occupied: 'Occupied',
  cleaning: 'Needs cleaning',
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

function App() {
  const { user, logout } = useAuth()
  const [currentDate, setCurrentDate] = useState<Date | null>(null)

  useEffect(() => {
    const updateDate = () => setCurrentDate(new Date())
    updateDate()

    const interval = window.setInterval(updateDate, 60_000)
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
  const [filter, setFilter] = useState<'all' | TableStatus>('all')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [notice, setNotice] = useState('')

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

  const showNotice = (message: string) => {
    setNotice(message)
    window.setTimeout(() => setNotice(''), 3000)
  }

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
          <button className="nav-item" onClick={() => showNotice('Settings will be available soon.')}>
            <Settings2 size={17} /><span>Settings</span>
          </button>
          <button className="nav-item" onClick={() => showNotice('Help centre will be available soon.')}>
            <CircleHelp size={17} /><span>Help & support</span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="plan-card">
            <div className="plan-icon"><Sparkles size={15} /></div>
            <strong>Smarter service starts here</strong>
            <p>Keep your tables moving and your team one step ahead.</p>
            <button className="plan-link" onClick={() => showNotice('More about RestroMind coming soon.')}>
              Explore features <ArrowRight size={12} style={{ verticalAlign: 'middle' }} />
            </button>
          </div>
          <div className="profile">
            <div className="avatar">
              {user.name
                .split(/\s+/)
                .filter(Boolean)
                .slice(0, 2)
                .map((part) => part[0].toUpperCase())
                .join('')}
            </div>
            <div className="profile-copy">
              <div className="profile-name">{user.name}</div>
              <div className="profile-role">
                {user.role.replaceAll('_', ' ')}
              </div>
            </div>
            <button
              className="profile-logout"
              onClick={logout}
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
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
            <button
              className="icon-button"
              aria-label={`Notifications, ${openAlerts.length} open alerts`}
              onClick={() => showNotice(
                openAlerts.length === 0
                  ? 'You have no open alerts.'
                  : `You have ${openAlerts.length} open alert${openAlerts.length === 1 ? '' : 's'}.`,
              )}
            >
              <Bell size={16} />
              {openAlerts.length > 0 && <span className="notification-dot" />}
            </button>
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
          </div>
        )}

        <div style={{ display: activeNav === 'Table management' ? 'block' : 'none' }}>
          <TableManagement />
        </div>

        <div style={{ display: activeNav === 'Live monitoring' ? 'block' : 'none' }}>
          <LiveMonitoring />
        </div>

        <div style={{ display: activeNav === 'Cleaning tasks' ? 'block' : 'none' }}>
          <CleaningTasks />
        </div>

        <div style={{ display: activeNav === 'Staff' ? 'block' : 'none' }}>
          <Staff />
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
                      {' '}Recent activity below is sample content.
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
            <section className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Floor overview</div>
                  <div className="panel-caption">Current table status from your database</div>
                </div>
                <button className="text-action" onClick={() => showNotice('Full floor plan is coming soon.')}>
                  View floor plan <ArrowRight size={12} style={{ verticalAlign: 'middle' }} />
                </button>
              </div>

              <div className="floor-summary">
                <FloorPill color="#6d9a70" label="Available" count={String(availableCount)} />
                <FloorPill color="#6d8870" label="Occupied" count={String(occupiedCount)} />
                <FloorPill color="#d1a052" label="Needs cleaning" count={String(cleaningCount)} />
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
                  visibleTables.map((table) => (
                    <button
                      className={`table-card ${table.status}`}
                      key={table.id}
                      onClick={() => showNotice(`${table.tableNumber} · ${table.name} · ${statusLabels[table.status]}`)}
                    >
                      <div className="table-top">
                        <span className="table-number">{table.tableNumber}</span>
                        <span className="table-seats">{table.name}</span>
                      </div>
                      <div className="table-status">
                        <span
                          className="legend-dot"
                          style={{
                            background: table.status === 'cleaning'
                              ? '#d1a052'
                              : table.status === 'occupied'
                                ? '#6d8870'
                                : '#6d9a70',
                          }}
                        />
                        {statusLabels[table.status]}
                      </div>
                      <div className="table-location">Table ID: {table.id}</div>
                    </button>
                  ))
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
                    <div className="panel-caption">Sample activity · history API not connected</div>
                  </div>
                  <Activity size={15} color="#9aa49b" />
                </div>
                <div className="activity-list">
                  <ActivityItem color="#6c9b70" text={<><strong>Table 04</strong> became occupied</>} time="2:41 PM" />
                  <ActivityItem color="#d1a052" text={<><strong>Table 03</strong> marked for cleaning</>} time="2:37 PM" />
                  <ActivityItem color="#6c9b70" text={<><strong>Table 01</strong> is now available</>} time="2:29 PM" />
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
