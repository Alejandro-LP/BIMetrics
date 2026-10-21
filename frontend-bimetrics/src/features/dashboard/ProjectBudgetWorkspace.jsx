import { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, Boxes, RotateCw } from 'lucide-react'
import { motion } from 'framer-motion'
import GlassCard from '../../components/ui/GlassCard.jsx'
import { API_BASE_URL, apiRequest } from '../../services/api.js'
import EmptyState from '../../components/ui/EmptyState.jsx'
import { toast } from 'sonner'

const currency = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })
const quantityFormat = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 3 })
const editorRoles = ['arquitecto', 'ingeniero', 'administrador']
const cities = ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena', 'Bucaramanga', 'Pereira', 'Manizales']

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00`)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'short', year: 'numeric' }).format(date)
}

function GlassSelect({ label, value, onChange, children, disabled = false }) {
  return (
    <label className="block min-w-0 flex-1 text-xs font-medium text-slate-500">
      {label}
      <select value={value} onChange={onChange} disabled={disabled} className="mt-2 w-full rounded-xl border border-white/10 bg-[#11151e] px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-400/40 disabled:opacity-50">
        {children}
      </select>
    </label>
  )
}

function ProjectBudgetWorkspace({ user, search = '' }) {
  const [projects, setProjects] = useState([])
  const [selectedProjectId, setSelectedProjectId] = useState('')
  const [budgets, setBudgets] = useState([])
  const [selectedBudgetId, setSelectedBudgetId] = useState('')
  const [budget, setBudget] = useState(null)
  const [catalog, setCatalog] = useState([])
  const [activities, setActivities] = useState([])
  const [activityLoading, setActivityLoading] = useState(true)
  const [projectLoading, setProjectLoading] = useState(true)
  const [budgetLoading, setBudgetLoading] = useState(false)
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [error, setError] = useState('')
  const [activityError, setActivityError] = useState('')
  const [notice, setNotice] = useState('')
  const [projectDialog, setProjectDialog] = useState(false)
  const [lineDialog, setLineDialog] = useState(false)
  const [newCatalogItem, setNewCatalogItem] = useState(false)
  const [projectForm, setProjectForm] = useState({ nombre_obra: '', ciudad: 'Bogotá', cliente: '' })
  const [lineForm, setLineForm] = useState({ id_insumo: '', cantidad: '' })
  const [newItemForm, setNewItemForm] = useState({ nombre_insumo: '', unidad_medida: '', costo_unitario: '' })
  const [busyAction, setBusyAction] = useState('')
  const noticeTimerRef = useRef(null)

  const project = projects.find((item) => String(item.id_proyecto) === String(selectedProjectId))
  const isEditor = editorRoles.includes(user?.rol)
  const isOwner = project?.es_propietario === true || project?.es_propietario === 1
  const canEdit = isEditor && Boolean(project)
  const query = search.trim().toLocaleLowerCase('es-CO')

  useEffect(() => {
    const controller = new AbortController()
    apiRequest('/proyectos', { signal: controller.signal })
      .then((items) => {
        setProjects(items)
        if (items.length) {
          setBudgetLoading(true)
          setCatalogLoading(true)
          setSelectedProjectId(String(items[0].id_proyecto))
        }
      })
      .catch((loadError) => {
        if (loadError.name !== 'AbortError') setError(loadError.message)
      })
      .finally(() => { if (!controller.signal.aborted) setProjectLoading(false) })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!selectedProjectId) return undefined
    const controller = new AbortController()
    apiRequest(`/presupuestos?id_proyecto=${encodeURIComponent(selectedProjectId)}`, { signal: controller.signal })
      .then((items) => {
        setBudgets(items)
        setBudgetLoading(Boolean(items.length))
        setSelectedBudgetId(items.length ? String(items[0].id_presupuesto) : '')
        if (!items.length) setBudget(null)
      })
      .catch((loadError) => { if (loadError.name !== 'AbortError') setError(loadError.message) })
      .finally(() => { if (!controller.signal.aborted) setBudgetLoading(false) })
    return () => controller.abort()
  }, [selectedProjectId])

  useEffect(() => {
    if (!selectedBudgetId) return undefined
    const controller = new AbortController()
    apiRequest(`/presupuestos/${selectedBudgetId}`, { signal: controller.signal })
      .then(setBudget)
      .catch((loadError) => { if (loadError.name !== 'AbortError') setError(loadError.message) })
      .finally(() => { if (!controller.signal.aborted) setBudgetLoading(false) })
    return () => controller.abort()
  }, [selectedBudgetId])

  useEffect(() => {
    if (!project?.ciudad) return undefined
    const controller = new AbortController()
    apiRequest(`/insumos?ciudad=${encodeURIComponent(project.ciudad)}`, { signal: controller.signal })
      .then(setCatalog)
      .catch((loadError) => { if (loadError.name !== 'AbortError') setError(loadError.message) })
      .finally(() => { if (!controller.signal.aborted) setCatalogLoading(false) })
    return () => controller.abort()
  }, [project?.ciudad])

  useEffect(() => {
    const controller = new AbortController()
    apiRequest(`/actividades-bim/usuario/${user.id_usuario}?limite=10`, { signal: controller.signal })
      .then((payload) => setActivities(Array.isArray(payload.actividades_recientes) ? payload.actividades_recientes : []))
      .catch((loadError) => { if (loadError.name !== 'AbortError') setActivityError(loadError.message) })
      .finally(() => { if (!controller.signal.aborted) setActivityLoading(false) })
    return () => controller.abort()
  }, [user.id_usuario])

  const lines = useMemo(() => Array.isArray(budget?.detalle) ? budget.detalle : [], [budget])
  const filteredLines = useMemo(() => lines.filter((line) => !query || `${line.nombre_insumo} ${line.unidad_medida}`.toLocaleLowerCase('es-CO').includes(query)), [lines, query])
  const filteredCatalog = useMemo(() => catalog.filter((item) => !query || `${item.nombre_insumo} ${item.unidad_medida}`.toLocaleLowerCase('es-CO').includes(query)), [catalog, query])
  const filteredActivities = useMemo(() => activities.filter((item) => !query || `${item.nombre_archivo} ${item.tipo_evento} ${item.software_origen}`.toLocaleLowerCase('es-CO').includes(query)), [activities, query])

  const costTotals = useMemo(() => lines.reduce((totals, line) => {
    const label = String(line.nombre_insumo || '').toLocaleLowerCase('es-CO')
    const unit = String(line.unidad_medida || '').toLocaleLowerCase('es-CO')
    const subtotal = Number(line.subtotal) || Number(line.cantidad) * Number(line.costo_unitario_aplicado) || 0
    if (/mano de obra|oficial|ayudante|operario|trabajador|salario|maestro/.test(label) || /^(jornal|hora|horas|día|dia|días|dias)$/.test(unit)) totals.labor += subtotal
    else totals.materials += subtotal
    if (/concreto|hormig[oó]n/.test(label) && /^(m3|m\^3|metro.?cúbico)$/.test(unit)) totals.concrete += Number(line.cantidad) || 0
    if (/acero|varilla|refuerzo/.test(label) && /^(kg|kilogramo|kilogramos)$/.test(unit)) totals.steel += Number(line.cantidad) || 0
    return totals
  }, { labor: 0, materials: 0, concrete: 0, steel: 0 }), [lines])

  useEffect(() => () => window.clearTimeout(noticeTimerRef.current), [])

  function announce(message) {
    toast.success(message)
    setNotice(message)
    window.clearTimeout(noticeTimerRef.current)
    noticeTimerRef.current = window.setTimeout(() => setNotice(''), 3500)
  }

  async function reloadProjects(preferredId) {
    const items = await apiRequest('/proyectos')
    setProjects(items)
    const nextProjectId = preferredId && items.some((item) => String(item.id_proyecto) === String(preferredId))
      ? String(preferredId)
      : items.length ? String(items[0].id_proyecto) : ''
    setBudgets([])
    setBudget(null)
    setSelectedBudgetId('')
    setBudgetLoading(Boolean(nextProjectId))
    setCatalogLoading(Boolean(nextProjectId))
    setSelectedProjectId(nextProjectId)
    return items
  }

  async function createProject(event) {
    event.preventDefault()
    setBusyAction('project')
    try {
      const created = await apiRequest('/proyectos', {
        method: 'POST',
        body: JSON.stringify({ ...projectForm, cliente: projectForm.cliente.trim() || null }),
      })
      setProjectDialog(false)
      setProjectForm({ nombre_obra: '', ciudad: 'Bogotá', cliente: '' })
      await reloadProjects(created.id_proyecto)
      announce('Proyecto creado. Puedes generar su presupuesto.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  async function deleteProject() {
    if (!project || !window.confirm(`¿Eliminar “${project.nombre_obra}” y sus presupuestos? Esta acción no se puede deshacer.`)) return
    setBusyAction('delete-project')
    try {
      await apiRequest(`/proyectos/${project.id_proyecto}`, { method: 'DELETE' })
      const remaining = projects.filter((item) => item.id_proyecto !== project.id_proyecto)
      setProjects(remaining)
      setBudgets([])
      setSelectedBudgetId('')
      setBudget(null)
      setBudgetLoading(false)
      setCatalogLoading(false)
      setSelectedProjectId(remaining.length ? String(remaining[0].id_proyecto) : '')
      announce('Proyecto y presupuestos eliminados.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  async function createBudget() {
    if (!project || !canEdit) return
    setBusyAction('create-budget')
    try {
      const created = await apiRequest('/presupuestos', {
        method: 'POST',
        body: JSON.stringify({ id_proyecto: project.id_proyecto }),
      })
      setBudgets((items) => [created, ...items])
      setSelectedBudgetId(String(created.id_presupuesto))
      setBudget(created)
      announce('Presupuesto creado.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  async function inviteCollaborator() {
    if (!project) return
    const email = window.prompt('Correo de la cuenta registrada del arquitecto o ingeniero:')
    if (!email?.trim()) return
    try {
      const result = await apiRequest(`/proyectos/${project.id_proyecto}/colaboradores`, {
        method: 'POST', body: JSON.stringify({ email: email.trim() }),
      })
      announce(result.mensaje || 'Colaborador agregado al proyecto.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
  }

  async function createLine(event) {
    event.preventDefault()
    if (!budget) return
    setBusyAction('line')
    try {
      let idInsumo = Number(lineForm.id_insumo)
      if (newCatalogItem) {
        const item = await apiRequest('/insumos', {
          method: 'POST',
          body: JSON.stringify({
            ...newItemForm,
            costo_unitario: Number(newItemForm.costo_unitario),
            ciudad: project?.ciudad || 'Bogotá',
          }),
        })
        idInsumo = item.id_insumo
      }
      const updated = await apiRequest(`/presupuestos/${budget.id_presupuesto}/detalle`, {
        method: 'POST',
        body: JSON.stringify({ id_insumo: idInsumo, cantidad: Number(lineForm.cantidad) }),
      })
      setBudget(updated)
      setBudgets((items) => items.map((item) => item.id_presupuesto === updated.id_presupuesto ? updated : item))
      setLineDialog(false)
      setLineForm({ id_insumo: '', cantidad: '' })
      setNewItemForm({ nombre_insumo: '', unidad_medida: '', costo_unitario: '' })
      setNewCatalogItem(false)
      announce('Insumo agregado al presupuesto.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  async function removeLine(line) {
    if (!window.confirm(`¿Quitar “${line.nombre_insumo}” del presupuesto?`)) return
    try {
      const updated = await apiRequest(`/presupuestos/${budget.id_presupuesto}/detalle/${line.id_detalle}`, { method: 'DELETE' })
      setBudget(updated)
      setBudgets((items) => items.map((item) => item.id_presupuesto === updated.id_presupuesto ? updated : item))
      announce('Partida eliminada del presupuesto.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
  }

  async function recalculate() {
    if (!budget) return
    setBusyAction('recalculate')
    try {
      await apiRequest(`/presupuestos/${budget.id_presupuesto}/calcular`, { method: 'POST' })
      const updated = await apiRequest(`/presupuestos/${budget.id_presupuesto}`)
      setBudget(updated)
      setBudgets((items) => items.map((item) => item.id_presupuesto === updated.id_presupuesto ? updated : item))
      announce('Presupuesto recalculado correctamente.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  async function duplicateBudget() {
    if (!budget) return
    setBusyAction('duplicate')
    try {
      const copy = await apiRequest(`/presupuestos/${budget.id_presupuesto}/duplicar`, { method: 'POST', body: JSON.stringify({}) })
      setBudgets((items) => [copy, ...items])
      setSelectedBudgetId(String(copy.id_presupuesto))
      setBudget(copy)
      announce('Copia creada con los precios vigentes del catálogo.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  async function exportExcel() {
    if (!budget) return
    setBusyAction('export')
    try {
      let response
      try {
        response = await fetch(`${API_BASE_URL}/presupuestos/${budget.id_presupuesto}/excel`, { credentials: 'include' })
      } catch (cause) {
        if (cause.name === 'AbortError') throw cause
        throw new Error('No fue posible conectar con BIMetrics para exportar el archivo.', { cause })
      }
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || 'No se pudo exportar el presupuesto.')
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `Presupuesto_${(project?.nombre_obra || 'BIMetrics').replace(/[^a-zA-Z0-9_-]/g, '_')}_${budget.id_presupuesto}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
    } catch (actionError) { setError(actionError.message) }
    finally { setBusyAction('') }
  }

  return (
    <div className="space-y-6">
      {error && <div role="alert" className="flex items-start justify-between gap-4 rounded-xl border border-rose-400/20 bg-rose-400/[0.07] px-4 py-3 text-sm text-rose-200"><span>{error}</span><button type="button" onClick={() => setError('')} aria-label="Cerrar aviso">Cerrar</button></div>}
      {notice && <div role="status" className="rounded-xl border border-emerald-400/20 bg-emerald-400/[0.07] px-4 py-3 text-sm text-emerald-200">{notice}</div>}

      <GlassCard id="projects" className="p-5 sm:p-6">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div><p className="text-sm font-semibold text-white">Proyectos y presupuestos</p><p className="mt-1 text-xs text-slate-500">Selecciona una obra para consultar o actualizar su presupuesto.</p></div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setProjectDialog(true)} disabled={!isEditor} className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-3.5 py-2 text-xs font-semibold text-white disabled:opacity-40"> Nuevo proyecto</button>
            {isOwner && isEditor && <button type="button" onClick={inviteCollaborator} className="inline-flex items-center justify-center rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:bg-white/[0.05]"> Invitar</button>}
            {isOwner && isEditor && <button type="button" onClick={deleteProject} disabled={busyAction === 'delete-project'} aria-label="Eliminar proyecto" className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-slate-400 transition hover:border-rose-400/20 hover:text-rose-300"></button>}
          </div>
        </div>
        {projectLoading ? <p className="py-6 text-sm text-slate-500">Cargando proyectos…</p> : projects.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            <GlassSelect label="Proyecto" value={selectedProjectId} onChange={(event) => { setBudgets([]); setBudget(null); setSelectedBudgetId(''); setBudgetLoading(true); setCatalogLoading(true); setError(''); setSelectedProjectId(event.target.value) }}>
              {projects.map((item) => <option key={item.id_proyecto} value={item.id_proyecto}>{item.nombre_obra} · {item.ciudad || 'Bogotá'}</option>)}
            </GlassSelect>
            <div className="flex items-end gap-3">
              <GlassSelect label="Presupuesto" value={selectedBudgetId} disabled={!budgets.length} onChange={(event) => { setBudgetLoading(true); setError(''); setSelectedBudgetId(event.target.value) }}>
                {budgets.length ? budgets.map((item, index) => <option key={item.id_presupuesto} value={item.id_presupuesto}>Presupuesto {budgets.length - index} · {formatDate(item.fecha_calculo)} · {currency.format(item.costo_total || 0)}</option>) : <option value="">Sin presupuestos</option>}
              </GlassSelect>
              {canEdit && <button type="button" onClick={createBudget} disabled={busyAction === 'create-budget'} className="mb-0.5 shrink-0 rounded-xl border border-white/10 px-3 py-2.5 text-xs text-slate-300 hover:bg-white/[0.05]">Nuevo</button>}
            </div>
          </div>
        ) : <EmptyState title="Todav?a no hay proyectos" description="Crea una obra para organizar sus presupuestos y actividad BIM." action="Crear proyecto" onAction={() => setProjectDialog(true)} />}
      </GlassCard>

      {project && <GlassCard className="p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Obra en desarrollo</p><h2 className="mt-2 text-xl font-semibold text-white">{project.nombre_obra}</h2><p className="mt-1 text-sm text-slate-400">{[project.ciudad, project.cliente, project.responsable].filter(Boolean).join(' · ')}</p></div>
          <div className="flex flex-wrap gap-2">
            {canEdit && <button type="button" disabled={!budget || Boolean(busyAction)} onClick={() => { setLineDialog(true); setNewCatalogItem(false) }} className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-3.5 py-2.5 text-xs font-semibold text-white disabled:opacity-40"> Agregar partida</button>}
            <button type="button" disabled={!budget || Boolean(busyAction)} onClick={recalculate} className="inline-flex items-center justify-center rounded-xl border border-white/10 px-3.5 py-2.5 text-xs text-slate-300 hover:bg-white/[0.05] disabled:opacity-40"> Recalcular</button>
            {canEdit && <button type="button" disabled={!budget || Boolean(busyAction)} onClick={duplicateBudget} className="inline-flex items-center justify-center rounded-xl border border-white/10 px-3.5 py-2.5 text-xs text-slate-300 hover:bg-white/[0.05] disabled:opacity-40"> Duplicar</button>}
            <button type="button" disabled={!budget || Boolean(busyAction)} onClick={exportExcel} className="inline-flex items-center justify-center rounded-xl border border-white/10 px-3.5 py-2.5 text-xs text-slate-300 hover:bg-white/[0.05] disabled:opacity-40"> Excel</button>
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ['Costo estimado', currency.format(Number(budget?.costo_total) || 0)],
            ['Partidas', String(lines.length).padStart(2, '0')],
            ['Concreto', costTotals.concrete ? `${quantityFormat.format(costTotals.concrete)} m³` : '—'],
            ['Acero', costTotals.steel ? `${quantityFormat.format(costTotals.steel)} kg` : '—'],
          ].map(([label, value]) => <div key={label} className="rounded-xl border border-white/[0.07] bg-black/20 p-4"><p className="text-[10px] font-semibold uppercase tracking-[.15em] text-slate-500">{label}</p><p className="mt-2 text-lg font-semibold text-white">{value}</p></div>)}
        </div>
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-400"><span>Materiales y otros: <strong className="text-slate-200">{currency.format(costTotals.materials)}</strong></span><span>Mano de obra: <strong className="text-slate-200">{currency.format(costTotals.labor)}</strong></span><span className="ml-auto">Último cálculo: {formatDate(budget?.fecha_calculo)}</span></div>
      </GlassCard>}

      <GlassCard id="presupuesto" className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] p-5 sm:px-6">
          <div><p className="text-sm font-semibold text-white">Detalle del presupuesto</p><p className="mt-1 text-xs text-slate-500">{budget?.nombre_obra || project?.nombre_obra || 'Selecciona un proyecto'} · {lines.length} partidas</p></div>
          {budgetLoading && <span className="text-xs text-slate-500">Actualizando…</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-xs">
            <thead className="bg-white/[0.025] text-[10px] uppercase tracking-[.12em] text-slate-500"><tr><th className="px-5 py-3 font-semibold sm:px-6">Insumo</th><th className="px-3 py-3 font-semibold">Unidad</th><th className="px-3 py-3 text-right font-semibold">Cantidad</th><th className="px-3 py-3 text-right font-semibold">Costo unitario</th><th className="px-3 py-3 text-right font-semibold">Subtotal</th><th className="px-4 py-3" /></tr></thead>
            <tbody className="divide-y divide-white/[0.06]">
              {filteredLines.map((line) => <tr key={line.id_detalle} className="text-slate-300 transition hover:bg-white/[0.02]"><td className="max-w-[260px] truncate px-5 py-3.5 font-medium text-slate-200 sm:px-6">{line.nombre_insumo}</td><td className="px-3 py-3.5 text-slate-500">{line.unidad_medida}</td><td className="px-3 py-3.5 text-right tabular-nums">{quantityFormat.format(Number(line.cantidad))}</td><td className="px-3 py-3.5 text-right tabular-nums">{currency.format(Number(line.costo_unitario_aplicado))}</td><td className="px-3 py-3.5 text-right font-medium tabular-nums text-white">{currency.format(Number(line.subtotal) || Number(line.cantidad) * Number(line.costo_unitario_aplicado))}</td><td className="px-4 py-3.5 text-right">{canEdit && <button type="button" onClick={() => removeLine(line)} aria-label={`Quitar ${line.nombre_insumo}`} className="rounded-md px-2 text-slate-500 hover:bg-rose-400/10 hover:text-rose-300">Quitar</button>}</td></tr>)}
              {(!filteredLines.length) && <tr><td colSpan="6" className="px-6 py-10 text-center text-slate-500">{budget ? query ? 'No hay partidas que coincidan con la búsqueda.' : 'Este presupuesto todavía no tiene partidas.' : project ? budgets.length ? 'Selecciona un presupuesto.' : 'Este proyecto no tiene presupuestos. Crea uno para comenzar.' : 'Selecciona o crea un proyecto para consultar el presupuesto.'}</td></tr>}
            </tbody>
            {budget && <tfoot><tr className="border-t border-white/10 bg-white/[0.02]"><td colSpan="4" className="px-5 py-4 text-right font-semibold text-slate-300 sm:px-6">Total del presupuesto</td><td className="px-3 py-4 text-right text-sm font-semibold text-white">{currency.format(Number(budget.costo_total) || 0)}</td><td /></tr></tfoot>}
          </table>
        </div>
      </GlassCard>

      <section className="grid gap-6 xl:grid-cols-2">
        <GlassCard id="catalog" className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/[0.08] p-5"><div><p className="text-sm font-semibold text-white">Catálogo de insumos</p><p className="mt-1 text-xs text-slate-500">Precios aplicables a {project?.ciudad || 'la ciudad seleccionada'}</p></div><Boxes size={18} className="text-indigo-300" /></div>
          {catalogLoading ? <p className="p-6 text-sm text-slate-500">Cargando catálogo…</p> : <div className="max-h-[360px] overflow-auto"><table className="w-full min-w-[440px] text-left text-xs"><thead className="sticky top-0 bg-[#11151e] text-[10px] uppercase tracking-[.12em] text-slate-500"><tr><th className="px-5 py-3 font-semibold">Insumo</th><th className="px-3 py-3 font-semibold">Unidad</th><th className="px-5 py-3 text-right font-semibold">Precio</th></tr></thead><tbody className="divide-y divide-white/[0.06]">{filteredCatalog.map((item) => <tr key={item.id_insumo}><td className="px-5 py-3 text-slate-200">{item.nombre_insumo}</td><td className="px-3 py-3 text-slate-500">{item.unidad_medida}</td><td className="px-5 py-3 text-right tabular-nums text-slate-300">{Number(item.costo_unitario) > 0 ? currency.format(Number(item.costo_unitario)) : <span className="text-amber-300">Sin precio</span>}</td></tr>)}{!filteredCatalog.length && <tr><td colSpan="3" className="px-5 py-8 text-center text-slate-500">{catalog.length ? 'No hay insumos que coincidan con la búsqueda.' : 'El catálogo está vacío para esta ciudad.'}</td></tr>}</tbody></table></div>}
        </GlassCard>

        <GlassCard id="activities" className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-white/[0.08] p-5"><div><p className="text-sm font-semibold text-white">Actividad BIM reciente</p><p className="mt-1 text-xs text-slate-500">Importaciones y procesos asociados a tu cuenta</p></div><Activity size={18} className="text-cyan-300" /></div>
          {activityError ? <p className="p-6 text-sm text-rose-200">{activityError}</p> : activityLoading ? <p className="p-6 text-sm text-slate-500">Cargando actividad BIM…</p> : <div className="overflow-x-auto"><table className="w-full min-w-[430px] text-left text-xs"><thead className="bg-white/[0.02] text-[10px] uppercase tracking-[.12em] text-slate-500"><tr><th className="px-5 py-3 font-semibold">Archivo / proceso</th><th className="px-3 py-3 font-semibold">Origen</th><th className="px-5 py-3 text-right font-semibold">Estado</th></tr></thead><tbody className="divide-y divide-white/[0.06]">{filteredActivities.map((item) => <tr key={item.id}><td className="max-w-[190px] truncate px-5 py-3.5 text-slate-200" title={item.nombre_archivo}>{item.nombre_archivo || item.tipo_evento || 'Actividad BIM'}</td><td className="px-3 py-3.5 text-slate-500">{item.software_origen || '—'}</td><td className="px-5 py-3.5 text-right"><span className={`rounded-full border px-2 py-1 text-[10px] ${item.estado === 'completado' ? 'border-emerald-300/20 bg-emerald-300/10 text-emerald-300' : item.estado === 'advertencia' ? 'border-amber-300/20 bg-amber-300/10 text-amber-300' : 'border-rose-300/20 bg-rose-300/10 text-rose-300'}`}>{item.estado || 'completado'}</span></td></tr>)}{!filteredActivities.length && <tr><td colSpan="3" className="px-5 py-8 text-center text-slate-500">{activities.length ? 'No hay actividad que coincida con la búsqueda.' : 'Todavía no hay importaciones BIM registradas.'}</td></tr>}</tbody></table></div>}
          <div className="flex items-center gap-2 border-t border-white/[0.06] px-5 py-3 text-[10px] text-slate-500"><RotateCw size={12} /> Historial BIM desde el almacén documental NoSQL</div>
        </GlassCard>
      </section>

      {projectDialog && <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setProjectDialog(false) }}><motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-lg"><GlassCard role="dialog" aria-modal="true" aria-labelledby="new-project-title" className="p-6 sm:p-7"><div className="mb-5 flex items-start justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Nueva obra</p><h2 id="new-project-title" className="mt-1 text-xl font-semibold text-white">Iniciar proyecto</h2></div><button type="button" onClick={() => setProjectDialog(false)} className="text-xl text-slate-500 hover:text-white" aria-label="Cerrar">×</button></div><form onSubmit={createProject} className="space-y-4"><label className="block text-sm text-slate-300">Nombre del proyecto<input required maxLength={150} value={projectForm.nombre_obra} onChange={(event) => setProjectForm({ ...projectForm, nombre_obra: event.target.value })} placeholder="Ej. Casa en Chapinero" className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" /></label><label className="block text-sm text-slate-300">Ciudad<select value={projectForm.ciudad} onChange={(event) => setProjectForm({ ...projectForm, ciudad: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-[#11151e] px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50">{cities.map((city) => <option key={city}>{city}</option>)}</select></label><label className="block text-sm text-slate-300">Cliente (opcional)<input maxLength={150} value={projectForm.cliente} onChange={(event) => setProjectForm({ ...projectForm, cliente: event.target.value })} placeholder="Nombre del cliente" className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" /></label><div className="flex justify-end gap-3 pt-2"><button type="button" onClick={() => setProjectDialog(false)} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300">Cancelar</button><button type="submit" disabled={busyAction === 'project'} className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busyAction === 'project' ? 'Creando…' : 'Crear proyecto'}</button></div></form></GlassCard></motion.div></div>}

      {lineDialog && <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setLineDialog(false) }}><motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-lg"><GlassCard role="dialog" aria-modal="true" aria-labelledby="add-line-title" className="p-6 sm:p-7"><div className="mb-5 flex items-start justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Nueva partida</p><h2 id="add-line-title" className="mt-1 text-xl font-semibold text-white">Agregar insumo</h2></div><button type="button" onClick={() => setLineDialog(false)} className="text-xl text-slate-500 hover:text-white" aria-label="Cerrar">×</button></div><form onSubmit={createLine} className="space-y-4">{!newCatalogItem ? <label className="block text-sm text-slate-300">Insumo del catálogo<select required value={lineForm.id_insumo} onChange={(event) => setLineForm({ ...lineForm, id_insumo: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-[#11151e] px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50"><option value="">Selecciona un insumo</option>{catalog.map((item) => <option key={item.id_insumo} value={item.id_insumo} disabled={Number(item.costo_unitario) <= 0}>{item.nombre_insumo} · {item.unidad_medida} · {Number(item.costo_unitario) > 0 ? currency.format(item.costo_unitario) : 'sin precio'}</option>)}</select></label> : <><label className="block text-sm text-slate-300">Nombre del insumo<input required maxLength={150} value={newItemForm.nombre_insumo} onChange={(event) => setNewItemForm({ ...newItemForm, nombre_insumo: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none" /></label><div className="grid gap-4 sm:grid-cols-2"><label className="block text-sm text-slate-300">Unidad<input required maxLength={30} placeholder="Ej. kg, m³" value={newItemForm.unidad_medida} onChange={(event) => setNewItemForm({ ...newItemForm, unidad_medida: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none" /></label><label className="block text-sm text-slate-300">Precio para {project?.ciudad}<input required type="number" min="0.01" step="0.01" value={newItemForm.costo_unitario} onChange={(event) => setNewItemForm({ ...newItemForm, costo_unitario: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none" /></label></div></>}
              <label className="block text-sm text-slate-300">Cantidad<input required type="number" min="0.001" step="any" value={lineForm.cantidad} onChange={(event) => setLineForm({ ...lineForm, cantidad: event.target.value })} placeholder="Ej. 2.5" className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" /></label>
              {canEdit && <button type="button" onClick={() => { setNewCatalogItem(!newCatalogItem); setLineForm({ ...lineForm, id_insumo: '' }) }} className="text-xs font-medium text-indigo-300 hover:text-indigo-200">{newCatalogItem ? 'Elegir del catálogo' : 'Crear insumo con precio para esta ciudad'}</button>}
              <div className="flex justify-end gap-3 border-t border-white/[0.08] pt-4"><button type="button" onClick={() => setLineDialog(false)} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300">Cancelar</button><button type="submit" disabled={busyAction === 'line'} className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busyAction === 'line' ? 'Guardando…' : 'Agregar partida'}</button></div>
            </form></GlassCard></motion.div></div>}
    </div>
  )
}

export default ProjectBudgetWorkspace
