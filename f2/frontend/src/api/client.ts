import axios, { AxiosInstance } from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (config.data instanceof FormData && config.headers) {
    delete (config.headers as Record<string, unknown>)['Content-Type']
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export interface User {
  id: number
  email: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface JobStatus {
  job_id: string
  status: string
  total_files: number
  processed_files: number
  progress_percent: number
  error_message?: string
  file_names: string[]
  created_at: string
  updated_at: string
}

export interface ExtractionResult {
  file_name: string
  file_path: string
  fields: Record<string, unknown>
  confidence_scores: Record<string, number>
  sections_detected: string[]
  is_scanned: boolean
  error?: string
}

export interface JobHistoryItem {
  job_id: string
  name?: string
  status: string
  total_files: number
  processed_files: number
  created_at: string
}
