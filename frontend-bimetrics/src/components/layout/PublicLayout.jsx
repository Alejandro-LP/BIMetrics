import { Link, NavLink } from 'react-router-dom'
import BrandLogo from '../brand/BrandLogo.jsx'

function PublicLayout({ children }) {
  return (
    <div className="min-h-screen bg-transparent text-slate-300">
      <header className="glass-surface sticky top-3 z-30 mx-3 rounded-2xl px-5 sm:mx-6 sm:px-8">
        <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between gap-5">
          <Link to="/" className="flex shrink-0" aria-label="BIMetrics inicio"><BrandLogo size="sm" /></Link>
          <nav className="flex items-center gap-4 text-sm text-slate-400 sm:gap-7" aria-label="Navegación principal">
            <NavLink to="/#como-funciona" className="hidden transition hover:text-white sm:inline">Cómo funciona</NavLink>
            <NavLink to="/contacto" className="hidden transition hover:text-white sm:inline">Contacto</NavLink>
            <NavLink to="/login" className="transition hover:text-white">Iniciar sesión</NavLink>
            <NavLink to="/registro" className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-3.5 py-2 font-medium text-white transition hover:from-blue-500 hover:to-indigo-500 sm:px-4">Crear cuenta</NavLink>
          </nav>
        </div>
      </header>
      {children}
      <footer className="border-t border-white/[0.08] px-5 py-7 text-xs text-slate-500 sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4">
          <Link to="/" className="font-semibold text-slate-300">BIMetrics</Link>
          <span>Colombia · COP</span>
          <div className="flex gap-4"><Link to="/terminos" className="hover:text-slate-300">Términos</Link><Link to="/privacidad" className="hover:text-slate-300">Privacidad</Link><Link to="/contacto" className="hover:text-slate-300">Contacto</Link></div>
        </div>
      </footer>
    </div>
  )
}

export default PublicLayout
