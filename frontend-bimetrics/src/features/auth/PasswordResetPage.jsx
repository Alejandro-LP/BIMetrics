import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import GlassCard from '../../components/ui/GlassCard.jsx'
import BrandLogo from '../../components/brand/BrandLogo.jsx'
import { apiRequest } from '../../services/api.js'

const inputClass = 'glass-control mt-2 w-full rounded-xl px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-indigo-300/50 focus:ring-2 focus:ring-indigo-400/15'

function PasswordResetPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [message, setMessage] = useState('')
  const [developmentLink, setDevelopmentLink] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      if (!token) {
        const result = await apiRequest('/auth/solicitar-restablecimiento', {
          method: 'POST', body: JSON.stringify({ email: email.trim() }),
        })
        setMessage(result.mensaje)
        setDevelopmentLink(result.enlace_desarrollo || '')
      } else {
        if (password !== confirmation) throw new Error('Las contraseñas no coinciden.')
        await apiRequest('/auth/restablecer-password', {
          method: 'POST', body: JSON.stringify({ token, password }),
        })
        navigate('/login?restablecida=1', { replace: true })
      }
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-transparent px-4 py-12 text-slate-300">
      <div aria-hidden="true" className="pointer-events-none absolute left-[-8%] top-[-18%] h-[520px] w-[520px] rounded-full bg-indigo-500/25 blur-[140px]" />
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative w-full max-w-md">
        <Link to="/" className="mb-8 flex flex-col items-center gap-3 text-center" aria-label="BIMetrics, inicio"><BrandLogo size="lg" /><span className="text-sm text-slate-400">Recupera el acceso a tu cuenta.</span></Link>
        <GlassCard className="p-7 sm:p-8">
          <h1 className="text-lg font-semibold text-white">{token ? 'Crea una contraseña nueva' : 'Restablece tu contraseña'}</h1>
          <p className="mt-1 text-xs leading-5 text-slate-400">{token ? 'Usa una contraseña de 10 a 128 caracteres.' : 'Te enviaremos un enlace de un solo uso que vence en 30 minutos.'}</p>
          {(error || message) && <p role={error ? 'alert' : 'status'} className={`mt-5 rounded-xl border px-3.5 py-3 text-sm ${error ? 'border-rose-400/20 bg-rose-400/[0.07] text-rose-200' : 'border-emerald-300/20 bg-emerald-300/[0.06] text-emerald-100'}`}>{error || message}</p>}
          {developmentLink && <a href={developmentLink} className="mt-3 block break-all rounded-xl border border-amber-300/20 bg-amber-300/[0.06] px-3.5 py-3 text-xs text-amber-100">Abrir enlace local de restablecimiento</a>}
          {!message || token ? <form onSubmit={submit} className="mt-5 space-y-4">
            {!token ? <label className="block text-sm text-slate-300">Correo electrónico<input type="email" autoComplete="email" maxLength={150} required value={email} onChange={(event) => setEmail(event.target.value)} className={inputClass} placeholder="nombre@empresa.com" /></label> : <>
              <label className="block text-sm text-slate-300">Nueva contraseña<input type="password" autoComplete="new-password" minLength={10} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} className={inputClass} /></label>
              <label className="block text-sm text-slate-300">Confirma la contraseña<input type="password" autoComplete="new-password" minLength={10} maxLength={128} required value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className={inputClass} /></label>
            </>}
            <button type="submit" disabled={busy} className="inline-flex w-full items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:from-blue-500 hover:to-indigo-500 disabled:opacity-60">{busy ? 'Procesando…' : token ? 'Actualizar contraseña' : 'Enviar enlace'}</button>
          </form> : null}
        </GlassCard>
        <p className="mt-5 text-center text-sm text-slate-500"><Link to="/login" className="font-medium text-indigo-300 transition hover:text-indigo-200">Volver a iniciar sesión</Link></p>
      </motion.div>
    </main>
  )
}

export default PasswordResetPage
