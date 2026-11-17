import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import DashboardLayout from '../../components/layout/DashboardLayout.jsx'
import GlassCard from '../../components/ui/GlassCard.jsx'
import { apiRequest } from '../../services/api.js'
import { useAuth } from '../auth/useAuth.js'
import AdminUsers from './AdminUsers.jsx'
import AdminCatalogPrices from './AdminCatalogPrices.jsx'

const number = new Intl.NumberFormat('es-CO')
const roles = { administrador: 'Administración', arquitecto: 'Arquitectura', ingeniero: 'Ingeniería', cliente: 'Clientes' }
const states = { completado: 'Completadas', advertencia: 'Con advertencias', fallido: 'Fallidas' }
const sections = { resumen: 'Resumen', usuarios: 'Usuarios', precios: 'Precios del catálogo' }

function Distribution({ title, values, labels }) {
  const total = Object.values(values ?? {}).reduce((sum, value) => sum + value, 0)
  return (
    <GlassCard className="p-6">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      {values ? (
        <ul className="mt-4 space-y-4">
          {Object.entries(labels).map(([key, label]) => {
            const count = values[key]
            return (
              <li key={key}>
                <div className="mb-1 flex justify-between gap-3 text-sm text-slate-200">
                  <span>{label}</span><span className="tabular-nums">{number.format(count)}</span>
                </div>
                <div aria-hidden="true" className="h-2 rounded-full bg-white/10">
                  <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-300" style={{ width: `${total ? count / total * 100 : 0}%` }} />
                </div>
              </li>
            )
          })}
        </ul>
      ) : <p className="mt-4 text-sm text-slate-400">No se pudo consultar la actividad BIM.</p>}
    </GlassCard>
  )
}

function AdminDashboardPage() {
  const { user, logout } = useAuth()
  const [searchParams] = useSearchParams()
  const requestedSection = searchParams.get('seccion')
  const section = Object.hasOwn(sections, requestedSection) ? requestedSection : 'resumen'
  const overview = section === 'resumen'
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState(null)
  const loading = result?.attempt !== attempt
  const summary = result?.summary
  const error = !loading && result?.error

  useEffect(() => {
    if (!overview) return
    const controller = new AbortController()
    apiRequest('/dashboard/administracion', { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setResult({ attempt, summary: data }) })
      .catch((failure) => { if (!controller.signal.aborted) setResult({ attempt, error: failure.message }) })
    return () => controller.abort()
  }, [attempt, overview])

  const metrics = summary ? [
    ['Cuentas registradas', Object.values(summary.cuentas_por_rol).reduce((sum, count) => sum + count, 0)],
    ['Proyectos', summary.proyectos],
    ['Proyectos compartidos', summary.proyectos_compartidos],
    ['Presupuestos', summary.presupuestos],
  ] : []

  return (
    <DashboardLayout user={user} onLogout={logout} administration>
      <section className="mx-auto max-w-7xl space-y-6" aria-busy={overview && loading}>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Panel de administración</h1>
            <p className="mt-2 text-sm text-slate-400">Consulta la actividad de BIMetrics y administra usuarios y precios.</p>
          </div>
          {overview && <button type="button" disabled={loading} onClick={() => setAttempt((value) => value + 1)} className="rounded-xl border border-indigo-300/30 px-4 py-2 text-sm font-medium text-indigo-100 hover:bg-indigo-400/10 disabled:opacity-60">
            {loading ? 'Actualizando…' : error ? 'Reintentar' : 'Actualizar estadísticas'}
          </button>}
        </div>
        <nav aria-label="Secciones de administración" className="flex flex-wrap gap-2 border-b border-white/10 pb-3">
          {Object.entries(sections).map(([key, label]) => (
            <Link key={key} to={key === 'resumen' ? '/administracion' : `?seccion=${key}`} aria-current={section === key ? 'page' : undefined} className="rounded-xl px-4 py-2 text-sm font-medium text-slate-300 hover:bg-white/5 aria-[current=page]:bg-indigo-400/15 aria-[current=page]:text-indigo-100">{label}</Link>
          ))}
        </nav>
        {section === 'usuarios' && <AdminUsers currentUser={user} />}
        {section === 'precios' && <AdminCatalogPrices />}
        {overview && error && <p role="alert" className="rounded-xl border border-rose-400/30 p-4 text-sm text-rose-200">{error}</p>}
        {overview && summary && <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map(([label, count]) => (
              <GlassCard key={label} className="p-5">
                <p className="text-sm text-indigo-200">{label}</p>
                <p className="mt-2 text-3xl font-semibold tabular-nums text-white">{number.format(count)}</p>
              </GlassCard>
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Distribution title="Cuentas por rol" values={summary.cuentas_por_rol} labels={roles} />
            <Distribution title="Actividades BIM por estado" values={summary.actividades_por_estado} labels={states} />
          </div>
        </>}
      </section>
    </DashboardLayout>
  )
}

export default AdminDashboardPage
