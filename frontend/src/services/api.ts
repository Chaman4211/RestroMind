import { getAccessToken } from './auth'

const API_BASE_URL = '/api/v1'

export type BackendTableStatus = 'FREE' | 'OCCUPIED' | 'NEEDS_CLEANING'

export type PublicRestaurantTable = {
  id: number
  table_number: string
  name: string
}

export type RestaurantTable = {
  id: number
  table_number: string
  name: string
  status: BackendTableStatus
  zone_coordinates: Record<string, unknown> | unknown[] | null
  upload_zone_coordinates: Record<string, unknown> | unknown[] | null
  upload_camera_source_id: number | null
  camera_source_id: number | null
  last_status_changed_at: string | null
  created_at: string
}

export type RestaurantAlert = {
  id: number
  table_id: number
  table_number: string
  table_name: string
  alert_type: string
  message: string
  status: 'OPEN' | 'RESOLVED'
  created_at: string
  resolved_at: string | null
  assigned_staff_id: number | null
  assigned_staff_name: string | null
  assigned_staff_role: string | null
}

export type StaffRole =
  | 'OWNER'
  | 'MANAGER'
  | 'ASSISTANT_MANAGER'
  | 'SUPERVISOR'
  | 'HEAD_CHEF'
  | 'SOUS_CHEF'
  | 'CHEF'
  | 'KITCHEN_ASSISTANT'
  | 'DISHWASHER'
  | 'WAITER'
  | 'HOST'
  | 'CASHIER'
  | 'BARTENDER'
  | 'BARISTA'
  | 'CLEANING_STAFF'
  | 'INVENTORY_MANAGER'
  | 'DELIVERY_STAFF'
  | 'SECURITY_STAFF'

export type StaffUser = {
  id: number
  name: string
  email: string | null
  phone: string | null
  role: StaffRole
  is_active: boolean
  created_at: string
}

export type CameraSource = {
  id: number
  name: string
  source_type: 'UPLOAD' | 'LIVE' | 'RTSP'
  is_active: boolean
  created_at: string
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken()

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  })

  if (!response.ok) {
    let message = `Request failed (${response.status})`

    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the HTTP status message if the response is not JSON.
    }

    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function getRestaurantTables(): Promise<RestaurantTable[]> {
  return request<RestaurantTable[]>('/restaurant-tables')
}

export type OccupancyHistoryEvent = {
  id: number
  table_id: number
  table_number: string
  table_name: string
  previous_status: string | null
  new_status: string
  description: string | null
  created_at: string
}

export type OccupancyVisit = {
  table_id: number
  table_number: string
  table_name: string
  started_at: string
  ended_at: string | null
  duration_seconds: number
  is_ongoing: boolean
}

export type OccupancyHistory = {
  events: OccupancyHistoryEvent[]
  visits: OccupancyVisit[]
}

export function getOccupancyHistory(): Promise<OccupancyHistory> {
  return request<OccupancyHistory>('/restaurant-tables/history')
}


export function getPublicRestaurantTable(
  tableId: number,
): Promise<PublicRestaurantTable> {
  return request<PublicRestaurantTable>(`/public/tables/${tableId}`)
}

export type SharedCartLine = {
  menu_item_id: number
  item_name: string
  size: string | null
  unit_price: number | string
  quantity: number
  notes: string | null
}

export type SharedTableCart = {
  table_id: number
  round_number: number
  last_order_token: string | null
  last_order_round: number | null
  cart: SharedCartLine[]
}

export function getSharedTableCart(tableId: number): Promise<SharedTableCart> {
  return request<SharedTableCart>(`/public/tables/${tableId}/shared-cart`)
}

export function changeSharedCartItem(
  tableId: number,
  payload: {
    menu_item_id: number
    size?: string | null
    quantity_delta: number
    notes?: string | null
  },
): Promise<SharedTableCart> {
  return request<SharedTableCart>(`/public/tables/${tableId}/shared-cart/items`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function submitSharedTableCart(
  tableId: number,
  payload: {
    customer_name?: string | null
    notes?: string
    customer_allergies: string[]
    allergy_notes?: string
  },
): Promise<CreatedRestaurantOrder> {
  return request<CreatedRestaurantOrder>(
    `/public/tables/${tableId}/shared-cart/submit`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export function createRestaurantTable(payload: {
  table_number: string
  name: string
  camera_source_id?: number | null
}): Promise<RestaurantTable> {
  return request<RestaurantTable>('/restaurant-tables', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteRestaurantTable(tableId: number): Promise<void> {
  return request<void>(`/restaurant-tables/${tableId}`, {
    method: 'DELETE',
  })
}

export function getAlerts(
  status: 'OPEN' | 'RESOLVED' = 'OPEN',
): Promise<RestaurantAlert[]> {
  return request<RestaurantAlert[]>(`/alerts?status=${status}`)
}

export function getStaffMembers(): Promise<StaffUser[]> {
  return request<StaffUser[]>('/staff')
}

export function createStaffMember(payload: {
  name: string
  email?: string | null
  phone?: string | null
  role: StaffRole
}): Promise<StaffUser> {
  return request<StaffUser>('/staff', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateStaffMember(
  staffId: number,
  updates: {
    name?: string
    email?: string | null
    phone?: string | null
    role?: StaffRole
    is_active?: boolean
  },
): Promise<StaffUser> {
  return request<StaffUser>(`/staff/${staffId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })
}

export function deleteStaffMember(staffId: number): Promise<void> {
  return request<void>(`/staff/${staffId}`, {
    method: 'DELETE',
  })
}

export function assignAlertToStaff(
  alertId: number,
  assignedStaffId: number | null,
): Promise<RestaurantAlert> {
  return request<RestaurantAlert>(`/alerts/${alertId}/assignment`, {
    method: 'PATCH',
    body: JSON.stringify({ assigned_staff_id: assignedStaffId }),
  })
}

export function getCameraSources(): Promise<CameraSource[]> {
  return request<CameraSource[]>('/camera-sources')
}

export function confirmTableCleaning(tableId: number): Promise<RestaurantTable> {
  return request<RestaurantTable>(
    `/restaurant-tables/${tableId}/confirm-cleaning`,
    { method: 'POST' },
  )
}

export function markTableCustomerLeft(tableId: number): Promise<RestaurantTable> {
  return request<RestaurantTable>(
    `/restaurant-tables/${tableId}/customer-left`,
    { method: 'POST' },
  )
}

export function updateRestaurantTable(
  tableId: number,
  updates: {
    name?: string
    zone_coordinates?: number[][] | null
    upload_zone_coordinates?: number[][] | null
    upload_camera_source_id?: number | null
    camera_source_id?: number | null
  },
): Promise<RestaurantTable> {
  return request<RestaurantTable>(
    `/restaurant-tables/${tableId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(updates),
    },
  )
}

export type VideoProcessingResult = {
  message: string
  file_name: string
  [key: string]: unknown
}

export type RTSPCameraStatus = {
  camera_source_id: number
  status: 'STARTING' | 'RUNNING' | 'STOPPING' | 'STOPPED' | 'ERROR'
  processed_frames: number
  error: string | null
}

export function createCameraSource(payload: {
  name: string
  source_type: 'UPLOAD' | 'LIVE' | 'RTSP'
  rtsp_url?: string
}): Promise<CameraSource> {
  return request<CameraSource>('/camera-sources', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function startRTSPCamera(id: number): Promise<RTSPCameraStatus> {
  return request<RTSPCameraStatus>(`/camera-sources/${id}/rtsp/start`, {
    method: 'POST',
  })
}

export function stopRTSPCamera(id: number): Promise<RTSPCameraStatus> {
  return request<RTSPCameraStatus>(`/camera-sources/${id}/rtsp/stop`, {
    method: 'POST',
  })
}

export function getRTSPCameraStatus(id: number): Promise<RTSPCameraStatus> {
  return request<RTSPCameraStatus>(`/camera-sources/${id}/rtsp/status`)
}

export async function uploadVideo(
  cameraSourceId: number,
  file: File,
): Promise<VideoProcessingResult> {
  const formData = new FormData()
  formData.append('file', file)
  const token = getAccessToken()

  const response = await fetch(
    `${API_BASE_URL}/camera-sources/${cameraSourceId}/process-video`,
    {
      method: 'POST',
      body: formData,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  )

  if (!response.ok) {
    let message = `Upload failed (${response.status})`

    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the HTTP status message.
    }

    throw new Error(message)
  }

  return response.json() as Promise<VideoProcessingResult>
}


export type VideoFrameResult = {
  camera_source_id: number
  people_detected: number
  frame_width: number
  frame_height: number
  people: Array<{
    track_id: number
    bbox: [number, number, number, number]
    confidence: number
  }>
  table_count: number
  assignments: Record<string, number[]>
  tables: Array<{
    table_id: number
    occupied: boolean
    person_count: number
    track_ids: number[]
    status: string
    events: unknown[]
  }>
}

export type VideoFrameEvent = {
  type: 'frame'
  frame_index: number
  video_time: number
  result: VideoFrameResult
}

export type VideoProcessingSummary = {
  camera_source_id: number
  total_frames: number
  processed_frames: number
  frame_interval: number
  fps: number
  duration_seconds: number
  max_people_detected: number
  tables: VideoFrameResult['tables']
}

export async function uploadVideoStream(
  cameraSourceId: number,
  file: File,
  onFrame: (event: VideoFrameEvent) => void,
): Promise<VideoProcessingSummary> {
  const formData = new FormData()
  formData.append('file', file)

  const token = getAccessToken()

  const response = await fetch(
    `${API_BASE_URL}/camera-sources/${cameraSourceId}/process-video-stream`,
    {
      method: 'POST',
      body: formData,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  )

  if (!response.ok) {
    let message = `Video processing failed (${response.status})`

    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the HTTP status message.
    }

    throw new Error(message)
  }

  if (!response.body) {
    throw new Error('The server did not provide a video processing stream.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let summary: VideoProcessingSummary | null = null

  const handleLine = (line: string) => {
    if (!line.trim()) return

    const event = JSON.parse(line)

    if (event.type === 'frame') {
      onFrame(event as VideoFrameEvent)
    } else if (event.type === 'complete') {
      summary = event.summary as VideoProcessingSummary
    } else if (event.type === 'error') {
      throw new Error(event.message || 'Video processing failed.')
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()

      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        handleLine(line)
      }
    }

    buffer += decoder.decode()

    if (buffer.trim()) {
      handleLine(buffer)
    }
  } finally {
    reader.releaseLock()
  }

  if (!summary) {
    throw new Error('Video processing ended without a completion summary.')
  }

  return summary
}

// ============================================================
// RESTAURANT ORDERING
// ============================================================

export type MenuItem = {
  id: number
  name: string
  description: string | null
  category: string
  price: number | string
  size_prices: Record<string, number | string>
  image_url: string | null
  ingredients: string[]
  allergens: string[]
  spice_level: 'MILD' | 'MEDIUM' | 'HOT' | 'EXTRA_HOT'
  is_available: boolean
}

export type OrderStatus =
  | 'NEW'
  | 'PREPARING'
  | 'READY'
  | 'SERVED'
  | 'CANCELLED'

export type RestaurantOrder = {
  id: number
  order_number: string
  table_id: number
  customer_name: string | null
  notes: string | null
  customer_allergies: string[]
  allergy_notes: string | null
  status: OrderStatus
  cancellation_reason?: string | null
  cancelled_at?: string | null
  eating_completed_at: string | null
  payment_method: string | null
  payment_provider: string | null
  payment_status: 'UNPAID' | 'PENDING' | 'PAID'
  payment_requested_at: string | null
  payment_confirmed_at: string | null
  total_amount: number | string
  created_at: string
  items: {
    id: number
    menu_item_id: number | null
    item_name: string
    unit_price: number | string
    size: string | null
    quantity: number
    notes: string | null
  }[]
}

export type CreatedRestaurantOrder = RestaurantOrder & {
  public_token: string
}

export function getPublicMenu(): Promise<MenuItem[]> {
  return request<MenuItem[]>('/menu')
}

export function getManagedMenu(): Promise<MenuItem[]> {
  return request<MenuItem[]>('/menu/manage')
}

export function createMenuItem(payload: {
  name: string
  description?: string
  category: string
  price: number
  size_prices?: Record<string, number>
  ingredients: string[]
  allergens: string[]
  spice_level: MenuItem['spice_level']
  is_available: boolean
}): Promise<MenuItem> {
  return request<MenuItem>('/menu', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateMenuItem(
  itemId: number,
  payload: Partial<Omit<MenuItem, 'id'>>,
): Promise<MenuItem> {
  return request<MenuItem>(`/menu/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteMenuItem(itemId: number): Promise<void> {
  return request<void>(`/menu/${itemId}`, { method: 'DELETE' })
}

export function createRestaurantOrder(payload: {
  table_id: number
  customer_name?: string | null
  notes?: string
  customer_allergies: string[]
  allergy_notes?: string
  items: { menu_item_id: number; size?: string | null; quantity: number; notes?: string }[]
}): Promise<CreatedRestaurantOrder> {
  return request<CreatedRestaurantOrder>('/orders', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getOrderTracking(token: string): Promise<RestaurantOrder> {
  return request<RestaurantOrder>(`/orders/track/${encodeURIComponent(token)}`)
}

export function cancelCustomerOrder(token: string): Promise<RestaurantOrder> {
  return request<RestaurantOrder>(
    `/orders/track/${encodeURIComponent(token)}/cancel`,
    { method: 'POST' },
  )
}

export function markOrderEatingComplete(token: string): Promise<RestaurantOrder> {
  return request<RestaurantOrder>(
    `/orders/track/${encodeURIComponent(token)}/eating-complete`,
    { method: "POST" },
  )
}

export function getKitchenOrders(includeHistory = false): Promise<RestaurantOrder[]> {
  const query = includeHistory ? '?include_history=true' : ''
  return request<RestaurantOrder[]>(`/orders/kitchen${query}`)
}

export function updateRestaurantOrderStatus(
  orderId: number,
  status: OrderStatus,
  cancellationReason?: string,
): Promise<RestaurantOrder> {
  return request<RestaurantOrder>(`/orders/${orderId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status, cancellation_reason: cancellationReason }),
  })
}

export function selectOrderPayment(
  token: string,
  method: string,
): Promise<RestaurantOrder> {
  return request<RestaurantOrder>(`/orders/track/${encodeURIComponent(token)}/payment`, {
    method: 'POST',
    body: JSON.stringify({ method }),
  })
}

export type OrderFeedback = {
  id: number
  rating: number
  feedback: string | null
  suggestion: string | null
  created_at: string
}

export type FeedbackSummary = {
  total_reviews: number
  average_rating: number
  recent_feedback: Array<OrderFeedback & { order_number: string }>
}

export function getOrderFeedback(token: string): Promise<OrderFeedback | null> {
  return request(`/orders/track/${encodeURIComponent(token)}/feedback`)
}

export function submitOrderFeedback(
  token: string,
  payload: { rating: number; feedback?: string | null; suggestion?: string | null },
): Promise<OrderFeedback> {
  return request(`/orders/track/${encodeURIComponent(token)}/feedback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getFeedbackSummary(): Promise<FeedbackSummary> {
  return request('/management/feedback-summary')
}

export function confirmOrderPayment(orderId: number): Promise<RestaurantOrder> {
  return request<RestaurantOrder>(`/orders/${orderId}/confirm-payment`, {
    method: 'POST',
  })
}

// ============================================================
// CUSTOMER SERVICE REQUESTS
// ============================================================

export type ServiceRequestType =
  | 'CALL_WAITER'
  | 'WATER'
  | 'TISSUES'
  | 'CUTLERY'
  | 'BILL'
  | 'WIFI'
  | 'OTHER'

export type ServiceRequestStatus = 'OPEN' | 'ACKNOWLEDGED' | 'COMPLETED'

export type RestaurantServiceRequest = {
  id: number
  table_id: number
  order_id: number | null
  table_number: string
  table_name: string
  request_type: ServiceRequestType
  message: string | null
  status: ServiceRequestStatus
  created_at: string
  acknowledged_at: string | null
  completed_at: string | null
  handled_by_staff_id: number | null
  handled_by_staff_name: string | null
}

export function createServiceRequest(payload: {
  table_id: number
  order_token?: string
  request_type: ServiceRequestType
  message?: string
}): Promise<RestaurantServiceRequest> {
  return request<RestaurantServiceRequest>('/service-requests', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getPublicTableServiceRequests(
  tableId: number,
): Promise<RestaurantServiceRequest[]> {
  return request<RestaurantServiceRequest[]>(`/service-requests/table/${tableId}`)
}

export function getPublicOrderServiceRequests(
  orderToken: string,
): Promise<RestaurantServiceRequest[]> {
  return request<RestaurantServiceRequest[]>(
    `/service-requests/order/${encodeURIComponent(orderToken)}`,
  )
}

export type TableRewards = {
  table_id: number
  points: number
  challenge_date: string
  question: string
  options: string[]
  already_played: boolean
  last_answer_correct: boolean | null
  points_awarded_today: number
}

export type RewardAnswerResult = {
  already_played: boolean
  correct: boolean
  points_awarded: number
  total_points: number
}

export function getTableRewards(tableId: number): Promise<TableRewards> {
  return request<TableRewards>(`/rewards/table/${tableId}`)
}

export function submitTableRewardAnswer(
  tableId: number,
  answerIndex: number,
): Promise<RewardAnswerResult> {
  return request<RewardAnswerResult>(`/rewards/table/${tableId}/answer`, {
    method: "POST",
    body: JSON.stringify({ answer_index: answerIndex }),
  })
}

export function getServiceRequests(): Promise<RestaurantServiceRequest[]> {
  return request<RestaurantServiceRequest[]>('/service-requests')
}

export function updateServiceRequestStatus(
  requestId: number,
  status: 'ACKNOWLEDGED' | 'COMPLETED',
): Promise<RestaurantServiceRequest> {
  return request<RestaurantServiceRequest>(
    `/service-requests/${requestId}/status`,
    {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    },
  )
}


export type WifiSettings = {
  ssid: string
  is_enabled: boolean
  password_configured: boolean
}

export type PublicWifiSettings = {
  is_enabled: boolean
  ssid?: string
  password?: string
}

export type WifiQr = {
  qr_payload: string | null
}

export function getWifiQr(): Promise<WifiQr> {
  return request<WifiQr>('/wifi/qr', {
    cache: 'no-store',
  })
}

export function getWifiSettings(): Promise<WifiSettings> {
  return request<WifiSettings>('/wifi/settings')
}

export function saveWifiSettings(payload: {
  ssid: string
  password?: string
  is_enabled: boolean
}): Promise<WifiSettings> {
  return request<WifiSettings>('/wifi/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function getRTSPCameraFrame(id: number): Promise<Blob> {
  const token = getAccessToken()

  const response = await fetch(
    `${API_BASE_URL}/camera-sources/${id}/rtsp/frame`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      cache: 'no-store',
    },
  )

  if (!response.ok) {
    let message = `Camera frame request failed (${response.status})`

    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the HTTP status message.
    }

    throw new Error(message)
  }

  return response.blob()
}
