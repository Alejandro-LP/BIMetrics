import { useEffect, useRef } from 'react'

function AdminDialog({ title, busy, error, onClose, children }) {
  const dialog = useRef(null)

  useEffect(() => {
    const element = dialog.current
    element.showModal()
    return () => element.close()
  }, [])

  return (
    <dialog
      ref={dialog}
      aria-labelledby="admin-dialog-title"
      onCancel={(event) => {
        event.preventDefault()
        if (!busy) onClose()
      }}
      className="glass-surface m-auto max-h-[90vh] w-[min(32rem,92vw)] overflow-y-auto rounded-2xl p-6 text-slate-200 backdrop:bg-black/70 backdrop:backdrop-blur-sm"
    >
      <h2 id="admin-dialog-title" className="text-xl font-semibold text-white">{title}</h2>
      {error && <p role="alert" className="mt-3 rounded-lg border border-rose-400/30 p-3 text-sm text-rose-200">{error}</p>}
      {children}
    </dialog>
  )
}

export default AdminDialog
