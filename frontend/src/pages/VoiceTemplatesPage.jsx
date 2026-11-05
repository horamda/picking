import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { speak, stopSpeaking } from '../voice/speech'

const samples = { position: '3', total: '12', quantity: '2 bultos y 4 unidades', product: 'Brahma de un litro',
    pallets: '4 pallets completos', court: '2' }
const preview = text => text.replace(/\{(\w+)\}/g, (_, key) => samples[key] ?? key)

function TemplateCard({ item, onSaved }) {
    const [text, setText] = useState(item.text), [enabled, setEnabled] = useState(item.enabled)
    const [busy, setBusy] = useState(false), [error, setError] = useState('')
    async function save() {
        setBusy(true); setError('')
        try { await api.put(`/voice-templates/${item.key}`, { text, enabled }); await onSaved() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar la frase.') }
        finally { setBusy(false) }
    }
    async function reset() {
        if (!window.confirm('¿Restaurar el texto original de esta frase?')) return
        setBusy(true); setError('')
        try { await api.delete(`/voice-templates/${item.key}`); await onSaved() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo restaurar la frase.') }
        finally { setBusy(false) }
    }
    return <article className="rounded-2xl border bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase text-brand-600">{item.process}</p><h2 className="text-lg font-bold">{item.name}</h2><p className="text-xs text-slate-500">{item.key} · {item.customized ? 'Personalizada' : 'Texto original'}</p></div>
            <label className="flex min-h-12 items-center gap-2"><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} /> Activa</label></div>
        <label className="mt-4 block text-sm font-medium">Texto que dirá la aplicación<textarea className="mt-1 min-h-28 w-full rounded-xl border p-3 text-base" value={text} onChange={e => setText(e.target.value)} /></label>
        <p className="mt-2 text-xs text-slate-500">Variables obligatorias: {item.variables.length ? item.variables.map(v => `{${v}}`).join(', ') : 'ninguna'}</p>
        <div className="mt-4 flex flex-wrap gap-2"><button disabled={busy} className="min-h-12 rounded-xl bg-brand-500 px-4 font-semibold text-white disabled:opacity-50" onClick={save}>Guardar</button>
            <button disabled={busy} className="min-h-12 rounded-xl border px-4" onClick={() => { stopSpeaking(); speak(preview(text), setError) }}>Escuchar prueba</button>
            <button disabled={busy || !item.customized} className="min-h-12 rounded-xl border px-4 disabled:opacity-40" onClick={reset}>Restaurar original</button></div>
        {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    </article>
}

export default function VoiceTemplatesPage() {
    const [items, setItems] = useState([]), [settings, setSettings] = useState([]), [error, setError] = useState(''), [loading, setLoading] = useState(true)
    async function load() {
        setLoading(true); setError('')
        try { const { data } = await api.get('/voice-templates'); setItems(data.templates || []); setSettings(data.settings || []) }
        catch { setError('No se pudieron cargar las frases de voz.') }
        finally { setLoading(false) }
    }
    async function toggleSetting(item) {
        setError('')
        try { await api.put(`/voice-templates/settings/${item.key}`, { enabled: !item.enabled }); await load() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar la configuración.') }
    }
    useEffect(() => { load(); return stopSpeaking }, [])
    return <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-8"><header><Link className="text-brand-600 underline" to="/administracion">Volver a administración</Link><h1 className="mt-3 text-2xl font-bold">Frases de voz</h1><p className="mt-2 text-slate-600">Editá lo que dicen la web y Android. Las variables entre llaves se completan automáticamente y no deben eliminarse.</p></header>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-700">{error}</p>}{loading ? <p>Cargando…</p> : <><section className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Lectura de frescura</h2><p className="mt-1 text-sm text-slate-600">La fecha siempre se muestra y se registra. Elegí en qué procesos también se pronuncia.</p><div className="mt-4 grid gap-3 sm:grid-cols-2">{settings.map(item => <label key={item.key} className="flex min-h-14 items-center justify-between rounded-xl border p-3"><span className="font-medium">{item.name}</span><input type="checkbox" checked={item.enabled} onChange={() => toggleSetting(item)} /></label>)}</div></section><div className="mt-4 grid gap-4">{items.map(item => <TemplateCard key={`${item.key}:${item.updated_at || 'default'}`} item={item} onSaved={load} />)}</div></>}
    </div>
}
