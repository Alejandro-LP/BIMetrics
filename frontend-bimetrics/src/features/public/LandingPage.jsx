import { ArrowDown, ArrowRight, ArrowUpRight, Boxes, ChartNoAxesCombined, ClipboardCheck } from 'lucide-react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import PublicLayout from '../../components/layout/PublicLayout.jsx'
import GlassCard from '../../components/ui/GlassCard.jsx'
import axonometry from '../../assets/AXONOMETRIA.png'

const features = [
  { number: '01 / COSTOS', title: 'Precios que quedan registrados', text: 'Cada presupuesto conserva el costo aplicado al insumo en el momento del cálculo, aunque el catálogo cambie después.', icon: ChartNoAxesCombined },
  { number: '02 / PARTIDAS', title: 'Ajustes a la vista', text: 'Agrega insumos y cantidades desde el catálogo. El total se actualiza con el cálculo del servidor.', icon: Boxes },
  { number: '03 / EQUIPO', title: 'Acceso según el trabajo', text: 'Arquitectos e ingenieros gestionan presupuestos. Los clientes pueden consultar proyectos compartidos.', icon: ClipboardCheck },
]

function LandingPage() {
  return (
    <PublicLayout>
      <main className="relative isolate overflow-hidden">
        <div aria-hidden="true" className="pointer-events-none absolute left-[-12%] top-[-5%] -z-10 h-[480px] w-[480px] rounded-full bg-indigo-400/20 blur-[130px]" />
        <div aria-hidden="true" className="pointer-events-none absolute right-[-10%] top-[28%] -z-10 h-[520px] w-[520px] rounded-full bg-cyan-400/15 blur-[140px]" />

        <section className="mx-auto grid max-w-7xl items-center gap-12 px-5 py-16 sm:px-8 lg:min-h-[620px] lg:grid-cols-[1fr_0.92fr] lg:gap-16 lg:py-20">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <p className="mb-5 text-xs font-semibold uppercase tracking-[.2em] text-indigo-300">Presupuestos de obra · Colombia</p>
            <h1 className="max-w-2xl text-4xl font-bold leading-[1.1] tracking-tight text-white sm:text-5xl xl:text-6xl">Una buena obra empieza con <span className="bg-gradient-to-r from-blue-300 to-indigo-300 bg-clip-text text-transparent">buenas cuentas.</span></h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-slate-400">Organiza insumos, cantidades y costos en un solo presupuesto. Revisa cada partida y conserva el precio aplicado al momento del cálculo.</p>
            <div className="mt-8 flex flex-wrap items-center gap-5">
              <Link to="/registro" className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:from-blue-500 hover:to-indigo-500">Empieza tu presupuesto <ArrowRight size={16} /></Link>
              <a href="#como-funciona" className="inline-flex items-center gap-2 text-sm font-medium text-slate-300 transition hover:text-white">Conoce la herramienta <ArrowDown size={15} className="text-indigo-300" /></a>
            </div>
            <p className="mt-7 text-xs text-slate-500">✓ Valores en COP · Control de costos de obra</p>
          </motion.div>

          <GlassCard className="relative p-3 sm:p-5" transition={{ delay: 0.15 }}>
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] px-2 pb-3 text-[10px] font-semibold uppercase tracking-[.13em] text-slate-500">
              <span>Vista axonométrica · estudio preliminar</span>
              <span className="inline-flex items-center gap-2 text-cyan-300"><span className="h-1.5 w-1.5 rounded-full bg-cyan-300" /> Modelo BIM 5D</span>
            </div>
            <div className="my-3 overflow-hidden rounded-xl border border-white/10 bg-slate-950/50">
              <img src={axonometry} alt="Vista axonométrica ilustrativa de un modelo de construcción BIM" className="h-56 w-full object-cover sm:h-72" />
            </div>
            <div className="flex items-center justify-between gap-4 px-2 pb-1 pt-2">
              <div><span className="text-[10px] font-semibold uppercase tracking-[.15em] text-slate-500">Presupuesto organizado</span><p className="mt-1 text-sm font-semibold text-white">Costos, partidas y proyectos</p></div>
              <span className="grid h-9 w-9 place-items-center rounded-full bg-indigo-400/10 text-indigo-300 ring-1 ring-indigo-300/15"><ArrowUpRight size={17} /></span>
            </div>
          </GlassCard>
        </section>

        <section className="border-y border-white/[0.07] bg-white/[0.015] px-5 py-5 sm:px-8">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-8 gap-y-3 text-[10px] font-semibold uppercase tracking-[.16em] text-slate-500">
            <span className="text-indigo-300">Menos supuestos. Más claridad.</span><span>01 · Costos a la vista</span><span>02 · Historial ordenado</span><span>03 · Cálculo consistente</span>
          </div>
        </section>

        <section id="como-funciona" className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:py-24">
          <div className="mb-8 max-w-2xl"><p className="mb-3 text-xs font-semibold uppercase tracking-[.2em] text-indigo-300">Un flujo sencillo</p><h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Del catálogo a una decisión clara.</h2></div>
          <div className="grid gap-5 md:grid-cols-3">
            {['Organiza el proyecto|Reúne la obra y su presupuesto en un mismo espacio.', 'Define las partidas|Incluye insumos y cantidades desde el catálogo disponible.', 'Revisa y reutiliza|Consulta los costos calculados y duplica presupuestos cuando lo necesites.'].map((step, index) => {
              const [title, text] = step.split('|')
              return <GlassCard key={title} className="p-6"><span className="mb-5 block text-xs font-semibold tracking-[.15em] text-indigo-300">0{index + 1}</span><h3 className="text-lg font-semibold text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-400">{text}</p></GlassCard>
            })}
          </div>
        </section>

        <section id="herramientas" className="mx-auto grid max-w-7xl gap-7 px-5 pb-16 sm:px-8 lg:grid-cols-[.75fr_1.25fr] lg:pb-24">
          <div><p className="mb-3 text-xs font-semibold uppercase tracking-[.2em] text-indigo-300">Hecho para el trabajo diario</p><h2 className="text-3xl font-bold tracking-tight text-white">De cada partida hasta el total.</h2><p className="mt-4 max-w-md text-sm leading-6 text-slate-400">Un presupuesto claro permite entender de dónde sale cada costo y qué cambia cuando ajustas la obra.</p><Link to="/registro" className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-indigo-300 hover:text-indigo-200">Crea tu cuenta <ArrowRight size={15} /></Link></div>
          <div className="grid gap-4 sm:grid-cols-2">
            {features.map(({ number, title, text, icon: Icon }, index) => <GlassCard key={number} className={`p-5 ${index === 2 ? 'sm:col-span-2' : ''}`}><div className="mb-5 flex items-center justify-between"><span className="text-[10px] font-semibold tracking-[.15em] text-slate-500">{number}</span><Icon size={18} className="text-indigo-300" /></div><h3 className="font-semibold text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-400">{text}</p></GlassCard>)}
          </div>
        </section>

        <section className="mx-auto mb-16 flex max-w-7xl flex-wrap items-center justify-between gap-6 px-5 sm:px-8 lg:mb-24">
          <div><p className="mb-2 text-xs font-semibold uppercase tracking-[.2em] text-indigo-300">Empieza con un proyecto</p><h2 className="text-2xl font-bold text-white sm:text-3xl">Haz que los números cuenten una historia clara.</h2></div>
          <Link to="/registro" className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 text-sm font-semibold text-white">Crear cuenta <ArrowRight size={16} /></Link>
        </section>
      </main>
    </PublicLayout>
  )
}

export default LandingPage
