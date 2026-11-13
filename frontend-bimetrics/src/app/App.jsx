import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../features/auth/AuthContext.jsx'
import { useAuth } from '../features/auth/useAuth.js'
import { Toaster } from 'sonner'

const DashboardPage = lazy(() => import('../features/dashboard/DashboardPage.jsx'))
const LandingPage = lazy(() => import('../features/public/LandingPage.jsx'))
const LegalPage = lazy(() => import('../features/public/LegalPage.jsx'))
const LoginPage = lazy(() => import('../features/auth/LoginPage.jsx'))
const PasswordResetPage = lazy(() => import('../features/auth/PasswordResetPage.jsx'))
const ProfilePage = lazy(() => import('../features/profile/ProfilePage.jsx'))
const ContactPage = lazy(() => import('../features/public/ContactPage.jsx'))

function RouteLoader() {
  return (
    <main className="grid min-h-screen place-items-center bg-transparent text-sm text-slate-300">
      Conectando con BIMetrics…
    </main>
  )
}

function ProtectedRoute({ children }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <RouteLoader />
  return user ? children : <Navigate to="/login" replace />
}

function GuestRoute({ children }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <RouteLoader />
  return user ? <Navigate to="/dashboard" replace /> : children
}

function AppRoutes() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<GuestRoute><LoginPage mode="login" /></GuestRoute>} />
        <Route path="/registro" element={<GuestRoute><LoginPage mode="register" /></GuestRoute>} />
        <Route path="/recuperar" element={<PasswordResetPage />} />
        <Route path="/restablecer" element={<PasswordResetPage />} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/perfil" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
        <Route path="/contacto" element={<ContactPage />} />
        <Route path="/terminos" element={<LegalPage document="terms" />} />
        <Route path="/privacidad" element={<LegalPage document="privacy" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster position="top-right" theme="dark" richColors closeButton duration={4000} />
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
