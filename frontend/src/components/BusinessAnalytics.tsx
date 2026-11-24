import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FileSpreadsheet,
  FileText,
  RefreshCw,
  Save,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  downloadBusinessAnalytics,
  getBusinessAnalytics,
  getRestaurantProfile,
  updateRestaurantProfile,
} from '../services/api'
import './BusinessAnalytics.css'

type Period = 'daily' | 'monthly' | 'yearly' | 'custom'

function localDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getPeriodDates(period: Period): [string, string] {
  const now = new Date()
  const today = localDate(now)

  if (period === 'daily') return [today, today]

  if (period === 'monthly') {
    return [
      localDate(new Date(now.getFullYear(), now.getMonth(), 1)),
      today,
    ]
  }

  if (period === 'yearly') {
    return [localDate(new Date(now.getFullYear(), 0, 1)), today]
  }

  return [today, today]
}

function formatMoney(value: number, currency: string): string {
  return `${currency} ${Number(value || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatPercent(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return 'No previous data'
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`
}

export default function BusinessAnalytics() {
  const queryClient = useQueryClient()
  const [period, setPeriod] = useState<Period>('monthly')
  const [dates, setDates] = useState<[string, string]>(() =>
    getPeriodDates('monthly'),
  )
  const [restaurantNameDraft, setRestaurantNameDraft] = useState<string | null>(null)
  const [currencyDraft, setCurrencyDraft] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [downloadLoading, setDownloadLoading] = useState<'pdf' | 'csv' | null>(
    null,
  )

  const reportQuery = useQuery({
    queryKey: ['business-analytics', dates[0], dates[1]],
    queryFn: () => getBusinessAnalytics(dates[0], dates[1]),
    enabled: Boolean(dates[0] && dates[1] && dates[0] <= dates[1]),
  })

  const profileQuery = useQuery({
    queryKey: ['restaurant-profile'],
    queryFn: getRestaurantProfile,
  })

  const restaurantName = restaurantNameDraft ?? profileQuery.data?.restaurant_name ?? ''
  const currency = currencyDraft ?? profileQuery.data?.currency ?? 'PKR'

  const saveProfile = useMutation({
    mutationFn: updateRestaurantProfile,
    onSuccess: async (profile) => {
      setRestaurantNameDraft(profile.restaurant_name)
      setCurrencyDraft(profile.currency)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['restaurant-profile'] }),
        queryClient.invalidateQueries({ queryKey: ['business-analytics'] }),
      ])
      setMessage('Restaurant profile saved.')
    },
    onError: (error) => {
      setMessage(error instanceof Error ? error.message : 'Could not save profile.')
    },
  })

  const report = reportQuery.data
  const summary = report?.summary
  const comparison = report?.comparison
  const methods = report
    ? Object.entries(report.payment_methods).map(([name, values]) => ({
        name,
        paid: values.paid,
        pending: values.pending,
        failed: values.failed,
        refunded: values.refunded,
      }))
    : []

  const paymentStatusData = report
    ? [
        { name: 'Paid', value: report.summary.paid_orders },
        { name: 'Pending / unpaid', value: report.summary.pending_orders },
        { name: 'Failed', value: report.summary.failed_orders },
        { name: 'Refunded', value: report.summary.refunded_orders },
      ].filter((entry) => entry.value > 0)
    : []

  const handlePeriod = (nextPeriod: Period) => {
    setPeriod(nextPeriod)
    if (nextPeriod !== 'custom') setDates(getPeriodDates(nextPeriod))
  }

  const handleDownload = async (format: 'pdf' | 'csv') => {
    setDownloadLoading(format)
    setMessage('')
    try {
      await downloadBusinessAnalytics(format, dates[0], dates[1])
      setMessage(`${format.toUpperCase()} report downloaded.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Download failed.')
    } finally {
      setDownloadLoading(null)
    }
  }

  const handleSaveProfile = () => {
    if (restaurantName.trim().length < 2) {
      setMessage('Enter a restaurant name with at least 2 characters.')
      return
    }
    saveProfile.mutate({
      restaurant_name: restaurantName.trim(),
      currency: currency.trim().toUpperCase(),
    })
  }

  return (
    <section className="content business-analytics">
      <div className="welcome-row analytics-heading">
        <div>
          <div className="eyebrow">BUSINESS PERFORMANCE</div>
          <h1 className="page-title">Business Analytics</h1>
          <p className="page-subtitle">
            Understand your orders, confirmed payments, and sales trends.
          </p>
        </div>
        <button
          className="analytics-refresh"
          onClick={() => void reportQuery.refetch()}
          disabled={reportQuery.isFetching}
        >
          <RefreshCw size={15} className={reportQuery.isFetching ? 'analytics-spin' : ''} />
          Refresh
        </button>
      </div>

      <div className="analytics-panel analytics-profile">
        <div className="analytics-panel-heading">
          <div>
            <h2>Restaurant report identity</h2>
            <p>This name and currency will appear on exported reports.</p>
          </div>
        </div>
        <div className="analytics-profile-fields">
          <label>
            Restaurant name
            <input
              value={restaurantName}
              onChange={(event) => setRestaurantNameDraft(event.target.value)}
              placeholder="Enter your restaurant name"
              maxLength={150}
            />
          </label>
          <label>
            Currency
            <select
              value={currency}
              onChange={(event) => setCurrencyDraft(event.target.value)}
            >
              <option value="PKR">PKR — Pakistani Rupee</option>
              <option value="USD">USD — US Dollar</option>
              <option value="GBP">GBP — British Pound</option>
              <option value="AED">AED — UAE Dirham</option>
              <option value="SAR">SAR — Saudi Riyal</option>
              <option value="EUR">EUR — Euro</option>
            </select>
          </label>
          <button
            className="analytics-primary-button"
            onClick={handleSaveProfile}
            disabled={saveProfile.isPending}
          >
            <Save size={15} />
            {saveProfile.isPending ? 'Saving...' : 'Save profile'}
          </button>
        </div>
      </div>

      <div className="analytics-toolbar">
        <div className="analytics-periods">
          {(['daily', 'monthly', 'yearly', 'custom'] as Period[]).map((item) => (
            <button
              key={item}
              className={period === item ? 'selected' : ''}
              onClick={() => handlePeriod(item)}
            >
              {item.charAt(0).toUpperCase() + item.slice(1)}
            </button>
          ))}
        </div>
        <div className="analytics-date-fields">
          <label>
            <CalendarDays size={14} />
            <input
              type="date"
              value={dates[0]}
              max={dates[1]}
              onChange={(event) => {
                setPeriod('custom')
                setDates([event.target.value, dates[1]])
              }}
            />
          </label>
          <span>to</span>
          <label>
            <CalendarDays size={14} />
            <input
              type="date"
              value={dates[1]}
              min={dates[0]}
              onChange={(event) => {
                setPeriod('custom')
                setDates([dates[0], event.target.value])
              }}
            />
          </label>
        </div>
        <div className="analytics-downloads">
          <button onClick={() => void handleDownload('pdf')} disabled={!!downloadLoading || !report}>
            <FileText size={15} />
            {downloadLoading === 'pdf' ? 'Preparing...' : 'PDF report'}
          </button>
          <button onClick={() => void handleDownload('csv')} disabled={!!downloadLoading || !report}>
            <FileSpreadsheet size={15} />
            {downloadLoading === 'csv' ? 'Preparing...' : 'CSV export'}
          </button>
        </div>
      </div>

      {message && <div className="analytics-message">{message}</div>}

      {dates[0] > dates[1] && (
        <div className="analytics-error">Start date must be before or equal to end date.</div>
      )}

      {reportQuery.isLoading && (
        <div className="analytics-empty">Loading business analytics...</div>
      )}

      {reportQuery.isError && (
        <div className="analytics-error">
          {reportQuery.error instanceof Error
            ? reportQuery.error.message
            : 'Could not load analytics. Check your management access and API connection.'}
        </div>
      )}

      {report && summary && comparison && (
        <>
          <div className="analytics-report-caption">
            <div>
              <strong>{report.restaurant_name}</strong>
              <span>{report.start_date} to {report.end_date}</span>
            </div>
            <span>{report.orders.length.toLocaleString()} order records</span>
          </div>

          <div className="analytics-kpi-grid">
            <article className="analytics-kpi">
              <div className="analytics-kpi-icon revenue"><Wallet size={19} /></div>
              <span>Confirmed revenue</span>
              <strong>{formatMoney(summary.confirmed_revenue, report.currency)}</strong>
              <small>{summary.paid_orders} paid orders</small>
            </article>
            <article className="analytics-kpi">
              <div className="analytics-kpi-icon sales"><Activity size={19} /></div>
              <span>Gross order value</span>
              <strong>{formatMoney(summary.gross_order_value, report.currency)}</strong>
              <small>{summary.orders} non-cancelled orders</small>
            </article>
            <article className="analytics-kpi">
              <div className="analytics-kpi-icon pending"><Clock3 size={19} /></div>
              <span>Outstanding amount</span>
              <strong>{formatMoney(summary.outstanding_amount, report.currency)}</strong>
              <small>{summary.pending_orders} pending or unpaid</small>
            </article>
            <article className="analytics-kpi">
              <div className="analytics-kpi-icon average"><CheckCircle2 size={19} /></div>
              <span>Average order value</span>
              <strong>{formatMoney(summary.average_order_value, report.currency)}</strong>
              <small>Based on non-cancelled orders</small>
            </article>
          </div>

          <div className="analytics-comparison-grid">
            <article className="analytics-comparison">
              <span>Gross order value vs previous period</span>
              <strong>{formatPercent(comparison.gross_change_percent)}</strong>
              {comparison.gross_change_percent !== null &&
                (comparison.gross_change_percent >= 0
                  ? <TrendingUp size={18} />
                  : <TrendingDown size={18} />)}
              <small>
                Previous: {formatMoney(comparison.previous_gross_order_value, report.currency)}
              </small>
            </article>
            <article className="analytics-comparison">
              <span>Confirmed revenue vs previous period</span>
              <strong>{formatPercent(comparison.revenue_change_percent)}</strong>
              {comparison.revenue_change_percent !== null &&
                (comparison.revenue_change_percent >= 0
                  ? <TrendingUp size={18} />
                  : <TrendingDown size={18} />)}
              <small>
                Previous: {formatMoney(comparison.previous_confirmed_revenue, report.currency)}
              </small>
            </article>
            <article className="analytics-comparison">
              <span>Payment status</span>
              <strong>{summary.paid_orders} / {summary.orders}</strong>
              <small>
                {summary.failed_orders} failed · {summary.refunded_orders} refunded · {summary.cancelled_orders} cancelled
              </small>
            </article>
          </div>

          <div className="analytics-chart-grid">
            <article className="analytics-panel">
              <div className="analytics-panel-heading">
                <div>
                  <h2>Sales trend</h2>
                  <p>Daily gross order value and confirmed payments</p>
                </div>
              </div>
              <div className="analytics-chart">
                {report.daily_sales.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={report.daily_sales}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={25} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(value) => formatMoney(Number(value), report.currency)} />
                      <Legend />
                      <Line type="monotone" dataKey="sales" name="Gross order value" stroke="#426348" strokeWidth={2.5} dot={false} />
                      <Line type="monotone" dataKey="received" name="Confirmed revenue" stroke="#d49a45" strokeWidth={2.5} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="analytics-chart-empty">No sales data for this period.</div>
                )}
              </div>
            </article>

            <article className="analytics-panel">
              <div className="analytics-panel-heading">
                <div>
                  <h2>Payment status breakdown</h2>
                  <p>Number of orders by payment status</p>
                </div>
              </div>
              <div className="analytics-chart">
                {paymentStatusData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={paymentStatusData} dataKey="value" nameKey="name" cx="50%" cy="48%" outerRadius={100} label>
                        {paymentStatusData.map((entry, index) => (
                          <Cell key={entry.name} fill={['#426348', '#d49a45', '#bd6258', '#7c78a8'][index % 4]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="analytics-chart-empty">No payment records for this period.</div>
                )}
              </div>
            </article>
          </div>

          <article className="analytics-panel analytics-payment-panel">
            <div className="analytics-panel-heading">
              <div>
                <h2>Payment methods</h2>
                <p>Confirmed, pending, failed and refunded amounts by method</p>
              </div>
            </div>
            <div className="analytics-chart analytics-payment-chart">
              {methods.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={methods} margin={{ top: 8, right: 20, left: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value) => formatMoney(Number(value), report.currency)} />
                    <Legend />
                    <Bar dataKey="paid" name="Confirmed" fill="#426348" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="pending" name="Pending" fill="#d49a45" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="failed" name="Failed" fill="#bd6258" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="refunded" name="Refunded" fill="#7c78a8" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="analytics-chart-empty">No payment methods recorded.</div>
              )}
            </div>
          </article>

          <article className="analytics-panel analytics-orders-panel">
            <div className="analytics-panel-heading">
              <div>
                <h2>Order details</h2>
                <p>Real orders recorded during the selected reporting period</p>
              </div>
              <span>{report.orders.length} records</span>
            </div>
            <div className="analytics-table-wrap">
              <table className="analytics-table">
                <thead>
                  <tr>
                    <th>Order number</th>
                    <th>Table</th>
                    <th>Date / time</th>
                    <th>Total</th>
                    <th>Payment method</th>
                    <th>Payment status</th>
                    <th>Transaction reference</th>
                  </tr>
                </thead>
                <tbody>
                  {report.orders.length ? report.orders.map((order) => (
                    <tr key={order.order_number}>
                      <td>{order.order_number}</td>
                      <td>{order.table_number}</td>
                      <td>{new Date(order.created_at).toLocaleString()}</td>
                      <td>{formatMoney(order.total, report.currency)}</td>
                      <td>{order.payment_method}</td>
                      <td>
                        <span className={`analytics-status ${order.payment_status.toLowerCase()}`}>
                          {order.payment_status}
                        </span>
                      </td>
                      <td>{order.transaction_reference || 'Not recorded'}</td>
                    </tr>
                  )) : (
                    <tr><td colSpan={7} className="analytics-no-orders">No orders found for this period.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>
        </>
      )}
    </section>
  )
}
