import { useState } from 'react'
import { ArrowRight, LockKeyhole } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import GlassCard from '../../components/ui/GlassCard.jsx'
import BrandLogo from '../../components/brand/BrandLogo.jsx'
import { useAuth } from './useAuth.js'

const inputClass = 'glass-control w-full rounded-xl px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-indigo-300/50 focus:ring-2 focus:ring-indigo-400/15'

function LoginPage({ mode = 'login' }) {
  const isRegister = mode === 'register'
  const navigate = useNavigate()
  const { login, register, sessionError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('arquitecto')
  const [authorized, setAuthorized] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setIsLoading(true)
    setError('')
    try {
      if (isRegister) {
        await register({ nombre_completo: name, email, password, rol: role, autoriza_datos: authorized })
      } else {
        await login({ email, password })
      }
      navigate('/dashboard', { replace: true })
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-transparent px-4 py-12 text-slate-300">
      <div aria-hidden="true" className="pointer-events-none absolute left-[-8%] top-[-18%] h-[520px] w-[520px] rounded-full bg-indigo-500/25 blur-[140px]" />
      <div aria-hidden="true" className="pointer-events-none absolute bottom-[-24%] right-[-12%] h-[480px] w-[480px] rounded-full bg-cyan-400/15 blur-[140px]" />

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative w-full max-w-md">
        <Link to="/" className="mb-8 flex flex-col items-center gap-3 text-center" aria-label="BIMetrics, inicio">
          <BrandLogo size="lg" />
          <span className="text-sm text-slate-400">Accede a tus presupuestos y proyectos.</span>
        </Link>

        <GlassCard className="p-7 sm:p-8">
          <div className="mb-6 flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/[0.05] text-indigo-300 ring-1 ring-white/10"><LockKeyhole size={18} /></span>
            <div>
              <h1 className="text-lg font-semibold text-white">{isRegister ? 'Crear cuenta' : 'Iniciar sesión'}</h1>
              <p className="mt-0.5 text-xs text-slate-500">{isRegister ? 'Configura tu espacio BIMetrics' : 'Ingresa con tu cuenta BIMetrics'}</p>
            </div>
          </div>

          {(error || sessionError) && (
            <p role="alert" className="mb-5 rounded-xl border border-rose-400/20 bg-rose-400/[0.07] px-3.5 py-3 text-sm text-rose-200">
              {error || sessionError}
            </p>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <>
                <label className="block text-sm font-medium text-slate-300" htmlFor="full-name">Nombre completo</label>
                <input id="full-name" name="nombre_completo" type="text" autoComplete="name" minLength={2} maxLength={150} required value={name} onChange={(event) => setName(event.target.value)} placeholder="Tu nombre" className={inputClass} />
              </>
            )}
            <label className="block text-sm font-medium text-slate-300" htmlFor="email">Correo electrónico</label>
            <input id="email" name="email" type="email" autoComplete="email" maxLength={150} required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="nombre@empresa.com" className={inputClass} />
            {isRegister && (
              <>
                <label className="block text-sm font-medium text-slate-300" htmlFor="role">Tipo de cuenta</label>
                <select id="role" name="rol" value={role} onChange={(event) => setRole(event.target.value)} className={`${inputClass} glass-select`}>
                  <option value="arquitecto">Arquitecto</option>
                  <option value="ingeniero">Ingeniero</option>
                  <option value="cliente">Cliente · solo consulta</option>
                </select>
              </>
            )}
            <label className="block text-sm font-medium text-slate-300" htmlFor="password">Contraseña</label>
            <input id="password" name="password" type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} minLength={isRegister ? 10 : undefined} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isRegister ? 'Mínimo 10 caracteres' : 'Tu contraseña'} className={inputClass} />
            {isRegister && (
              <label className="flex items-start gap-2.5 text-xs leading-5 text-slate-400">
                <input type="checkbox" name="autoriza_datos" checked={authorized} onChange={(event) => setAuthorized(event.target.checked)} required className="mt-1 accent-indigo-400" />
                Autorizo el tratamiento de mis datos para crear y administrar mi cuenta BIMetrics.
              </label>
            )}
            <button type="submit" disabled={isLoading} className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:from-blue-500 hover:to-indigo-500 disabled:cursor-wait disabled:opacity-60">
              {isLoading ? 'Procesando…' : isRegister ? 'Crear cuenta' : 'Entrar'}
              {!isLoading && <ArrowRight size={16} />}
            </button>
          </form>
        </GlassCard>

        <p className="mt-5 text-center text-sm text-slate-500">
          {isRegister ? '¿Ya tienes una cuenta?' : '¿Todavía no tienes cuenta?'}{' '}
          <Link to={isRegister ? '/login' : '/registro'} className="font-medium text-indigo-300 transition hover:text-indigo-200">
            {isRegister ? 'Iniciar sesión' : 'Crear cuenta'}
          </Link>
        </p>
        <p className="mt-5 text-center text-xs text-slate-600">Presupuestos de obra · Estimación BIM 5D</p>
      </motion.div>
    </main>
  )
}

export default LoginPage
