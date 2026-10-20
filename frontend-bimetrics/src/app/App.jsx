import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../features/auth/AuthContext.jsx'
import { useAuth } from '../features/auth/useAuth.js'
import DashboardPage from '../features/dashboard/DashboardPage.jsx'
import LandingPage from '../features/public/LandingPage.jsx'
import LegalPage from '../features/public/LegalPage.jsx'
import LoginPage from '../features/auth/LoginPage.jsx'
import ProfilePage from '../features/profile/ProfilePage.jsx'
import ContactPage from '../features/public/ContactPage.jsx'

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
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<GuestRoute><LoginPage mode="login" /></GuestRoute>} />
      <Route path="/registro" element={<GuestRoute><LoginPage mode="register" /></GuestRoute>} />
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/perfil" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
      <Route path="/contacto" element={<ContactPage />} />
      <Route path="/terminos" element={<LegalPage document="terms" />} />
      <Route path="/privacidad" element={<LegalPage document="privacy" />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
