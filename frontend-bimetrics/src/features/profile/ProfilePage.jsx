import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import DashboardLayout from '../../components/layout/DashboardLayout.jsx'
import GlassCard from '../../components/ui/GlassCard.jsx'
import { useAuth } from '../auth/useAuth.js'
import { apiRequest } from '../../services/api.js'
import { toast } from 'sonner'

const inputClass = 'glass-control mt-2 w-full rounded-xl px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-indigo-300/50 focus:ring-2 focus:ring-indigo-400/15'

function ProfilePage() {
  const { user, updateUser, logout } = useAuth()
  const [name, setName] = useState(user?.nombre_completo || '')
  const [email, setEmail] = useState(user?.email || '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [message, setMessage] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setMessage(null)
    if (newPassword && newPassword !== confirmation) {
      setMessage({ error: 'Las nuevas contraseñas no coinciden.' })
      return
    }

    setIsLoading(true)
    try {
      const updatedUser = await apiRequest('/auth/perfil', {
        method: 'PUT',
        body: JSON.stringify({
          nombre_completo: name,
          email,
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })
      updateUser(updatedUser)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmation('')
      setMessage({ success: 'Tus datos se actualizaron correctamente.' })
      toast.success('Tus datos se actualizaron correctamente.')
    } catch (error) {
      setMessage({ error: error.message })
      toast.error(error.message || 'No se pudieron guardar los cambios.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <DashboardLayout user={user} onLogout={logout}>
      <main className="mx-auto max-w-5xl">
        <Link to="/dashboard" className="mb-7 inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"><ArrowLeft size={16} /> Volver al dashboard</Link>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="grid gap-8 lg:grid-cols-[.75fr_1fr]">
          <section>
            <p className="mb-3 text-xs font-semibold uppercase tracking-[.2em] text-indigo-300">Tu cuenta</p>
            <h1 className="text-3xl font-bold tracking-tight text-white">Datos al día.<br /><span className="text-indigo-300">Todo en orden.</span></h1>
            <p className="mt-4 max-w-sm text-sm leading-6 text-slate-400">Actualiza tu información personal y mantén tu acceso seguro.</p>
            <p className="mt-7 text-xs font-semibold uppercase tracking-[.15em] text-slate-500">Tipo de cuenta · <span className="text-slate-300">{user?.rol}</span></p>
          </section>

          <GlassCard className="p-6 sm:p-8">
            <h2 className="text-lg font-semibold text-white">Información personal</h2>
            <p className="mt-1 text-sm text-slate-400">Confirma tu contraseña actual para guardar cambios.</p>
            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <label className="block text-sm text-slate-300" htmlFor="profile-name">Nombre completo<input id="profile-name" name="nombre_completo" autoComplete="name" minLength={2} maxLength={150} required value={name} onChange={(event) => setName(event.target.value)} className={inputClass} /></label>
              <label className="block text-sm text-slate-300" htmlFor="profile-email">Correo electrónico<input id="profile-email" name="email" type="email" autoComplete="email" maxLength={150} required value={email} onChange={(event) => setEmail(event.target.value)} className={inputClass} /></label>
              <label className="block text-sm text-slate-300" htmlFor="current-password">Contraseña actual<input id="current-password" name="current_password" type="password" autoComplete="current-password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} className={inputClass} /></label>
              <div className="border-t border-white/[0.08] pt-4">
                <label className="block text-sm text-slate-300" htmlFor="new-password">Nueva contraseña <span className="text-xs text-slate-500">OPCIONAL</span><input id="new-password" name="new_password" type="password" autoComplete="new-password" minLength={10} maxLength={128} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="Déjalo vacío para conservarla" className={inputClass} /></label>
                <label className="mt-4 block text-sm text-slate-300" htmlFor="confirm-password">Confirma la nueva contraseña<input id="confirm-password" type="password" autoComplete="new-password" minLength={10} maxLength={128} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className={inputClass} /></label>
              </div>
              {message && <p role={message.error ? 'alert' : 'status'} className={`rounded-xl border p-3 text-sm ${message.error ? 'border-rose-400/20 bg-rose-400/[0.07] text-rose-200' : 'border-emerald-400/20 bg-emerald-400/[0.07] text-emerald-200'}`}>{message.error || message.success}</p>}
              <button type="submit" disabled={isLoading} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:from-blue-500 hover:to-indigo-500 disabled:opacity-60">{isLoading ? 'Guardando…' : 'Guardar cambios'}</button>
            </form>
          </GlassCard>
        </motion.div>
      </main>
    </DashboardLayout>
  )
}

export default ProfilePage
