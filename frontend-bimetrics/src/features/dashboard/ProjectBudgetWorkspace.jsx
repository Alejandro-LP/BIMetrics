import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Trash2 } from 'lucide-react'
import GlassCard from '../../components/ui/GlassCard.jsx'
import { API_BASE_URL, apiRequest } from '../../services/api.js'
import EmptyState from '../../components/ui/EmptyState.jsx'
import { toast } from 'sonner'

const currency = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 })
const quantityFormat = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 3 })
const editorRoles = ['arquitecto', 'ingeniero', 'administrador']
const cities = ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena', 'Bucaramanga', 'Pereira', 'Manizales']
const ASSOCIATED_LABOR_PAIRS = [
  { equipmentCode: '0XA110', laborCode: '0XA130', label: 'andamio tubular de fachada' },
  { equipmentCode: '0XA113', laborCode: '0XA133', label: 'torre de trabajo móvil' },
  { equipmentCode: '0XA114', laborCode: '0XA134', label: 'plataforma motorizada' },
  { equipmentCode: '0XA115', laborCode: '0XA135', label: 'plataforma suspendida' },
  { equipmentCode: '0XT110', laborCode: '0XT130', label: 'grúa torre' },
]

function formatDate(value) {
  if (!value) return '—'
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00`)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'short', year: 'numeric' }).format(date)
}

function isLaborResourceForRole(item, role) {
  const name = item.nombre_insumo.toLocaleLowerCase('es-CO')
  const checks = [
    [/montador de andamios|montador de plataformas/, /montaje y desmontaje de (andamio|torre de trabajo|plataforma|gr[uú]a)/],
    [/coordinador de trabajo en alturas/, /coordinador.*alturas/],
    [/montador de estructuras met[aá]licas/, /montador|armador.*estructura met[aá]lica/],
    [/conductor de cami[oó]n/, /conductor|chofer|transportista/],
    [/operador/, /operador|operari|maquinaria/],
    [/oficial de obra negra|oficial de obra|oficial de construcci[oó]n/, /oficial|maestro/],
    [/mampostero/, /mamposter|ladrillero|oficial/],
    [/ayudante/, /ayudante|auxiliar|jornal/],
    [/encofrador|formaletero/, /encofrador|formaleter|carpintero de obra/],
    [/armador de acero/, /armador|acero.*mano de obra|fierrero/],
    [/mampostero/, /mamposter|ladrillero/],
    [/oficial de acabados/, /oficial de acabados|pintor|acabado/],
    [/electricista/, /electricista|eléctrico.*mano de obra/],
    [/plomero|plomería|hidrosanitario/, /plomer[ií]a|plomero|fontanero|hidrosanit/],
    [/pintor/, /pintor/],
    [/estucador/, /estucador|estuco/],
    [/enchapador|ceramista/, /enchapador|ceramista|enchape/],
    [/instalador de cubierta/, /cubierta|techo|teja/],
    [/soldador|armador/, /soldador|armador|soldadura/],
  ]
  const rule = checks.find(([rolePattern]) => rolePattern.test(role.toLocaleLowerCase('es-CO')))
  return Boolean(rule && rule[1].test(name))
}

function GlassSelect({ label, value, onChange, children, disabled = false }) {
  return (
    <label className="block min-w-0 flex-1 text-xs font-medium text-slate-500">
      {label}
      <select value={value} onChange={onChange} disabled={disabled} className="glass-select mt-2 w-full rounded-xl border border-white/10 bg-[#11151e] px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-400/40 disabled:opacity-50">
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
  const [catalogData, setCatalogData] = useState({ city: '', items: [] })
  const [masterPartidas, setMasterPartidas] = useState([])
  const [masterPartidaSearch, setMasterPartidaSearch] = useState('')
  const [masterPartidasLoading, setMasterPartidasLoading] = useState(false)
  const [masterPartidasHasMore, setMasterPartidasHasMore] = useState(false)
  const [partidas, setPartidas] = useState([])
  const [partidaSearch, setPartidaSearch] = useState('')
  const [selectedPartidaCode, setSelectedPartidaCode] = useState('')
  const [selectedPartidaDetail, setSelectedPartidaDetail] = useState(null)
  const [selectedVariationId, setSelectedVariationId] = useState('')
  const [partidasHasMore, setPartidasHasMore] = useState(false)
  const [partidasLoading, setPartidasLoading] = useState(false)
  const [laborSelection, setLaborSelection] = useState({})
  const [laborQuantities, setLaborQuantities] = useState({})
  const [activities, setActivities] = useState([])
  const [activityLoading, setActivityLoading] = useState(true)
  const [projectLoading, setProjectLoading] = useState(true)
  const [budgetLoading, setBudgetLoading] = useState(false)
  const [error, setError] = useState('')
  const [activityError, setActivityError] = useState('')
  const [notice, setNotice] = useState('')
  const [projectDialog, setProjectDialog] = useState(false)
  const [aiuDialog, setAiuDialog] = useState(false)
  const [creatingBudget, setCreatingBudget] = useState(false)
  const [aiuForm, setAiuForm] = useState({ administracion: '0', imprevistos: '0', utilidad: '0' })
  const [lineDialog, setLineDialog] = useState(false)
  const [txtDialog, setTxtDialog] = useState(false)
  const [txtSoftware, setTxtSoftware] = useState('revit')
  const [txtFile, setTxtFile] = useState(null)
  const [txtImport, setTxtImport] = useState(null)
  const [txtChoices, setTxtChoices] = useState({})
  const [txtLoading, setTxtLoading] = useState(false)
  const [txtAdding, setTxtAdding] = useState(null)
  const [newCatalogItem, setNewCatalogItem] = useState(false)
  const [projectForm, setProjectForm] = useState({ nombre_obra: '', ciudad: 'Bogotá', cliente: '' })
  const [lineForm, setLineForm] = useState({ id_insumo: '', cantidad: '' })
  const [newItemForm, setNewItemForm] = useState({ nombre_insumo: '', unidad_medida: '', costo_unitario: '' })
  const [busyAction, setBusyAction] = useState('')
  const noticeTimerRef = useRef(null)

  const project = projects.find((item) => String(item.id_proyecto) === String(selectedProjectId))
  const catalog = useMemo(() => catalogData.city === project?.ciudad ? catalogData.items : [], [catalogData, project?.ciudad])
  const laborCatalogLoading = Boolean(project?.ciudad && catalogData.city !== project.ciudad)
  const isEditor = editorRoles.includes(user?.rol)
  const isOwner = project?.es_propietario === true || project?.es_propietario === 1
  const canEdit = isEditor && Boolean(project)
  const isAdmin = user?.rol === 'administrador'
  const query = search.trim().toLocaleLowerCase('es-CO')

  useEffect(() => {
    const controller = new AbortController()
    apiRequest('/proyectos', { signal: controller.signal })
      .then((items) => {
        setProjects(items)
        if (items.length) {
          setBudgetLoading(true)
          setSelectedProjectId(String(items[0].id_proyecto))
        } else {
          setBudgetLoading(false)
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
        if (items.length) {
          setBudgetLoading(true)
          setSelectedBudgetId(String(items[0].id_presupuesto))
        } else {
          setSelectedBudgetId('')
          setBudget(null)
          setBudgetLoading(false)
        }
      })
      .catch((loadError) => {
        if (loadError.name !== 'AbortError') {
          setError(loadError.message)
          setBudgetLoading(false)
        }
      })
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
    const city = project.ciudad
    apiRequest(`/insumos?ciudad=${encodeURIComponent(project.ciudad)}`, { signal: controller.signal })
      .then((items) => { if (!controller.signal.aborted) setCatalogData({ city, items }) })
      .catch((loadError) => {
        if (loadError.name !== 'AbortError') {
          setCatalogData({ city, items: [] })
          setError(loadError.message)
        }
      })
    return () => controller.abort()
  }, [project?.ciudad])

  const projectId = project?.id_proyecto
  useEffect(() => {
    if (!projectId) return undefined
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setMasterPartidas([])
      setMasterPartidasLoading(true)
      setMasterPartidasHasMore(false)
      const term = masterPartidaSearch.trim()
      const endpoint = term
        ? `/partidas/buscar?q=${encodeURIComponent(term)}&limit=200&offset=0`
        : '/partidas?limit=200&offset=0'
      apiRequest(endpoint, { signal: controller.signal })
        .then((items) => {
          setMasterPartidas(items)
          setMasterPartidasHasMore(items.length === 200)
        })
        .catch((loadError) => { if (loadError.name !== 'AbortError') setError(loadError.message) })
        .finally(() => { if (!controller.signal.aborted) setMasterPartidasLoading(false) })
    }, 200)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [projectId, masterPartidaSearch])

  useEffect(() => {
    if (!lineDialog || newCatalogItem) return undefined
    const term = partidaSearch.trim()
    if (term.length < 2) return undefined
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      setPartidasLoading(true)
      setPartidas([])
      setPartidasHasMore(false)
      const endpoint = `/partidas/buscar?q=${encodeURIComponent(term)}&limit=200&offset=0`
      apiRequest(endpoint, { signal: controller.signal })
        .then((items) => { setPartidas(items); setPartidasHasMore(items.length === 200) })
        .catch((loadError) => { if (loadError.name !== 'AbortError') setError(loadError.message) })
        .finally(() => { if (!controller.signal.aborted) setPartidasLoading(false) })
    }, 250)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [lineDialog, newCatalogItem, partidaSearch])

  useEffect(() => {
    if (!lineDialog || !selectedPartidaCode || newCatalogItem) return undefined
    const controller = new AbortController()
    apiRequest(`/partidas/${encodeURIComponent(selectedPartidaCode)}`, { signal: controller.signal })
      .then(setSelectedPartidaDetail)
      .catch((loadError) => { if (loadError.name !== 'AbortError') setError(loadError.message) })
    return () => controller.abort()
  }, [lineDialog, newCatalogItem, selectedPartidaCode])

  useEffect(() => {
    const controller = new AbortController()
    apiRequest(`/actividades-bim/usuario/${user.id_usuario}?limite=10`, { signal: controller.signal })
      .then((payload) => setActivities(Array.isArray(payload.actividades_recientes) ? payload.actividades_recientes : []))
      .catch((loadError) => { if (loadError.name !== 'AbortError') setActivityError(loadError.message) })
      .finally(() => { if (!controller.signal.aborted) setActivityLoading(false) })
    return () => controller.abort()
  }, [user.id_usuario])

  const lines = useMemo(() => Array.isArray(budget?.detalle) ? budget.detalle : [], [budget])
  const missingAssociatedLabor = useMemo(() => ASSOCIATED_LABOR_PAIRS.flatMap((pair) => {
    const matchingRentals = lines.filter((line) => String(line.nombre_insumo || '').startsWith(`${pair.equipmentCode} ·`))
    const alreadyIncluded = lines.some((line) => String(line.nombre_insumo || '').startsWith(`${pair.laborCode} ·`))
    if (!matchingRentals.length || alreadyIncluded) return []
    return [{ ...pair, quantity: matchingRentals.reduce((total, line) => total + Number(line.cantidad || 0), 0) }]
  }), [lines])
  const filteredLines = useMemo(() => lines.filter((line) => !query || `${line.nombre_insumo} ${line.unidad_medida}`.toLocaleLowerCase('es-CO').includes(query)), [lines, query])
  const filteredMasterPartidas = useMemo(() => (project ? masterPartidas : []).filter((item) => !query || `${item.codigo} ${item.descripcion} ${item.unidad}`.toLocaleLowerCase('es-CO').includes(query)), [masterPartidas, project, query])
  const selectedPartida = selectedPartidaDetail?.codigo === selectedPartidaCode
    ? selectedPartidaDetail
    : partidas.find((item) => item.codigo === selectedPartidaCode)
  const visiblePartidaSuggestions = selectedPartidaCode ? [] : partidas.slice(0, 8)
  const selectedVariation = selectedPartida?.variaciones?.find((item) => String(item.id) === selectedVariationId)
  const laborRecommendations = useMemo(() => {
    if (!selectedPartida) return []
    const recomendacionesSQL = selectedPartidaDetail?.codigo === selectedPartida.codigo
      ? selectedPartidaDetail.recomendaciones_mano_obra || []
      : []
    if (recomendacionesSQL.length) {
      const roles = recomendacionesSQL.map((item) => item.perfil)
      const availableRoles = roles.filter((role) => catalog.some((item) => Number(item.costo_unitario) > 0 && isLaborResourceForRole(item, role)))
      return [{ title: 'Perfiles sugeridos para esta partida', roles, availableRoles, detalles: recomendacionesSQL }]
    }
    const description = selectedPartida.descripcion.toLocaleLowerCase('es-CO')
    const rules = [
      { match: /alquiler de andamio|alquiler de torre de trabajo|alquiler de plataforma|alquiler de gr[uú]a/, title: 'Montaje y desmontaje de equipo', roles: ['Montador de andamios'] },
      { match: /montaje y desmontaje de (andamio|torre de trabajo|plataforma|gr[uú]a)/, title: 'Montaje y desmontaje de equipo', roles: ['Montador de andamios'] },
      { match: /excav|demolici|zanja|movimiento de tierras/, title: 'Excavación y demolición', roles: ['Operador de maquinaria', 'Oficial de obra', 'Ayudante de construcción'] },
      { match: /concreto|hormig[oó]n|cimentaci|formaleta|estructura|acero de refuerzo/, title: 'Concreto y estructura', roles: ['Oficial de obra negra', 'Ayudante de construcción', 'Encofrador / formaletero', 'Armador de acero'] },
      { match: /mamposter[ií]a|ladrillo|bloque|pañete|revoque|mortero/, title: 'Mampostería y pañetes', roles: ['Oficial mampostero', 'Ayudante de construcción'] },
      { match: /electric|cableado|luminaria|tablero|puesta a tierra/, title: 'Instalaciones eléctricas', roles: ['Oficial electricista', 'Auxiliar electricista'] },
      { match: /hidrosanit|fontaner[ií]a|tuber[ií]a|desag[uü]e|sanitario|grifer[ií]a/, title: 'Instalaciones hidrosanitarias', roles: ['Oficial plomero / instalador hidrosanitario', 'Auxiliar de plomería'] },
      { match: /pintura|estuco|enchape|cer[aá]mica|acabado|impermeabiliz/, title: 'Acabados', roles: ['Pintor de obra', 'Estucador', 'Enchapador / ceramista', 'Ayudante de construcción'] },
      { match: /cubierta|teja|cubrici[oó]n|estructura met[aá]lica|soldadura/, title: 'Cubiertas y metal', roles: ['Instalador de cubierta', 'Soldador / armador', 'Ayudante de construcción'] },
    ]
    const rule = rules.find((item) => item.match.test(description))
    const fallbackRule = { title: 'Mano de obra general (revisar especialidad)', roles: ['Oficial de obra', 'Ayudante de construcción'] }
    const selectedRule = rule || fallbackRule
    const availableRoles = selectedRule.roles.filter((role) => catalog.some((item) => Number(item.costo_unitario) > 0 && isLaborResourceForRole(item, role)))
    return [{ ...selectedRule, availableRoles, detalles: [] }]
  }, [catalog, selectedPartida, selectedPartidaDetail])
  const suggestedLaborItems = useMemo(() => {
    const itemsById = new Map()
    laborRecommendations.forEach((suggestion) => {
      suggestion.roles.forEach((role) => {
        const item = catalog.find((candidate) => Number(candidate.costo_unitario) > 0 && isLaborResourceForRole(candidate, role))
        if (item) {
          const current = itemsById.get(item.id_insumo)
          const evidence = suggestion.detalles?.find((detail) => detail.perfil === role)
          const roles = [...(current?.sugerido_para || []), role]
          const conditionalRoles = [...(current?.roles_condicionales || [])]
          if (evidence?.tipo === 'condicional') conditionalRoles.push(role)
          itemsById.set(item.id_insumo, {
            ...item,
            sugerido_para: roles,
            roles_condicionales: conditionalRoles,
            condicional: roles.every((suggestedRole) => conditionalRoles.includes(suggestedRole)),
          })
        }
      })
    })
    return [...itemsById.values()]
  }, [catalog, laborRecommendations])
  const selectedLaborItems = newCatalogItem
    ? []
    : suggestedLaborItems.filter((item) => laborSelection[item.id_insumo] ?? !item.condicional)
  const filteredActivities = useMemo(() => activities.filter((item) => !query || `${item.nombre_archivo} ${item.tipo_evento} ${item.software_origen}`.toLocaleLowerCase('es-CO').includes(query)), [activities, query])

  const costTotals = useMemo(() => lines.reduce((totals, line) => {
    const label = String(line.nombre_insumo || '').toLocaleLowerCase('es-CO')
    const unit = String(line.unidad_medida || '').toLocaleLowerCase('es-CO').trim()
    const subtotal = Number(line.subtotal) || Number(line.cantidad) * Number(line.costo_unitario_aplicado) || 0
    if (/mano de obra|oficial|ayudante|operario|trabajador|salario|maestro|montaje y desmontaje de andamio/.test(label) || /^(jornal|hora|horas|día|dia|días|dias)$/.test(unit)) {
      totals.labor += subtotal
      totals.laborCount += 1
    } else {
      totals.materials += subtotal
      totals.materialCount += 1
    }
    return totals
  }, { labor: 0, materials: 0, laborCount: 0, materialCount: 0 }), [lines])

  const budgetCards = [
    {
      label: 'Costo estimado',
      value: budgetLoading && !budget
        ? 'Cargando…'
        : !budget
          ? 'Sin presupuesto'
          : lines.length
            ? currency.format(Number(budget.costo_total) || 0)
            : 'Pendiente',
      detail: !budget
        ? 'Crea o selecciona un presupuesto'
        : lines.length
          ? 'Total calculado para esta obra'
          : 'Agrega insumos para calcular el total',
    },
    {
      label: 'Insumos',
      value: costTotals.materialCount ? currency.format(costTotals.materials) : 'Sin insumos',
      detail: `${costTotals.materialCount} ${costTotals.materialCount === 1 ? 'partida' : 'partidas'} en el presupuesto`,
    },
    {
      label: 'Mano de obra',
      value: costTotals.laborCount ? currency.format(costTotals.labor) : 'Sin mano de obra',
      detail: `${costTotals.laborCount} ${costTotals.laborCount === 1 ? 'recurso laboral' : 'recursos laborales'} agregados`,
    },
    {
      label: 'Elementos del presupuesto',
      value: String(lines.length).padStart(2, '0'),
      detail: lines.length ? 'Líneas registradas en esta obra' : 'Aún no hay líneas registradas',
    },
  ]

  useEffect(() => () => window.clearTimeout(noticeTimerRef.current), [])

  function announce(message) {
    toast.success(message)
    setNotice(message)
    window.clearTimeout(noticeTimerRef.current)
    noticeTimerRef.current = window.setTimeout(() => setNotice(''), 3500)
  }


  async function addScaffoldLabor() {
    if (!budget || !missingAssociatedLabor.length) return
    setBusyAction('scaffold-labor')
    try {
      const updated = await apiRequest(`/presupuestos/${budget.id_presupuesto}/mano-obra-asociada`, { method: 'POST' })
      setBudget(updated)
      setBudgets((items) => items.map((entry) => entry.id_presupuesto === updated.id_presupuesto ? updated : entry))
      announce('Se agregó el montaje de los equipos con el precio del catálogo SQL.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  async function analyzeTxt() {
    if (!budget || !txtFile) return
    setTxtLoading(true)
    setError('')
    try {
      const form = new FormData()
      form.append('archivo', txtFile)
      form.append('software', txtSoftware)
      const result = await apiRequest(`/presupuestos/${budget.id_presupuesto}/importar-txt/analizar`, { method: 'POST', body: form })
      setTxtImport(result)
      setTxtChoices(Object.fromEntries(result.filas.map((row) => [row.indice, row.sugerencias[0]?.codigo || ''])))
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setTxtLoading(false) }
  }

  async function addImportedRow(row) {
    const codigo = txtChoices[row.indice]
    if (!codigo) return
    setTxtAdding(row.indice)
    try {
      const updated = await apiRequest(`/presupuestos/${budget.id_presupuesto}/partidas`, {
        method: 'POST',
        body: JSON.stringify({ codigo, cantidad: row.cantidad }),
      })
      setBudget(updated)
      setBudgets((items) => items.map((item) => item.id_presupuesto === updated.id_presupuesto ? updated : item))
      setTxtImport((current) => ({ ...current, filas: current.filas.map((item) => item.indice === row.indice ? { ...item, agregado: true } : item) }))
      announce(`“${row.nombre}” agregado con el precio vigente del catálogo SQL.`)
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setTxtAdding(null) }
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
      setSelectedProjectId(remaining.length ? String(remaining[0].id_proyecto) : '')
      announce('Proyecto y presupuestos eliminados.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  function createBudget() {
    if (!project || !canEdit) return
    setCreatingBudget(true)
    setAiuForm({ administracion: '0', imprevistos: '0', utilidad: '0' })
    setAiuDialog(true)
  }

  async function saveAiu(event) {
    event.preventDefault()
    if (!project || !canEdit) return
    const isNew = creatingBudget
    setBusyAction('create-budget')
    try {
      const data = { aiu: Object.fromEntries(Object.entries(aiuForm).map(([key, value]) => [key, Number(value)])) }
      const result = isNew
        ? await apiRequest('/presupuestos', { method: 'POST', body: JSON.stringify({ id_proyecto: project.id_proyecto, ...data }) })
        : await apiRequest(`/presupuestos/${budget.id_presupuesto}/aiu`, { method: 'PUT', body: JSON.stringify(data) })
      setBudgets((items) => isNew ? [result, ...items] : items.map((item) => item.id_presupuesto === result.id_presupuesto ? result : item))
      setSelectedBudgetId(String(result.id_presupuesto))
      setBudget(result)
      setAiuDialog(false)
      announce(isNew ? 'Presupuesto creado con AIU.' : 'Porcentajes AIU actualizados.')
    } catch (actionError) { setError(actionError.message); toast.error(actionError.message) }
    finally { setBusyAction('') }
  }

  function openAiuEditor() {
    setCreatingBudget(false)
    setAiuForm({
      administracion: String(Number(budget?.porcentaje_administracion) || 0),
      imprevistos: String(Number(budget?.porcentaje_imprevistos) || 0),
      utilidad: String(Number(budget?.porcentaje_utilidad) || 0),
    })
    setAiuDialog(true)
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

  async function loadMorePartidas() {
    if (partidasLoading || !partidasHasMore) return
    setPartidasLoading(true)
    try {
      const term = partidaSearch.trim()
      const nextPages = []
      let offset = partidas.length
      let hasMore = true
      while (hasMore) {
        const endpoint = term
          ? `/partidas/buscar?q=${encodeURIComponent(term)}&limit=200&offset=${offset}`
          : `/partidas?limit=200&offset=${offset}`
        const nextPage = await apiRequest(endpoint)
        nextPages.push(...nextPage)
        offset += nextPage.length
        hasMore = nextPage.length === 200
      }
      setPartidas((items) => [...items, ...nextPages])
      setPartidasHasMore(false)
    } catch (actionError) {
      setError(actionError.message)
    } finally {
      setPartidasLoading(false)
    }
  }

  async function loadAllMasterPartidas() {
    if (masterPartidasLoading || !masterPartidasHasMore) return
    setMasterPartidasLoading(true)
    try {
      const term = masterPartidaSearch.trim()
      const remaining = []
      let offset = masterPartidas.length
      let hasMore = true
      while (hasMore) {
        const endpoint = term
          ? `/partidas/buscar?q=${encodeURIComponent(term)}&limit=200&offset=${offset}`
          : `/partidas?limit=200&offset=${offset}`
        const page = await apiRequest(endpoint)
        remaining.push(...page)
        offset += page.length
        hasMore = page.length === 200
      }
      setMasterPartidas((items) => [...items, ...remaining])
      setMasterPartidasHasMore(false)
    } catch (actionError) {
      setError(actionError.message)
    } finally {
      setMasterPartidasLoading(false)
    }
  }

  async function createLine(event) {
    event.preventDefault()
    if (!budget) return
    setBusyAction('line')
    try {
      const laborLines = selectedLaborItems.map((item) => ({
        id_insumo: item.id_insumo,
        cantidad: Number(laborQuantities[item.id_insumo] || 1),
      }))
      let updated
      if (!newCatalogItem) {
        if (!selectedPartida) throw new Error('Selecciona un insumo del catálogo.')
        updated = await apiRequest(`/presupuestos/${budget.id_presupuesto}/partidas`, {
          method: 'POST',
          body: JSON.stringify({
            codigo: selectedPartida.codigo,
            variacion_id: selectedVariationId ? Number(selectedVariationId) : null,
            cantidad: Number(lineForm.cantidad),
            lineas_mano_obra: laborLines,
          }),
        })
      } else {
        if (!isAdmin) throw new Error('Solo un administrador puede crear insumos y registrar precios manuales.')
        const item = await apiRequest('/insumos', {
          method: 'POST',
          body: JSON.stringify({ ...newItemForm, costo_unitario: Number(newItemForm.costo_unitario), ciudad: project?.ciudad || 'Bogotá' }),
        })
        updated = await apiRequest(`/presupuestos/${budget.id_presupuesto}/detalle`, {
          method: 'POST',
          body: JSON.stringify({ id_insumo: item.id_insumo, cantidad: Number(lineForm.cantidad), lineas_mano_obra: laborLines }),
        })
      }
      setBudget(updated)
      setBudgets((items) => items.map((item) => item.id_presupuesto === updated.id_presupuesto ? updated : item))
      setLineDialog(false)
      setLineForm({ id_insumo: '', cantidad: '' })
      setSelectedPartidaCode('')
      setSelectedPartidaDetail(null)
      setSelectedVariationId('')
      setPartidaSearch('')
      setNewItemForm({ nombre_insumo: '', unidad_medida: '', costo_unitario: '' })
      setNewCatalogItem(false)
      announce(selectedLaborItems.length
        ? `Insumo del catálogo y ${selectedLaborItems.length} recurso(s) laboral(es) agregados.`
        : 'Insumo agregado con precio vigente del catálogo SQL.')
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

  async function exportDocument(format) {
    if (!budget) return
    setBusyAction('export')
    try {
      let response
      try {
        response = await fetch(`${API_BASE_URL}/presupuestos/${budget.id_presupuesto}/${format}`, { credentials: 'include' })
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
      const extension = { excel: 'xlsx', pdf: 'pdf', word: 'docx' }[format]
      link.download = `Presupuesto_${(project?.nombre_obra || 'BIMetrics').replace(/[^a-zA-Z0-9_-]/g, '_')}_${budget.id_presupuesto}.${extension}`
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
            {isOwner && isEditor && <button type="button" onClick={deleteProject} disabled={busyAction === 'delete-project'} aria-label="Eliminar proyecto" title="Eliminar proyecto" className="grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-slate-400 transition hover:border-rose-400/20 hover:text-rose-300 disabled:opacity-50"><Trash2 size={15} aria-hidden="true" /></button>}
          </div>
        </div>
        {projectLoading ? <p className="py-6 text-sm text-slate-500">Cargando proyectos…</p> : projects.length ? (
          <div className="grid gap-4 md:grid-cols-2">
              <GlassSelect label="Obra activa" value={selectedProjectId} onChange={(event) => { setBudgets([]); setBudget(null); setSelectedBudgetId(''); setBudgetLoading(true); setError(''); setSelectedProjectId(event.target.value) }}>
              {projects.map((item) => <option key={item.id_proyecto} value={item.id_proyecto}>{item.nombre_obra} · {item.ciudad || 'Bogotá'}</option>)}
            </GlassSelect>
            <div className="flex items-end gap-3">
              <GlassSelect label="Presupuesto" value={selectedBudgetId} disabled={!budgets.length} onChange={(event) => { setBudget(null); setBudgetLoading(true); setError(''); setSelectedBudgetId(event.target.value) }}>
                {budgets.length ? budgets.map((item, index) => <option key={item.id_presupuesto} value={item.id_presupuesto}>Presupuesto {budgets.length - index} · {formatDate(item.fecha_calculo)} · {currency.format(item.costo_total || 0)}</option>) : <option value="">Sin presupuestos</option>}
              </GlassSelect>
              {canEdit && <button type="button" onClick={createBudget} disabled={busyAction === 'create-budget'} className="mb-0.5 shrink-0 rounded-xl border border-white/10 px-3 py-2.5 text-xs text-slate-300 hover:bg-white/[0.05]">Nuevo</button>}
            </div>
          </div>
        ) : <EmptyState title="Todav?a no hay proyectos" description="Crea una obra para organizar sus presupuestos y actividad BIM." action="Crear proyecto" onAction={() => setProjectDialog(true)} />}
      </GlassCard>

      {project && <GlassCard className="border border-indigo-300/15 bg-indigo-400/[0.035] p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Proyecto seleccionado</p><h2 className="mt-2 text-2xl font-semibold text-white">{project.nombre_obra}</h2><p className="mt-1 text-sm text-slate-400">{budgetLoading ? 'Cargando el presupuesto de esta obra…' : budget ? `Presupuesto #${budget.id_presupuesto} · ${formatDate(budget.fecha_calculo)}` : budgets.length ? 'Selecciona un presupuesto para esta obra.' : 'Esta obra aún no tiene presupuesto.'}</p></div>
          <div className="budget-action-group flex flex-wrap gap-2.5">
            {canEdit && <button type="button" disabled={!budget || Boolean(busyAction)} title={!budget ? 'Crea o selecciona un presupuesto para continuar' : undefined} onClick={() => { setLineDialog(true); setNewCatalogItem(false); setSelectedPartidaCode(''); setSelectedPartidaDetail(null); setSelectedVariationId(''); setPartidaSearch('') }} className="budget-action-primary inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-md shadow-indigo-950/30">Agregar insumo</button>}
            {canEdit && <button type="button" disabled={!budget || Boolean(busyAction)} title={!budget ? 'Crea o selecciona un presupuesto para continuar' : undefined} onClick={() => { setTxtDialog(true); setTxtImport(null); setTxtFile(null); setError('') }} className="budget-action-secondary inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-xs font-semibold">Importar TXT BIM</button>}
            {canEdit && budget && missingAssociatedLabor.length > 0 && <button type="button" disabled={Boolean(busyAction)} onClick={addScaffoldLabor} className="budget-action-labor inline-flex items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-300/[0.06] px-4 py-2.5 text-xs font-semibold text-emerald-100">{busyAction === 'scaffold-labor' ? 'Agregando mano de obra…' : 'Agregar montaje de equipo'}</button>}
            <button type="button" disabled={!budget || Boolean(busyAction)} title={!budget ? 'Crea o selecciona un presupuesto para continuar' : undefined} onClick={recalculate} className="budget-action-secondary inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-xs font-semibold">Recalcular</button>
            {canEdit && <button type="button" disabled={!budget || Boolean(busyAction)} title={!budget ? 'Crea o selecciona un presupuesto para continuar' : undefined} onClick={duplicateBudget} className="budget-action-secondary inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-xs font-semibold">Duplicar</button>}
            {canEdit && budget && <button type="button" disabled={Boolean(busyAction)} onClick={openAiuEditor} className="budget-action-secondary inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-xs font-semibold">AIU</button>}
            <button type="button" disabled={!budget || Boolean(busyAction)} title={!budget ? 'Crea o selecciona un presupuesto para continuar' : undefined} onClick={() => exportDocument('excel')} className="budget-action-secondary inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-xs font-semibold">Excel</button>
            <button type="button" disabled={!budget || Boolean(busyAction)} title={!budget ? 'Crea o selecciona un presupuesto para continuar' : undefined} onClick={() => exportDocument('pdf')} className="budget-action-secondary inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-xs font-semibold">PDF</button>
            <button type="button" disabled={!budget || Boolean(busyAction)} title={!budget ? 'Crea o selecciona un presupuesto para continuar' : undefined} onClick={() => exportDocument('word')} className="budget-action-secondary inline-flex items-center justify-center rounded-xl border px-4 py-2.5 text-xs font-semibold">Word</button>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {budgetCards.map(({ label, value, detail }) => <div key={label} className="min-h-28 rounded-xl border border-white/[0.07] bg-black/20 p-4"><p className="text-[10px] font-semibold uppercase tracking-[.15em] text-slate-500">{label}</p><p className="mt-2 text-lg font-semibold text-white">{value}</p><p className="mt-1 text-xs leading-5 text-slate-400">{detail}</p></div>)}
        </div>
        <div className="mt-4 grid gap-2 border-t border-white/[0.08] pt-4 text-xs text-slate-400 sm:grid-cols-3"><span>Ciudad: <strong className="text-slate-200">{project.ciudad || 'Sin definir'}</strong></span><span>Cliente: <strong className="text-slate-200">{project.cliente || 'Sin asignar'}</strong></span><span>Responsable: <strong className="text-slate-200">{project.responsable || 'Sin asignar'}</strong></span></div>
      </GlassCard>}

      <GlassCard id="presupuesto" className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] p-5 sm:px-6">
          <div><p className="text-sm font-semibold text-white">Detalle del presupuesto</p><p className="mt-1 text-xs text-slate-500">{budget?.nombre_obra || project?.nombre_obra || 'Selecciona un proyecto'} · {lines.length} insumos y recursos</p></div>
          {budgetLoading && <span className="text-xs text-slate-500">Actualizando…</span>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-xs">
            <thead className="bg-white/[0.025] text-[10px] uppercase tracking-[.12em] text-slate-500"><tr><th className="px-5 py-3 font-semibold sm:px-6">Insumo</th><th className="px-3 py-3 font-semibold">Unidad</th><th className="px-3 py-3 text-right font-semibold">Cantidad</th><th className="px-3 py-3 text-right font-semibold">Costo unitario</th><th className="px-3 py-3 text-right font-semibold">Subtotal</th><th className="px-4 py-3" /></tr></thead>
            <tbody className="divide-y divide-white/[0.06]">
              {filteredLines.map((line) => <tr key={line.id_detalle} className="text-slate-300 transition hover:bg-white/[0.02]"><td className="max-w-[260px] truncate px-5 py-3.5 font-medium text-slate-200 sm:px-6">{line.nombre_insumo}</td><td className="px-3 py-3.5 text-slate-500">{line.unidad_medida}</td><td className="px-3 py-3.5 text-right tabular-nums">{quantityFormat.format(Number(line.cantidad))}</td><td className="px-3 py-3.5 text-right tabular-nums">{currency.format(Number(line.costo_unitario_aplicado))}</td><td className="px-3 py-3.5 text-right font-medium tabular-nums text-white">{currency.format(Number(line.subtotal) || Number(line.cantidad) * Number(line.costo_unitario_aplicado))}</td><td className="px-4 py-3.5 text-right">{canEdit && <button type="button" onClick={() => removeLine(line)} aria-label={`Quitar ${line.nombre_insumo}`} className="rounded-md px-2 text-slate-500 hover:bg-rose-400/10 hover:text-rose-300">Quitar</button>}</td></tr>)}
              {(!filteredLines.length) && <tr><td colSpan="6" className="px-6 py-10 text-center text-slate-500">{budgetLoading ? `Cargando presupuesto de ${project?.nombre_obra || 'la obra'}…` : budget ? query ? 'No hay insumos que coincidan con la búsqueda.' : 'Este presupuesto todavía no tiene insumos.' : project ? budgets.length ? 'Selecciona un presupuesto.' : 'Este proyecto no tiene presupuesto. Usa “Nuevo” para comenzar.' : 'Selecciona o crea un proyecto para consultar el presupuesto.'}</td></tr>}
            </tbody>
            {budget && <tfoot><tr className="border-t border-white/10"><td colSpan="4" className="px-5 py-2 text-right text-slate-400 sm:px-6">Costo directo</td><td className="px-3 py-2 text-right tabular-nums text-slate-300">{currency.format(Number(budget.costo_directo) || 0)}</td><td /></tr>{[['administracion', 'Administración'], ['imprevistos', 'Imprevistos'], ['utilidad', 'Utilidad']].map(([key, label]) => <tr key={key}><td colSpan="4" className="px-5 py-1.5 text-right text-slate-500 sm:px-6">{label} ({Number(budget[`porcentaje_${key}`]) || 0}%)</td><td className="px-3 py-1.5 text-right tabular-nums text-slate-400">{currency.format(Number(budget[`valor_${key}`]) || 0)}</td><td /></tr>)}<tr className="border-t border-white/10 bg-white/[0.02]"><td colSpan="4" className="px-5 py-4 text-right font-semibold text-slate-300 sm:px-6">Total del presupuesto</td><td className="px-3 py-4 text-right text-sm font-semibold text-white">{currency.format(Number(budget.costo_total) || 0)}</td><td /></tr></tfoot>}
          </table>
        </div>
      </GlassCard>

      <section className="grid gap-6 xl:grid-cols-2">
        <GlassCard id="catalog" className="overflow-hidden">
          <div className="border-b border-white/[0.08] px-5 py-5 sm:px-6">
            <p className="text-sm font-semibold text-white">Catálogo maestro de insumos</p>
            <p className="mt-1 text-xs text-slate-500">Insumos y precios del catálogo SQL, aplicables a {project?.ciudad || 'la ciudad del proyecto'}.</p>
            <input value={masterPartidaSearch} disabled={masterPartidasLoading} onChange={(event) => setMasterPartidaSearch(event.target.value)} placeholder="Buscar insumo por código o descripción" className="mt-3 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-white outline-none focus:border-indigo-400/40 disabled:opacity-50" />
          </div>
          {masterPartidasLoading && !masterPartidas.length ? (
            <div className="space-y-3 p-5" aria-label="Cargando partidas">
              {[0, 1, 2, 3].map((row) => <div key={row} className="h-10 animate-pulse rounded-lg bg-white/[0.045]" />)}
            </div>
          ) : !filteredMasterPartidas.length ? (
            <div className="p-4">
              <EmptyState
                title={masterPartidas.length || masterPartidaSearch ? 'No hay insumos que coincidan' : 'No hay insumos cargados'}
                description={masterPartidas.length || masterPartidaSearch ? 'Prueba con otro código o descripción.' : 'Importa el catálogo de precios CSV a MySQL para mostrar aquí las partidas.'}
                action={canEdit && budget ? 'Agregar insumo' : undefined}
                onAction={canEdit && budget ? () => { setLineDialog(true); setNewCatalogItem(false); setSelectedPartidaCode(''); setSelectedPartidaDetail(null); setSelectedVariationId('') } : undefined}
              />
            </div>
          ) : (
            <>
              <div className="max-h-[440px] overflow-auto">
                <table className="w-full min-w-[620px] border-separate border-spacing-0 text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-[#11151e] text-[10px] uppercase tracking-[.12em] text-slate-500">
                    <tr>
                      <th scope="col" className="px-4 py-3 font-semibold">Código</th>
                      <th scope="col" className="px-4 py-3 font-semibold">Insumo</th>
                      <th scope="col" className="px-3 py-3 font-semibold">Unidad</th>
                      <th scope="col" className="px-4 py-3 text-right font-semibold">Precio base</th>
                      {canEdit && <th scope="col" className="px-4 py-3" />}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMasterPartidas.map((item) => (
                      <tr key={item.codigo} className="transition-colors hover:bg-white/[0.035]">
                        <td className="border-t border-white/[0.06] px-4 py-3 font-mono text-[11px] text-indigo-200">{item.codigo}</td>
                        <td className="max-w-[280px] border-t border-white/[0.06] px-4 py-3 text-xs text-slate-200">{item.descripcion}</td>
                        <td className="border-t border-white/[0.06] px-3 py-3 text-xs text-slate-400">{item.unidad}</td>
                        <td className="border-t border-white/[0.06] px-4 py-3 text-right text-xs tabular-nums text-slate-200">{currency.format(item.precio_defecto)}</td>
                        {canEdit && <td className="border-t border-white/[0.06] px-4 py-3 text-right"><button type="button" disabled={!budget} onClick={() => { setLineDialog(true); setNewCatalogItem(false); setSelectedPartidaCode(item.codigo); setSelectedPartidaDetail(null); setSelectedVariationId(''); setPartidaSearch(item.descripcion) }} className="rounded-lg border border-white/10 px-2.5 py-1.5 text-[10px] text-indigo-200 hover:bg-white/[0.05] disabled:opacity-40">Agregar</button></td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-white/[0.06] px-5 py-3">
                <span className="text-[10px] text-slate-500">{filteredMasterPartidas.length} insumos mostrados{masterPartidaSearch ? ' en la búsqueda' : ' de la página actual'}</span>
                {masterPartidasHasMore && <button type="button" onClick={loadAllMasterPartidas} disabled={masterPartidasLoading} className="text-xs text-indigo-300 hover:text-indigo-200 disabled:opacity-50">{masterPartidasLoading ? 'Cargando insumos restantes…' : 'Cargar todos los insumos restantes'}</button>}
              </div>
            </>
          )}
        </GlassCard>

        <GlassCard id="activities" className="overflow-hidden">
          <div className="border-b border-white/[0.08] p-5"><div><p className="text-sm font-semibold text-white">Actividad BIM reciente</p><p className="mt-1 text-xs text-slate-500">Importaciones y procesos asociados a tu cuenta</p></div></div>
          {activityError ? <p className="p-6 text-sm text-rose-200">{activityError}</p> : activityLoading ? <p className="p-6 text-sm text-slate-500">Cargando actividad BIM…</p> : <div className="overflow-x-auto"><table className="w-full min-w-[430px] text-left text-xs"><thead className="bg-white/[0.02] text-[10px] uppercase tracking-[.12em] text-slate-500"><tr><th className="px-5 py-3 font-semibold">Archivo / proceso</th><th className="px-3 py-3 font-semibold">Origen</th><th className="px-5 py-3 text-right font-semibold">Estado</th></tr></thead><tbody className="divide-y divide-white/[0.06]">{filteredActivities.map((item) => <tr key={item.id}><td className="max-w-[190px] truncate px-5 py-3.5 text-slate-200" title={item.nombre_archivo}>{item.nombre_archivo || item.tipo_evento || 'Actividad BIM'}</td><td className="px-3 py-3.5 text-slate-500">{item.software_origen || '—'}</td><td className="px-5 py-3.5 text-right"><span className={`rounded-full border px-2 py-1 text-[10px] ${item.estado === 'completado' ? 'border-emerald-300/20 bg-emerald-300/10 text-emerald-300' : item.estado === 'advertencia' ? 'border-amber-300/20 bg-amber-300/10 text-amber-300' : 'border-rose-300/20 bg-rose-300/10 text-rose-300'}`}>{item.estado || 'completado'}</span></td></tr>)}{!filteredActivities.length && <tr><td colSpan="3" className="px-5 py-8 text-center text-slate-500">{activities.length ? 'No hay actividad que coincida con la búsqueda.' : 'Todavía no hay importaciones BIM registradas.'}</td></tr>}</tbody></table></div>}
          <div className="border-t border-white/[0.06] px-5 py-3 text-[10px] text-slate-500">Historial BIM desde el almacén documental NoSQL</div>
        </GlassCard>
      </section>

      {aiuDialog && <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setAiuDialog(false) }}><motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-lg"><GlassCard role="dialog" aria-modal="true" aria-labelledby="aiu-title" className="p-6 sm:p-7"><div className="mb-5 flex items-start justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Costo indirecto y utilidad</p><h2 id="aiu-title" className="mt-1 text-xl font-semibold text-white">{creatingBudget ? 'Nuevo presupuesto' : 'Configurar AIU'}</h2></div><button type="button" onClick={() => setAiuDialog(false)} className="text-xl text-slate-500 hover:text-white" aria-label="Cerrar">×</button></div><p className="mb-4 text-xs leading-5 text-slate-400">Los porcentajes se aplican al costo directo. BIMetrics no fija tarifas; valida los valores para cada contrato y obra.</p><form onSubmit={saveAiu} className="space-y-4">{[['administracion', 'Administración'], ['imprevistos', 'Imprevistos'], ['utilidad', 'Utilidad']].map(([key, label]) => <label key={key} className="block text-sm text-slate-300">{label} (%)<input required type="number" min="0" max="100" step="0.01" value={aiuForm[key]} onChange={(event) => setAiuForm((form) => ({ ...form, [key]: event.target.value }))} className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" /></label>)}<div className="flex justify-end gap-3 pt-2"><button type="button" onClick={() => setAiuDialog(false)} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300">Cancelar</button><button type="submit" disabled={Boolean(busyAction)} className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busyAction ? 'Guardando…' : budget ? 'Guardar AIU' : 'Crear presupuesto'}</button></div></form></GlassCard></motion.div></div>}

      {projectDialog && <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setProjectDialog(false) }}><motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-lg"><GlassCard role="dialog" aria-modal="true" aria-labelledby="new-project-title" className="p-6 sm:p-7"><div className="mb-5 flex items-start justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Nueva obra</p><h2 id="new-project-title" className="mt-1 text-xl font-semibold text-white">Iniciar proyecto</h2></div><button type="button" onClick={() => setProjectDialog(false)} className="text-xl text-slate-500 hover:text-white" aria-label="Cerrar">×</button></div><form onSubmit={createProject} className="space-y-4"><label className="block text-sm text-slate-300">Nombre del proyecto<input required maxLength={150} value={projectForm.nombre_obra} onChange={(event) => setProjectForm({ ...projectForm, nombre_obra: event.target.value })} placeholder="Ej. Casa en Chapinero" className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" /></label><label className="block text-sm text-slate-300">Ciudad<select value={projectForm.ciudad} onChange={(event) => setProjectForm({ ...projectForm, ciudad: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-[#11151e] px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50">{cities.map((city) => <option key={city}>{city}</option>)}</select></label><label className="block text-sm text-slate-300">Cliente (opcional)<input maxLength={150} value={projectForm.cliente} onChange={(event) => setProjectForm({ ...projectForm, cliente: event.target.value })} placeholder="Nombre del cliente" className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" /></label><div className="flex justify-end gap-3 pt-2"><button type="button" onClick={() => setProjectDialog(false)} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300">Cancelar</button><button type="submit" disabled={busyAction === 'project'} className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busyAction === 'project' ? 'Creando…' : 'Crear proyecto'}</button></div></form></GlassCard></motion.div></div>}

      {txtDialog && <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setTxtDialog(false) }}><motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-3xl"><GlassCard role="dialog" aria-modal="true" aria-labelledby="txt-import-title" className="max-h-[90vh] overflow-y-auto p-6"><div className="flex items-start justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Cómputo BIM</p><h2 id="txt-import-title" className="mt-1 text-xl font-semibold text-white">Importar TXT de Revit o Archicad</h2><p className="mt-2 text-xs text-slate-400">Lee tablas delimitadas, encuentra partidas en SQL y utiliza sus precios oficiales. Precios del archivo son ignorados.</p></div><button type="button" onClick={() => setTxtDialog(false)} className="text-xl text-slate-500" aria-label="Cerrar">×</button></div><div className="mt-5 grid gap-3 sm:grid-cols-[1fr_2fr_auto] sm:items-end"><label className="text-xs text-slate-300">Software<select value={txtSoftware} onChange={(event) => setTxtSoftware(event.target.value)} className="glass-select mt-2 w-full rounded-lg border border-white/10 px-3 py-2.5 text-sm text-white"><option value="revit">Autodesk Revit</option><option value="archicad">Graphisoft Archicad</option></select></label><label className="text-xs text-slate-300">Archivo TXT (máximo 5 MB)<input type="file" accept=".txt,text/plain" onChange={(event) => { setTxtFile(event.target.files?.[0] || null); setTxtImport(null) }} className="mt-2 block w-full text-xs text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-500/20 file:px-3 file:py-2 file:text-indigo-100" /></label><button type="button" disabled={!txtFile || txtLoading} onClick={analyzeTxt} className="rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white disabled:opacity-40">{txtLoading ? 'Leyendo…' : 'Leer archivo'}</button></div>{txtImport && <div className="mt-5 space-y-3"><div className="flex flex-wrap justify-between gap-2 text-xs text-slate-300"><span>{txtImport.software} · {txtImport.total_filas} filas reconocidas</span><span className="text-amber-200">{txtImport.aviso_precios}</span></div><div className="max-h-[45vh] space-y-2 overflow-y-auto">{txtImport.filas.map((row) => <div key={row.indice} className="grid gap-2 rounded-xl border border-white/[0.08] bg-black/15 p-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)_auto] sm:items-center"><div className="min-w-0"><p className="truncate text-xs font-medium text-white" title={row.nombre}>{row.nombre}</p><p className="mt-1 text-[10px] text-slate-500">{row.cantidad} {row.unidad || 'unidades'}{row.codigo_origen ? ` · Código: ${row.codigo_origen}` : ''}</p></div><select disabled={!row.sugerencias.length || row.agregado} value={txtChoices[row.indice] || ''} onChange={(event) => setTxtChoices((current) => ({ ...current, [row.indice]: event.target.value }))} className="glass-select min-w-0 rounded-lg border border-white/10 px-2 py-2 text-xs text-white"><option value="">Sin coincidencia en catálogo</option>{row.sugerencias.map((item) => <option key={item.codigo} value={item.codigo}>{item.codigo} · {item.descripcion} · {currency.format(item.precio_defecto)}</option>)}</select><button type="button" disabled={!txtChoices[row.indice] || row.agregado || txtAdding === row.indice} onClick={() => addImportedRow(row)} className="rounded-lg border border-emerald-300/20 px-3 py-2 text-xs text-emerald-200 disabled:opacity-40">{row.agregado ? 'Agregado' : txtAdding === row.indice ? 'Agregando…' : 'Agregar'}</button></div>)}</div><p className="text-[10px] leading-4 text-slate-500">Revisa cada coincidencia y agrega las filas necesarias. La importación no sobrescribe el catálogo ni utiliza precios del TXT.</p></div>}<div className="mt-5 flex justify-end"><button type="button" onClick={() => setTxtDialog(false)} className="rounded-lg border border-white/10 px-4 py-2 text-xs text-slate-300">Cerrar</button></div></GlassCard></motion.div></div>}

      {lineDialog && <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setLineDialog(false) }}><motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-lg"><GlassCard role="dialog" aria-modal="true" aria-labelledby="add-line-title" className="p-6 sm:p-7"><div className="mb-5 flex items-start justify-between"><div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-indigo-300">Nuevo insumo</p><h2 id="add-line-title" className="mt-1 text-xl font-semibold text-white">Agregar insumo al presupuesto</h2></div><button type="button" onClick={() => setLineDialog(false)} className="text-xl text-slate-500 hover:text-white" aria-label="Cerrar">×</button></div><form onSubmit={createLine} className="space-y-4">{!newCatalogItem ? <><label className="block text-sm text-slate-300">Buscar en el catálogo de insumos<input value={partidaSearch} onChange={(event) => { setPartidaSearch(event.target.value); setPartidas([]); setPartidasHasMore(false); setPartidasLoading(event.target.value.trim().length >= 2); setSelectedPartidaCode(""); setSelectedPartidaDetail(null); setSelectedVariationId("") }} autoComplete="off" aria-autocomplete="list" aria-controls="catalog-suggestions" placeholder="Ej. andamio, concreto, tubería…" className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" /></label>{!selectedPartidaCode && partidaSearch.trim().length >= 2 && <div id="catalog-suggestions" className="-mt-2 overflow-hidden rounded-xl border border-indigo-300/20 bg-[#17172d] shadow-xl" role="listbox" aria-label="Sugerencias del catálogo">{partidasLoading ? <p className="px-4 py-3 text-xs text-slate-400">Buscando coincidencias en el catálogo…</p> : visiblePartidaSuggestions.length ? <><p className="border-b border-white/[0.06] px-4 py-2 text-[10px] uppercase tracking-wider text-slate-500">Sugerencias · {partidas.length}{partidasHasMore ? "+" : ""} coincidencias</p><div className="max-h-64 overflow-y-auto">{visiblePartidaSuggestions.map((item) => <button key={item.codigo} type="button" role="option" aria-selected="false" onClick={() => { setSelectedPartidaCode(item.codigo); setSelectedPartidaDetail(null); setSelectedVariationId("") }} className="flex w-full items-start justify-between gap-3 border-b border-white/[0.05] px-4 py-3 text-left last:border-0 hover:bg-indigo-400/10 focus:bg-indigo-400/10 focus:outline-none"><span className="min-w-0"><span className="block text-xs font-semibold text-indigo-200">{item.codigo} · {item.descripcion}</span><span className="mt-1 block text-[11px] text-slate-400">Unidad: {item.unidad}</span>{item.recomendaciones_mano_obra?.length > 0 && <span className="mt-1 block line-clamp-2 text-[10px] text-emerald-200">Mano de obra: {item.recomendaciones_mano_obra.slice(0, 2).map((role) => role.perfil).join(" · ")}{item.recomendaciones_mano_obra.length > 2 ? " · más" : ""}</span>}</span><span className="shrink-0 text-xs font-medium tabular-nums text-white">{currency.format(item.precio_defecto)}</span></button>)}</div>{partidasHasMore && <button type="button" onClick={loadMorePartidas} disabled={partidasLoading} className="w-full border-t border-white/[0.06] px-4 py-2.5 text-left text-xs text-indigo-300 hover:bg-white/[0.04] disabled:opacity-50">{partidasLoading ? "Cargando más coincidencias…" : `Ver más sugerencias (${partidas.length} cargadas)`}</button>}</> : <p className="px-4 py-3 text-xs text-slate-400">No hay insumos que coincidan. Prueba con otro término.</p>}</div>}{!selectedPartidaCode && partidaSearch.trim().length < 2 && <p className="-mt-2 text-[11px] text-slate-500">Escribe al menos 2 letras para ver sugerencias del catálogo.</p>}{selectedPartidaCode && <button type="button" onClick={() => { setSelectedPartidaCode(""); setSelectedPartidaDetail(null); setSelectedVariationId("") }} className="-mt-2 text-xs text-indigo-300 hover:text-indigo-200">Cambiar insumo seleccionado</button>}{selectedPartida && <div className="space-y-3 rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div><p className="text-xs font-semibold text-white">{selectedPartida.codigo} · {selectedPartida.descripcion}</p><p className="mt-1 text-xs text-slate-400">Unidad: {selectedPartida.unidad} · Precio base del catálogo: {currency.format(selectedPartida.precio_defecto)}</p>{selectedPartidaDetail?.variaciones?.length > 0 && <label className="mt-3 block text-xs text-slate-300">Opción de la partida<select value={selectedVariationId} onChange={(event) => setSelectedVariationId(event.target.value)} className="glass-select mt-2 w-full rounded-lg border border-white/10 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-400/50"><option value="">Precio base de la partida</option>{selectedPartidaDetail.variaciones.map((variation) => { const label = [variation.opcion, variation.parametro, variation.valor_probado].filter(Boolean).join(' · ') || variation.tipo; return <option key={variation.id} value={variation.id}>{label} · {variation.precio == null ? 'precio por definir' : currency.format(variation.precio)}</option> })}</select></label>}{selectedPartidaCode && !selectedPartidaDetail && <p className="mt-2 text-[11px] text-slate-500">Cargando opciones de esta partida…</p>}<p className="mt-3 rounded-lg border border-emerald-300/10 bg-emerald-300/[0.04] px-3 py-2 text-xs text-emerald-100">Precio de referencia SQL para {project?.ciudad || 'la ciudad del proyecto'}: {currency.format(selectedVariation?.precio ?? selectedPartida.precio_defecto)}. El precio se aplica desde el catálogo al guardar y no se puede modificar desde el presupuesto.</p><p className="mt-2 text-[11px] text-slate-400">Referencia laboral Colombia 2026: salario mínimo legal mensual de {currency.format(1750905)} y auxilio de transporte de {currency.format(249095)} cuando aplica. Son pisos/beneficios legales, no tarifas de oficial, ayudante ni costo total del empleador. <a className="text-indigo-300 underline" href="https://dapre.presidencia.gov.co/normativa/normativa/DECRETO%20No.%200159%20DEL%2019%20DE%20FEBRERO%20DE%202026.pdf" target="_blank" rel="noreferrer">Decreto 0159 de 2026</a> · <a className="text-indigo-300 underline" href="https://www.presidencia.gov.co/Documents/251230-Decreto-1470-MinTrabajo.pdf" target="_blank" rel="noreferrer">Decreto 1470 de 2025</a></p></div>{laborRecommendations.map((suggestion) => <div key={suggestion.title} className="border-t border-white/[0.08] pt-3"><p className="text-xs font-semibold text-indigo-200">Mano de obra sugerida · {suggestion.title}</p><div className="mt-2 space-y-2">{suggestion.roles.map((role) => { const available = suggestion.availableRoles.includes(role); const evidence = suggestion.detalles?.find((item) => item.perfil === role); return <div key={role} className="rounded-lg border border-white/[0.06] bg-black/15 p-2"><div className="flex flex-wrap items-center justify-between gap-2"><span className="text-[11px] text-slate-200">{role}</span><span className={`rounded-full border px-2 py-1 text-[10px] ${available ? 'border-emerald-300/20 bg-emerald-300/[0.06] text-emerald-200' : evidence?.tipo === 'condicional' ? 'border-amber-300/20 bg-amber-300/[0.06] text-amber-200' : 'border-indigo-300/15 bg-indigo-300/[0.06] text-slate-300'}`}>{evidence?.tipo === 'condicional' ? 'condicional · verificar alcance' : available ? 'referencia 2026' : 'por cotizar'}</span>{evidence && <a href={evidence.fuente_url} target="_blank" rel="noreferrer" className="text-[10px] text-cyan-300 underline">Fuente</a>}</div>{evidence && <p className="mt-1 text-[10px] leading-4 text-slate-400">{evidence.fundamento}</p>}</div> })}</div><p className="mt-2 text-[10px] text-slate-500">Sugerencia por palabras clave de la actividad, no constituye análisis de rendimiento ni cálculo de cuadrilla. Define cantidades y tarifas según planos, alcance y cotización.</p></div>)}{laborRecommendations.length > 0 && <div className="border-t border-white/[0.08] pt-3"><p className="text-xs font-semibold text-emerald-200">Cotizaciones referenciales de mano de obra</p>{laborCatalogLoading ? <p className="mt-2 text-[11px] text-slate-400">Revisando insumos con precio para {project?.ciudad || "esta ciudad"}…</p> : suggestedLaborItems.length ? <div className="mt-2 space-y-2">{suggestedLaborItems.map((item) => <div key={item.id_insumo} className="flex items-center gap-2 rounded-lg border border-white/[0.07] bg-black/20 p-2"><input type="checkbox" checked={laborSelection[item.id_insumo] ?? !item.condicional} onChange={(event) => setLaborSelection((current) => ({ ...current, [item.id_insumo]: event.target.checked }))} aria-label={`Incluir ${item.nombre_insumo}`} /><div className="min-w-0 flex-1"><p className="truncate text-[11px] text-slate-200">{item.nombre_insumo}</p><p className="text-[10px] text-slate-400">{item.unidad_medida} · referencia aplicada: {currency.format(item.cotizacion_referencial ?? item.costo_unitario)}</p>{item.cotizacion_minima != null && item.cotizacion_maxima != null && <p className="text-[10px] text-slate-500">Rango consultado: {currency.format(item.cotizacion_minima)}–{currency.format(item.cotizacion_maxima)} por {item.unidad_medida}</p>}{item.metodologia_cotizacion && <p className="mt-1 text-[10px] leading-4 text-slate-500">{item.metodologia_cotizacion}</p>}{item.url_cotizacion && <a className="text-[10px] text-cyan-300 underline" href={item.url_cotizacion} target="_blank" rel="noreferrer">{item.fuente_cotizacion || 'Consultar fuente'}</a>}</div><input type="number" required={laborSelection[item.id_insumo] ?? !item.condicional} min="0.001" step="any" value={laborQuantities[item.id_insumo] ?? '1'} onChange={(event) => setLaborQuantities((current) => ({ ...current, [item.id_insumo]: event.target.value }))} aria-label={`Cantidad de ${item.nombre_insumo}`} className="w-20 rounded-md border border-white/10 bg-[#11151e] px-2 py-1.5 text-xs text-white" /></div>)}</div> : <p className="mt-2 text-[11px] text-amber-200">No hay cotizaciones cargadas para {project?.ciudad || 'esta ciudad'}. Ejecuta el cargador de cotizaciones referenciales para poblar el catálogo SQL.</p>}<p className="mt-2 text-[10px] text-slate-500">Los perfiles no condicionales quedan seleccionados inicialmente; los condicionales requieren confirmación del alcance. Las cantidades son 1 jornal de referencia y deben ajustarse al rendimiento real. Las tarifas no son ofertas vinculantes y deben validarse para cada obra.</p></div>}{!laborRecommendations.length && <p className="text-[11px] text-slate-400">No hay una regla específica para esta descripción. Revisa el alcance y define el perfil de mano de obra según la actividad.</p>}</div>}</> : <><label className="block text-sm text-slate-300">Nombre del insumo<input required maxLength={150} value={newItemForm.nombre_insumo} onChange={(event) => setNewItemForm({ ...newItemForm, nombre_insumo: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none" /></label><div className="grid gap-4 sm:grid-cols-2"><label className="block text-sm text-slate-300">Unidad<input required maxLength={30} placeholder="Ej. kg, m³" value={newItemForm.unidad_medida} onChange={(event) => setNewItemForm({ ...newItemForm, unidad_medida: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none" /></label><label className="block text-sm text-slate-300">Precio para {project?.ciudad}<input required type="number" min="0.01" step="0.01" value={newItemForm.costo_unitario} onChange={(event) => setNewItemForm({ ...newItemForm, costo_unitario: event.target.value })} className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none" /></label></div></>}
              <label className="block text-sm text-slate-300">Cantidad<input required type="number" min="0.001" step="any" value={lineForm.cantidad} onChange={(event) => setLineForm({ ...lineForm, cantidad: event.target.value })} placeholder="Ej. 2.5" className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400/50" /></label>
              {canEdit && isAdmin && <button type="button" onClick={() => { setNewCatalogItem(!newCatalogItem); setLineForm({ ...lineForm, id_insumo: '' }) }} className="text-xs font-medium text-indigo-300 hover:text-indigo-200">{newCatalogItem ? 'Elegir del catálogo' : 'Crear insumo con precio para esta ciudad'}</button>}
              <div className="flex justify-end gap-3 border-t border-white/[0.08] pt-4"><button type="button" onClick={() => setLineDialog(false)} className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300">Cancelar</button><button type="submit" disabled={busyAction === 'line' || laborCatalogLoading || (!newCatalogItem && (!selectedPartidaCode || !selectedPartidaDetail))} className="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busyAction === 'line' ? 'Guardando…' : 'Agregar insumo'}</button></div>
            </form></GlassCard></motion.div></div>}
    </div>
  )
}

export default ProjectBudgetWorkspace
