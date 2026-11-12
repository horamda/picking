import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { speak, stopSpeaking } from '../voice/speech'

const samples = { position: '3', total: '12', quantity: '2 bultos y 4 unidades', product: 'Brahma de un litro',
    pallets: '4 pallets completos', court: '2', date: '15/11/2026', group: 'A', reparto: '1042',
    pallet: 'P-03', truck: 'AC 123 BC', summary: 'Carga total: 12 pallets.', loads: '3', courts: '5',
    bultos: '240', unidades: '18', hl: '36,5' }
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
    const [items, setItems] = useState([]), [settings, setSettings] = useState([]), [commands, setCommands] = useState([]), [rate, setRate] = useState(1), [warningDays, setWarningDays] = useState(30), [error, setError] = useState(''), [loading, setLoading] = useState(true)
    const [query, setQuery] = useState(''), [status, setStatus] = useState('all')
    async function load() {
        setLoading(true); setError('')
        try { const { data } = await api.get('/voice-templates'); setItems(data.templates || []); setSettings(data.settings || []); setCommands(data.commands || []); setRate(data.speech_rate || 1); setWarningDays(data.freshness_warning_days ?? 30) }
        catch { setError('No se pudieron cargar las frases de voz.') }
        finally { setLoading(false) }
    }
    async function toggleSetting(item) {
        setError('')
        try { await api.put(`/voice-templates/settings/${item.key}`, { enabled: !item.enabled }); await load() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar la configuración.') }
    }
    async function saveCommand(item, value) {
        setError('')
        try { await api.put(`/voice-templates/commands/${item.key}`, { aliases: value.split(',').map(v => v.trim()).filter(Boolean) }); await load() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar el comando.') }
    }
    async function saveRate() {
        setError('')
        try { await api.put('/voice-templates/speech-rate', { value: Number(rate) }); await load() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar la velocidad.') }
    }
    async function saveWarningDays() {
        setError('')
        try { await api.put('/voice-templates/freshness-warning-days', { value: Number(warningDays) }); await load() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar el aviso de frescura.') }
    }
    useEffect(() => { load(); return stopSpeaking }, [])
    const visibleItems = items.filter(item => (status === 'all' || (status === 'active') === item.enabled)
        && `${item.name} ${item.process} ${item.key} ${item.text}`.toLowerCase().includes(query.trim().toLowerCase()))
    return <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-8"><header><h1 className="text-2xl font-bold">Frases de voz</h1><p className="mt-2 text-slate-600">Editá lo que dicen la web y Android. Las variables entre llaves se completan automáticamente y no deben eliminarse.</p></header>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-700">{error}</p>}{loading ? <p>Cargando…</p> : <><section className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Comandos y velocidad</h2><p className="mt-1 text-sm text-slate-600">Separá los alias con comas. Cada palabra o frase puede pertenecer a una sola acción.</p><div className="mt-4 grid gap-3 sm:grid-cols-2">{commands.map(item => <label key={item.key} className="text-sm font-medium">{item.name}<div className="mt-1 flex gap-2"><input id={`command-${item.key}`} className="min-h-12 min-w-0 flex-1 rounded-xl border p-3" defaultValue={item.aliases.join(', ')} /><button className="rounded-xl border px-3" onClick={() => saveCommand(item, document.getElementById(`command-${item.key}`).value)}>Guardar</button></div></label>)}</div><div className="mt-5 flex flex-wrap items-end gap-3"><label className="text-sm font-medium">Velocidad de lectura: {Number(rate).toFixed(2)}×<input type="range" min="0.6" max="1.6" step="0.05" value={rate} onChange={e => setRate(e.target.value)} className="block w-64" /></label><button className="min-h-12 rounded-xl bg-brand-500 px-4 font-semibold text-white" onClick={saveRate}>Guardar velocidad</button><button className="min-h-12 rounded-xl border px-4" onClick={() => { const previous=rate; import('../voice/speech').then(({setSpeechRate}) => { setSpeechRate(previous); speak('Prueba de velocidad de voz', setError) }) }}>Escuchar prueba</button></div></section><section className="rounded-2xl border bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Frescura de productos</h2><p className="mt-1 text-sm text-slate-600">La fecha siempre se muestra y se registra. Configurá lectura, advertencias y bloqueo.</p><div className="mt-4 grid gap-3 sm:grid-cols-2">{settings.map(item => <label key={item.key} className="flex min-h-14 items-center justify-between rounded-xl border p-3"><span className="font-medium">{item.name}</span><input type="checkbox" checked={item.enabled} onChange={() => toggleSetting(item)} /></label>)}</div><div className="mt-4 flex flex-wrap items-end gap-3"><label className="text-sm font-medium">Avisar si vence dentro de<input type="number" min="0" max="365" value={warningDays} onChange={e => setWarningDays(e.target.value)} className="mt-1 block min-h-12 w-32 rounded-xl border p-3" /><span className="ml-2 text-xs text-slate-500">días (0 desactiva el aviso)</span></label><button className="min-h-12 rounded-xl bg-brand-500 px-4 font-semibold text-white" onClick={saveWarningDays}>Guardar aviso</button></div></section><section className="rounded-2xl border bg-white p-5 shadow-sm"><div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-lg font-bold">Catálogo de frases</h2><p className="text-sm text-slate-500">{visibleItems.length} de {items.length} frases visibles. Cada una puede editarse, probarse, activarse o desactivarse.</p></div><div className="flex flex-1 flex-wrap gap-2 sm:flex-none"><input aria-label="Buscar frase" className="min-h-12 min-w-0 flex-1 rounded-xl border px-3 sm:w-72" placeholder="Buscar frase o proceso" value={query} onChange={e => setQuery(e.target.value)} /><select aria-label="Filtrar frases" className="min-h-12 rounded-xl border px-3" value={status} onChange={e => setStatus(e.target.value)}><option value="all">Todas</option><option value="active">Activas</option><option value="inactive">Desactivadas</option></select></div></div></section><div className="mt-4 grid gap-4">{visibleItems.map(item => <TemplateCard key={`${item.key}:${item.updated_at || 'default'}`} item={item} onSaved={load} />)}{!visibleItems.length && <p className="rounded-xl border p-5 text-center text-slate-500">No hay frases que coincidan con el filtro.</p>}</div></>}
    </div>
}
