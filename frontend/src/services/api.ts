import { getAccessToken } from './auth'

const API_BASE_URL = '/api/v1'

export type BackendTableStatus = 'FREE' | 'OCCUPIED' | 'NEEDS_CLEANING'

export type RestaurantTable = {
  id: number
  table_number: string
  name: string
  status: BackendTableStatus
  zone_coordinates: Record<string, unknown> | unknown[] | null
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

export function updateRestaurantTable(
  tableId: number,
  updates: {
    name?: string
    zone_coordinates?: number[][]
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

export function createCameraSource(payload: {
  name: string
  source_type: 'UPLOAD' | 'LIVE'
}): Promise<CameraSource> {
  return request<CameraSource>('/camera-sources', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
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
