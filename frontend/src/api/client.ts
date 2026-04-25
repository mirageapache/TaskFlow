import axios from 'axios'
import type { AxiosInstance } from 'axios'

// Phase 1 TDD 階段會加上 JWT Authorization header 與 401 Refresh 連鎖
// 詳見 .doc/taskflow-frontend.md §4.3
const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
})

export default client
