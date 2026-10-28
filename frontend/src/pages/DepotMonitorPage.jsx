import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { todayInputValue } from '../utils/format'

const stages = ['Picking', 'Control 1', 'Control 2', 'Activos', 'Pallets completos']
const labels = { running: 'En curso', paused: 'Pausado', done: 'Finalizado', pending: 'Sin iniciar' }
const colors = { running: 'border-emerald-500 bg-emerald-950', paused: 'border-amber-400 bg-amber-950', done: 'border-sky-500 bg-sky-950', pending: 'border-slate-600 bg-slate-900' }
const actions = { seleccionar_cola_armado: 'Cola de camiones actualizada', respuesta_control: 'Producto registrado', iniciar_control: 'Tarea iniciada', reanudar_proceso: 'Tarea reanudada', pausar_proceso: 'Tarea pausada', finalizar_control: 'Tarea finalizada', aprobar_planificacion: 'Carga aprobada', iniciar_planificacion: 'Planificación iniciada', asignar_canchas: 'Canchas asignadas', reasignar_canchas: 'Trabajo reasignado', registrar_activos: 'Activos registrados', liberacion_en_aplicacion: 'Camión liberado', faltante_approve: 'Faltante aprobado', faltante_adjusted: 'Ajuste confirmado', importar_planilla_control: 'Reparto incorporado', importacion_csv_autorizada: 'Maestro de artículos importado', editar_descripcion_voz: 'Descripción de voz actualizada' }

export default function DepotMonitorPage() {
    const [date, setDate] = useState(todayInputValue()), [data, setData] = useState(null)
    const [error, setError] = useState(''), [last, setLast] = useState(null), [filter, setFilter] = useState('all')
    useEffect(() => {
        let active = true, timer, controller
        setData(null); setLast(null)
        async function refresh() {
            controller = new AbortController()
            try {
                const response = await api.get('/load-control/monitor', { params: { date }, signal: controller.signal, timeout: 12000 })
                if (active) { setData(response.data); setLast(new Date()); setError('') }
            } catch (e) { if (active) setError('SIN CONEXIÓN · Los datos pueden estar desactualizados') }
            finally { if (active) timer = setTimeout(refresh, 5000) }
        }
        refresh()
        return () => { active = false; clearTimeout(timer); controller?.abort() }
    }, [date])
    const processes = data?.processes || []
    const rows = processes.filter(p => filter === 'all' || p.status === filter)
    return <div className="min-h-screen bg-slate-950 p-4 text-white sm:p-8">
        <header className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm uppercase tracking-widest text-slate-400">Del Palacio · Depósito</p><h1 className="text-2xl font-bold sm:text-4xl">Armado en vivo</h1></div><div className="flex flex-wrap items-center gap-3"><label className="text-sm">Fecha<input aria-label="Fecha del monitor" type="date" value={date} onChange={e => e.target.value && setDate(e.target.value)} className="ml-2 min-h-12 rounded-lg bg-slate-800 p-2 text-white" /></label><button className="min-h-12 rounded-lg border border-slate-600 px-4" onClick={() => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen().catch(() => setError('El navegador no permite pantalla completa.'))}>Pantalla completa</button><Link to="/supervision" className="p-3 underline">Supervisión</Link></div></header>
        <div role="status" className={`my-5 rounded-xl p-3 ${error ? 'bg-red-800' : 'bg-slate-900 text-slate-300'}`}>{error || `Actualización automática cada 5 segundos · Última lectura: ${last?.toLocaleTimeString('es-AR') || 'Cargando…'}`}</div>
        <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">{Object.entries(labels).map(([key, label]) => <button key={key} onClick={() => setFilter(filter === key ? 'all' : key)} aria-pressed={filter === key} className={`rounded-xl border-2 p-4 text-left ${colors[key]} ${filter === key ? 'ring-2 ring-white' : ''}`}><p>{label}</p><b className="text-4xl">{processes.filter(p => p.status === key).length}</b></button>)}</div>
        <section className="mb-6"><h2 className="mb-3 text-xl font-semibold">Cargas, aprobaciones y salida</h2><div className="grid gap-3 md:grid-cols-3">{data?.trucks?.map(t => <article key={t.id} className="rounded-xl border border-slate-700 bg-slate-900 p-4"><b>{t.position ? `${t.position}. ` : ""}{t.truck} · {t.branch}</b>{t.summary && <p className="mt-2 text-slate-300">{t.summary.loads} repartos · {t.summary.bultos} bultos + {t.summary.unidades} unidades · {t.summary.pallets ?? "Pendiente"} pallets / {t.summary.capacity ?? "Pendiente"} · {t.summary.hl ?? "Pendiente"} HL</p>}<p className="mt-2">{t.released ? 'Liberado' : t.planning === 'approved' ? 'Armado aprobado' : t.planning === 'legacy' ? 'Operación anterior en curso' : 'Espera aprobación del supervisor'}</p><p className="text-slate-300">Activos: {labels[t.assets_status]}{t.assets_username ? ` · ${t.assets_username}` : ''}</p></article>)}</div></section>
        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">{rows.map(p => <article key={p.id} className={`rounded-2xl border-l-8 p-5 ${colors[p.status]}`}><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-2xl font-bold">{p.username || 'Por asignar'}</h2><span className="rounded-lg bg-black/20 px-3 py-2">{labels[p.status]}</span></div><p className="mt-3 text-xl">Cancha {p.court} · {stages[p.stage]}</p><p className="mt-1 text-slate-300">Camión {p.truck} · Reparto {p.reparto}</p><div className="my-4 flex items-end justify-between gap-3"><b className="text-4xl">{p.total ? Math.round(p.answered * 100 / p.total) : 0}%</b><span>{p.answered} / {p.total} productos</span></div><progress value={p.answered} max={p.total || 1} aria-label={`Avance de ${p.username || 'cancha '+p.court}`} className="h-4 w-full accent-emerald-400" /><div className="mt-3 flex justify-between"><span>{Math.floor(p.elapsed_seconds / 60)} min activos</span><span>{p.shortages} faltantes</span></div>{p.status === 'done' && p.answered < p.total && <p className="mt-3 font-bold text-amber-200">Finalizado con productos sin registrar</p>}{p.planning === 'pending' && <p className="mt-3 text-amber-200">Pendiente de aprobación</p>}</article>)}</div>
        {data && !rows.length && <p className="rounded-xl bg-slate-900 p-6 text-xl">Sin tareas para esta fecha y estado.</p>}
        <section className="mt-8"><h2 className="mb-3 text-xl font-semibold">Últimas acciones del día</h2><div className="grid gap-2 md:grid-cols-2">{data?.events?.map(e => <div key={e.id} className="rounded-xl bg-slate-900 p-3"><time className="mr-3 text-slate-400">{new Date(e.at).toLocaleTimeString('es-AR')}</time><b>{e.username || 'Sistema'}</b><span> · {actions[e.action] || 'Actividad registrada'}</span></div>)}</div></section>
        <section className="mt-8"><h2 className="mb-3 text-xl font-semibold">Sin proceso en curso en esta fecha</h2><div className="flex flex-wrap gap-3">{data?.operators.filter(u => !processes.some(p => p.user_id === u.id && p.status === 'running')).map(u => <div key={u.id} className="rounded-xl border border-slate-700 p-4"><b>{u.username}</b><p className="text-slate-400">{u.courts.length ? `Canchas ${u.courts.join(', ')}` : 'Sin canchas asignadas'}</p></div>)}</div></section>
    </div>
}
