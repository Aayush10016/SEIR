export const env = {
  /** Centralized fallback; override with VITE_API_BASE_URL. */
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  useMock: import.meta.env.VITE_USE_MOCK !== 'false',
}
