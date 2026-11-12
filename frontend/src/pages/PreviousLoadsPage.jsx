import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'

const labels = { pending: 'Pendiente', in_progress: 'Armado incompleto', completed: 'Armado completo', cancelled: 'Anulada' }
const colors = { pending: 'bg-slate-100 text-slate-700', in_progress: 'bg-amber-100 text-amber-900', completed: 'bg-emerald-100 text-emerald-800', cancelled: 'bg-red-100 text-red-800' }

export default function PreviousLoadsPage() {
    const [loads, setLoads] = useState([])
    const [filter, setFilter] = useState('open')
    const [reasons, setReasons] = useState({})
    const [busy, setBusy] = useState(null)
    const [error, setError] = useState('')

    async function load() {
        setError('')
        try { setLoads((await api.get('/load-control/admin/previous-loads')).data) }
        catch (e) { setError(e.response?.data?.error || 'No se pudieron cargar las cargas anteriores.') }
    }
    useEffect(() => { load() }, [])
    const visible = useMemo(() => loads.filter(item => filter === 'all'
        || (filter === 'open' ? ['pending', 'in_progress'].includes(item.state) : item.state === filter)), [loads, filter])

    async function cancel(item) {
        const reason = (reasons[item.id] || '').trim()
        if (reason.length < 5) { setError('Escribí un motivo de al menos 5 caracteres.'); return }
        if (!window.confirm(`¿Anular el reparto ${item.reparto} del camión ${item.truck}? Dejará de aparecer a operarios y controladores.`)) return
        setBusy(item.id); setError('')
        try { await api.post(`/load-control/admin/loads/${item.id}/cancel`, { reason }); await load() }
        catch (e) { setError(e.response?.data?.error || 'No se pudo anular la carga.') }
        finally { setBusy(null) }
    }

    return <div className="mx-auto max-w-6xl space-y-5 p-4 sm:p-8">
        <header><h1 className="text-2xl font-bold">Cargas anteriores</h1><p className="mt-2 text-slate-600">Cargas con fecha anterior a hoy. Anular conserva todo el historial, pero retira la tarea de picking, pallets completos y controles.</p></header>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-800">{error}</p>}
        <div className="flex flex-wrap gap-2">{[['open', 'Pendientes'], ['in_progress', 'Armado incompleto'], ['completed', 'Completas'], ['cancelled', 'Anuladas'], ['all', 'Todas']].map(([value, text]) => <button key={value} className={`min-h-11 rounded-xl border px-4 ${filter === value ? 'bg-brand-500 text-white' : 'bg-white'}`} onClick={() => setFilter(value)}>{text}</button>)}</div>
        <p className="text-sm text-slate-500">{visible.length} cargas</p>
        <div className="grid gap-4 lg:grid-cols-2">{visible.map(item => <article key={item.id} className="rounded-2xl border bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm text-slate-500">{new Date(`${item.date}T00:00:00`).toLocaleDateString('es-AR')} · {item.branch}</p><h2 className="text-xl font-bold">Camión {item.truck}</h2><p className="font-medium">Reparto {item.reparto}</p></div><span className={`rounded-full px-3 py-1 text-sm font-semibold ${colors[item.state]}`}>{labels[item.state]}</span></div>
            <div className="mt-4"><div className="flex justify-between text-sm"><span>Avance de armado</span><b>{item.assembly.done} de {item.assembly.total} {item.assembly.unit}</b></div><progress className="mt-2 w-full accent-emerald-600" value={item.assembly.done} max={Math.max(1, item.assembly.total)} /></div>
            {item.cancellation && <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-900"><b>Anulada por {item.cancellation.cancelled_by_username}</b><p>{item.cancellation.reason}</p><p className="mt-1 text-xs">{new Date(item.cancellation.cancelled_at).toLocaleString('es-AR')}</p></div>}
            {item.can_cancel && <div className="mt-4 border-t pt-4"><label className="text-sm font-medium">Motivo de anulación<input className="mt-1 min-h-12 w-full rounded-xl border p-3" maxLength="500" placeholder="Ej.: carga antigua que no se preparará" value={reasons[item.id] || ''} onChange={e => setReasons(current => ({ ...current, [item.id]: e.target.value }))} /></label><button disabled={busy === item.id} className="mt-3 min-h-12 rounded-xl bg-red-700 px-4 font-semibold text-white disabled:opacity-50" onClick={() => cancel(item)}>{busy === item.id ? 'Anulando…' : 'Anular carga pendiente'}</button></div>}
        </article>)}</div>
        {!visible.length && <p className="rounded-2xl border bg-white p-8 text-center text-slate-500">No hay cargas en este estado.</p>}
    </div>
}
