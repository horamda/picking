import { useEffect, useState } from 'react'
import api from '../api/axiosClient'
import DispatchPreview from './DispatchPreview'
const button = 'min-h-12 rounded-xl border bg-white px-4 py-2 disabled:opacity-40'
export default function DispatchBoard({ date, onSaved, onPlan }) {
    const [board, setBoard] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [dirty, setDirty] = useState(false)
    useEffect(() => {
        let active = true
        setBoard(null); setError(''); setDirty(false)
        if (date) api.get('/load-control/dispatch', { params: { date } }).then(r => { if (active) setBoard(r.data) }).catch(() => { if (active) setError('No se pudo leer la selección de cargas.') })
        return () => { active = false }
    }, [date])
    function toggle(index, id, value) {
        setBoard(b => ({ ...b, groups: b.groups.map((g, n) => n !== index ? g : { ...g, sources: g.sources.map(s => (!id || s.id === id) && !s.error ? { ...s, selected: value } : s) }) })); setDirty(true)
    }
    function move(index, step) {
        setBoard(b => { const groups = [...b.groups]; [groups[index], groups[index + step]] = [groups[index + step], groups[index]]; return { ...b, groups } }); setDirty(true)
    }
    async function save() {
        setBusy(true); setError('')
        try {
            const entries = board.groups.map(g => ({ branch: g.branch, truck: g.truck, source_ids: g.sources.filter(s => s.selected).map(s => s.id) })).filter(g => g.source_ids.length)
            await api.post('/load-control/dispatch', { date, versions: board.versions, entries })
            setBoard((await api.get('/load-control/dispatch', { params: { date } })).data); setDirty(false); await onSaved()
        } catch (e) { setError(e.response?.data?.error || 'No se pudo guardar la cola. Actualizá la página y reintentá.') }
        finally { setBusy(false) }
    }
    return <section className="space-y-4 rounded-2xl border bg-white p-4 sm:p-6">
        <h2 className="text-xl font-bold">Seleccionar cargas y ordenar camiones</h2>
        <p className="text-sm text-slate-600">Marcá repartos, guardá la cola y aprobá los pallets. Cada operario pasa al siguiente camión al terminar sus propias canchas. Los repartos permanecen separados.</p>
        {!date && <p>Seleccioná la fecha de reparto del PDF.</p>}
        {error && <p role="alert" className="text-red-700">{error}</p>}
        {board?.groups.length === 0 && <p>No hay cargas para esta fecha. Usá la fecha de reparto del PDF, que puede diferir de la fecha de subida.</p>}
        {board?.groups.map((g, index) => {
            const selected = g.sources.filter(s => s.selected), bultos = selected.reduce((n, s) => n + s.totals.bultos, 0), units = selected.reduce((n, s) => n + s.totals.unidades, 0)
            return <article key={`${g.branch}/${g.truck}`} className="rounded-xl border p-4">
                <div className="flex flex-wrap items-center justify-between gap-3"><label className="flex min-h-12 items-center gap-3 font-bold"><input type="checkbox" disabled={busy || g.locked} checked={g.sources.every(s => s.selected)} onChange={e => toggle(index, null, e.target.checked)} className="h-5 w-5" />Camión {g.truck} · {g.branch}</label><div className="flex gap-2"><button className={button} disabled={busy || g.locked || index === 0 || board.groups[index - 1]?.locked} aria-label={`Adelantar camión ${g.truck}`} onClick={() => move(index, -1)}>↑</button><button className={button} disabled={busy || g.locked || index === board.groups.length - 1 || board.groups[index + 1]?.locked} aria-label={`Retrasar camión ${g.truck}`} onClick={() => move(index, 1)}>↓</button></div></div>
                {g.locked && <p className="text-sm text-amber-800">Trabajo iniciado: selección y orden fijados.</p>}<p className="my-2 text-sm">Seleccionado: {selected.length} repartos · {bultos} bultos + {units} unidades</p>
                <DispatchPreview sourceIds={selected.map(s => s.id)} />
                {g.sources.map(s => <label key={s.id} className="my-1 flex min-h-12 items-center gap-3 rounded-lg bg-slate-50 p-2"><input type="checkbox" className="h-5 w-5" disabled={busy || g.locked || !!s.error} checked={s.selected} onChange={e => toggle(index, s.id, e.target.checked)} /><span>Reparto {s.reparto}{s.error ? ` · ${s.error}` : ` · ${s.totals.bultos} bultos + ${s.totals.unidades} unidades`}</span></label>)}
                {g.truck_id && selected.length > 0 && <button className={`${button} mt-3`} disabled={busy || dirty} onClick={() => onPlan({ id: g.truck_id, truck: g.truck, branch: g.branch })}>Revisar pallets y aprobar{g.planning_status === 'approved' ? ' · Aprobado' : ''}</button>}
            </article>
        })}
        {!!board?.groups.length && <button className="min-h-12 rounded-xl bg-brand-500 px-5 text-white disabled:opacity-40" disabled={busy} onClick={save}>{busy ? 'Guardando…' : 'Guardar selección y orden'}</button>}
    </section>
}
