import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, CheckCircle2, Clock3, RefreshCw, UserRound } from 'lucide-react'
import {
  getServiceRequests,
  confirmOrderPayment,
  updateServiceRequestStatus,
  type RestaurantServiceRequest,
} from '../services/api'
import './ServiceRequests.css'

function formatRequestTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Time unavailable'

  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function requestLabel(request: RestaurantServiceRequest) {
  const labels: Record<string, string> = {
    CALL_WAITER: 'Call waiter',
    WATER: 'Request water',
    TISSUES: 'Request tissues',
    CUTLERY: 'Request cutlery',
    BILL: 'Request bill',
    WIFI: 'Wi-Fi details',
    OTHER: 'Other assistance',
  }
  return labels[request.request_type] ?? request.request_type
}

export default function ServiceRequests() {
  const queryClient = useQueryClient()

  const requestsQuery = useQuery({
    queryKey: ['service-requests'],
    queryFn: getServiceRequests,
    refetchInterval: 5000,
  })

  const statusMutation = useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: number
      status: 'ACKNOWLEDGED' | 'COMPLETED'
    }) => updateServiceRequestStatus(id, status),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['service-requests'] }),
  })

  const paymentMutation = useMutation({
    mutationFn: confirmOrderPayment,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['service-requests'] }),
        queryClient.invalidateQueries({ queryKey: ['order-tracking'] }),
        queryClient.invalidateQueries({ queryKey: ['alerts'] }),
        queryClient.invalidateQueries({ queryKey: ['restaurant-tables'] }),
      ])
    },
  })

  const requests = requestsQuery.data ?? []
  const open = requests.filter((item) => item.status === 'OPEN')
  const acknowledged = requests.filter((item) => item.status === 'ACKNOWLEDGED')
  const completed = requests.filter((item) => item.status === 'COMPLETED')

  function renderRequest(item: RestaurantServiceRequest) {
    const busy = statusMutation.isPending &&
      statusMutation.variables?.id === item.id

    return (
      <article className="service-request-card" key={item.id}>
        <div className="service-request-card-top">
          <div>
            <span className="service-request-table">
              Table {item.table_number}
            </span>
            <h3>{requestLabel(item)}</h3>
          </div>
          <span className={`service-request-status ${item.status.toLowerCase()}`}>
            {item.status.replace('_', ' ')}
          </span>
        </div>

        {item.message && <p className="service-request-message">{item.message}</p>}

        <div className="service-request-meta">
          <span><Clock3 size={14} /> {formatRequestTime(item.created_at)}</span>
          {item.handled_by_staff_name && (
            <span><UserRound size={14} /> {item.handled_by_staff_name}</span>
          )}
        </div>

        <div className="service-request-actions">
          {item.status === 'OPEN' && (
            <button
              type="button"
              disabled={busy}
              onClick={() => statusMutation.mutate({
                id: item.id,
                status: 'ACKNOWLEDGED',
              })}
            >
              <Check size={15} /> Acknowledge
            </button>
          )}
          {item.status === 'ACKNOWLEDGED' && item.request_type === 'BILL' && item.order_id !== null && (
            <button
              type="button"
              disabled={paymentMutation.isPending}
              onClick={() => {
                if (window.confirm('Confirm that the restaurant has actually received this payment?')) {
                  paymentMutation.mutate(item.order_id!)
                }
              }}
            >
              <CheckCircle2 size={15} /> Confirm payment received
            </button>
          )}
          {item.status === 'ACKNOWLEDGED' && !(item.request_type === 'BILL' && item.order_id !== null) && (
            <button
              type="button"
              disabled={busy}
              onClick={() => statusMutation.mutate({
                id: item.id,
                status: 'COMPLETED',
              })}
            >
              <CheckCircle2 size={15} /> Mark completed
            </button>
          )}
        </div>
      </article>
    )
  }

  return (
    <main className="service-requests-workspace">
      <header className="service-requests-header">
        <div>
          <p className="service-requests-eyebrow">RESTAURANT OPERATIONS</p>
          <h1>Customer service requests</h1>
          <p>Respond to assistance requests sent from customer table QR codes.</p>
        </div>
        <button
          type="button"
          className="service-refresh-button"
          onClick={() => queryClient.invalidateQueries({ queryKey: ['service-requests'] })}
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </header>

      {requestsQuery.isLoading && <p>Loading customer requests...</p>}
      {requestsQuery.isError && (
        <p className="ordering-error">
          {requestsQuery.error.message}
        </p>
      )}
      {statusMutation.isError && (
        <p className="ordering-error">
          {statusMutation.error.message}
        </p>
      )}
      {paymentMutation.isError && (
        <p className="ordering-error">{paymentMutation.error.message}</p>
      )}

      {!requestsQuery.isLoading && !requestsQuery.isError && (
        <>
          <section className="service-request-summary">
            <div><strong>{open.length}</strong><span>New requests</span></div>
            <div><strong>{acknowledged.length}</strong><span>Being handled</span></div>
            <div><strong>{completed.length}</strong><span>Completed</span></div>
          </section>

          <section className="service-request-section">
            <h2>New requests</h2>
            {open.length ? open.map(renderRequest) : <p className="service-empty">No new requests.</p>}
          </section>

          <section className="service-request-section">
            <h2>Being handled</h2>
            {acknowledged.length
              ? acknowledged.map(renderRequest)
              : <p className="service-empty">No requests are being handled.</p>}
          </section>

          <section className="service-request-section">
            <h2>Completed requests</h2>
            {completed.length
              ? completed.slice(0, 20).map(renderRequest)
              : <p className="service-empty">No completed requests yet.</p>}
          </section>
        </>
      )}
    </main>
  )
}
