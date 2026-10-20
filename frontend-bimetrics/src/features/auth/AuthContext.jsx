import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiRequest } from '../../services/api.js'
import { AuthContext } from './auth-context.js'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [sessionError, setSessionError] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    apiRequest('/auth/sesion', { signal: controller.signal })
      .then((currentUser) => setUser(currentUser))
      .catch((error) => {
        if (error.name === 'AbortError') return
        if (error.status !== 401) setSessionError(error.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [])

  const login = useCallback(async (credentials) => {
    const currentUser = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    })
    setSessionError('')
    setUser(currentUser)
    return currentUser
  }, [])

  const register = useCallback(async (details) => {
    const currentUser = await apiRequest('/auth/registro', {
      method: 'POST',
      body: JSON.stringify(details),
    })
    setSessionError('')
    setUser(currentUser)
    return currentUser
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' })
    } catch {
      // Limpia el estado local incluso si el servidor no responde.
    } finally {
      setUser(null)
    }
  }, [])

  const updateUser = useCallback((currentUser) => setUser(currentUser), [])

  const value = useMemo(() => ({ user, isLoading, sessionError, login, register, logout, updateUser }), [
    user, isLoading, sessionError, login, register, logout, updateUser,
  ])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
