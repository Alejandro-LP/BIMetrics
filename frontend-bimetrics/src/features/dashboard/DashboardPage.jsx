import { useEffect, useState } from 'react'
import { Activity, ArrowUpRight, Boxes, Building2, CircleAlert, Clock3, DollarSign, RefreshCw } from 'lucide-react'
import DashboardLayout from '../../components/layout/DashboardLayout.jsx'
import GlassCard from '../../components/ui/GlassCard.jsx'
import { API_BASE_URL, apiRequest } from '../../services/api.js'
import { useAuth } from '../auth/useAuth.js'
import ProjectBudgetWorkspace from './ProjectBudgetWorkspace.jsx'

const formatCurrency = (value) => new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
}).format(value || 0)

const formatDate = (value) => {
  if (!value) return 'Fecha no disponible'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? 'Fecha no disponible'
    : date.toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })
}

function DashboardPage() {
  const { user, logout } = useAuth()
  const [summary, setSummary] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    async function loadSummary() {
      setIsLoading(true)
      setError('')

      try {
        const payload = await apiRequest('/dashboard/resumen', { signal: controller.signal })
        setSummary(payload.resumen)
      } catch (fetchError) {
        if (fetchError.name !== 'AbortError') {
          setError(fetchError.message || 'No se pudo conectar con la API de BIMetrics.')
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    loadSummary()
    return () => controller.abort()
  }, [reloadKey])

  const metrics = summary ? [
    {
      label: 'Presupuesto vigente',
      value: formatCurrency(summary.presupuesto_total),
      detail: 'Suma del último presupuesto de cada proyecto',
      icon: DollarSign,
      accent: 'text-emerald-300 bg-emerald-400/10 ring-emerald-300/15',
    },
    {
      label: 'Proyectos',
      value: summary.total_proyectos.toLocaleString('es-CO'),
      detail: 'Proyectos propios y compartidos',
      icon: Building2,
      accent: 'text-indigo-300 bg-indigo-400/10 ring-indigo-300/15',
    },
    {
      label: 'Insumos disponibles',
      value: summary.total_insumos.toLocaleString('es-CO'),
      detail: 'Elementos del catálogo de costos',
      icon: Boxes,
      accent: 'text-cyan-300 bg-cyan-400/10 ring-cyan-300/15',
    },
  ] : []

  return (
    <DashboardLayout user={user} onLogout={logout} onSearch={setSearch}>
      <section id="dashboard" className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-2 text-sm font-medium text-indigo-300">Resumen general</p>
            <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Dashboard BIM 5D
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Proyectos, presupuestos y actividad BIM de tu espacio de trabajo.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setReloadKey((key) => key + 1)}
            disabled={isLoading}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-indigo-400/30 hover:bg-indigo-400/10 disabled:cursor-wait disabled:opacity-60"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            Actualizar
          </button>
        </div>

        {error && (
          <GlassCard role="alert" className="mb-6 flex flex-wrap items-center justify-between gap-4 border-rose-400/20 p-5">
            <div className="flex items-start gap-3">
              <CircleAlert size={19} className="mt-0.5 shrink-0 text-rose-300" />
              <div>
                <p className="font-medium text-rose-200">No se pudo cargar el dashboard</p>
                <p className="mt-1 text-sm text-slate-400">{error}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/[0.06]"
            >
              Reintentar
            </button>
          </GlassCard>
        )}

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {isLoading && !summary
            ? [0, 1, 2].map((item) => (
              <GlassCard key={item} className="h-40 animate-pulse p-6" aria-label="Cargando métrica">
                <div className="mb-8 h-3 w-32 rounded bg-white/10" />
                <div className="h-8 w-40 rounded bg-white/10" />
                <div className="mt-3 h-3 w-48 rounded bg-white/[0.06]" />
              </GlassCard>
            ))
            : metrics.map(({ label, value, detail, icon: Icon, accent }, index) => (
              <GlassCard key={label} className="p-6" transition={{ delay: index * 0.1 }}>
                <div className="mb-7 flex items-start justify-between gap-3">
                  <p className="text-sm font-medium text-slate-400">{label}</p>
                  <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ring-1 ${accent}`}>
                    <Icon size={19} strokeWidth={1.8} />
                  </span>
                </div>
                <p className="break-words text-3xl font-semibold tracking-tight text-white">{value}</p>
                <p className="mt-2 text-xs text-slate-500">{detail}</p>
              </GlassCard>
            ))}
        </div>

        <GlassCard className="mt-6 p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-cyan-400/10 text-cyan-300 ring-1 ring-cyan-300/15">
                {summary?.ultima_actividad_bim ? <Activity size={19} /> : <Clock3 size={19} />}
              </span>
              <div>
                <p className="text-sm font-semibold text-white">Última actividad BIM</p>
                {summary?.ultima_actividad_bim ? (
                  <>
                    <p className="mt-1 text-sm text-slate-300">
                      {summary.ultima_actividad_bim.nombre_archivo || summary.ultima_actividad_bim.tipo_evento}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {summary.ultima_actividad_bim.software_origen || 'Origen no especificado'}
                      {' · '}{formatDate(summary.ultima_actividad_bim.fecha_registro)}
                    </p>
                  </>
                ) : (
                  <p className="mt-1 text-sm text-slate-500">
                    {summary?.mongodb_disponible === false
                      ? 'MongoDB no está disponible; las métricas SQL siguen activas.'
                      : 'Todavía no hay importaciones BIM registradas.'}
                  </p>
                )}
              </div>
            </div>
            <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${
              error
                ? 'border-rose-400/20 bg-rose-400/10 text-rose-300'
                : summary
                  ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                  : 'border-indigo-400/20 bg-indigo-400/10 text-indigo-300'
            }`}>
              <span className={`h-1.5 w-1.5 rounded-full ${
                error ? 'bg-rose-300' : summary ? 'bg-emerald-300' : 'bg-indigo-300'
              }`} />
              {error ? 'API no disponible' : summary ? 'API conectada' : 'Conectando'}
            </span>
          </div>
          <a
            href={`${API_BASE_URL}/salud`}
            target="_blank"
            rel="noreferrer"
            className="mt-5 inline-flex items-center gap-1 text-xs text-indigo-300 transition hover:text-indigo-200"
          >
            Estado del servicio <ArrowUpRight size={13} />
          </a>
        </GlassCard>

        <div className="mt-8">
          <ProjectBudgetWorkspace user={user} search={search} />
        </div>
      </section>
    </DashboardLayout>
  )
}

export default DashboardPage
