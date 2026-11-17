import { useEffect, useRef, useState } from 'react'
import { apiRequest } from '../../services/api.js'

const modes = { ifc: 'Modelo IFC', tabla: 'Pegar tabla', txt: 'Archivo TXT' }
const measures = {
  area_neta: 'Área neta (m²)',
  area_bruta: 'Área bruta (m²)',
  volumen_neto: 'Volumen neto (m³)',
  volumen_bruto: 'Volumen bruto (m³)',
  longitud: 'Longitud (m)',
}
const input = 'glass-control mt-1 block w-full rounded-xl px-3 py-2 text-sm text-white'
const button = 'rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-50'
const quantity = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 6 })
const currency = new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 2 })

function BimImportDialog({ budgetId, onClose, onAdded }) {
  const dialog = useRef(null)
  const [mode, setMode] = useState('ifc')
  const [software, setSoftware] = useState('archicad')
  const [measure, setMeasure] = useState('area_neta')
  const [decimal, setDecimal] = useState(',')
  const [file, setFile] = useState(null)
  const [text, setText] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [choices, setChoices] = useState({})
  const [added, setAdded] = useState({})
  const [loading, setLoading] = useState(false)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')
  const busy = loading || adding

  useEffect(() => {
    const element = dialog.current
    element.showModal()
    return () => element.close()
  }, [])

  function invalidatePreview() {
    setAnalysis(null)
    setError('')
  }

  async function analyze(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      let body
      if (mode === 'tabla') {
        body = JSON.stringify({ texto: text, software, separador_decimal: decimal })
      } else {
        body = new FormData()
        body.set('archivo', file)
        body.set(mode === 'ifc' ? 'medida' : 'software', mode === 'ifc' ? measure : software)
      }
      const result = await apiRequest(`/presupuestos/${budgetId}/importar-${mode}/analizar`, { method: 'POST', body })
      setAnalysis(result)
      setAdded({})
      setChoices({})
    } catch (failure) {
      setError(failure.message)
    } finally {
      setLoading(false)
    }
  }

  async function add(row) {
    setAdding(true)
    setError('')
    try {
      const updated = await apiRequest(`/presupuestos/${budgetId}/partidas`, {
        method: 'POST',
        body: JSON.stringify({ codigo: choices[row.indice], cantidad: row.cantidad }),
      })
      setAdded((current) => ({ ...current, [row.indice]: true }))
      onAdded(updated, row.nombre)
    } catch (failure) {
      setError(failure.message)
    } finally {
      setAdding(false)
    }
  }

  return (
    <dialog ref={dialog} aria-labelledby="bim-import-title" onCancel={(event) => { event.preventDefault(); if (!busy) onClose() }} className="glass-surface m-auto max-h-[90vh] w-[min(56rem,94vw)] overflow-y-auto rounded-2xl p-5 text-slate-200 backdrop:bg-black/70 backdrop:backdrop-blur-sm sm:p-6">
      <div className="flex justify-between gap-4">
        <h2 id="bim-import-title" className="text-xl font-semibold text-white">Importar cantidades BIM</h2>
        <button type="button" aria-label="Cerrar" disabled={busy} onClick={onClose} className={button}>Cerrar</button>
      </div>
      <div aria-label="Origen de cantidades" role="group" className="my-4 flex flex-wrap gap-2 border-b border-white/10 pb-4">
        {Object.entries(modes).map(([value, label]) => (
          <button key={value} type="button" disabled={busy} aria-pressed={mode === value} className={`${button} aria-pressed:bg-indigo-500/30`} onClick={() => {
            if (mode === value) return
            setMode(value)
            setFile(null)
            invalidatePreview()
          }}>{label}</button>
        ))}
      </div>
      {error && <p role="alert" className="mb-4 rounded-xl border border-rose-400/30 p-3 text-sm text-rose-200">{error}</p>}
      <form onSubmit={analyze} className="space-y-3">
        {mode === 'ifc' ? <>
          <p className="text-sm text-slate-300">En Archicad, activa <strong>Cantidades base IFC</strong> en el traductor de exportación y guarda el modelo como <strong>.ifc</strong>.</p>
          <label className="block text-sm">Medida del modelo<select className={input} value={measure} disabled={busy} onChange={(event) => { setMeasure(event.target.value); invalidatePreview() }}>
            {Object.entries(measures).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
        </> : (
          <label className="block text-sm" htmlFor="bim-software">Software
            <select id="bim-software" className={input} value={software} disabled={busy} onChange={(event) => { setSoftware(event.target.value); invalidatePreview() }}>
              <option value="archicad">Graphisoft Archicad</option><option value="revit">Autodesk Revit</option>
            </select>
          </label>
        )}
        {mode === 'tabla' ? <>
          <p className="text-sm text-slate-300">Copia el listado con sus encabezados. La tabla debe identificar el elemento y la cantidad o medida de cada fila.</p>
          <label htmlFor="bim-paste-decimal" className="block text-sm">Separador decimal<select id="bim-paste-decimal" className={input} disabled={busy} value={decimal} onChange={(event) => { setDecimal(event.target.value); invalidatePreview() }}>
            <option value=",">Coma (1,25)</option><option value=".">Punto (1.25)</option>
          </select></label>
          <label className="block text-sm">Tabla copiada<textarea className={`${input} font-mono`} rows={5} required disabled={busy} value={text} placeholder={'Nombre\tCantidad\tUnidad\nMuro de concreto\t12,5\tm²'} onChange={(event) => { setText(event.target.value); invalidatePreview() }} /></label>
        </> : (
          <label className="block text-sm">{mode === 'ifc' ? 'Archivo IFC (hasta 25 MB)' : 'Archivo TXT (hasta 5 MB)'}
            <input key={mode} required disabled={busy} className={input} type="file" accept={mode === 'ifc' ? '.ifc' : '.txt,text/plain'} onChange={(event) => { setFile(event.target.files?.[0] ?? null); invalidatePreview() }} />
          </label>
        )}
        <button type="submit" disabled={busy || Boolean(analysis) || (mode === 'tabla' ? !text.trim() : !file)} className={`${button} bg-indigo-600 text-white`}>{loading ? 'Analizando…' : 'Analizar cantidades'}</button>
      </form>
      {analysis && (
        <div className="mt-5 space-y-3 border-t border-white/10 pt-4">
          <p role="status" className="font-medium text-white">{analysis.total_filas} filas reconocidas · {analysis.software}</p>
          {analysis.elementos_omitidos > 0 && <p className="text-sm text-amber-200">{analysis.elementos_omitidos} elemento(s) sin la medida seleccionada o sin unidad válida.</p>}
          <p className="text-sm text-slate-300">{analysis.aviso_precios}</p>
          <ul className="divide-y divide-white/10">
            {analysis.filas.map((row) => (
              <li key={row.indice} className="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] sm:items-center">
                <div className="min-w-0">
                  <p className="break-words font-medium text-white">{row.nombre}</p>
                  <p className="text-sm text-cyan-200">{quantity.format(row.cantidad)} {row.unidad}</p>
                  {row.origen && <p className="text-xs text-slate-400">{row.origen}</p>}
                </div>
                {row.sugerencias.length ? (
                  <select aria-label={`Partida de catálogo para ${row.nombre}`} disabled={busy || added[row.indice]} className={input} value={choices[row.indice] || ''} onChange={(event) => setChoices((current) => ({ ...current, [row.indice]: event.target.value }))}>
                    <option value="">Selecciona una partida</option>
                    {row.sugerencias.map((item) => <option key={item.codigo} value={item.codigo}>{item.codigo} · {item.descripcion} · {currency.format(item.precio_defecto)}</option>)}
                  </select>
                ) : <p className="text-sm text-slate-400">Sin coincidencia. Puedes cargar la cantidad desde Agregar insumo.</p>}
                <button type="button" disabled={busy || !choices[row.indice] || added[row.indice]} onClick={() => add(row)} className={button}>{added[row.indice] ? 'Agregado' : 'Agregar'}</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </dialog>
  )
}

export default BimImportDialog
