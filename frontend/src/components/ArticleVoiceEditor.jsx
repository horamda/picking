import { useEffect, useState } from 'react'
import api from '../api/axiosClient'
import { speak, stopSpeaking } from '../voice/speech'

export default function ArticleVoiceEditor({ article, onClose, onSaved }) {
    const [value, setValue] = useState(article.descripcion_voz || '')
    const [source, setSource] = useState(null)
    const [error, setError] = useState('')
    const [saving, setSaving] = useState(false)
    useEffect(() => {
        let active = true
        api.get(`/articles/${article.id}`).then(r => { if (active) setSource(r.data.datos_origen) }).catch(() => { if (active) setError('No se pudieron cargar los datos originales.') })
        return () => { active = false; stopSpeaking() }
    }, [article.id])
    async function save(event) {
        event.preventDefault(); setSaving(true); setError('')
        try { await api.put(`/articles/${article.id}/voice`, { descripcion_voz: value, previous: article.descripcion_voz || '' }); onSaved() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar.') }
        finally { setSaving(false) }
    }
    return <section className="mb-6 rounded-2xl border bg-white p-4" aria-label="Editar descripción para voz">
        <h2 className="text-lg font-semibold">{article.sku} · {article.descripcion}</h2>
        <form onSubmit={save} className="mt-4 space-y-3">
            <label className="block">Descripción para voz<input autoFocus maxLength={255} value={value} onChange={e => setValue(e.target.value)} className="mt-2 block min-h-12 w-full rounded-xl border p-3" placeholder="Ej.: Brahma de un litro retornable, pack de doce" /></label>
            <p className="text-sm text-slate-500">Opcional. Si está vacía, se lee la descripción original. Se conserva al importar otro CSV.</p>
            {error && <p role="alert" className="text-red-700">{error}</p>}
            <div className="flex flex-wrap gap-3"><button disabled={saving} className="min-h-12 rounded-xl bg-brand-500 px-4 text-white">{saving ? 'Guardando…' : 'Guardar'}</button><button type="button" className="min-h-12 rounded-xl border px-4" onClick={() => speak(value.trim() || article.descripcion, setError)}>Escuchar</button><button disabled={saving} type="button" className="min-h-12 px-4" onClick={onClose}>Cerrar</button></div>
        </form>
        <details className="mt-4"><summary className="min-h-12 cursor-pointer py-3">Datos originales del CSV</summary>{source === null ? <p>Cargando…</p> : <dl className="grid gap-2 sm:grid-cols-2">{Object.entries(source).map(([key, item]) => <div className="min-w-0 rounded-lg bg-slate-50 p-2" key={key}><dt className="text-xs text-slate-500">{key}</dt><dd className="break-words">{item || '—'}</dd></div>)}</dl>}</details>
    </section>
}
