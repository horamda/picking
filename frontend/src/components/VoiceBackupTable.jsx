import { useEffect, useState } from 'react'
import api from '../api/axiosClient'
import { voiceBackupCsv, voiceBackupJson } from '../utils/voiceBackup'

export default function VoiceBackupTable({ onClose }) {
    const [backup, setBackup] = useState(null), [error, setError] = useState('')
    const [busy, setBusy] = useState(false), [query, setQuery] = useState('')
    async function refresh(signal) {
        setBusy(true); setError('')
        try { const r = await api.get('/articles/voice-backup', { signal }); if (!signal?.aborted) setBackup(r.data) }
        catch { if (!signal?.aborted) setError('No se pudo obtener el respaldo. Reintentá.') }
        finally { if (!signal?.aborted) setBusy(false) }
    }
    useEffect(() => { const controller = new AbortController(); refresh(controller.signal); return () => controller.abort() }, [])
    function download(format) {
        if (!backup) return
        const text = format === 'json' ? voiceBackupJson(backup) : voiceBackupCsv(backup.items)
        const url = URL.createObjectURL(new Blob([text], { type: format === 'json' ? 'application/json;charset=utf-8' : 'text/csv;charset=utf-8' }))
        const link = document.createElement('a')
        link.href = url; link.download = `respaldo-voz-${backup.exported_at.replace(/[:.]/g, '-')}.${format}`
        document.body.appendChild(link); link.click(); link.remove()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
    }
    const rows = backup?.items.filter(i => `${i.sku} ${i.descripcion_voz}`.toLowerCase().includes(query.toLowerCase())) || []
    return <section className="mb-6 rounded-2xl border bg-white p-4 sm:p-6" aria-label="Respaldo de descripciones de voz">
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-semibold">Respaldo de descripciones de voz</h2><button className="min-h-12 rounded-xl border px-4" onClick={onClose}>Cerrar respaldo</button></div>
        <p className="mt-2 text-sm text-slate-600">Incluye todos los artículos con voz personalizada, activos e inactivos. Descargá el JSON para conservar una copia exacta fuera del sistema; el CSV sirve para consultar la tabla en Excel.</p>
        <div className="my-4 flex flex-wrap gap-3"><button disabled={busy} className="min-h-12 rounded-xl border px-4 disabled:opacity-50" onClick={() => refresh()}>Actualizar tabla</button><button disabled={!backup || busy || !!error} className="min-h-12 rounded-xl bg-brand-500 px-4 text-white disabled:opacity-50" onClick={() => download('json')}>Descargar respaldo JSON</button><button disabled={!backup || busy || !!error} className="min-h-12 rounded-xl border px-4 disabled:opacity-50" onClick={() => download('csv')}>Exportar tabla CSV</button></div>
        {busy && <p role="status">Cargando descripciones…</p>}{error && <p role="alert" className="text-red-700">{error}</p>}
        {backup && <><p className="mb-3 text-sm text-slate-500">{backup.total} descripciones · Consulta del {new Date(backup.exported_at).toLocaleString('es-AR')}. Las descargas incluyen todas las filas, aunque filtres la tabla.</p><input aria-label="Buscar en respaldo de voz" placeholder="Buscar código o descripción" value={query} onChange={e => setQuery(e.target.value)} className="mb-3 min-h-12 w-full rounded-xl border p-3 sm:max-w-md" /><div className="max-h-96 overflow-auto"><table className="w-full text-left text-sm"><thead className="sticky top-0 bg-slate-100"><tr><th className="p-3">Código</th><th className="p-3">Descripción para voz</th></tr></thead><tbody>{rows.map(i => <tr className="border-t" key={i.sku}><td className="p-3 align-top font-medium">{i.sku}</td><td className="whitespace-pre-wrap break-words p-3">{i.descripcion_voz}</td></tr>)}</tbody></table></div>{!rows.length && <p className="py-4 text-slate-500">{backup.total ? 'No hay coincidencias para esta búsqueda.' : 'Todavía no hay descripciones de voz personalizadas guardadas.'}</p>}</>}
    </section>
}
