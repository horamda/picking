import { useEffect, useState } from 'react'
import api from '../api/axiosClient'
import DispatchPreview from './DispatchPreview'
const button = 'min-h-12 rounded-xl border bg-white px-4 py-2 disabled:opacity-40'
const primary = 'min-h-12 rounded-xl bg-brand-500 px-5 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40'
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
    const groups = board?.groups || []
    const selectedSources = groups.flatMap(g => g.sources.filter(s => s.selected))
    const selectedTrucks = groups.filter(g => g.sources.some(s => s.selected)).length
    const selectedBultos = selectedSources.reduce((n, s) => n + s.totals.bultos, 0)
    const selectedUnits = selectedSources.reduce((n, s) => n + s.totals.unidades, 0)
    return <section className="space-y-4 rounded-2xl border bg-white p-4 sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-4">
            <div><h2 className="text-lg font-semibold">Seleccionar cargas y ordenar camiones</h2><p className="mt-1 max-w-3xl text-sm text-slate-600">1. Marcá las cargas · 2. Ordená los camiones · 3. Guardá los cambios · 4. Revisá y aprobá los pallets.</p></div>
            {board && <div className="text-right text-sm"><b className="block font-medium tabular-nums">{date.split('-').reverse().join('/')}</b><span className="text-slate-600">{groups.length} camiones · {groups.reduce((n, g) => n + g.sources.length, 0)} cargas</span></div>}
        </div>
        {!date && <p>Seleccioná la fecha de reparto del PDF.</p>}
        {error && <p role="alert" className="text-red-700">{error}</p>}
        {groups.length === 0 && board && <p className="text-muted py-6 text-center text-sm">No hay cargas para esta fecha. Usá la fecha de reparto del PDF, que puede diferir de la fecha de subida.</p>}
        {groups.map((g, index) => {
            const selected = g.sources.filter(s => s.selected), bultos = selected.reduce((n, s) => n + s.totals.bultos, 0), units = selected.reduce((n, s) => n + s.totals.unidades, 0)
            const allSelected = g.sources.length > 0 && selected.length === g.sources.length
            return <article key={`${g.branch}/${g.truck}`} className={`tile overflow-hidden rounded-2xl ${selected.length ? 'tile-selected' : ''}`}>
                <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-2.5">
                    <label className="flex min-h-11 min-w-0 flex-1 cursor-pointer items-center gap-3"><input type="checkbox" disabled={busy || g.locked} checked={allSelected} onChange={e => toggle(index, null, e.target.checked)} className="h-5 w-5 shrink-0" /><span className="stepper-mark shrink-0">{index + 1}</span><span className="min-w-0"><b className="block truncate text-base">Camión {g.truck}</b><span className="block truncate text-xs text-slate-500">{g.branch} · {selected.length} de {g.sources.length} cargas seleccionadas</span></span></label>
                    <div className="flex items-center gap-2">{g.locked && <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">Trabajo iniciado</span>}<button className={`${button} min-h-10 px-3`} disabled={busy || g.locked || index === 0 || groups[index - 1]?.locked} aria-label={`Adelantar camión ${g.truck}`} title="Mover antes" onClick={() => move(index, -1)}>↑</button><button className={`${button} min-h-10 px-3`} disabled={busy || g.locked || index === groups.length - 1 || groups[index + 1]?.locked} aria-label={`Retrasar camión ${g.truck}`} title="Mover después" onClick={() => move(index, 1)}>↓</button></div>
                </header>
                <div className="p-4">
                {g.locked && <p className="mb-3 rounded-lg bg-amber-50 p-2 text-sm text-amber-900">La preparación ya comenzó. La selección y el orden no se pueden modificar.</p>}
                <div className="grid gap-2 md:grid-cols-2">
                    {g.sources.map(s => <label key={s.id} className={`flex min-h-20 cursor-pointer items-start gap-3 rounded-xl border-2 p-3 transition-colors ${s.selected ? 'tile tile-selected' : 'tile'} ${s.error ? 'cursor-not-allowed border-red-200' : ''}`}><input type="checkbox" className="mt-1 h-5 w-5 shrink-0" disabled={busy || g.locked || !!s.error} checked={s.selected} onChange={e => toggle(index, s.id, e.target.checked)} /><span className="min-w-0 flex-1"><span className="flex flex-wrap items-center justify-between gap-2"><b>Reparto {s.reparto}</b>{s.selected && <span className="rounded-full bg-brand-500 px-2 py-0.5 text-[11px] font-semibold text-white">Incluido</span>}</span>{s.error ? <span className="text-sm text-red-700">{s.error}</span> : <><span className="mt-1 block text-sm">Canchas {s.court_numbers?.join(', ') || 'sin detalle'}</span><span className="block text-sm text-slate-600">{s.totals.bultos} bultos · {s.totals.unidades} unidades</span></>}</span></label>)}
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t pt-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Total a preparar</p><p className="font-medium tabular-nums">{selected.length} cargas · {bultos} bultos · {units} unidades</p></div>{!selected.length ? <p className="text-sm text-slate-500">Marcá al menos una carga.</p> : <span className="rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold text-white">Seleccionado</span>}</div>
                {!!selected.length && <details className="mt-3 rounded-xl border border-slate-200"><summary className="min-h-11 cursor-pointer px-4 py-3 text-sm font-semibold">Ver cálculo preliminar de pallets y HL</summary><div className="px-3 pb-1"><DispatchPreview sourceIds={selected.map(s => s.id)} /></div></details>}
                {g.truck_id && selected.length > 0 && <div className="mt-3 flex flex-wrap items-center justify-end gap-3">{dirty && <span className="text-sm text-amber-700">Primero guardá los cambios de selección.</span>}<button className={g.planning_status === 'approved' ? button : primary} disabled={busy || dirty} onClick={() => onPlan({ id: g.truck_id, truck: g.truck, branch: g.branch })}>{g.planning_status === 'approved' ? 'Revisar planificación aprobada' : 'Revisar pallets y aprobar →'}</button></div>}
                </div>
            </article>
        })}
        {!!groups.length && <div className="sticky-bar sticky bottom-3 z-20 flex flex-wrap items-center justify-between gap-3 rounded-2xl p-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Selección total</p><p className="text-sm"><b>{selectedSources.length} cargas en {selectedTrucks} camiones</b> · {selectedBultos} bultos · {selectedUnits} unidades</p></div><button className={primary} disabled={busy || !dirty} onClick={save}>{busy ? 'Guardando…' : dirty ? 'Guardar selección y orden' : 'Cambios guardados'}</button></div>}
    </section>
}
