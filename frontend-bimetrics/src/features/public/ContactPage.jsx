import { useState } from 'react'
import { motion } from 'framer-motion'
import { Mail } from 'lucide-react'
import GlassCard from '../../components/ui/GlassCard.jsx'
import PublicLayout from '../../components/layout/PublicLayout.jsx'

function ContactPage() {
  const [status, setStatus] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const subject = encodeURIComponent('Solicitud desde BIMetrics')
    const body = encodeURIComponent(`Nombre: ${form.get('nombre') || 'No indicado'}\nCorreo: ${form.get('email')}\n\n${form.get('mensaje')}\n\nAutorizo el tratamiento de estos datos para atender esta solicitud.`)
    window.location.href = `mailto:joral2112@hotmail.com?subject=${subject}&body=${body}`
    setStatus('Se abrió tu aplicación de correo con el mensaje preparado. Revísalo y envíalo para completar la solicitud.')
  }

  return (
    <PublicLayout>
      <main className="mx-auto grid max-w-6xl gap-10 px-5 py-12 sm:px-8 sm:py-16 lg:grid-cols-[.8fr_1fr] lg:gap-16">
        <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <p className="mb-3 text-xs font-semibold uppercase tracking-[.2em] text-indigo-300">Atención y solicitudes</p>
          <h1 className="text-4xl font-bold leading-tight tracking-tight text-white sm:text-5xl">Estamos aquí para <span className="text-indigo-300">escucharte.</span></h1>
          <p className="mt-5 max-w-md text-sm leading-7 text-slate-400">Usa este formulario para consultas, solicitudes de privacidad o reportes de propiedad intelectual.</p>
          <p className="mt-8 inline-flex items-center gap-2 text-sm text-slate-400"><Mail size={16} className="text-indigo-300" /> joral2112@hotmail.com</p>
        </motion.section>

        <GlassCard className="p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-white">Escríbenos</h2>
          <p className="mt-2 text-sm text-slate-400">No incluyas datos sensibles ni información confidencial.</p>
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block text-sm text-slate-300" htmlFor="contact-name">Nombre <span className="text-xs text-slate-500">OPCIONAL</span></label>
            <input id="contact-name" name="nombre" maxLength={100} autoComplete="name" className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" />
            <label className="block text-sm text-slate-300" htmlFor="contact-email">Correo para responder</label>
            <input id="contact-email" name="email" type="email" maxLength={150} autoComplete="email" required className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" />
            <label className="block text-sm text-slate-300" htmlFor="contact-message">Mensaje</label>
            <textarea id="contact-message" name="mensaje" maxLength={2000} rows={5} required className="w-full resize-y rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" />
            <p className="text-xs leading-5 text-slate-500">Tu correo y mensaje se usarán solo para responder esta solicitud.</p>
            <label className="flex items-start gap-2.5 text-xs leading-5 text-slate-400"><input type="checkbox" name="autoriza" required className="mt-1 accent-indigo-400" /> He leído el aviso y autorizo el tratamiento de estos datos para atender mi solicitud.</label>
            {status && <p role="status" aria-live="polite" className="rounded-xl border border-emerald-400/20 bg-emerald-400/[0.07] p-3 text-sm text-emerald-200">{status}</p>}
            <button type="submit" className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-sm font-semibold text-white transition hover:from-blue-500 hover:to-indigo-500">Preparar correo</button>
          </form>
        </GlassCard>
      </main>
    </PublicLayout>
  )
}

export default ContactPage
