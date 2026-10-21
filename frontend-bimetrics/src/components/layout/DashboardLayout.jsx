import { useState } from 'react'
import { Link } from 'react-router-dom'
import BrandLogo from '../brand/BrandLogo.jsx'

const navigation = [
  { label: 'Resumen general', href: '#dashboard' },
  { label: 'Proyectos y presupuestos', href: '#projects' },
  { label: 'Catálogo de insumos', href: '#catalog' },
  { label: 'Actividad BIM', href: '#activities' },
]

function DashboardLayout({ children, user, onLogout, onSearch }) {
  const [activeItem, setActiveItem] = useState('Resumen general')
  const displayName = user?.nombre_completo || 'BIMetrics'

  return (
    <div className="relative flex min-h-screen flex-col bg-transparent lg:flex-row">
      <aside className="glass-surface relative z-10 m-3 flex shrink-0 flex-col rounded-2xl p-4 sm:m-4 sm:p-5 lg:sticky lg:top-4 lg:m-4 lg:h-[calc(100vh-2rem)] lg:w-64 lg:rounded-3xl">
        <Link to="/dashboard" className="mb-5 flex items-center px-1" aria-label="BIMetrics, resumen general">
          <BrandLogo size="sm" />
        </Link>

        <p className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          Espacio de trabajo
        </p>
        <nav aria-label="Navegación principal" className="grid grid-cols-2 gap-1 lg:grid-cols-1">
          {navigation.map(({ label, href }) => {
            const active = activeItem === label
            return (
              <a
                key={label}
                href={href}
                onClick={() => setActiveItem(label)}
                aria-current={active ? 'location' : undefined}
                className={`rounded-xl px-3 py-2.5 text-sm leading-5 transition-colors ${
                  active
                    ? 'bg-indigo-400/10 font-medium text-indigo-100 ring-1 ring-indigo-300/20'
                    : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-100'
                }`}
              >
                {label}
              </a>
            )
          })}
        </nav>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.08] px-2 pt-4 lg:mt-auto">
          <Link to="/perfil" className="min-w-0 rounded-lg text-left" aria-label={`Abrir perfil de ${displayName}`}>
            <span className="block truncate text-sm font-medium text-slate-200">{displayName}</span>
            <span className="mt-0.5 block truncate text-xs capitalize text-slate-500">
              {user?.rol || 'Sesión'} · Ver perfil
            </span>
          </Link>
          {onLogout && (
            <button
              type="button"
              onClick={onLogout}
              className="rounded-lg px-3 py-2 text-sm text-slate-400 transition hover:bg-white/[0.05] hover:text-white"
            >
              Cerrar sesión
            </button>
          )}
        </div>
      </aside>

      <main className="relative z-10 flex min-h-0 min-w-0 flex-1 flex-col lg:h-screen">
        <header className="glass-surface mx-3 flex shrink-0 flex-wrap items-center justify-between gap-3 rounded-2xl px-4 py-3 sm:mx-4 sm:px-5 lg:mt-4">
          <label className="glass-control dashboard-search min-w-[min(100%,18rem)] flex-1 rounded-xl px-4 py-2.5 text-slate-300 transition-colors focus-within:border-indigo-300/50 focus-within:ring-2 focus-within:ring-indigo-400/10">
            <span className="sr-only">Buscar proyectos e insumos</span>
            <input
              type="search"
              placeholder="Buscar proyectos e insumos"
              aria-label="Buscar proyectos e insumos"
              onChange={(event) => onSearch?.(event.target.value)}
              className="w-full bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
            />
          </label>
          <p className="hidden max-w-52 truncate text-sm text-slate-400 sm:block" title={displayName}>
            {displayName}
          </p>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">{children}</div>
      </main>
    </div>
  )
}

export default DashboardLayout
