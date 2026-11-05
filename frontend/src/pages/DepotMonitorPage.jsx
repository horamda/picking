import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { todayInputValue } from '../utils/format'

const labels = { running: 'En curso', paused: 'Pausado', done: 'Finalizado', pending: 'Listo para iniciar', waiting: 'En espera' }
const colors = { running: 'border-emerald-500 bg-emerald-950', paused: 'border-amber-400 bg-amber-950', done: 'border-sky-500 bg-sky-950', pending: 'border-violet-500 bg-violet-950', waiting: 'border-slate-600 bg-slate-900' }
const actions = { guardar_semana: 'Borrador semanal guardado', publicar_semana: 'Semana publicada', activar_semana: 'Asignación semanal activada', asignar_refuerzo: 'Refuerzo asignado', devolver_refuerzo: 'Pendientes de refuerzo devueltos', vencer_refuerzo: 'Refuerzo vencido: revisar pendientes', seleccionar_cola_armado: 'Cola de camiones actualizada', respuesta_control: 'Producto registrado', iniciar_control: 'Tarea iniciada', reanudar_proceso: 'Tarea reanudada', pausar_proceso: 'Tarea pausada', finalizar_control: 'Tarea finalizada', aprobar_planificacion: 'Carga aprobada', iniciar_planificacion: 'Planificación iniciada', asignar_canchas: 'Canchas asignadas', reasignar_canchas: 'Trabajo reasignado', registrar_activos: 'Activos registrados', liberacion_en_aplicacion: 'Camión liberado', faltante_approve: 'Faltante aprobado', faltante_adjusted: 'Ajuste confirmado', importar_planilla_control: 'Reparto incorporado', importacion_csv_autorizada: 'Maestro de artículos importado', editar_descripcion_voz: 'Descripción de voz actualizada' }

function ProcessCard({ entries, stage, group }) {
    const process = entries.find(item => !item.assistance) || entries[0]
    const helpers = entries.filter(item => item.assistance)
    const title = ['1 · Armado', '2 · Control 1', '3 · Control 2'][stage]
    if (!process) { const destinations = group.assemblyDestinations || []; return <article className="monitor-process-card border-slate-600 bg-slate-900"><div className="flex items-center justify-between gap-2"><h3 className="font-bold">{title}</h3><span className="rounded-md bg-black/20 px-2 py-1 text-xs">No requerido</span></div><p className="mt-3 text-lg font-semibold">No requiere picking propio</p><p className="mt-1 text-sm text-slate-300">{destinations.length ? `Sus productos se prepararon en ${destinations.map(item => `${item.pallet_id} por Cancha ${item.owner_court}`).join(', ')}.` : 'Esta cancha no tiene bultos ni unidades sueltas.'}</p><progress value="0" max="1" className="mt-auto h-2 w-full" /></article> }
    const displayStatus = process.status === 'pending' && process.available === false ? 'waiting' : process.status
    const candidates = process.responsible_candidates || []
    const responsibility = process.username ? `Responsable: ${process.username}` : candidates.length === 1 ? `Responsable previsto: ${candidates[0]}` : candidates.length ? `Disponibles: ${candidates.join(', ')}` : 'Sin responsable asignado'
    const equivalent = process.bultos_equiv == null ? '' : ` · ${Number(process.bultos_equiv).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} bultos equiv.`
    const pct = process.total ? Math.round(process.answered * 100 / process.total) : 0
    return <article className={`monitor-process-card ${colors[displayStatus]}`}><div className="flex items-center justify-between gap-2"><h3 className="font-bold">{title}</h3><span className="rounded-md bg-black/20 px-2 py-1 text-xs">{labels[displayStatus]}</span></div><div className="mt-2 flex items-end justify-between gap-2"><div><p className="text-sm font-bold">{responsibility}</p>{displayStatus === 'waiting' && <p className="text-xs text-slate-300">{process.blocked_reason}</p>}{helpers.length > 0 && <p className="text-xs text-sky-200">Refuerzo: {helpers.map(item => item.username || 'Por asignar').join(', ')}</p>}</div><b className="text-2xl">{pct}%</b></div><p className="mt-2 text-xs font-semibold text-slate-200">Carga: {process.bultos} bultos + {process.unidades} unidades{equivalent}</p><div className="mt-1 flex justify-between text-xs text-slate-300"><span>{process.answered}/{process.total} productos</span><span>{Math.floor(process.elapsed_seconds / 60)} min</span></div><progress value={process.answered} max={process.total || 1} aria-label={`Avance de ${process.username || 'cancha ' + group.court}`} className="mt-2 h-2 w-full accent-emerald-400" /><div className="mt-2 flex justify-between text-xs"><span>{process.shortages} faltantes</span>{process.timing?.needs_review && <span className="font-bold text-amber-200">Revisar tiempo</span>}{process.status === 'done' && process.answered < process.total && <span className="font-bold text-amber-200">Incompleto</span>}</div></article>
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
        const key = `${process.load_id}:${process.court}`
        if (!grouped.has(key)) grouped.set(key, { key, truck: process.truck, reparto: process.reparto, court: process.court, assemblyDestinations: process.assembly_destinations || [], stages: [[], [], []] })
        if (!grouped.get(key).assemblyDestinations.length && process.assembly_destinations?.length) grouped.get(key).assemblyDestinations = process.assembly_destinations
        grouped.get(key).stages[process.stage].push(process)
    })
    const groups = [...grouped.values()].sort((a, b) => (truckOrder.get(a.truck) ?? 999) - (truckOrder.get(b.truck) ?? 999) || String(a.truck).localeCompare(String(b.truck), 'es', { numeric: true }) || String(a.reparto).localeCompare(String(b.reparto), 'es', { numeric: true }) || a.court - b.court)
    const displayStatus = process => process.status === 'pending' && process.available === false ? 'waiting' : process.status
    const rows = groups.filter(group => filter === 'all' || group.stages.some(stage => stage.some(process => displayStatus(process) === filter)))

    return <div className="min-h-screen bg-slate-950 p-4 text-white sm:p-6">
        <header className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm uppercase tracking-widest text-slate-400">Del Palacio · Depósito</p><h1 className="text-2xl font-bold sm:text-3xl">Armado en vivo</h1></div><div className="flex flex-wrap items-center gap-3"><label className="text-sm">Fecha<input aria-label="Fecha del monitor" type="date" value={date} onChange={event => event.target.value && setDate(event.target.value)} className="ml-2 min-h-11 rounded-lg bg-slate-800 p-2 text-white" /></label><button className="min-h-11 rounded-lg border border-slate-600 px-4" onClick={() => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen().catch(() => setError('El navegador no permite pantalla completa.'))}>Pantalla completa</button><Link to="/supervision" className="p-3 underline">Supervisión</Link></div></header>
        <div role="status" className={`my-4 rounded-xl p-3 ${error ? 'bg-red-800' : 'bg-slate-900 text-slate-300'}`}>{error || `Actualización automática cada 5 segundos · Última lectura: ${last?.toLocaleTimeString('es-AR') || 'Cargando…'}`}</div>
        <div className="mb-5 grid grid-cols-2 gap-2 lg:grid-cols-5">{Object.entries(labels).map(([key, label]) => <button key={key} onClick={() => setFilter(filter === key ? 'all' : key)} aria-pressed={filter === key} className={`rounded-xl border-2 p-3 text-left ${colors[key]} ${filter === key ? 'ring-2 ring-white' : ''}`}><span>{label}</span><b className="ml-3 text-2xl">{processes.filter(process => [0, 1, 2].includes(process.stage) && displayStatus(process) === key).length}</b></button>)}</div>
        <section className="mb-5"><h2 className="mb-2 text-lg font-semibold">Cargas, aprobaciones y salida</h2><div className="grid gap-2 md:grid-cols-3">{data?.trucks?.map(truck => <article key={truck.id} className="rounded-xl border border-slate-700 bg-slate-900 p-3"><b>{truck.position ? `${truck.position}. ` : ''}{truck.truck} · {truck.branch}</b>{truck.summary && <p className="mt-1 text-sm text-slate-300">{truck.summary.loads} repartos · {truck.summary.bultos} bultos + {truck.summary.unidades} unidades · {truck.summary.pallets ?? 'Pendiente'} pallets / {truck.summary.capacity ?? 'Pendiente'} · {truck.summary.hl ?? 'Pendiente'} HL</p>}<p className="mt-1 text-sm">{truck.released ? 'Liberado' : truck.planning === 'approved' ? 'Armado aprobado' : truck.planning === 'legacy' ? 'Operación anterior en curso' : 'Espera aprobación del supervisor'}</p><p className="text-sm text-slate-300">Activos: {labels[truck.assets_status]}{truck.assets_username ? ` · ${truck.assets_username}` : ''}</p></article>)}</div></section>
        <section className="space-y-3">{rows.map(group => <article key={group.key} className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/70 p-3"><header className="mb-2 flex flex-wrap items-center justify-between gap-2"><h2 className="font-bold">Camión {group.truck} · Reparto {group.reparto}</h2><span className="rounded-full bg-slate-800 px-3 py-1 text-sm font-semibold">Cancha {group.court}</span></header><div className="grid min-w-[760px] grid-cols-3 gap-3">{[0, 1, 2].map(stage => <ProcessCard key={stage} entries={group.stages[stage]} stage={stage} group={group} />)}</div></article>)}</section>
        {data && !rows.length && <p className="rounded-xl bg-slate-900 p-6 text-xl">Sin tareas para esta fecha y estado.</p>}
        <section className="mt-6"><h2 className="mb-2 text-lg font-semibold">Últimas acciones del día</h2><div className="grid gap-2 md:grid-cols-2">{data?.events?.map(event => <div key={event.id} className="rounded-xl bg-slate-900 p-3 text-sm"><time className="mr-3 text-slate-400">{new Date(event.at).toLocaleTimeString('es-AR')}</time><b>{event.username || 'Sistema'}</b><span> · {actions[event.action] || 'Actividad registrada'}</span></div>)}</div></section>
        <section className="mt-6"><h2 className="mb-2 text-lg font-semibold">Sin proceso en curso en esta fecha</h2><div className="flex flex-wrap gap-2">{data?.operators.filter(user => !processes.some(process => process.user_id === user.id && process.status === 'running')).map(user => <div key={user.id} className="rounded-xl border border-slate-700 p-3 text-sm"><b>{user.username}</b><p className="text-slate-400">{user.courts.length ? `Canchas ${user.courts.join(', ')}` : 'Sin canchas asignadas'}</p></div>)}</div></section>
    </div>
}
