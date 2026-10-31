import { useEffect, useState } from 'react'
import api from '../api/axiosClient'
import { todayInputValue } from '../utils/format'

const button = 'min-h-12 rounded-xl border px-4 py-3 disabled:opacity-50'
export default function DailyAssistance({ users }) {
    const [date, setDate] = useState(todayInputValue), [rows, setRows] = useState([])
    const [selected, setSelected] = useState({}), [people, setPeople] = useState({}), [reviewed, setReviewed] = useState({})
    const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
    const key = r => `${r.load_id}:${r.court}:${r.stage}`
    async function refresh(signal) {
        const r = await api.get('/load-control/assistance', { params: { date }, signal })
        if (!signal?.aborted) { setRows(r.data); setSelected({}); setReviewed({}); setError('') }
    }
    useEffect(() => {
        const controller = new AbortController()
        setRows([])
        refresh(controller.signal).catch(e => { if (!controller.signal.aborted) setError(e.response?.data?.error || 'No se pudieron cargar los refuerzos.') })
        return () => controller.abort()
    }, [date])
    async function act(fn) {
        if (busy) return
        setBusy(true); setError(''); setMessage('')
        try { await fn(); await refresh(); setMessage('Refuerzo actualizado. La app recibirá el cambio al actualizar su trabajo.') }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar. Actualizá y reintentá.') }
        finally { setBusy(false) }
    }
    return <section className="space-y-4 rounded-2xl border bg-white p-5">
        <h2 className="text-xl font-bold">Refuerzos del día</h2>
        <p className="text-sm text-slate-600">Elegí una cancha pausada y cedé productos pendientes a una persona disponible. El refuerzo no cambia su planificación semanal.</p>
        <div className="flex flex-wrap gap-3"><label>Fecha de las cargas<input type="date" className={`${button} block`} disabled={busy} value={date} onChange={e => e.target.value && setDate(e.target.value)} /></label><button className={button} disabled={busy} onClick={() => act(() => refresh())}>Actualizar pendientes</button></div>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-800">{error}</p>}
        {message && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-emerald-800">{message}</p>}
        {!rows.length && !error && <p>No hay tareas aprobadas para repartir en esta fecha.</p>}
        {rows.map(r => <article key={key(r)} className="space-y-3 rounded-xl border p-4">
            <h3 className="font-bold">Camión {r.truck} · Reparto {r.reparto} · Cancha {r.court}</h3>
            <p>{r.stage === 0 ? 'Picking' : 'Pallets completos'} · {r.owner || 'Sin iniciar'}</p>
            {r.running && <p className="text-amber-800">El titular debe pausar para ceder productos.</p>}
            {!r.closed && <fieldset disabled={busy || r.running} className="space-y-3">
                <label className="block">Operario de refuerzo<select className={`${button} block w-full bg-white`} value={people[key(r)] || ''} onChange={e => setPeople({ ...people, [key(r)]: e.target.value })}><option value="">Seleccionar persona</option>{users.filter(u => u.active && u.role === (r.stage === 0 ? 'operador' : 'palletizador') && u.username !== r.owner).map(u => <option key={u.id} value={u.id}>{u.username}</option>)}</select></label>
                {r.products.map(p => <label key={p.sku} className="flex min-h-12 items-center gap-3"><input type="checkbox" checked={(selected[key(r)] || []).includes(p.sku)} onChange={e => setSelected({ ...selected, [key(r)]: e.target.checked ? [...(selected[key(r)] || []), p.sku] : selected[key(r)].filter(s => s !== p.sku) })} /><span>{p.sku} · {p.descripcion} · {p.bultos} bultos + {p.unidades || 0} unidades</span></label>)}
                <button className={`${button} bg-brand-500 text-white`} disabled={!people[key(r)] || !selected[key(r)]?.length} onClick={() => act(() => api.post(`/load-control/loads/${r.load_id}/courts/${r.court}/assistance/${r.stage}`, { user_id: Number(people[key(r)]), skus: selected[key(r)], version: r.version }))}>Asignar productos seleccionados</button>
            </fieldset>}
            {r.helpers.map(h => <div className="rounded-xl bg-slate-50 p-3" key={h.id}>
                <p className="font-semibold">Refuerzo: {h.username} · {h.day}</p>
                <p>{Object.keys(h.answers).length} de {h.skus.length} productos · {Math.floor(h.elapsed_seconds / 60)} min · {h.status === 'done' ? 'Finalizado' : h.status === 'returned' ? 'Devuelto' : h.timer_started_at ? 'En curso' : 'Pendiente / pausado'}</p>
                {h.status === 'active' && <><label className="my-2 flex items-center gap-2"><input type="checkbox" checked={!!reviewed[h.id]} onChange={e => setReviewed({ ...reviewed, [h.id]: e.target.checked })} />Revisé lo preparado sin confirmar antes de devolver los pendientes</label><button className={button} disabled={busy || !reviewed[h.id] || !!h.timer_started_at} onClick={() => act(() => api.post(`/load-control/loads/${r.load_id}/courts/${r.court}/assistance/${h.id}/return`, { physical_review: true }))}>Devolver pendientes al titular</button></>}
            </div>)}
        </article>)}
    </section>
}
