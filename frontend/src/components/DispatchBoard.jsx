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
        <h2 className="text-xl font-bold">Cargas del día por camión</h2>
        <p className="text-sm text-slate-600">Cada camión reúne todos sus repartos de la fecha seleccionada, aunque estén intercalados en el PDF. Marcá las cargas a preparar, ordená los camiones y aprobá el armado consolidado.</p>
        {board && <p className="rounded-lg bg-slate-100 p-3 text-sm"><b>{date.split('-').reverse().join('/')}</b> · {board.groups.length} camiones · {board.groups.reduce((n, g) => n + g.sources.length, 0)} cargas / repartos</p>}
        {!date && <p>Seleccioná la fecha de reparto del PDF.</p>}
        {error && <p role="alert" className="text-red-700">{error}</p>}
        {board?.groups.length === 0 && <p>No hay cargas para esta fecha. Usá la fecha de reparto del PDF, que puede diferir de la fecha de subida.</p>}
        {board?.groups.map((g, index) => {
            const selected = g.sources.filter(s => s.selected), bultos = selected.reduce((n, s) => n + s.totals.bultos, 0), units = selected.reduce((n, s) => n + s.totals.unidades, 0)
            return <article key={`${g.branch}/${g.truck}`} className="rounded-xl border p-4">
                <div className="flex flex-wrap items-center justify-between gap-3"><label className="flex min-h-12 items-center gap-3 font-bold"><input type="checkbox" disabled={busy || g.locked} checked={g.sources.every(s => s.selected)} onChange={e => toggle(index, null, e.target.checked)} className="h-5 w-5" />Camión {g.truck} · {g.branch}</label><div className="flex gap-2"><button className={button} disabled={busy || g.locked || index === 0 || board.groups[index - 1]?.locked} aria-label={`Adelantar camión ${g.truck}`} onClick={() => move(index, -1)}>↑</button><button className={button} disabled={busy || g.locked || index === board.groups.length - 1 || board.groups[index + 1]?.locked} aria-label={`Retrasar camión ${g.truck}`} onClick={() => move(index, 1)}>↓</button></div></div>
                {g.locked && <p className="text-sm text-amber-800">Trabajo iniciado: selección y orden fijados.</p>}
                <p className="my-2 text-sm font-semibold">{g.sources.length} cargas de este camión · {selected.length} seleccionadas</p>
                <div className="space-y-2 border-l-2 border-blue-200 pl-3 sm:pl-5">
                    {g.sources.map(s => <label key={s.id} className={`flex min-h-12 items-start gap-3 rounded-lg border p-3 ${s.selected ? 'border-blue-200 bg-blue-50' : 'border-slate-200 bg-slate-50'}`}><input type="checkbox" className="mt-1 h-5 w-5 shrink-0" disabled={busy || g.locked || !!s.error} checked={s.selected} onChange={e => toggle(index, s.id, e.target.checked)} /><span className="min-w-0"><b className="block">Carga · Reparto {s.reparto}</b>{s.error ? <span className="text-red-700">{s.error}</span> : <><span className="block text-sm">Canchas: {s.court_numbers?.join(', ') || 'Sin detalle'}</span><span className="block text-sm text-slate-600">{s.totals.bultos} bultos + {s.totals.unidades} unidades</span></>}</span></label>)}
                </div>
                <h3 className="mt-4 font-bold">Total a preparar · Camión {g.truck}</h3>
                <p className="text-sm">{selected.length} cargas seleccionadas · {bultos} bultos + {units} unidades</p>
                {!selected.length && <p className="mt-2 text-sm text-slate-500">Seleccioná las cargas que querés incluir en el armado de este camión.</p>}
                <DispatchPreview sourceIds={selected.map(s => s.id)} />
                {g.truck_id && selected.length > 0 && <button className={`${button} mt-3`} disabled={busy || dirty} onClick={() => onPlan({ id: g.truck_id, truck: g.truck, branch: g.branch })}>Revisar pallets y aprobar{g.planning_status === 'approved' ? ' · Aprobado' : ''}</button>}
            </article>
        })}
        {!!board?.groups.length && <button className="min-h-12 rounded-xl bg-brand-500 px-5 text-white disabled:opacity-40" disabled={busy} onClick={save}>{busy ? 'Guardando…' : 'Guardar selección y orden'}</button>}
    </section>
}
