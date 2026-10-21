export default function EmptyState({ title = 'No hay datos aún', description, action, onAction }) {
  return <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.015] px-6 py-10 text-center">
    <p className="text-sm font-medium text-slate-200">{title}</p>
    {description && <p className="mx-auto mt-2 max-w-md text-xs leading-5 text-slate-500">{description}</p>}
    {action && onAction && <button type="button" onClick={onAction} className="mt-5 rounded-xl border border-white/10 bg-white/[0.04] px-6 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/[0.08]">{action}</button>}
  </div>
}
