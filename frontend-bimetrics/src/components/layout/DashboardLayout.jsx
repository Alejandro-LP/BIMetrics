import { useState } from 'react'
import { Box, Folder, LayoutDashboard, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import BrandLogo from '../brand/BrandLogo.jsx'

const navigation = [
  { label: 'Resumen general', icon: LayoutDashboard, href: '#dashboard' },
  { label: 'Proyectos y presupuestos', icon: Folder, href: '#projects' },
  { label: 'Cat?logo de insumos', icon: Box, href: '#catalog' },
  { label: 'Actividad BIM', icon: Box, href: '#activities' },
]

function DashboardLayout({ children, user, onLogout, onSearch }) {
  const [activeItem, setActiveItem] = useState('Resumen general')
  const displayName = user?.nombre_completo || 'BIMetrics'
  const initials = displayName.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-transparent">
      <div
        aria-hidden="true"
        className="pointer-events-none fixed left-[-10%] top-[-10%] h-[560px] w-[560px] rounded-full bg-indigo-400/20 blur-[145px]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none fixed bottom-[-20%] right-[-8%] h-[560px] w-[560px] rounded-full bg-cyan-400/15 blur-[150px]"
      />
      <div aria-hidden="true" className="pointer-events-none fixed left-[45%] top-[42%] h-72 w-72 rounded-full bg-purple-500/[0.12] blur-[120px]" />

      <aside className="glass-surface relative z-10 m-4 flex w-64 shrink-0 flex-col rounded-3xl p-5 max-md:w-56 max-md:px-3">
        <a href="#dashboard" className="mb-10 flex items-center px-1 max-md:justify-center" aria-label="BIMetrics inicio">
          <BrandLogo size="sm" className="max-md:[&>span]:hidden" />
        </a>

        <p className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
          Navegaci?n del espacio
        </p>
        <nav aria-label="Navegación principal" className="space-y-1">
          {navigation.map(({ label, icon: Icon, href }) => {
            const active = activeItem === label
            return (
              <a
                key={label}
                href={href}
                onClick={() => setActiveItem(label)}
                aria-current={active ? 'location' : undefined}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition-colors ${
                  active
                    ? 'bg-indigo-500/15 font-medium text-indigo-200 ring-1 ring-indigo-400/20'
                    : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-100'
                }`}
              >
                <Icon size={18} strokeWidth={1.8} />
                <span>{label}</span>
              </a>
            )
          })}
        </nav>

        <div className="mt-auto border-t border-white/10 pt-4 max-md:border-0">
          <div className="flex items-center gap-3 rounded-xl px-1 py-2">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-indigo-400 to-cyan-400 text-xs font-bold text-slate-950">
              {initials}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-200">{displayName}</p>
              <p className="truncate text-xs capitalize text-slate-500">{user?.rol || 'Sesión'}</p>
            </div>
          </div>
        </div>
      </aside>

      <main className="relative z-10 flex h-screen min-w-0 flex-1 flex-col overflow-hidden">
        <header className="glass-surface mx-4 mt-4 flex h-[72px] shrink-0 items-center justify-between gap-6 rounded-2xl px-5 max-sm:mx-3 max-sm:px-3">
          <label className="glass-control flex w-full max-w-md items-center gap-3 rounded-xl px-3.5 py-2.5 text-slate-400 transition-colors focus-within:border-indigo-300/50 focus-within:ring-2 focus-within:ring-indigo-400/10">
            <Search size={17} />
            <input
              type="search"
              placeholder="Buscar proyectos, modelos..."
              aria-label="Buscar proyectos y modelos"
              onChange={(event) => onSearch?.(event.target.value)}
              className="w-full bg-transparent text-sm text-slate-200 outline-none placeholder:text-slate-600"
            />
            <kbd className="rounded border border-white/10 px-1.5 py-0.5 text-[10px] text-slate-600">⌘ K</kbd>
          </label>
          <Link to="/perfil" className="flex shrink-0 items-center gap-3 rounded-full text-left" aria-label={`Perfil de ${displayName}`}>
            <span className="grid h-9 w-9 place-items-center rounded-full border border-white/10 bg-gradient-to-br from-indigo-400 to-cyan-400 text-xs font-bold text-slate-950">
              {initials}
            </span>
            <span className="text-sm font-medium text-slate-300 max-sm:hidden">Perfil: {displayName}</span>
          </Link>
          {onLogout && <button type="button" onClick={onLogout} className="rounded-lg px-2 py-2 text-xs text-slate-500 transition hover:bg-white/[0.05] hover:text-slate-200">Salir</button>}
        </header>

        <div className="flex-1 overflow-y-auto p-8 max-sm:p-4">{children}</div>
      </main>
    </div>
  )
}

export default DashboardLayout
