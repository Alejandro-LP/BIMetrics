const API_BASE_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/+$/, '')

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
