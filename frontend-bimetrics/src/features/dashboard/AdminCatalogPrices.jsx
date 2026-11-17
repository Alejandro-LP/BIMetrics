import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import GlassCard from '../../components/ui/GlassCard.jsx'
import { apiRequest } from '../../services/api.js'
import AdminDialog from './AdminDialog.jsx'
import { cities } from './projectCities.js'

const pageSize = 25
const currency = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 2 })
const field = 'glass-control rounded-xl px-3 py-2 text-sm text-white'
const button = 'rounded-xl border border-white/15 px-3 py-2 text-sm font-medium text-indigo-100 hover:bg-indigo-400/10 disabled:opacity-50'
const startQuery = { term: '', page: 0, attempt: 0, city: '' }

function PriceEditor({ item, city, onClose, onSaved }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    const price = new FormData(event.currentTarget).get('price')
    setBusy(true)
    setError('')
    try {
      const endpoint = city ? `/insumos/${item.id_insumo}/precio-ciudad` : `/partidas/${encodeURIComponent(item.codigo)}/precio`
      const payload = city ? { ciudad: city, costo_unitario: price } : { precio_defecto: price }
      const saved = await apiRequest(endpoint, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      onSaved(saved)
      toast.success('Precio del catálogo actualizado')
    } catch (failure) {
      setError(failure.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog title={city ? `Editar precio en ${city}` : 'Editar precio base'} busy={busy} error={error} onClose={onClose}>
      <p className="mt-3 text-sm leading-6 text-slate-300">{city ? item.nombre_insumo : `${item.codigo} · ${item.descripcion}`}</p>
      <form onSubmit={submit} className="mt-4 space-y-4">
        <label className="block space-y-1 text-sm">
          {city ? 'Precio en COP' : 'Precio base en COP'} por {city ? item.unidad_medida : item.unidad}
          <input name="price" type="number" inputMode="decimal" min="0" max="999999999999.99" step="0.01" required defaultValue={city ? item.costo_unitario : item.precio_defecto} className={`${field} block w-full`} />
        </label>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} disabled={busy} className={button}>Cancelar</button>
          <button type="submit" disabled={busy} className={`${button} bg-indigo-600 text-white`}>{busy ? 'Guardando…' : 'Guardar precio'}</button>
        </div>
      </form>
    </AdminDialog>
  )
}

function AdminCatalogPrices() {
  const [text, setText] = useState('')
  const [city, setCity] = useState('')
  const [query, setQuery] = useState(startQuery)
  const [result, setResult] = useState(null)
  const [editing, setEditing] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({ limit: pageSize + 1, offset: query.page * pageSize })
    if (query.term) params.set('q', query.term)
    const endpoint = query.city ? '/insumos' : query.term ? '/partidas/buscar' : '/partidas'
    if (query.city) params.set('ciudad', query.city)
    apiRequest(`${endpoint}?${params}`, { signal: controller.signal })
      .then((data) => {
        const offset = query.page * pageSize
        const items = query.city ? data.slice(offset, offset + pageSize + 1) : data
        if (!controller.signal.aborted) setResult({ query, items })
      })
      .catch((failure) => { if (!controller.signal.aborted) setResult({ query, error: failure.message }) })
    return () => controller.abort()
  }, [query])

  const loading = result?.query !== query
  const items = loading ? null : result.items
  const error = !loading && result.error

  function search(event) {
    event.preventDefault()
    setQuery({ ...startQuery, term: text.trim(), city: city.trim() })
  }

  function saved(item) {
    setResult((previous) => ({
      ...previous,
      items: previous.items.map((row) => (query.city ? row.id_insumo === item.id_insumo : row.codigo === item.codigo) ? item : row),
    }))
    setEditing(null)
  }

  return (
    <GlassCard className="space-y-5 p-5 sm:p-6">
      <div>
        <h2 className="text-xl font-semibold text-white">Precios del catálogo</h2>
        <p className="mt-1 text-sm text-slate-400">El precio por ciudad se aplica cuando existe. Deja la ciudad vacía para consultar el catálogo maestro.</p>
      </div>
      <form onSubmit={search} className="flex flex-wrap items-end gap-2">
        <label className="min-w-52 flex-1 space-y-1 text-sm text-slate-300">
          Buscar partida o insumo
          <input type="search" maxLength={150} placeholder="Código o descripción" value={text} onChange={(event) => setText(event.target.value)} className={`${field} block w-full`} />
        </label>
        <label className="min-w-40 flex-1 space-y-1 text-sm text-slate-300 sm:max-w-56">
          Ciudad (opcional)
          <input type="text" list="ciudades-catalogo" maxLength={100} placeholder="Ej. Bogotá" value={city} onChange={(event) => setCity(event.target.value)} className={`${field} block w-full`} />
          <datalist id="ciudades-catalogo">{cities.map((name) => <option key={name} value={name} />)}</datalist>
        </label>
        <button type="submit" className={button}>Buscar</button>
      </form>
      {loading && <p role="status" className="text-sm text-slate-400">Cargando partidas…</p>}
      {error && <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-rose-200">
        {error}<button className={button} type="button" onClick={() => setQuery((current) => ({ ...current, attempt: current.attempt + 1 }))}>Reintentar</button>
      </div>}
      {items && <p className="text-xs font-semibold uppercase tracking-wide text-indigo-200">{query.city ? `Precios para ${query.city}` : 'Precios base · Catálogo maestro'}</p>}
      {items && (items.length ? <ul className="divide-y divide-white/10">
        {items.slice(0, pageSize).map((item) => (
          <li key={item.codigo ?? item.id_insumo} className="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center sm:gap-4">
            <div className="min-w-0">
              <p className="break-words text-sm font-medium text-white">{item.descripcion ?? item.nombre_insumo}</p>
              <p className="mt-0.5 break-words text-xs text-slate-400">{query.city ? `${item.unidad_medida} · ${item.origen_precio === 'precio_ciudad' ? 'Precio por ciudad' : 'Referencia general'}` : `${item.codigo} · ${item.unidad}`}</p>
            </div>
            <span className="text-sm font-medium tabular-nums text-cyan-200">{currency.format(item.precio_defecto ?? item.costo_unitario)}</span>
            <button type="button" className={button} aria-label={`Editar precio de ${item.codigo ?? item.nombre_insumo}`} onClick={() => setEditing(item)}>Editar precio</button>
          </li>
        ))}
      </ul> : <p className="text-sm text-slate-400">No se encontraron resultados para esta búsqueda.</p>)}
      {(query.page > 0 || items?.length > pageSize) && (
        <nav aria-label="Paginación de precios" className="flex flex-wrap items-center justify-end gap-3">
          <button className={button} type="button" disabled={loading || query.page === 0} onClick={() => setQuery((current) => ({ ...current, page: current.page - 1 }))}>Anterior</button>
          <span className="text-sm text-slate-300">Página {query.page + 1}</span>
          <button className={button} type="button" disabled={loading || !items || items.length <= pageSize} onClick={() => setQuery((current) => ({ ...current, page: current.page + 1 }))}>Siguiente</button>
        </nav>
      )}
      {editing && <PriceEditor item={editing} city={query.city} onClose={() => setEditing(null)} onSaved={saved} />}
    </GlassCard>
  )
}

export default AdminCatalogPrices
