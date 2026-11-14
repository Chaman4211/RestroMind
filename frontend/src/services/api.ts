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

export type CameraSource = {
  id: number
  name: string
  source_type: 'UPLOAD' | 'LIVE'
  is_active: boolean
  created_at: string
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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
