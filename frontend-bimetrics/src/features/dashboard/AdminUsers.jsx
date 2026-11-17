import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import GlassCard from '../../components/ui/GlassCard.jsx'
import { apiRequest } from '../../services/api.js'
import AdminDialog from './AdminDialog.jsx'

const roles = { administrador: 'Administrador', arquitecto: 'Arquitecto', ingeniero: 'Ingeniero', cliente: 'Cliente' }
const field = 'glass-control block w-full rounded-xl px-3 py-2 text-sm text-white'
const button = 'rounded-xl border border-white/15 px-3 py-2 text-sm font-medium text-indigo-100 transition hover:bg-indigo-400/10 disabled:opacity-50'

function UserEditor({ selection, onClose, onSaved }) {
  const { mode, account } = selection
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const deleting = mode === 'delete'
  const creating = mode === 'create'
  const title = deleting ? 'Eliminar usuario' : creating ? 'Crear usuario' : 'Editar usuario'

  async function submit(event) {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const payload = Object.fromEntries(values)
    if (!deleting) {
      payload.nombre_completo = payload.nombre_completo.trim()
      payload.email = payload.email.trim()
    }
    setBusy(true)
    setError('')
    try {
      const saved = await apiRequest(creating ? '/usuarios' : `/usuarios/${account.id_usuario}`, deleting
        ? { method: 'DELETE' }
        : { method: creating ? 'POST' : 'PUT', body: JSON.stringify(payload) })
      onSaved(deleting ? null : saved, account?.id_usuario)
      toast.success(deleting ? 'Cuenta eliminada' : creating ? 'Cuenta creada' : 'Cuenta actualizada')
    } catch (failure) {
      setError(failure.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog title={title} onClose={onClose} busy={busy} error={error}>
      <form onSubmit={submit} className="mt-4 space-y-4">
        {deleting ? (
          <p className="text-sm leading-6">¿Quieres eliminar a <strong>{account.nombre_completo}</strong> ({account.email})? Perderá el acceso a BIMetrics y a los proyectos compartidos.</p>
        ) : <>
          <label className="block space-y-1 text-sm">Nombre completo<input className={field} name="nombre_completo" defaultValue={account?.nombre_completo} required maxLength={150} /></label>
          <label className="block space-y-1 text-sm">Correo electrónico<input className={field} name="email" type="email" autoComplete="off" defaultValue={account?.email} required maxLength={254} /></label>
          <div className="space-y-1 text-sm"><label htmlFor="admin-user-role">Rol</label><select id="admin-user-role" className={field} name="rol" defaultValue={account?.rol ?? 'cliente'}>
            {Object.entries(roles).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select></div>
          {creating && <div className="space-y-1 text-sm"><label htmlFor="admin-user-password">Contraseña inicial</label><input id="admin-user-password" aria-describedby="admin-user-password-help" className={field} name="password" type="password" autoComplete="new-password" required minLength={10} maxLength={128} /><p id="admin-user-password-help" className="text-xs text-slate-400">Usa entre 10 y 128 caracteres.</p></div>}
        </>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className={button} onClick={onClose} disabled={busy}>Cancelar</button>
          <button type="submit" disabled={busy} className={`${button} ${deleting ? 'border-rose-300/30 bg-rose-500/15 text-rose-100' : 'bg-indigo-600 text-white'}`}>
            {busy ? 'Guardando…' : deleting ? 'Confirmar eliminación' : creating ? 'Crear cuenta' : 'Guardar cambios'}
          </button>
        </div>
      </form>
    </AdminDialog>
  )
}

function AdminUsers({ currentUser }) {
  const [users, setUsers] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [selection, setSelection] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    apiRequest('/usuarios', { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setUsers(data) })
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message) })
    return () => controller.abort()
  }, [attempt])

  const term = search.trim().toLocaleLowerCase('es-CO')
  const filtered = users?.filter((account) =>
    (!role || account.rol === role) && `${account.nombre_completo} ${account.email}`.toLocaleLowerCase('es-CO').includes(term))
    .sort((a, b) => a.nombre_completo.localeCompare(b.nombre_completo, 'es-CO'))

  function saved(account, id) {
    setUsers((list) => [...(list ?? []).filter((item) => item.id_usuario !== id), ...(account ? [account] : [])])
    setSelection(null)
  }

  return (
    <GlassCard className="space-y-5 p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><h2 className="text-xl font-semibold text-white">Usuarios</h2><p className="mt-1 text-sm text-slate-400">Crea cuentas y administra los roles de acceso.</p></div>
        <button type="button" className={`${button} bg-indigo-600 text-white`} onClick={() => setSelection({ mode: 'create' })} disabled={!users}>Nuevo usuario</button>
      </div>
      <div className="grid gap-3 sm:grid-cols-[1fr_13rem]">
        <label className="block space-y-1 text-sm text-slate-300">Buscar usuario<input className={field} type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nombre o correo" /></label>
        <label className="block space-y-1 text-sm text-slate-300">Filtrar por rol<select className={field} value={role} onChange={(event) => setRole(event.target.value)}>
          <option value="">Todos los roles</option>{Object.entries(roles).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
      </div>
      {error ? <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-rose-200">{error}<button className={button} type="button" onClick={() => { setError(''); setAttempt((value) => value + 1) }}>Reintentar</button></div>
        : !filtered ? <p role="status" className="text-sm text-slate-400">Cargando usuarios…</p>
        : !filtered.length ? <p className="text-sm text-slate-400">No hay usuarios que coincidan con los filtros.</p>
        : <ul className="divide-y divide-white/10">
          {filtered.map((account) => {
            const own = account.id_usuario === currentUser.id_usuario
            return (
              <li key={account.id_usuario} className="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_9rem_auto] sm:items-center">
                <div className="min-w-0">
                  <p className="break-words font-medium text-white">{account.nombre_completo}{own && <span className="ml-2 text-xs text-slate-400">Tu cuenta</span>}</p>
                  <p className="break-all text-sm text-slate-400">{account.email}</p>
                </div>
                <span className="text-sm text-indigo-200">{roles[account.rol] ?? account.rol}</span>
                <div className="flex min-w-36 gap-2">
                  {!own && <>
                    <button type="button" aria-label={`Editar a ${account.email}`} className={button} onClick={() => setSelection({ mode: 'edit', account })}>Editar</button>
                    <button type="button" aria-label={`Eliminar a ${account.email}`} className={`${button} text-rose-200`} onClick={() => setSelection({ mode: 'delete', account })}>Eliminar</button>
                  </>}
                </div>
              </li>
            )
          })}
        </ul>}
      {selection && <UserEditor selection={selection} onClose={() => setSelection(null)} onSaved={saved} />}
    </GlassCard>
  )
}

export default AdminUsers
