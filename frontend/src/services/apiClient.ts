import axios from 'axios'
import { env } from '@/lib/env'

/** The only configured HTTP client. Services use it; components never do. */
export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})
