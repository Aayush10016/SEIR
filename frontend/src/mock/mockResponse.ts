/** Resolves with a copy of `data` after a short delay so loading states behave like a real request. */
export function mockResponse<T>(data: T, delayMs = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(data)), delayMs))
}
