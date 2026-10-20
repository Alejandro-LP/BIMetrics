import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import GlassCard from '../../components/ui/GlassCard.jsx'
import PublicLayout from '../../components/layout/PublicLayout.jsx'

const documents = {
  terms: {
    title: 'Términos y condiciones de uso',
    eyebrow: 'CONDICIONES DEL SERVICIO',
    version: 'Versión 2026-10-15 · Sitio: bimetrics.co (dominio sujeto a confirmación)',
    sections: [
      ['Titular y aceptación', 'BIMetrics es un proyecto educativo y de validación técnica administrado por Jorge Alejandro Lopez Paez, persona natural domiciliada en Bogotá D.C., Colombia. Contacto: joral2112@hotmail.com. Dirección de notificación: completar antes de publicar. Para crear una cuenta se solicita aceptación separada de la autorización de tratamiento de datos descrita en la política de privacidad.'],
      ['Servicio y alcance', 'La plataforma permite organizar proyectos de obra, registrar insumos y cantidades, calcular presupuestos y consultar historial. Actualmente es gratuita, con posible membresía futura. Los valores y catálogos son referencias educativas; no constituyen oferta, cotización, aval técnico ni garantía del costo real. Verifica precios, cantidades, impuestos y requisitos con fuentes y profesionales pertinentes antes de decidir.'],
      ['Cuenta y uso permitido', 'Servicio dirigido a mayores de 18 años. Proporciona datos exactos, protege tus credenciales y reporta accesos sospechosos. No compartas la cuenta ni intentes acceder a cuentas o proyectos ajenos. Está prohibido suplantar personas, interferir con el servicio, evadir controles, introducir código malicioso o vulnerar derechos de terceros. Ante un riesgo de seguridad o abuso concreto, se podrá limitar temporalmente el acceso y se atenderán observaciones razonables del usuario.'],
      ['Contenido de usuarios', 'Solo registra nombres de clientes o propietarios si cuentas con autorización o fundamento jurídico aplicable, los informas cuando corresponda y limitas los datos a lo necesario. Evita datos sensibles, identificaciones y datos de menores. La carga de archivos aún no está disponible. Conservas los derechos sobre tu contenido y autorizas únicamente el tratamiento técnico necesario para alojarlo y mostrarlo en tu cuenta mientras usas el servicio.'],
      ['Pagos futuros', 'Actualmente no se reciben pagos ni datos de tarjeta. Antes de ofrecer membresías se informarán precio total, periodicidad, alcance, renovación, cancelación, medios de pago y derechos aplicables. Se publicarán las condiciones comerciales y se identificará la pasarela antes de contratar. BIMetrics no almacenará números completos de tarjeta ni códigos de seguridad.'],
      ['Propiedad intelectual', 'Los textos, diseño, logotipo, código e ilustraciones originales están protegidos por las normas aplicables. No se autoriza su reproducción o explotación salvo permiso escrito o excepción legal. Los materiales de terceros pertenecen a sus titulares. Para reportar una posible infracción, identifica la obra, URL, titularidad y forma de contacto en joral2112@hotmail.com.'],
      ['Disponibilidad, enlaces y responsabilidad', 'Se procura mantener el servicio disponible y adoptar medidas razonables de seguridad, pero pueden ocurrir interrupciones o fallos. Los enlaces externos se rigen por sus propias condiciones y políticas. En la medida permitida por la ley, no se responde por decisiones basadas exclusivamente en estimaciones ilustrativas o datos incorrectos ingresados por usuarios. Estas condiciones no excluyen derechos irrenunciables ni obligaciones legales de seguridad, información, calidad o diligencia.'],
      ['Cierre y cambios', 'Puedes pedir el cierre de cuenta en joral2112@hotmail.com. Los datos asociados se depuran dentro de 30 días, salvo conservación legal aplicable, conforme a la política de privacidad. Los términos podrán actualizarse por cambios del servicio o la ley; se indicará la fecha y se comunicará lo sustancial. La continuidad de uso no reemplaza una aceptación expresa cuando esta sea necesaria.'],
      ['Ley y atención', 'Se aplica la legislación colombiana. Puedes plantear inquietudes en joral2112@hotmail.com, sin limitar el acceso a las autoridades o mecanismos legales competentes. Si existe relación de consumo, se respetarán los derechos previstos en el Estatuto del Consumidor.'],
    ],
  },
  privacy: {
    title: 'Política de tratamiento de datos personales',
    eyebrow: 'INFORMACIÓN Y PRIVACIDAD',
    version: 'Versión 2026-10-15 · Vigencia desde su publicación',
    sections: [
      ['Responsable y contacto', 'Jorge Alejandro Lopez Paez, persona natural, Bogotá D.C., Colombia. Correo para privacidad y reclamos: joral2112@hotmail.com. Dirección de notificación: completar antes de publicar. Dominio: bimetrics.co, sujeto a confirmación al desplegar.'],
      ['Datos y finalidades', 'Cuenta: nombre, correo, rol y hash de contraseña para crear, autenticar y administrar la cuenta. La contraseña no se almacena en texto legible. Proyectos: nombre de obra, ciudad, nombre opcional del cliente o propietario, insumos, cantidades, precios por ciudad, costos, fechas e historial para organizar y calcular presupuestos solicitados. Contacto: nombre opcional, correo de respuesta y mensaje para responder consultas y solicitudes. Operación y seguridad: cookie técnica de sesión y registros que genere el alojamiento, potencialmente con IP, fecha y datos del navegador. Proveedor, región y periodo exactos de logs: completar antes de producción.'],
      ['Información sensible y de terceros', 'No se solicitan datos sensibles ni se dirige el servicio a menores de edad. No ingreses identificaciones, datos de salud, datos de menores ni información personal innecesaria. Los archivos adjuntos de presupuestos no están habilitados actualmente; se actualizará esta política antes de habilitarlos. Si registras el nombre de un cliente o propietario, debes contar con autorización o fundamento jurídico aplicable, informarle cuando corresponda y limitarte a lo necesario.'],
      ['Autorización y derechos', 'Cuando se requiere autorización, se solicita con una casilla vacía y una acción afirmativa, separada de cualquier aceptación de términos. Se conserva evidencia de la cuenta, fecha y versión de la política. No se solicita autorización promocional actualmente; si se incorpora publicidad, será opcional y separada. Puedes conocer, actualizar y rectificar tus datos; solicitar prueba de autorización e información sobre el uso; pedir supresión o revocar autorización cuando proceda; y presentar queja ante la SIC después de agotar la consulta o reclamo ante el responsable.'],
      ['Consultas y reclamos', 'Escribe a joral2112@hotmail.com con asunto “Datos personales – consulta” o “Datos personales – reclamo”. Indica nombre, correo de la cuenta, solicitud y datos que permitan localizarla. Se podrá pedir verificación razonable de identidad. No envíes contraseñas ni documentos de identidad por correo si no son estrictamente necesarios. Las consultas se atenderán en un máximo de 10 días hábiles; si no es posible, se informará el motivo y la fecha de respuesta dentro de los 5 días hábiles adicionales permitidos. Los reclamos completos se responderán en 15 días hábiles, prorrogables con explicación por hasta 8 días hábiles adicionales.'],
      ['Conservación y eliminación', 'Los datos de cuenta y proyectos se conservan mientras la cuenta esté activa. Tras solicitar el cierre, se depuran de la base de producción dentro de 30 días, salvo datos que deban conservarse por obligación legal o para atender reclamaciones. El ciclo de eliminación de respaldos y los plazos de mensajes de contacto y registros técnicos se deben confirmar antes de producción.'],
      ['Proveedores internacionales', 'Se prevé alojamiento en nube fuera de Colombia. Antes del lanzamiento se informarán el proveedor, país o región de almacenamiento, subencargados y medidas contractuales. El responsable verificará si hay transmisión o transferencia internacional y documentará las garantías aplicables. Las futuras pasarelas de pago se identificarán antes de activar membresías; BIMetrics no almacenará números completos de tarjeta ni códigos de seguridad.'],
      ['Cookies, seguridad y cambios', 'El sitio usa una cookie técnica de sesión necesaria para autenticación, configurada como HttpOnly, SameSite=Lax y Secure en producción HTTPS. No se implementan analítica ni píxeles publicitarios en la versión actual. Se aplican medidas proporcionales de control de acceso, hash de contraseñas, HTTPS, copias restringidas y actualización de dependencias; ninguna medida ofrece seguridad absoluta. Esta política puede actualizarse por cambios legales o funcionales. Normativa de referencia: Ley 1581 de 2012 y reglamentación compilada en el Decreto 1074 de 2015.'],
    ],
  },
}

function LegalPage({ document }) {
  const content = documents[document] || documents.terms

  return (
    <PublicLayout>
      <main className="mx-auto max-w-4xl px-5 py-12 sm:px-8 sm:py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <p className="mb-3 text-xs font-semibold uppercase tracking-[.2em] text-indigo-300">{content.eyebrow}</p>
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">{content.title}</h1>
          <p className="mt-3 text-sm text-slate-500">{content.version}</p>
          <GlassCard className="mt-8 space-y-7 p-6 sm:p-9">
            {content.sections.map(([heading, text], index) => (
              <section key={heading}>
                <h2 className="text-base font-semibold text-white">{index + 1}. {heading}</h2>
                <p className="mt-2 text-sm leading-7 text-slate-400">{text}</p>
              </section>
            ))}
            <p className="border-t border-white/10 pt-5 text-sm text-slate-400">Consulta también nuestra <Link to={document === 'privacy' ? '/terminos' : '/privacidad'} className="text-indigo-300 hover:text-indigo-200">{document === 'privacy' ? 'política de privacidad' : 'política de tratamiento de datos'}</Link>.</p>
          </GlassCard>
        </motion.div>
      </main>
    </PublicLayout>
  )
}

export default LegalPage
