import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import {
  createMenuItem,
  getSharedTableCart,
  changeSharedCartItem,
  submitSharedTableCart,
  createServiceRequest,
  deleteMenuItem,
  getKitchenOrders,
  getManagedMenu,
  getOrderTracking,
  markOrderEatingComplete,
  selectOrderPayment,
  submitOrderFeedback,
  getPublicMenu,
  getPublicRestaurantTable,
  getPublicOrderServiceRequests,
  getTableRewards,
  submitTableRewardAnswer,
  getRestaurantTables,
  updateMenuItem,
  updateRestaurantOrderStatus,
  type MenuItem,
  type OrderStatus,
  type RestaurantOrder,
  type TableRewards,
  type ServiceRequestType,
} from '../services/api'
import './OrderingPages.css'

const money = (value: number | string) =>
  `Rs. ${Number(value).toLocaleString('en-PK', { maximumFractionDigits: 2 })}`

const statusText: Record<OrderStatus, string> = {
  NEW: 'New order',
  PREPARING: 'Preparing',
  READY: 'Ready to serve',
  SERVED: 'Served',
  CANCELLED: 'Cancelled',
}

const ALLERGY_OPTIONS = [
  'Peanuts',
  'Tree nuts',
  'Dairy',
  'Gluten',
  'Eggs',
  'Soy',
  'Seafood',
  'Sesame',
  'Mustard',
]

function elapsedSeconds(createdAt: string, now: number) {
  const created = new Date(createdAt).getTime()
  return Math.max(0, Math.floor((now - created) / 1000))
}

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  const remaining = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(remaining).padStart(2, '0')}`
}

function formatTableLabel(tableNumber?: string | null, fallbackId?: number) {
  if (!tableNumber) return fallbackId ? `Table ${fallbackId}` : 'your table'
  const numericPart = tableNumber.match(/\d+/)?.[0]
  return numericPart ? `Table ${Number(numericPart)}` : `Table ${tableNumber}`
}

function CustomerServicePanel({
  tableId,
  orderToken,
  wifiOnly = false,
}: {
  tableId: number
  orderToken: string
  wifiOnly?: boolean
}) {
  const [message, setMessage] = useState('')
  const queryClient = useQueryClient()

  const requestsQuery = useQuery({
    queryKey: ['public-service-requests', orderToken],
    queryFn: () => getPublicOrderServiceRequests(orderToken),
    enabled: tableId > 0 && Boolean(orderToken),
    refetchInterval: 3000,
  })

  const mutation = useMutation({
    mutationFn: createServiceRequest,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['public-service-requests', orderToken],
      })
      queryClient.invalidateQueries({ queryKey: ['service-requests'] })
      setMessage('')
    },
  })

  const choices: [ServiceRequestType, string][] = wifiOnly
    ? [['WIFI', 'Request Wi-Fi details']]
    : [
        ['CALL_WAITER', 'Call waiter'],
        ['WATER', 'Request water'],
        ['TISSUES', 'Request tissues'],
        ['CUTLERY', 'Request cutlery'],
        ['BILL', 'Request bill'],
        ['OTHER', 'Other assistance'],
      ]

  const requestLabels: Record<string, string> = {
    CALL_WAITER: 'Call waiter',
    WATER: 'Water',
    TISSUES: 'Tissues',
    CUTLERY: 'Cutlery',
    BILL: 'Bill',
    WIFI: 'Wi-Fi details',
    OTHER: 'Other assistance',
  }

  function customerStatus(request: {
    request_type: string
    status: string
  }) {
    if (request.status === 'COMPLETED') return 'Your request has been completed.'
    if (request.status === 'OPEN') return 'Waiting for staff to accept your request.'
    if (request.request_type === 'CALL_WAITER') {
      return 'Your waiter has accepted the request and is coming.'
    }
    if (request.request_type === 'WATER') {
      return 'Your water request has been accepted. Water is on the way.'
    }
    if (request.request_type === 'WIFI') {
      return 'Staff has accepted your request and will share the Wi-Fi details.'
    }
    return 'Staff has accepted your request and is handling it.'
  }

  return (
    <section className="customer-service-panel">
      <div>
        <p className="ordering-eyebrow">
          {wifiOnly ? 'RESTAURANT WI-FI' : 'TABLE ASSISTANCE'}
        </p>
        <h2>{wifiOnly ? 'Connect to Wi-Fi' : 'Need help?'}</h2>
        <p>
          {wifiOnly
            ? 'Request the restaurant Wi-Fi network name and password from staff.'
            : 'Send a request to restaurant staff. Your request status updates automatically.'}
        </p>
      </div>

      <div className="customer-service-buttons">
        {choices.map(([requestType, label]) => (
          <button
            key={requestType}
            type="button"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({
              table_id: tableId,
              order_token: orderToken,
              request_type: requestType,
              message: requestType === 'OTHER' ? message.trim() || undefined : undefined,
            })}
          >
            {mutation.isPending ? 'Sending...' : label}
          </button>
        ))}
      </div>

      {!wifiOnly && (
        <label className="ordering-label">
          Extra details (optional)
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={250}
            placeholder="Tell us what you need"
          />
        </label>
      )}

      {mutation.isError && (
        <p className="ordering-error">{mutation.error.message}</p>
      )}

      <div className="customer-request-status-list">
        <h3>{wifiOnly ? 'Wi-Fi request status' : 'Your recent requests'}</h3>
        {requestsQuery.isLoading && (
          <p className="ordering-message">Loading request status...</p>
        )}
        {requestsQuery.isError && (
          <p className="ordering-error">{requestsQuery.error.message}</p>
        )}
        {!requestsQuery.isLoading && !requestsQuery.isError &&
          (requestsQuery.data ?? []).filter((request) =>
            wifiOnly ? request.request_type === 'WIFI' : true
          ).slice(0, 8).map((request) => (
            <article className="customer-request-status" key={request.id}>
              <strong>{requestLabels[request.request_type] ?? request.request_type}</strong>
              <span>{customerStatus(request)}</span>
              {request.message && <small>{request.message}</small>}
              {request.handled_by_staff_name && (
                <small>Accepted by {request.handled_by_staff_name}</small>
              )}
            </article>
          ))}
        {!requestsQuery.isLoading && !requestsQuery.isError &&
          (requestsQuery.data ?? []).filter((request) =>
            wifiOnly ? request.request_type === 'WIFI' : true
          ).length === 0 && (
            <p className="ordering-message">You have no recent requests.</p>
          )}
      </div>
    </section>
  )
}


function escapeCustomerWifiValue(value: string): string {
  return value.replace(/([\\;,:"])/g, '\\$1')
}

function CustomerWifiPanel() {
  const wifiQuery = useQuery({
    queryKey: ['public-wifi-settings'],
    queryFn: async () => {
      const response = await fetch('/api/v1/wifi/public')
      if (!response.ok) throw new Error('Could not load restaurant Wi-Fi details.')
      return response.json() as Promise<{
        is_enabled: boolean
        ssid?: string
        password?: string
      }>
    },
    staleTime: 60_000,
  })

  const [showPassword, setShowPassword] = useState(false)
  const wifi = wifiQuery.data

  if (wifiQuery.isLoading) {
    return <section className="customer-service-panel"><p>Loading Wi-Fi details...</p></section>
  }

  if (wifiQuery.isError || !wifi?.is_enabled || !wifi.ssid || !wifi.password) {
    return (
      <section className="customer-service-panel">
        <p className="ordering-eyebrow">RESTAURANT WI-FI</p>
        <h2>Wi-Fi is currently unavailable</h2>
        <p>Please ask a member of staff for assistance.</p>
      </section>
    )
  }

  const qrValue = `WIFI:T:WPA;S:${escapeCustomerWifiValue(wifi.ssid)};P:${escapeCustomerWifiValue(wifi.password)};;`

  return (
    <section className="customer-service-panel">
      <p className="ordering-eyebrow">RESTAURANT WI-FI</p>
      <h2>Connect to our Wi-Fi</h2>
      <p>Scan this QR code with your phone camera to connect automatically.</p>
      <div style={{ display: 'flex', justifyContent: 'center', padding: 18, background: '#fff', borderRadius: 12, margin: '18px auto', width: 'fit-content' }}>
        <QRCodeSVG value={qrValue} size={190} level="M" />
      </div>
      <div style={{ padding: 14, border: '1px solid #e4eae3', borderRadius: 10 }}>
        <p style={{ margin: '0 0 5px', color: '#829087', fontSize: 11 }}>NETWORK NAME</p>
        <strong>{wifi.ssid}</strong>
        <p style={{ margin: '15px 0 5px', color: '#829087', fontSize: 11 }}>PASSWORD</p>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
          <strong>{showPassword ? wifi.password : '••••••••••••'}</strong>
          <button type="button" onClick={() => setShowPassword((value) => !value)} style={{ border: 0, background: 'transparent', color: '#315b43', cursor: 'pointer' }}>
            {showPassword ? 'Hide' : 'Show'}
          </button>
          <button type="button" onClick={() => void navigator.clipboard.writeText(wifi.password!)} style={{ border: 0, background: 'transparent', color: '#315b43', cursor: 'pointer' }}>
            Copy
          </button>
        </div>
      </div>
    </section>
  )
}

function CustomerRewardsPanel({ tableId }: { tableId: number }) {
  const queryClient = useQueryClient()
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null)

  const rewardsQuery = useQuery({
    queryKey: ["table-rewards", tableId],
    queryFn: () => getTableRewards(tableId),
    enabled: tableId > 0,
  })

  const answerMutation = useMutation({
    mutationFn: (answerIndex: number) =>
      submitTableRewardAnswer(tableId, answerIndex),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["table-rewards", tableId] })
    },
  })

  const rewards: TableRewards | undefined = rewardsQuery.data

  return (
    <section className="customer-rewards-panel">
      <div className="customer-rewards-heading">
        <div>
          <p className="ordering-eyebrow">RESTROMIND REWARDS</p>
          <h2>Play & earn points</h2>
          <p>Answer today's food trivia question to earn reward points.</p>
        </div>
        <div className="customer-rewards-balance">
          <strong>{rewards?.points ?? 0}</strong>
          <span>Points</span>
        </div>
      </div>

      {rewardsQuery.isLoading && (
        <p className="ordering-message">Loading today's challenge...</p>
      )}
      {rewardsQuery.isError && (
        <p className="ordering-error">Could not load rewards. Please try again later.</p>
      )}

      {rewards && (
        <div className="customer-rewards-game">
          <span className="customer-rewards-daily">DAILY CHALLENGE · +10 POINTS</span>
          <h3>{rewards.question}</h3>

          {rewards.already_played ? (
            <div className="customer-rewards-result">
              <strong>
                {rewards.last_answer_correct
                  ? "Correct answer! Well done."
                  : "Today's attempt has been used."}
              </strong>
              <p>
                {rewards.points_awarded_today > 0
                  ? `You earned ${rewards.points_awarded_today} points today.`
                  : "Try the next daily challenge to earn points."}
              </p>
            </div>
          ) : (
            <>
              <div className="customer-rewards-options">
                {rewards.options.map((option, index) => (
                  <button
                    type="button"
                    key={option}
                    className={selectedAnswer === index ? "selected" : ""}
                    disabled={answerMutation.isPending}
                    onClick={() => setSelectedAnswer(index)}
                  >
                    {option}
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="customer-rewards-submit"
                disabled={selectedAnswer === null || answerMutation.isPending}
                onClick={() => {
                  if (selectedAnswer !== null) {
                    answerMutation.mutate(selectedAnswer)
                  }
                }}
              >
                {answerMutation.isPending ? "Checking..." : "Submit answer"}
              </button>
              {answerMutation.isError && (
                <p className="ordering-error">{answerMutation.error.message}</p>
              )}
              {answerMutation.isSuccess && (
                <p className="customer-service-success">
                  {answerMutation.data.correct
                    ? `Correct! You earned ${answerMutation.data.points_awarded} points.`
                    : "Not quite! Try tomorrow's challenge for another chance."}
                </p>
              )}
            </>
          )}
        </div>
      )}
      <p className="ordering-footnote">
        Points are currently shared by this table and are not yet linked to an individual customer account.
      </p>
    </section>
  )
}

function CustomerMiniGame() {
  const [cells, setCells] = useState<(string | null)[]>(Array(9).fill(null))
  const [turn, setTurn] = useState<'X' | 'O'>('X')
  const [finished, setFinished] = useState(false)

  const lines = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],
    [0, 3, 6], [1, 4, 7], [2, 5, 8],
    [0, 4, 8], [2, 4, 6],
  ]
  const winner = lines
    .map(([a, b, c]) => cells[a] && cells[a] === cells[b] && cells[a] === cells[c] ? cells[a] : null)
    .find(Boolean)

  function play(index: number) {
    if (cells[index] || finished || winner) return
    const next = [...cells]
    next[index] = turn
    setCells(next)
    setTurn(turn === 'X' ? 'O' : 'X')
    if (next.every(Boolean) || lines.some(([a, b, c]) => next[a] && next[a] === next[b] && next[a] === next[c])) {
      setFinished(true)
    }
  }

  function reset() {
    setCells(Array(9).fill(null))
    setTurn('X')
    setFinished(false)
  }

  return (
    <section className="customer-game-panel">
      <p className="ordering-eyebrow">QUICK GAME</p>
      <h2>Tic-Tac-Toe</h2>
      <p>{winner ? `${winner} wins!` : finished ? "It's a draw!" : `Player ${turn}'s turn`}</p>
      <div className="customer-game-grid">
        {cells.map((cell, index) => (
          <button type="button" key={index} onClick={() => play(index)} disabled={Boolean(cell) || finished}>
            {cell}
          </button>
        ))}
      </div>
      <button type="button" onClick={reset}>Play again</button>
      <p className="ordering-footnote">This mini-game is for fun and does not award points.</p>
    </section>
  )
}

function CustomerShell({ children }: { children: React.ReactNode }) {
  return <main className="customer-page"><div className="customer-container">{children}</div></main>
}

// PUBLIC CUSTOMER PAGE — no AuthGate, login, or customer account.
export function CustomerOrderPage() {
  const { tableId: rawTableId } = useParams()
  const tableId = Number(rawTableId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedSizes, setSelectedSizes] = useState<Record<number, string>>({})
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [customerName, setCustomerName] = useState('')
  const [orderNotes, setOrderNotes] = useState('')
  const [allergyNotes, setAllergyNotes] = useState('')
  const [allergies, setAllergies] = useState<string[]>([])
  const [dishAllergies, setDishAllergies] = useState<Record<number, string[]>>({})
  const [dishOtherAllergies, setDishOtherAllergies] = useState<Record<number, string>>({})
  const [customizations, setCustomizations] = useState<Record<number, {
    spice: string
    extras: string
    remove: string
    instructions: string
  }>>({})

  const menuQuery = useQuery({
    queryKey: ['public-menu'],
    queryFn: getPublicMenu,
    enabled: Number.isInteger(tableId) && tableId > 0,
  })


  const tableQuery = useQuery({
    queryKey: ['public-restaurant-table', tableId],
    queryFn: () => getPublicRestaurantTable(tableId),
    enabled: Number.isInteger(tableId) && tableId > 0,
    retry: false,
  })

  const sharedCartQuery = useQuery({
    queryKey: ['shared-table-cart', tableId],
    queryFn: () => getSharedTableCart(tableId),
    enabled: Number.isInteger(tableId) && tableId > 0 && !tableQuery.isError,
    refetchInterval: 2000,
    retry: false,
  })

  const observedRound = useRef<number | null>(null)

  useEffect(() => {
    const shared = sharedCartQuery.data
    if (!shared) return
    if (observedRound.current === null) {
      observedRound.current = shared.round_number
      return
    }
    if (
      shared.round_number > observedRound.current &&
      shared.last_order_round === observedRound.current &&
      shared.last_order_token
    ) {
      navigate(`/track/${shared.last_order_token}`, { replace: true })
    }
  }, [sharedCartQuery.data, navigate])

  const sharedCartLines = sharedCartQuery.data?.cart ?? []

  const cart = Object.fromEntries(
    sharedCartLines.map((line) => [
      `${line.menu_item_id}::${line.size || 'default'}::${line.notes || ''}`,
      line.quantity,
    ]),
  ) as Record<string, number>

  const cartMutation = useMutation({
    mutationFn: (payload: {
      menu_item_id: number
      size?: string | null
      quantity_delta: number
      notes?: string | null
    }) => changeSharedCartItem(tableId, payload),
    onSuccess: (updatedCart) => {
      queryClient.setQueryData(['shared-table-cart', tableId], updatedCart)
    },
  })

  const items = menuQuery.data ?? []
  const isFoodAllergyRelevant = (item: MenuItem) => {
    const category = item.category.toLowerCase()
    const name = item.name.toLowerCase()
    if (category.includes('drink') || category.includes('juice')) return false
    if (category.includes('tea') || category.includes('coffee') || category.includes('shake')) return false
    if (/\b(water|cola|sprite|fanta|pepsi|7up|soft drink)\b/.test(name)) return false
    return true
  }
  const selectedLines = sharedCartLines.flatMap((line, index) => {
    const item = items.find((candidate) => candidate.id === line.menu_item_id)
    if (!item || line.quantity <= 0) return []
    return [{
      key: `${line.menu_item_id}::${line.size || 'default'}::${line.notes || ''}::${index}`,
      item,
      size: line.size || '',
      quantity: line.quantity,
      unitPrice: Number(line.unit_price),
      notes: line.notes || '',
    }]
  })
  const totalItems = selectedLines.reduce((sum, line) => sum + line.quantity, 0)
  const total = selectedLines.reduce(
    (sum, line) => sum + line.unitPrice * line.quantity,
    0,
  )
  const categories = [...new Set(items.map((item) => item.category))].sort()
  const visibleCategories = selectedCategory === 'All' ? categories : [selectedCategory]
  const getSelectedSize = (item: MenuItem) =>
    selectedSizes[item.id] ?? Object.keys(item.size_prices ?? {})[0] ?? ''
  const getItemNotes = (item: MenuItem) => {
    const choice = customizations[item.id]
    const details = choice ? [
      `Spice: ${choice.spice}`,
      choice.extras.trim() ? `Extras: ${choice.extras.trim()}` : '',
      choice.remove.trim() ? `Remove: ${choice.remove.trim()}` : '',
      choice.instructions.trim() ? `Instructions: ${choice.instructions.trim()}` : '',
    ].filter(Boolean).join('; ') : ''
    const selectedDishAllergies = dishAllergies[item.id] ?? []
    const otherDishAllergy = dishOtherAllergies[item.id]?.trim() ?? ''
    const allDishAllergies = [
      ...selectedDishAllergies,
      ...(otherDishAllergy ? [otherDishAllergy] : []),
    ]
    const allergyWarning = allDishAllergies.length
      ? `ALLERGY WARNING: ${allDishAllergies.join(', ')}`
      : ''
    return [allergyWarning, details].filter(Boolean).join('; ').slice(0, 300)
  }

  const getCartKey = (item: MenuItem) =>
    `${item.id}::${getSelectedSize(item) || 'default'}::${getItemNotes(item)}`

  const getCartQuantity = (item: MenuItem) =>
    cart[getCartKey(item)] ?? 0

  const getItemQuantity = (itemId: number) =>
    selectedLines
      .filter((line) => line.item.id === itemId)
      .reduce((sum, line) => sum + line.quantity, 0)

  const orderMutation = useMutation({
    mutationFn: (payload: {
      customer_name?: string | null
      notes?: string
      customer_allergies: string[]
      allergy_notes?: string
    }) => submitSharedTableCart(tableId, payload),
    onSuccess: (order) => navigate(`/track/${order.public_token}`),
  })

  if (!Number.isInteger(tableId) || tableId < 1) {
    return <CustomerShell><p className="ordering-error">This table QR link is not valid.</p></CustomerShell>
  }

  return (
    <CustomerShell>
      <header className="customer-header">
        <div className="ordering-eyebrow">RESTROMIND DIGITAL MENU</div>
        <h1>Good food, made fresh.</h1>
        <p>
          {tableQuery.isLoading
            ? 'Loading table details...'
            : tableQuery.isError
              ? 'This table QR link is not valid.'
              : `You're ordering from ${formatTableLabel(tableQuery.data?.table_number, tableId)}. No account or sign-up required.`}
        </p>
      </header>

      {tableQuery.isError ? (
        <p className="ordering-error">This table QR link is not valid. Please ask staff for help.</p>
      ) : tableQuery.isLoading ? (
        <p className="ordering-message">Loading table details...</p>
      ) : menuQuery.isLoading ? (
        <p className="ordering-message">Loading menu...</p>
      ) : menuQuery.isError ? (
        <p className="ordering-error">{menuQuery.error.message}</p>
      ) : items.length === 0 ? (
        <p className="ordering-message">The menu is currently empty. Please ask a staff member.</p>
      ) : (
        <>
          <nav className="menu-category-filter" aria-label="Menu categories">
            {['All', ...categories].map((category) => (
              <button
                type="button"
                key={category}
                className={selectedCategory === category ? 'selected' : ''}
                onClick={() => setSelectedCategory(category)}
              >
                {category}
              </button>
            ))}
          </nav>
          {visibleCategories.map((category) => (
          <section className="menu-section" key={category}>
            <h2>{category}</h2>
            <div className="menu-grid">
              {items.filter((item) => item.category === category).map((item) => (
                <article className="menu-card" key={item.id}>
                  {item.image_url && (
                    <img className="menu-image" src={item.image_url} alt={item.name} />
                  )}
                  <div className="menu-card-body">
                    <div className="menu-card-heading">
                      <h3>{item.name}</h3>
                      <strong>{money(
                        getSelectedSize(item)
                          ? item.size_prices?.[getSelectedSize(item)] ?? item.price
                          : item.price
                      )}</strong>
                    </div>
                    {Object.keys(item.size_prices ?? {}).length > 0 && (
                      <label className="menu-size-selector">
                        Choose size
                        <select
                          value={getSelectedSize(item)}
                          onChange={(event) => setSelectedSizes((old) => ({
                            ...old,
                            [item.id]: event.target.value,
                          }))}
                        >
                          {Object.entries(item.size_prices ?? {}).map(([size, sizePrice]) => (
                            <option key={size} value={size}>
                              {size} — {money(sizePrice)}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    {item.description && <p>{item.description}</p>}
                    {item.ingredients.length > 0 && (
                      <div className="menu-ingredients">
                        <strong>Ingredients:</strong> {item.ingredients.join(', ')}
                      </div>
                    )}
                    <div className="menu-tags">
                      <span>{item.spice_level.replace('_', ' ')}</span>
                      {isFoodAllergyRelevant(item) && item.allergens.length > 0 && (
                        <span>Allergens: {item.allergens.join(', ')}</span>
                      )}
                    </div>
                    {getItemQuantity(item.id) > 0 && isFoodAllergyRelevant(item) && (
                      <div className="item-customization">
                        {isFoodAllergyRelevant(item) && item.allergens.length > 0 && (
                          <div className="dish-allergy-options">
                            <strong>Are you allergic to any listed allergens?</strong>
                            {item.allergens.map((allergen) => {
                              const selected = dishAllergies[item.id] ?? []
                              const checked = selected.includes(allergen)
                              return (
                                <label key={allergen}>
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={(event) => setDishAllergies((old) => ({
                                      ...old,
                                      [item.id]: event.target.checked
                                        ? [...(old[item.id] ?? []), allergen]
                                        : (old[item.id] ?? []).filter((value) => value !== allergen),
                                    }))}
                                  />
                                  I am allergic to {allergen}
                                </label>
                              )
                            })}
                          </div>
                        )}
                        {isFoodAllergyRelevant(item) && (
                        <label className="ordering-label dish-custom-allergy">
                          Other allergy for this dish (optional)
                          <input
                            value={dishOtherAllergies[item.id] ?? ''}
                            onChange={(event) => setDishOtherAllergies((old) => ({
                              ...old,
                              [item.id]: event.target.value,
                            }))}
                            maxLength={200}
                            placeholder="Type an allergy not listed above"
                          />
                        </label>
                        )}
                        <strong>Customize this dish</strong>

                        <label>
                          Spice level
                          <select
                            value={customizations[item.id]?.spice ?? item.spice_level.replace('_', ' ')}
                            onChange={(event) => setCustomizations((old) => ({
                              ...old,
                              [item.id]: {
                                spice: event.target.value,
                                extras: old[item.id]?.extras ?? '',
                                remove: old[item.id]?.remove ?? '',
                                instructions: old[item.id]?.instructions ?? '',
                              },
                            }))}
                          >
                            <option value="NO SPICE">No spice</option>
                            <option value="MILD">Mild</option>
                            <option value="MEDIUM">Medium</option>
                            <option value="HOT">Hot</option>
                            <option value="EXTRA HOT">Extra hot</option>
                          </select>
                        </label>

                        <label>
                          Add extra ingredients
                          <input
                            value={customizations[item.id]?.extras ?? ''}
                            onChange={(event) => setCustomizations((old) => ({
                              ...old,
                              [item.id]: {
                                spice: old[item.id]?.spice ?? item.spice_level.replace('_', ' '),
                                extras: event.target.value,
                                remove: old[item.id]?.remove ?? '',
                                instructions: old[item.id]?.instructions ?? '',
                              },
                            }))}
                            placeholder="e.g. extra cheese, sauce"
                          />
                        </label>

                        <label>
                          Remove ingredients
                          <input
                            value={customizations[item.id]?.remove ?? ''}
                            onChange={(event) => setCustomizations((old) => ({
                              ...old,
                              [item.id]: {
                                spice: old[item.id]?.spice ?? item.spice_level.replace('_', ' '),
                                extras: old[item.id]?.extras ?? '',
                                remove: event.target.value,
                                instructions: old[item.id]?.instructions ?? '',
                              },
                            }))}
                            placeholder="e.g. onion, mayo"
                          />
                        </label>

                        <label>
                          Special instructions
                          <input
                            value={customizations[item.id]?.instructions ?? ''}
                            onChange={(event) => setCustomizations((old) => ({
                              ...old,
                              [item.id]: {
                                spice: old[item.id]?.spice ?? item.spice_level.replace('_', ' '),
                                extras: old[item.id]?.extras ?? '',
                                remove: old[item.id]?.remove ?? '',
                                instructions: event.target.value,
                              },
                            }))}
                            placeholder="Any other preference?"
                          />
                        </label>
                      </div>
                    )}

                    <div className="quantity-control">
                      <button
                        type="button"
                        aria-label={`Remove one ${item.name}`}
                        disabled={!getCartQuantity(item)}
                        onClick={() => cartMutation.mutate({
                          menu_item_id: item.id,
                          size: getSelectedSize(item) || null,
                          quantity_delta: -1,
                          notes: getItemNotes(item) || null,
                        })}
                      >−</button>
                      <span>{getCartQuantity(item)}</span>
                      <button
                        type="button"
                        aria-label={`Add one ${item.name}`}
                        disabled={getCartQuantity(item) >= 30}
                        onClick={() => cartMutation.mutate({
                          menu_item_id: item.id,
                          size: getSelectedSize(item) || null,
                          quantity_delta: 1,
                          notes: getItemNotes(item) || null,
                        })}
                      >+</button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
          ))}
        </>
      )}

      {sharedCartQuery.isLoading ? (
        <p className="ordering-message">Loading shared table cart...</p>
      ) : totalItems > 0 && (
        <section className="customer-checkout">
          <h2>Your order</h2>
          {selectedLines.map((line) => {
            const { item, size, quantity, unitPrice, key } = line
            return (
              <div className="checkout-line checkout-customized-line" key={key}>
                <div>
                  <span>{item.name}{size ? ` (${size})` : ''} × {quantity}</span>
                  {line.notes && <small>{line.notes}</small>}
                </div>
                <strong>{money(unitPrice * quantity)}</strong>
              </div>
            )
          })}
          <div className="checkout-total">
            <span>Total</span><strong>{money(total)}</strong>
          </div>

          <label className="ordering-label">
            Name (optional)
            <input value={customerName} onChange={(event) => setCustomerName(event.target.value)} placeholder="Guest" />
          </label>
          <div className="ordering-label">
            <span>Food allergies</span>
            <p className="allergy-help">Select anything you are allergic to. These warnings will be sent to the kitchen.</p>
            <div className="allergy-options">
              {ALLERGY_OPTIONS.map((allergy) => (
                <label key={allergy}>
                  <input
                    type="checkbox"
                    checked={allergies.includes(allergy)}
                    onChange={(event) => setAllergies((old) =>
                      event.target.checked
                        ? [...old, allergy]
                        : old.filter((value) => value !== allergy)
                    )}
                  />
                  {allergy}
                </label>
              ))}
            </div>
          </div>
          <label className="ordering-label">
            Allergy details (optional)
            <textarea value={allergyNotes} onChange={(event) => setAllergyNotes(event.target.value)} placeholder="Please tell us about any allergy concerns." />
          </label>
          <label className="ordering-label">
            Order notes (optional)
            <textarea value={orderNotes} onChange={(event) => setOrderNotes(event.target.value)} placeholder="Any special instructions?" />
          </label>

          {sharedCartQuery.isError && (
            <p className="ordering-error">{sharedCartQuery.error.message}</p>
          )}
          {cartMutation.isError && (
            <p className="ordering-error">{cartMutation.error.message}</p>
          )}
          {orderMutation.isError && (
            <p className="ordering-error">{orderMutation.error.message}</p>
          )}
          <button
            className="ordering-primary"
            disabled={orderMutation.isPending || cartMutation.isPending || sharedCartQuery.isFetching}
            onClick={() => orderMutation.mutate({
              customer_name: customerName.trim() || null,
              notes: orderNotes.trim() || undefined,
              customer_allergies: allergies,
              allergy_notes: allergyNotes.trim() || undefined,
            })}
          >
            {orderMutation.isPending ? 'Sending order...' : `Place order · ${money(total)}`}
          </button>
          <p className="ordering-footnote">Your order will be sent directly to the kitchen. Please tell restaurant staff about serious allergies. Ingredient and cross-contamination safety must be confirmed by staff.</p>
        </section>
      )}


    </CustomerShell>
  )
}


// Separate customer checkout page. Payment selection displays the bill immediately.
export function OrderCheckoutPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [method, setMethod] = useState('')
  const query = useQuery({
    queryKey: ['order-tracking', token],
    queryFn: () => getOrderTracking(token),
    enabled: Boolean(token),
    refetchInterval: 4000,
  })
  const paymentMutation = useMutation({
    mutationFn: () => selectOrderPayment(token, method),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['order-tracking', token] }),
  })

  useEffect(() => {
    if (query.data?.payment_status === 'PAID') {
      navigate(`/thank-you/${token}`, { replace: true })
    }
  }, [query.data?.payment_status, navigate, token])

  if (query.isLoading) return <CustomerShell><p className="ordering-message">Loading your bill...</p></CustomerShell>
  if (query.isError || !query.data) return <CustomerShell><p className="ordering-error">{query.error?.message ?? 'Order not found.'}</p></CustomerShell>

  const order = query.data
  const methods = ['Cash', 'Card', 'JazzCash', 'Easypaisa', 'SadaPay', 'NayaPay', 'Other bank app']

  return (
    <CustomerShell>
      <header className="customer-header">
        <p className="ordering-eyebrow">SECURE RESTAURANT CHECKOUT</p>
        <h1>Your digital bill</h1>
        <p>Order {order.order_number} · Table {order.table_id}</p>
      </header>

      <section className="tracking-card">
        <h2>Order summary</h2>
        {order.items.map((item) => (
          <div className="checkout-line checkout-customized-line" key={item.id}>
            <div>
              <span>{item.quantity} × {item.item_name}{item.size ? ` (${item.size})` : ''}</span>
              {item.notes && <small>{item.notes}</small>}
            </div>
            <strong>{money(Number(item.unit_price) * item.quantity)}</strong>
          </div>
        ))}
        <div className="checkout-total"><span>Total to pay</span><strong>{money(order.total_amount)}</strong></div>
      </section>

      {order.payment_status === 'PAID' ? (
        <section className="customer-service-success">
          <h2>Payment confirmed</h2>
          <p>Your payment has been confirmed by restaurant staff.</p>
          <strong>{money(order.total_amount)} · PAID</strong>
          {order.payment_method && <p>Method: {order.payment_method}</p>}
        </section>
      ) : (
        <section className="customer-pay-bill">
          <p className="ordering-eyebrow">PAYMENT METHOD</p>
          <h2>How would you like to pay?</h2>
          <p>Select a method to display your digital bill. Staff will verify and confirm payment.</p>
          <div className="payment-method-options">
            {methods.map((value) => (
              <button
                type="button"
                key={value}
                className={method === value ? 'selected' : ''}
                onClick={() => { setMethod(value); paymentMutation.reset() }}
              >
                {value}
              </button>
            ))}
          </div>

          {method && (
            <div className="tracking-card">
              <p className="ordering-eyebrow">DIGITAL BILL</p>
              <h2>Order {order.order_number}</h2>
              <p>Payment method: <strong>{method}</strong></p>
              <div className="checkout-total"><span>Amount due</span><strong>{money(order.total_amount)}</strong></div>
              <p className="ordering-message">
                {method === 'Cash'
                  ? 'Please pay the cashier or waiter in cash.'
                  : method === 'Card'
                    ? 'Please use the restaurant card terminal. Do not share your PIN.'
                    : 'Use your selected wallet or bank app to pay the restaurant through its verified payment instructions. Do not share your PIN or OTP.'}
              </p>
              <button
                type="button"
                className="ordering-primary"
                disabled={paymentMutation.isPending || order.payment_status === 'PENDING'}
                onClick={() => paymentMutation.mutate()}
              >
                {paymentMutation.isPending
                  ? 'Sending to staff...'
                  : order.payment_status === 'PENDING'
                    ? 'Payment request sent'
                    : 'Send payment method to staff'}
              </button>
              {paymentMutation.isError && <p className="ordering-error">{paymentMutation.error.message}</p>}
            </div>
          )}

          {order.payment_status === 'PENDING' && (
            <p className="customer-service-success">
              Payment method: {order.payment_method}{order.payment_provider ? ` (${order.payment_provider})` : ''}.
              Your payment is awaiting staff verification. It is not marked paid yet.
            </p>
          )}
        </section>
      )}
    </CustomerShell>
  )
}


// PUBLIC CUSTOMER TRACKING PAGE.
export function OrderTrackingPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const query = useQuery({
    queryKey: ['order-tracking', token],
    queryFn: () => getOrderTracking(token),
    enabled: Boolean(token),
    refetchInterval: 5000,
  })
  const trackedTableId = query.data?.table_id ?? 0
  const tableQuery = useQuery({
    queryKey: ['public-restaurant-table', trackedTableId],
    queryFn: () => getPublicRestaurantTable(trackedTableId),
    enabled: trackedTableId > 0,
    retry: false,
  })
  const [now, setNow] = useState(0)
  const [activeTab, setActiveTab] = useState<'track' | 'help' | 'rewards'>('track')
  const queryClient = useQueryClient()
  const eatingCompleteMutation = useMutation({
    mutationFn: () => markOrderEatingComplete(token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['order-tracking', token] })
      navigate(`/checkout/${token}`)
    },
  })

  useEffect(() => {
    const initialUpdate = window.setTimeout(() => setNow(Date.now()), 0)
    const interval = window.setInterval(() => setNow(Date.now()), 1000)

    return () => {
      window.clearTimeout(initialUpdate)
      window.clearInterval(interval)
    }
  }, [])

  useEffect(() => {
    if (query.data?.status === 'SERVED' && query.data.eating_completed_at) {
      navigate(`/checkout/${token}`, { replace: true })
    }
  }, [query.data?.status, query.data?.eating_completed_at, navigate, token])

  if (query.isLoading) return <CustomerShell><p className="ordering-message">Loading your order...</p></CustomerShell>
  if (query.isError || !query.data) {
    return <CustomerShell><p className="ordering-error">{query.error?.message ?? 'Order not found.'}</p></CustomerShell>
  }

  const order = query.data
  const elapsed = elapsedSeconds(order.created_at, now)
  const estimateRemaining = Math.max(0, 15 * 60 - elapsed)

  return (
    <CustomerShell>
      <header className="customer-header">
        <div className="ordering-eyebrow">ORDER TRACKING</div>
        <h1>Order {order.order_number}</h1>
        <p>{formatTableLabel(tableQuery.data?.table_number, order.table_id)} · Your order status updates automatically.</p>
      </header>
      <nav className="customer-post-order-tabs" aria-label="Customer options">
        <button type="button" className={activeTab === 'track' ? 'selected' : ''} onClick={() => setActiveTab('track')}>
          Track Order
        </button>
        <button type="button" className={activeTab === 'help' ? 'selected' : ''} onClick={() => setActiveTab('help')}>
          Call Waiter / Help
        </button>
        <button type="button" className={activeTab === 'rewards' ? 'selected' : ''} onClick={() => setActiveTab('rewards')}>
          Wi-Fi, Tasks & Rewards
        </button>
      </nav>

      {activeTab === 'track' && (
        <>
      <section className="tracking-card">
        <span className={`order-status status-${order.status.toLowerCase()}`}>{statusText[order.status]}</span>
        <div className="tracking-time">
          <span>Estimated preparation time remaining</span>
          <strong>{order.status === 'READY' || order.status === 'SERVED' ? 'Ready' : order.status === 'CANCELLED' ? 'Cancelled' : formatDuration(estimateRemaining)}</strong>
        </div>
        <p className="ordering-footnote">This is an indicative 15-minute estimate, not a guaranteed serving time.</p>
        <div className="tracking-steps">
          {(['NEW', 'PREPARING', 'READY', 'SERVED'] as OrderStatus[]).map((status) => {
            const orderStates = ['NEW', 'PREPARING', 'READY', 'SERVED']
            const activeIndex = orderStates.indexOf(order.status)
            const stepIndex = orderStates.indexOf(status)
            return (
              <div className={`tracking-step ${stepIndex <= activeIndex && order.status !== 'CANCELLED' ? 'is-done' : ''}`} key={status}>
                <span className="tracking-dot" />
                <span>{statusText[status]}</span>
              </div>
            )
          })}
        </div>
        {order.status === 'CANCELLED' && <p className="ordering-error">This order was cancelled. Please contact restaurant staff.</p>}
      </section>
      <section className="tracking-card">
        <h2>Order details</h2>
        {order.items.map((item) => (
          <div className="checkout-line checkout-customized-line" key={item.id}>
            <div>
              <span>{item.quantity} × {item.item_name}{item.size ? ` (${item.size})` : ''}</span>
              {item.notes && <small>{item.notes}</small>}
            </div>
            <strong>{money(Number(item.unit_price) * item.quantity)}</strong>
          </div>
        ))}
        {(order.customer_allergies.length > 0 || order.allergy_notes) && (
          <div className="customer-allergy-warning">
            <strong>Your allergy warnings</strong>
            <p>{order.customer_allergies.join(', ')}</p>
            {order.allergy_notes && <p>{order.allergy_notes}</p>}
          </div>
        )}
        <div className="checkout-total"><span>Total</span><strong>{money(order.total_amount)}</strong></div>
      </section>
      {order.status === 'SERVED' && !order.eating_completed_at && (
        <section className="customer-pay-bill">
          <p className="ordering-eyebrow">ENJOY YOUR MEAL</p>
          <h2>Finished eating?</h2>
          <p>When you have finished your meal, confirm below to open your bill and checkout.</p>
          <button
            type="button"
            className="ordering-primary"
            disabled={eatingCompleteMutation.isPending}
            onClick={() => eatingCompleteMutation.mutate()}
          >
            {eatingCompleteMutation.isPending ? 'Saving...' : "I'm Done Eating"}
          </button>
          {eatingCompleteMutation.isError && (
            <p className="ordering-error">{eatingCompleteMutation.error.message}</p>
          )}
        </section>
      )}

      {order.status !== 'SERVED' && order.status !== 'CANCELLED' && (
        <p className="ordering-message">
          Checkout will appear here after your order is served and you finish eating.
        </p>
      )}

      {order.eating_completed_at && order.status === 'SERVED' && (
        <section className="customer-pay-bill">
          <p className="customer-service-success">Eating complete. Your checkout is ready.</p>
          <button type="button" className="ordering-primary" onClick={() => navigate(`/checkout/${token}`)}>
            Open digital bill and checkout
          </button>
        </section>
      )}
        </>
      )}

      {activeTab === 'help' && trackedTableId > 0 && (
        <CustomerServicePanel tableId={trackedTableId} orderToken={token} />
      )}

      {activeTab === 'rewards' && trackedTableId > 0 && (
        <>
          <CustomerWifiPanel />
          <CustomerRewardsPanel tableId={trackedTableId} />
          <CustomerMiniGame />
        </>
      )}
    </CustomerShell>
  )
}

// STAFF KITCHEN DISPLAY — protected by the existing staff AuthGate.
export function KitchenDisplay() {
  const queryClient = useQueryClient()
  const [now, setNow] = useState(0)
  const [view, setView] = useState<'ACTIVE' | 'HISTORY'>('ACTIVE')
  const [filter, setFilter] = useState<'ALL' | OrderStatus>('ALL')

  const query = useQuery({
    queryKey: ['kitchen-orders', view],
    queryFn: () => getKitchenOrders(view === 'HISTORY'),
    refetchInterval: 5000,
  })
  const tablesQuery = useQuery({
    queryKey: ['restaurant-tables'],
    queryFn: getRestaurantTables,
  })

  useEffect(() => {
    const initialUpdate = window.setTimeout(() => setNow(Date.now()), 0)
    const interval = window.setInterval(() => setNow(Date.now()), 1000)

    return () => {
      window.clearTimeout(initialUpdate)
      window.clearInterval(interval)
    }
  }, [])

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: OrderStatus }) =>
      updateRestaurantOrderStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kitchen-orders'] })
      queryClient.invalidateQueries({ queryKey: ['order-tracking'] })
    },
  })

  const tableNumbers = new Map((tablesQuery.data ?? []).map((table) => [table.id, table.table_number]))
  const orders = useMemo(() => [...(query.data ?? [])].sort((a, b) => {
    if (view === 'HISTORY') {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    }
    const aAge = elapsedSeconds(a.created_at, now)
    const bAge = elapsedSeconds(b.created_at, now)
    const aLate = aAge >= 15 * 60 ? 1 : 0
    const bLate = bAge >= 15 * 60 ? 1 : 0
    return bLate - aLate || bAge - aAge
  }), [query.data, now, view])

  const visibleOrders = filter === 'ALL'
    ? orders
    : orders.filter((order) => order.status === filter)

  return (
    <section className="ordering-staff-page">
      <header className="ordering-staff-header">
        <div>
          <div className="ordering-eyebrow">RESTAURANT OPERATIONS</div>
          <h1>Kitchen {view === 'HISTORY' ? 'order history' : 'display'}</h1>
          <p>
            {view === 'HISTORY'
              ? 'Previously served and cancelled orders, newest first.'
              : 'Orders are sorted by urgency. Older and late tickets appear first.'}
          </p>
        </div>
        <div className="kitchen-count">
          {orders.length} {view === 'HISTORY' ? 'past orders' : 'active tickets'}
        </div>
      </header>

      <div className="kitchen-filters">
        <button
          className={view === 'ACTIVE' ? 'selected' : ''}
          onClick={() => { setView('ACTIVE'); setFilter('ALL') }}
        >
          Active orders
        </button>
        <button
          className={view === 'HISTORY' ? 'selected' : ''}
          onClick={() => { setView('HISTORY'); setFilter('ALL') }}
        >
          Order history
        </button>
      </div>

      {view === 'ACTIVE' && (
        <div className="kitchen-legend">
          <span className="urgency-normal">Under 10 min · Normal</span>
          <span className="urgency-warning">10–15 min · Approaching</span>
          <span className="urgency-late">15+ min · Late / priority</span>
        </div>
      )}

      <div className="kitchen-filters">
        {(view === 'ACTIVE'
          ? ['ALL', 'NEW', 'PREPARING', 'READY'] as const
          : ['ALL', 'SERVED', 'CANCELLED'] as const
        ).map((status) => (
          <button
            className={filter === status ? 'selected' : ''}
            key={status}
            onClick={() => setFilter(status)}
          >
            {status === 'ALL'
              ? view === 'ACTIVE' ? 'All active' : 'All history'
              : statusText[status]}
          </button>
        ))}
      </div>

      {query.isLoading ? <p className="ordering-message">Loading kitchen orders...</p> : null}
      {query.isError ? <p className="ordering-error">{query.error.message}</p> : null}
      {!query.isLoading && visibleOrders.length === 0 && (
        <div className="ordering-empty">
          {view === 'HISTORY'
            ? 'No served or cancelled orders found.'
            : 'No active orders. New customer orders will appear here.'}
        </div>
      )}

      <div className="kitchen-grid">
        {visibleOrders.map((order: RestaurantOrder) => {
          const seconds = elapsedSeconds(order.created_at, now)
          const late = view === 'ACTIVE' && seconds >= 15 * 60
          const warning = view === 'ACTIVE' && seconds >= 10 * 60 && !late
          const nextStatus: Partial<Record<OrderStatus, OrderStatus>> = {
            NEW: 'PREPARING',
            PREPARING: 'READY',
            READY: 'SERVED',
          }
          return (
            <article className={`kitchen-ticket ${late ? 'ticket-late' : warning ? 'ticket-warning' : ''}`} key={order.id}>
              <div className="ticket-top">
                <div>
                  <span className="ticket-number">{order.order_number}</span>
                  <h2>Table {tableNumbers.get(order.table_id) ?? order.table_id}</h2>
                </div>
                <strong className={`ticket-timer ${late ? 'timer-late' : warning ? 'timer-warning' : ''}`}>
                  {view === 'HISTORY'
                    ? new Date(order.created_at).toLocaleString()
                    : formatDuration(seconds)}
                </strong>
              </div>
              <span className={`order-status status-${order.status.toLowerCase()}`}>{statusText[order.status]}</span>
              <div className="ticket-items">
                {order.items.map((item) => (
                  <div className="ticket-item" key={item.id}>
                    <strong>{item.quantity} ×</strong>
                    <span>{item.item_name}{item.size ? ` — ${item.size}` : ''}</span>
                    {item.notes && <small>{item.notes}</small>}
                  </div>
                ))}
              </div>
              {(order.customer_allergies.length > 0 || order.allergy_notes) && (
                <div className="ticket-allergy">
                  <strong>Allergy information</strong>
                  {order.customer_allergies.join(', ')}
                  {order.allergy_notes && <p>{order.allergy_notes}</p>}
                </div>
              )}
              {order.notes && <p className="ticket-notes">Note: {order.notes}</p>}
              <div className="ticket-bottom">
                <strong>{money(order.total_amount)}</strong>
                {nextStatus[order.status] && (
                  <button
                    className="ordering-primary ticket-action"
                    disabled={mutation.isPending}
                    onClick={() => mutation.mutate({ id: order.id, status: nextStatus[order.status]! })}
                  >
                    {order.status === 'NEW' ? 'Start preparing' : order.status === 'PREPARING' ? 'Mark ready' : 'Mark served'}
                  </button>
                )}
              </div>
              {view === 'ACTIVE' && late && (
                <p className="ticket-priority">Priority: this order has passed 15 minutes.</p>
              )}
            </article>
          )
        })}
      </div>
      {mutation.isError && <p className="ordering-error">{mutation.error.message}</p>}
    </section>
  )
}

// STAFF MENU MANAGEMENT.
export function MenuManagement() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['managed-menu'], queryFn: getManagedMenu })
  const [name, setName] = useState('')
  const [category, setCategory] = useState('Main course')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [smallPrice, setSmallPrice] = useState('')
  const [mediumPrice, setMediumPrice] = useState('')
  const [largePrice, setLargePrice] = useState('')
  const [halfPrice, setHalfPrice] = useState('')
  const [fullPrice, setFullPrice] = useState('')
  const [ingredients, setIngredients] = useState('')
  const [allergens, setAllergens] = useState('')
  const [spice, setSpice] = useState<MenuItem['spice_level']>('MILD')

  const addMutation = useMutation({
    mutationFn: createMenuItem,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['managed-menu'] })
      client.invalidateQueries({ queryKey: ['public-menu'] })
      setName('')
      setDescription('')
      setPrice('')
      setSmallPrice('')
      setMediumPrice('')
      setLargePrice('')
      setHalfPrice('')
      setFullPrice('')
      setAllergens('')
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (item: MenuItem) => updateMenuItem(item.id, { is_available: !item.is_available }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['managed-menu'] })
      client.invalidateQueries({ queryKey: ['public-menu'] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: deleteMenuItem,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['managed-menu'] })
      client.invalidateQueries({ queryKey: ['public-menu'] })
    },
  })

  return (
    <section className="ordering-staff-page">
      <header className="ordering-staff-header">
        <div><div className="ordering-eyebrow">RESTAURANT OPERATIONS</div><h1>Menu management</h1><p>Add dishes and control what customers can order.</p></div>
      </header>
      <form className="menu-admin-form" onSubmit={(event) => {
        event.preventDefault()
        addMutation.mutate({
          name, category, description: description || undefined,
          price: Number(price),
          size_prices: Object.fromEntries(
            Object.entries({
              Small: smallPrice,
              Medium: mediumPrice,
              Large: largePrice,
              Half: halfPrice,
              Full: fullPrice,
            })
              .filter(([, value]) => value.trim() !== '')
              .map(([size, value]) => [size, Number(value)])
          ),
          ingredients: ingredients.split(',').map((x) => x.trim()).filter(Boolean),
          allergens: allergens.split(',').map((x) => x.trim()).filter(Boolean),
          spice_level: spice, is_available: true,
        })
      }}>
        <h2>Add menu item</h2>
        <div className="menu-admin-fields">
          <label>Name<input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} /></label>
          <label>Category<input required value={category} onChange={(e) => setCategory(e.target.value)} /></label>
          <label>Base price (Rs.)<input required type="number" min="1" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} /></label>
          <label>Small price (Rs.)<input type="number" min="1" step="0.01" value={smallPrice} onChange={(e) => setSmallPrice(e.target.value)} placeholder="Optional" /></label>
          <label>Medium price (Rs.)<input type="number" min="1" step="0.01" value={mediumPrice} onChange={(e) => setMediumPrice(e.target.value)} placeholder="Optional" /></label>
          <label>Large price (Rs.)<input type="number" min="1" step="0.01" value={largePrice} onChange={(e) => setLargePrice(e.target.value)} placeholder="Optional" /></label>
          <label>Half price (Rs.)<input type="number" min="1" step="0.01" value={halfPrice} onChange={(e) => setHalfPrice(e.target.value)} placeholder="Optional" /></label>
          <label>Full price (Rs.)<input type="number" min="1" step="0.01" value={fullPrice} onChange={(e) => setFullPrice(e.target.value)} placeholder="Optional" /></label>
          <label>Spice level<select value={spice} onChange={(e) => setSpice(e.target.value as MenuItem['spice_level'])}><option value="MILD">Mild</option><option value="MEDIUM">Medium</option><option value="HOT">Hot</option><option value="EXTRA_HOT">Extra hot</option></select></label>
          <label className="wide-field">Description<input value={description} onChange={(e) => setDescription(e.target.value)} /></label>
          <label className="wide-field">Ingredients (comma separated)<input value={ingredients} onChange={(e) => setIngredients(e.target.value)} placeholder="Chicken, tomato, onion, ginger, spices" /></label>
          <label className="wide-field">Allergens (comma separated)<input value={allergens} onChange={(e) => setAllergens(e.target.value)} placeholder="Peanuts, dairy, gluten" /></label>
        </div>
        <button className="ordering-primary" disabled={addMutation.isPending}> {addMutation.isPending ? 'Saving...' : 'Add to menu'} </button>
        {addMutation.isError && <p className="ordering-error">{addMutation.error.message}</p>}
      </form>
      <div className="managed-menu-list">
        {query.isLoading && <p>Loading menu...</p>}
        {query.isError && <p className="ordering-error">{query.error.message}</p>}
        {(query.data ?? []).map((item) => (
          <article className="managed-menu-item" key={item.id}>
            <div><strong>{item.name}</strong><p>{item.category} · {money(item.price)} · {item.spice_level}</p>
            {Object.keys(item.size_prices ?? {}).length > 0 && (
              <small>Sizes: {Object.entries(item.size_prices).map(([size, amount]) => `${size}: ${money(amount)}`).join(' · ')}</small>
            )}
            <br /><small>Ingredients: {item.ingredients.join(', ') || 'Not entered yet'}</small><br /><small>Allergens: {item.allergens.join(', ') || 'Not specified'}</small></div>
            <div className="managed-menu-actions">
              <button onClick={() => toggleMutation.mutate(item)}>{item.is_available ? 'Hide from menu' : 'Make available'}</button>
              <button className="danger-action" onClick={() => {
                if (window.confirm(`Delete ${item.name} from the menu?`)) removeMutation.mutate(item.id)
              }}>Delete</button>
            </div>
          </article>
        ))}
      </div>
      {(toggleMutation.isError || removeMutation.isError) && <p className="ordering-error">Could not update menu item.</p>}
    </section>
  )
}

// STAFF QR PAGE — QR URLs are generated from the current browser origin.
export function TableQRCodes() {
  const query = useQuery({ queryKey: ['restaurant-tables'], queryFn: getRestaurantTables })
  return (
    <section className="ordering-staff-page">
      <header className="ordering-staff-header">
        <div><div className="ordering-eyebrow">CUSTOMER ACCESS</div><h1>Table QR codes</h1><p>Print or display these codes on each table. Customers can scan without signing in.</p></div>
      </header>
      {query.isLoading && <p>Loading tables...</p>}
      {query.isError && <p className="ordering-error">{query.error.message}</p>}
      <div className="qr-grid">
        {(query.data ?? []).map((table) => {
          const url = `${window.location.origin}/order/${table.id}`
          return (
            <article className="qr-card" key={table.id}>
              <QRCodeSVG value={url} size={180} level="H" />
              <h2>Table {table.table_number}</h2>
              <p>{table.name}</p>
              <a href={url} target="_blank" rel="noreferrer">Open customer menu</a>
              <button onClick={() => window.print()}>Print QR codes</button>
            </article>
          )
        })}
      </div>
      {(query.data ?? []).length === 0 && !query.isLoading && <p className="ordering-empty">Add restaurant tables first to generate their QR codes.</p>}
    </section>
  )
}


// PUBLIC CUSTOMER THANK-YOU PAGE — shown only after staff confirms payment.
export function OrderThankYouPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const [rating, setRating] = useState(5)
  const [feedback, setFeedback] = useState('')
  const query = useQuery({
    queryKey: ['order-tracking', token],
    queryFn: () => getOrderTracking(token),
    enabled: Boolean(token),
    refetchInterval: 4000,
  })
  const order = query.data
  const tableQuery = useQuery({
    queryKey: ['public-restaurant-table', order?.table_id ?? 0],
    queryFn: () => getPublicRestaurantTable(order!.table_id),
    enabled: Boolean(order?.table_id),
    retry: false,
  })
  const feedbackMutation = useMutation({
    mutationFn: () => submitOrderFeedback(token, {
      rating,
      feedback: feedback.trim() || null,
    }),
  })

  useEffect(() => {
    if (order && order.payment_status !== 'PAID') {
      navigate(`/checkout/${token}`, { replace: true })
    }
  }, [order, navigate, token])

  if (query.isLoading || (order && order.payment_status !== 'PAID')) {
    return <CustomerShell><p className="ordering-message">Checking payment confirmation...</p></CustomerShell>
  }

  if (query.isError || !order) {
    return <CustomerShell><p className="ordering-error">{query.error?.message ?? 'Order not found.'}</p></CustomerShell>
  }

  return (
    <CustomerShell>
      <section className="thank-you-hero">
        <div className="thank-you-icon" aria-hidden="true">✓</div>
        <p className="ordering-eyebrow">RESTROMIND · PAYMENT CONFIRMED</p>
        <h1>Thank you for dining with us!</h1>
        <p>Your payment is confirmed. We hope you enjoyed your meal and look forward to welcoming you again.</p>
        <span className="thank-you-paid">PAID · {money(order.total_amount)}</span>
      </section>

      <section className="tracking-card thank-you-receipt">
        <p className="ordering-eyebrow">YOUR DIGITAL RECEIPT</p>
        <h2>Order {order.order_number}</h2>
        <p>{formatTableLabel(tableQuery.data?.table_number, order.table_id)}</p>
        <div className="thank-you-receipt-divider" />
        {order.items.map((item) => (
          <div className="checkout-line checkout-customized-line" key={item.id}>
            <div>
              <span>{item.quantity} × {item.item_name}{item.size ? ` (${item.size})` : ''}</span>
              {item.notes && <small>{item.notes}</small>}
            </div>
            <strong>{money(Number(item.unit_price) * item.quantity)}</strong>
          </div>
        ))}
        <div className="checkout-total">
          <span>Total paid</span>
          <strong>{money(order.total_amount)}</strong>
        </div>
        <div className="thank-you-payment-details">
          <p>Payment status <strong>PAID</strong></p>
          {order.payment_method && <p>Payment method <strong>{order.payment_method}</strong></p>}
          {order.payment_confirmed_at && (
            <p>Confirmed <strong>{new Date(order.payment_confirmed_at).toLocaleString()}</strong></p>
          )}
        </div>
      </section>

      <section className="customer-pay-bill thank-you-feedback">
        <p className="ordering-eyebrow">YOUR EXPERIENCE MATTERS</p>
        <h2>How was your experience?</h2>
        <p>Please rate your visit. Your feedback helps us improve.</p>
        {feedbackMutation.isSuccess ? (
          <div className="customer-service-success">
            <h3>Thank you for your feedback!</h3>
            <p>Your rating has been saved.</p>
          </div>
        ) : (
          <>
            <div className="thank-you-stars" role="group" aria-label="Rate your experience">
              {[1, 2, 3, 4, 5].map((value) => (
                <button
                  type="button"
                  key={value}
                  className={value <= rating ? 'active' : ''}
                  aria-label={`${value} star${value === 1 ? '' : 's'}`}
                  aria-pressed={rating === value}
                  onClick={() => setRating(value)}
                >
                  ★
                </button>
              ))}
            </div>
            <label className="thank-you-feedback-label" htmlFor="order-feedback">
              Optional comments
            </label>
            <textarea
              id="order-feedback"
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
              maxLength={1000}
              rows={4}
              placeholder="Tell us what you liked or what we can improve..."
            />
            <button
              type="button"
              className="ordering-primary"
              disabled={feedbackMutation.isPending}
              onClick={() => feedbackMutation.mutate()}
            >
              {feedbackMutation.isPending ? 'Submitting...' : 'Submit rating'}
            </button>
            {feedbackMutation.isError && (
              <p className="ordering-error">{feedbackMutation.error.message}</p>
            )}
          </>
        )}
      </section>
    </CustomerShell>
  )
}
