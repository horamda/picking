import TruckWorkSummary from './TruckWorkSummary'
const action = 'min-h-12 rounded-xl bg-brand-500 px-4 py-3 text-sm font-semibold text-white disabled:opacity-40'
const secondary = 'min-h-12 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700'

export default function ControlTruckCard({ truck: t, manager, pickingOnly = false, onOpen, onActivate, onAssets, onAudit, onPlan }) {
    const unapproved = t.status.shortages.filter(s => !s.approved_by).length
    const pending = t.total - t.completed
    const next = t.loads.find(l => !l.canchas.length || !l.canchas.every(c => c.status.done))
    const title = t.released ? 'Liberado para reparto' : pending ? 'Controles pendientes' : !t.status.assets ? 'Faltan activos de salida' : unapproved ? 'Requiere autorización' : 'Revisar salida'
    if (pickingOnly) return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-xl font-bold">Camión {t.truck || 'Sin identificar'}</h2>
        <TruckWorkSummary summary={t.summary} waiting={t.planning_status === 'pending'} />
        <p className="mb-3 text-sm text-slate-500">{t.load_date} · {t.branch}</p>
        {t.loads.map(load => {
            const done = load.canchas.filter(c => c.status.checks.some(ch => ch.stage === (t.summary?.mine?.stage ?? 0) && ch.status === 'done')).length
            return <div key={load.id} className="flex flex-wrap items-center justify-between gap-3 border-t py-3">
                <div><b>Reparto {load.reparto}</b><p className="text-sm">{done}/{load.canchas.length} canchas preparadas</p></div>
                <button className={secondary} onClick={() => onOpen(load.id)}>Abrir picking</button>
            </div>
        })}
        {t.pending.map(source => <div key={source.id} className="flex items-center justify-between gap-3 border-t py-3">
            <b>Reparto {source.reparto}</b><button className={secondary} disabled={Boolean(t.status.released_at)} onClick={() => onActivate(source.id)}>Preparar carga</button>
        </div>)}
    </article>
    return <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {manager && t.id && <div className="px-5 pt-4"><button className={secondary} onClick={onPlan}>Planificar pallets</button></div>}
        <div className="space-y-4 p-4 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Camión</p><h2 className="text-2xl font-bold text-slate-900">{t.truck || 'Sin identificar'}</h2><p className="mt-1 text-sm text-slate-500">{t.load_date || 'Sin fecha'} · {t.branch || 'Sin depósito'}</p></div>
                <span className={`rounded-full px-3 py-2 text-xs font-semibold ${t.released ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-50 text-amber-900'}`}>{title}</span>
            </div>
            <div><div className="mb-2 flex justify-between gap-2 text-sm"><b>{t.total} {t.total === 1 ? 'carga' : 'cargas'}</b><span>{t.completed} de {t.total} con doble control</span></div><progress value={t.completed} max={t.total || 1} aria-label={`Cargas controladas del camión ${t.truck}`} className="h-2 w-full accent-emerald-600" /></div>
            {!t.released && (next || t.pending.length > 0) && <button className={`${action} w-full sm:w-auto`} disabled={Boolean(t.status.released_at)} onClick={() => next ? onOpen(next.id) : onActivate(t.pending[0].id)}>Ingresar a la siguiente carga</button>}
            {t.status.released_at && !t.released && <p role="alert" className="text-sm text-red-700">La liberación anterior no cubre las cargas pendientes actuales. Requiere revisión del supervisor.</p>}
        </div>
        <TruckWorkSummary summary={t.summary} />
        <details className="border-t border-slate-200" open={t.total <= 3}>
            <summary className="min-h-12 cursor-pointer px-4 py-3 text-sm font-semibold sm:px-6">Cargas de este camión ({t.total})</summary>
            <ol className="divide-y divide-slate-100 px-4 sm:px-6">
                {t.loads.map(l => {
                    const done = l.canchas.filter(c => c.status.done).length
                    const finished = l.canchas.length > 0 && done === l.canchas.length
                    const started = l.canchas.some(c => c.status.checks.length > 0)
                    return <li key={`load-${l.id}`} className="flex flex-wrap items-center justify-between gap-3 py-4"><div><h3 className="font-semibold">Carga / reparto {l.reparto}</h3><p className={`text-sm ${finished ? 'text-emerald-700' : 'text-slate-500'}`}>{finished ? 'Controlada' : started ? 'En control' : 'Sin iniciar'} · {done}/{l.canchas.length} canchas completas</p></div><button className={secondary} onClick={() => onOpen(l.id)}>{pickingOnly ? 'Abrir picking' : finished ? 'Ver control' : 'Ingresar al control'}</button></li>
                })}
                {t.pending.map(s => <li key={`source-${s.id}`} className="flex flex-wrap items-center justify-between gap-3 py-4"><div><h3 className="font-semibold">Carga / reparto {s.reparto}</h3><p className="text-sm text-slate-500">Sin iniciar · PDF ya importado</p></div><button className={secondary} disabled={Boolean(t.status.released_at)} onClick={() => onActivate(s.id)}>{pickingOnly ? 'Preparar carga' : 'Iniciar control'}</button></li>)}
            </ol>
        </details>
        {!pickingOnly && <div className="space-y-3 border-t border-slate-200 bg-slate-50 px-4 py-4 sm:px-6">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Salida del camión</h3>
            <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm"><span>{pending ? `${pending} cargas pendientes` : 'Todas las cargas controladas'}</span><span>Activos: {t.status.assets ? 'confirmados' : 'pendientes'}</span><span>{unapproved ? `${unapproved} faltantes por autorizar` : 'Sin autorizaciones pendientes'}</span></div>
            <div className="flex flex-wrap gap-2">{t.status.complete && !t.status.assets && <button className={action} onClick={onAssets}>Registrar activos y completar salida</button>}{manager && t.id && <button className={secondary} onClick={onAudit}>Trazabilidad</button>}</div>
            {t.status.assets && <details className="text-sm"><summary className="min-h-12 cursor-pointer py-3">Ver activos registrados</summary><div className="grid gap-1 sm:grid-cols-2">{Object.entries(t.status.assets.quantities).map(([name, count]) => <p key={name}>{name}: <b>{count}</b></p>)}</div></details>}
        </div>}
    </article>
}
