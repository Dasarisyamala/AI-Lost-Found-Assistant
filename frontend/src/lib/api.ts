import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const tokenKey = 'ai-lost-found-token'

export const api = axios.create({ baseURL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(tokenKey)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export function saveToken(token: string) {
  localStorage.setItem(tokenKey, token)
}

export function clearToken() {
  localStorage.removeItem(tokenKey)
}

export function getToken() {
  return localStorage.getItem(tokenKey)
}

export async function register(payload: { name: string; email: string; password: string }) {
  const { data } = await api.post('/auth/register', payload)
  return data
}

export async function login(payload: { email: string; password: string }) {
  const { data } = await api.post('/auth/login', payload)
  return data
}

export async function me() {
  const { data } = await api.get('/users/me')
  return data
}

export async function listLostItems() {
  const { data } = await api.get('/lost-items')
  return data
}

export async function listPublicLostItems() {
  const { data } = await api.get('/lost-items/public')
  return data
}

export async function listFoundItems() {
  const { data } = await api.get('/found-items')
  return data
}

export async function listMatches(statusFilter?: string) {
  const { data } = await api.get('/matches', { params: statusFilter ? { status_filter: statusFilter } : undefined })
  return data
}

export async function getMatch(id: number) {
  const { data } = await api.get(`/matches/${id}`)
  return data
}

export async function confirmMatch(id: number) {
  const { data } = await api.post(`/matches/${id}/confirm`)
  return data
}

export async function rejectMatch(id: number) {
  const { data } = await api.post(`/matches/${id}/reject`)
  return data
}

export async function createLostItem(formData: FormData) {
  const { data } = await api.post('/lost-items', formData)
  return data
}

export async function createFoundItem(formData: FormData) {
  const { data } = await api.post('/found-items', formData)
  return data
}

export function getApiErrorMessage(error: unknown, fallbackMessage: string) {
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data as { detail?: unknown; message?: unknown } | string | undefined
    const detail = typeof responseData === 'string' ? responseData : responseData?.detail ?? responseData?.message

    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .map((entry) => {
          if (typeof entry === 'string') return entry
          if (entry && typeof entry === 'object' && 'msg' in entry && typeof entry.msg === 'string') {
            return entry.msg
          }
          return null
        })
        .filter((message): message is string => Boolean(message))

      if (messages.length > 0) {
        return messages.join(', ')
      }
    }

    if (error.message && error.message !== 'Network Error') {
      return error.message
    }

    return fallbackMessage
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  return fallbackMessage
}
