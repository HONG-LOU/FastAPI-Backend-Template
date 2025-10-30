import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000
})

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.tokens?.access_token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${auth.tokens.access_token}`
  }
  return config
})

let refreshing = false
let pending: Array<() => void> = []

api.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const auth = useAuthStore()
    const status = error?.response?.status
    if (status === 401 && auth.tokens?.refresh_token && !refreshing) {
      refreshing = true
      try {
        const { data } = await axios.post(
          `${API_BASE_URL}/api/auth/refresh`,
          {
            access_token: auth.tokens.access_token,
            refresh_token: auth.tokens.refresh_token,
            token_type: 'bearer'
          },
          { timeout: 10000 }
        )
        auth.setTokens(data)
        pending.forEach((fn) => fn())
        pending = []
        return api(error.config)
      } catch (e) {
        auth.logout()
      } finally {
        refreshing = false
      }
    }
    if (status === 401 && refreshing) {
      return new Promise((resolve) => {
        pending.push(() => resolve(api(error.config)))
      })
    }
    return Promise.reject(error)
  }
)

export function setTokensFromUrlOnce() {
  const url = new URL(window.location.href)
  const access = url.searchParams.get('access_token')
  const refresh = url.searchParams.get('refresh_token')
  const tokenType = url.searchParams.get('token_type') || 'bearer'
  if (access && refresh) {
    // 注意：此处在应用创建前调用，不能依赖 Pinia 实例
    try {
      const tokenPair = { access_token: access, refresh_token: refresh, token_type: tokenType }
      localStorage.setItem('token_pair', JSON.stringify(tokenPair))
    } catch {}
    url.searchParams.delete('access_token')
    url.searchParams.delete('refresh_token')
    url.searchParams.delete('token_type')
    window.history.replaceState({}, '', url.toString())
  }
}


