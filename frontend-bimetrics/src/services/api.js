const configuredApiUrl = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')
// El backend publica sus endpoints bajo /api. Acepta una URL raíz en el .env
// y agrega el prefijo automáticamente, evitando duplicarlo si ya está presente.
const isLocalBackendUrl = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(configuredApiUrl)
// Local development uses Vite's /api proxy to keep session cookies same-origin.
// Production can use an absolute API origin; normalize its /api prefix here.
const API_BASE_URL = import.meta.env.DEV && isLocalBackendUrl
  ? '/api'
  : /^https?:\/\//.test(configuredApiUrl) && !configuredApiUrl.endsWith('/api')
    ? `${configuredApiUrl}/api`
    : configuredApiUrl

export async function apiRequest(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      credentials: 'include',
      ...options,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    })
  } catch (cause) {
    if (cause.name === 'AbortError') throw cause
    const error = new Error('No fue posible conectar con BIMetrics. Verifica que la API esté disponible e inténtalo de nuevo.')
    error.cause = cause
    throw error
  }

  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    const error = new Error(payload.error || 'La solicitud no pudo completarse.')
    error.status = response.status
    throw error
  }

  return payload
}

export { API_BASE_URL }
