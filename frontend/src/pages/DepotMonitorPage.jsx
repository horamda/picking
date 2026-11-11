import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { todayInputValue } from '../utils/format'

const labels = { running: 'En curso', paused: 'Pausado', done: 'Finalizado', pending: 'Listo para iniciar', waiting: 'En espera' }
const colors = { running: 'border-emerald-500 bg-emerald-950', paused: 'border-amber-400 bg-amber-950', done: 'border-sky-500 bg-sky-950', pending: 'border-brand-500 bg-brand-950', waiting: 'border-slate-600 bg-slate-900' }
const actions = { guardar_semana: 'Borrador semanal guardado', publicar_semana: 'Semana publicada', activar_semana: 'Asignación semanal activada', asignar_refuerzo: 'Refuerzo asignado', devolver_refuerzo: 'Pendientes de refuerzo devueltos', vencer_refuerzo: 'Refuerzo vencido: revisar pendientes', seleccionar_cola_armado: 'Cola de camiones actualizada', respuesta_control: 'Producto registrado', iniciar_control: 'Tarea iniciada', reanudar_proceso: 'Tarea reanudada', pausar_proceso: 'Tarea pausada', finalizar_control: 'Tarea finalizada', aprobar_planificacion: 'Carga aprobada', iniciar_planificacion: 'Planificación iniciada', asignar_canchas: 'Canchas asignadas', reasignar_canchas: 'Trabajo reasignado', registrar_activos: 'Activos registrados', liberacion_en_aplicacion: 'Camión liberado', faltante_approve: 'Faltante aprobado', faltante_adjusted: 'Ajuste confirmado', importar_planilla_control: 'Reparto incorporado', importacion_csv_autorizada: 'Maestro de artículos importado', editar_descripcion_voz: 'Descripción de voz actualizada' }

function ProcessCard({ entries, stage, group }) {
    const process = entries.find(item => !item.assistance) || entries[0]
    const helpers = entries.filter(item => item.assistance)
    const title = ['1 · Armado', '2 · Control 1', '3 · Control 2'][stage]
    if (!process) { const destinations = group.assemblyDestinations || []; return <article className="monitor-process-card border-slate-600 bg-slate-900"><div className="flex items-center justify-between gap-2"><h3 className="text-sm font-bold">{title}</h3><span className="rounded-md bg-black/20 px-2 py-1 text-sm">No requerido</span></div><p className="mt-2 text-sm font-semibold">No requiere trabajo propio</p><p className="mt-1 text-sm text-slate-300">{destinations.length ? `Productos incluidos en ${destinations.map(item => `${item.pallet_id} · Cancha ${item.owner_court}`).join(', ')}.` : 'Sin bultos ni unidades sueltas.'}</p></article> }
    const displayStatus = process.status === 'pending' && process.available === false ? 'waiting' : process.status
    const candidates = process.responsible_candidates || []
    const responsibility = process.username ? `Responsable: ${process.username}` : candidates.length === 1 ? `Responsable previsto: ${candidates[0]}` : candidates.length ? `Disponibles: ${candidates.join(', ')}` : 'Sin responsable asignado'
    const equivalent = process.bultos_equiv == null ? '' : ` · ${Number(process.bultos_equiv).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} bultos equiv.`
    const pct = process.total ? Math.round(process.answered * 100 / process.total) : 0
    const incidentCount = (process.picking_errors || 0) + (process.control_errors || 0) + (process.stock_differences || 0)
    return <article className={`monitor-process-card ${colors[displayStatus]}`}>
        <div className="flex items-center justify-between gap-2"><h3 className="text-sm font-bold">{title}</h3><span className="rounded-md bg-black/20 px-2 py-1 text-sm">{labels[displayStatus]}</span></div>
        <div className="mt-1 flex items-center justify-between gap-2"><div className="min-w-0"><p className="truncate text-sm font-bold">{responsibility}</p>{displayStatus === 'waiting' && <p className="truncate text-sm text-slate-300" title={process.blocked_reason}>{process.blocked_reason}</p>}{helpers.length > 0 && <p className="truncate text-sm text-sky-200">Refuerzo: {helpers.map(item => item.username || 'Por asignar').join(', ')}</p>}</div><b className="shrink-0 text-xl">{pct}%</b></div>
        <p className="mt-1 truncate text-sm font-semibold text-slate-200" title={`${process.bultos} bultos + ${process.unidades} unidades${equivalent}`}>{process.bultos} bultos + {process.unidades} unidades{equivalent}</p>
        {incidentCount > 0 && <p className="mt-1 truncate rounded bg-black/25 px-2 py-1 text-sm" title={`Picking ${process.picking_errors || 0}; control ${process.control_errors || 0}; stock ${process.stock_differences || 0}`}><b>{incidentCount} diferencias</b> · picking {process.picking_errors || 0} · control {process.control_errors || 0} · stock {process.stock_differences || 0}</p>}
        <div className="mt-auto flex justify-between text-sm text-slate-300"><span>{process.answered}/{process.total} productos · {process.shortages} faltantes</span><span>{Math.floor(process.elapsed_seconds / 60)} min</span></div>
        <progress value={process.answered} max={process.total || 1} aria-label={`Avance de ${process.username || 'cancha ' + group.court}`} className="mt-1 h-1.5 w-full accent-emerald-400" />
        {(process.timing?.needs_review || process.status === 'done' && process.answered < process.total) && <p className="mt-1 text-sm font-bold text-amber-200">{process.timing?.needs_review ? 'Revisar tiempo' : 'Finalizado con registros incompletos'}</p>}
    </article>
}

export default function DepotMonitorPage() {
    const [date, setDate] = useState(todayInputValue()), [data, setData] = useState(null)
    const [error, setError] = useState(''), [last, setLast] = useState(null), [filter, setFilter] = useState('all')
    useEffect(() => {
        let active = true, timer, controller
        setData(null); setLast(null)
        async function refresh() {
            controller = new AbortController()
            try { const response = await api.get('/load-control/monitor', { params: { date }, signal: controller.signal, timeout: 12000 }); if (active) { setData(response.data); setLast(new Date()); setError('') } }
            catch { if (active) setError('SIN CONEXIÓN · Los datos pueden estar desactualizados') }
            finally { if (active) timer = setTimeout(refresh, 5000) }
        }
        refresh(); return () => { active = false; clearTimeout(timer); controller?.abort() }
    }, [date])

    const processes = data?.processes || []
    const truckOrder = new Map((data?.trucks || []).map((truck, index) => [truck.truck, truck.position ?? index + 1]))
    const grouped = new Map()
    processes.filter(process => [0, 1, 2].includes(process.stage)).forEach(process => {
        const key = process.pallet_id ? `pallet:${process.load_id}:${process.pallet_id}` : `${process.load_id}:${process.court}`
        if (!grouped.has(key)) grouped.set(key, { key, truck: process.truck, reparto: process.reparto, court: process.court, palletId: process.pallet_id, palletKind: process.pallet_kind, assemblyStage: process.assembly_stage, assemblyDestinations: process.assembly_destinations || [], stages: [[], [], []] })
        if (!grouped.get(key).assemblyDestinations.length && process.assembly_destinations?.length) grouped.get(key).assemblyDestinations = process.assembly_destinations
        grouped.get(key).stages[process.stage].push(process)
    })
    const groups = [...grouped.values()].sort((a, b) => (truckOrder.get(a.truck) ?? 999) - (truckOrder.get(b.truck) ?? 999) || String(a.truck).localeCompare(String(b.truck), 'es', { numeric: true }) || String(a.reparto).localeCompare(String(b.reparto), 'es', { numeric: true }) || a.court - b.court)
    const displayStatus = process => process.status === 'pending' && process.available === false ? 'waiting' : process.status
    const rows = groups.filter(group => filter === 'all' || group.stages.some(stage => stage.some(process => displayStatus(process) === filter)))

    return <div className="min-h-screen bg-slate-950 p-3 text-white sm:p-4">
        <header className="grid gap-2 border-b border-slate-800 pb-2 lg:grid-cols-[minmax(190px,1fr)_auto] lg:items-end">
            <div><p className="text-sm font-semibold uppercase tracking-widest text-[#FFD27A]">PickearYa · Depósito</p><h1 className="text-xl font-bold leading-tight sm:text-2xl">Armado en vivo</h1></div>
            <div className="flex flex-wrap items-center gap-2 lg:justify-end"><label className="text-sm text-slate-300">Fecha<input aria-label="Fecha del monitor" type="date" value={date} onChange={event => event.target.value && setDate(event.target.value)} className="ml-2 min-h-11 rounded-lg bg-slate-800 px-3 py-2 text-white" /></label><button className="min-h-11 rounded-lg border border-slate-600 px-3 text-sm" onClick={() => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen().catch(() => setError('El navegador no permite pantalla completa.'))}>Pantalla completa</button><Link to="/supervision" className="inline-flex min-h-11 items-center px-3 py-2 text-sm underline">Supervisión</Link></div>
        </header>
        <section className="my-2 grid gap-2 xl:grid-cols-[minmax(260px,.8fr)_minmax(640px,2.2fr)]">
            <div role="status" className={`flex min-h-11 items-center rounded-lg px-3 py-2 text-sm ${error ? 'bg-red-800' : 'bg-slate-900 text-slate-300'}`}>{error || `Actualización cada 5 segundos · ${last?.toLocaleTimeString('es-AR') || 'Cargando…'}`}</div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">{Object.entries(labels).map(([key, label]) => <button key={key} onClick={() => setFilter(filter === key ? 'all' : key)} aria-pressed={filter === key} className={`flex min-h-11 items-center justify-between rounded-lg border-2 px-3 py-2 text-left text-sm ${colors[key]} ${filter === key ? 'ring-2 ring-white' : ''}`}><span className="truncate">{label}</span><b className="ml-2 text-lg leading-none">{processes.filter(process => [0, 1, 2].includes(process.stage) && displayStatus(process) === key).length}</b></button>)}</div>
        </section>
        <section className="mb-3"><h2 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-300">Cargas, aprobaciones y salida</h2><div className="grid gap-2">{data?.trucks?.map(truck => { const planned=truck.summary?.pallets, capacity=truck.summary?.capacity, free=Number.isFinite(planned)&&Number.isFinite(capacity)?Math.max(0,capacity-planned):null; const planningLabel=truck.released ? 'Liberado' : truck.planning === 'approved' ? 'Armado aprobado' : truck.planning === 'legacy' ? 'Operación anterior en curso' : 'Espera aprobación'; return <article key={truck.id} className="grid gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs sm:grid-cols-[minmax(170px,1fr)_minmax(260px,2fr)_auto] sm:items-center"><div><b className="text-sm">{truck.position ? `${truck.position}. ` : ''}{truck.truck} · {truck.branch}</b><p className="mt-0.5 text-slate-300">{truck.summary?.loads ?? 0} repartos</p></div>{truck.summary && <div className="flex flex-wrap gap-x-4 gap-y-1 text-slate-300"><span><b className="text-white">{truck.summary.bultos}</b> bultos + <b className="text-white">{truck.summary.unidades}</b> unidades</span><span><b className="text-white">{truck.summary.hl ?? 'Pendiente'}</b> HL</span><span><b className="text-white">{planned ?? 'Pendiente'}</b> pallets / capacidad {capacity ?? 'Pendiente'}{free != null ? ` / ${free} libres` : ''}</span></div>}<div className="sm:text-right"><p className="font-semibold text-sky-200">{planningLabel}</p><p className="text-slate-300">Activos: {labels[truck.assets_status]}{truck.assets_username ? ` · ${truck.assets_username}` : ''}</p></div></article>})}</div></section>
        <section className="space-y-2">{rows.map(group => <article key={group.key} className="overflow-x-auto rounded-lg border border-slate-700 bg-slate-900/70 p-2"><header className="mb-1 flex flex-wrap items-center justify-between gap-2 text-xs"><h2 className="font-bold">Camión {group.truck} · Reparto {group.reparto}{group.palletId ? ` · Pallet ${group.palletId}` : ''}{group.palletKind === 'full' ? ' · Completo' : ''}</h2><span className="rounded-full bg-slate-800 px-2 py-1 font-semibold">{group.palletKind === 'full' ? `Origen cancha ${group.court}` : `Cancha responsable ${group.court}`}</span></header><div className="grid min-w-[720px] grid-cols-3 gap-2">{[0, 1, 2].map(stage => <ProcessCard key={stage} entries={group.stages[stage]} stage={stage} group={group} />)}</div></article>)}</section>
        {data && !rows.length && <p className="rounded-xl bg-slate-900 p-6 text-xl">Sin tareas para esta fecha y estado.</p>}
        <section className="mt-6"><h2 className="mb-2 text-lg font-semibold">Últimas acciones del día</h2><div className="grid gap-2 md:grid-cols-2">{data?.events?.map(event => <div key={event.id} className="rounded-xl bg-slate-900 p-3 text-sm"><time className="mr-3 text-slate-400">{new Date(event.at).toLocaleTimeString('es-AR')}</time><b>{event.username || 'Sistema'}</b><span> · {actions[event.action] || 'Actividad registrada'}</span></div>)}</div></section>
        <section className="mt-6"><h2 className="mb-2 text-lg font-semibold">Sin proceso en curso en esta fecha</h2><div className="flex flex-wrap gap-2">{data?.operators.filter(user => !processes.some(process => process.user_id === user.id && process.status === 'running')).map(user => <div key={user.id} className="rounded-xl border border-slate-700 p-3 text-sm"><b>{user.username}</b><p className="text-slate-400">{user.courts.length ? `Canchas ${user.courts.join(', ')}` : 'Sin canchas asignadas'}</p></div>)}</div></section>
    </div>
}
