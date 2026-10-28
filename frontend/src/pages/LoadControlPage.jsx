import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { getStoredUser } from '../utils/auth'
import { stagesForRole } from '../utils/roleAccess'
import { matchesProcess, filterProcessGroups, processState } from '../utils/processFilter'
import { todayInputValue } from '../utils/format'
import { groupControlTrucks } from '../utils/controlTrucks'
import ControlTruckCard from '../components/ControlTruckCard'
import PalletPlanning from '../components/PalletPlanning'
import VoiceControl from '../components/VoiceControl'
import { speak } from '../voice/speech'

import { voicePrompt } from '../voice/productPrompt'
import FullPalletInfo from '../components/FullPalletInfo'
import DispatchBoard from '../components/DispatchBoard'
import TruckWorkSummary from '../components/TruckWorkSummary'

const base = '/load-control'
const stages = ['Picking', 'Control 1', 'Control 2', 'Activos', 'Pallets completos']
const button = 'min-h-12 touch-manipulation rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40'
const secondary = 'min-h-12 touch-manipulation rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-40'
const input = 'min-h-12 text-base w-full rounded-xl border border-slate-300 px-3 py-2 text-slate-900'
const card = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm'
const duration = value => { const s = Math.floor(value || 0); return `${Math.floor(s / 3600)}h ${Math.floor(s % 3600 / 60)}m ${s % 60}s` }
const localTime = value => value ? new Date(value).toLocaleString('es-AR') : '—'
const liveSeconds = check => (check.active_seconds || 0) + (check.timer_started_at ? Math.max(0, (Date.now() - new Date(check.timer_started_at).getTime()) / 1000) : 0)

export default function LoadControlPage({ pickingOnly = false, controlsOnly = false, palletsOnly = false, supervisorOnly = false, initialView = 'loads' }) {
    const user = getStoredUser()
    const palletizer = palletsOnly || user?.role === 'palletizador'
    const picker = palletizer || pickingOnly || user?.role === 'operador'
    const controller = controlsOnly || user?.role === 'controlador'
    const visibleStages = stagesForRole(palletizer ? 'palletizador' : picker ? 'operador' : controller ? 'controlador' : user?.role)
    const manager = !picker && !controller && ['administrador', 'supervisor'].includes(user?.role)
    const [trucks, setTrucks] = useState([])
    const [sources, setSources] = useState([])
    const [operators, setOperators] = useState([])
    const [types, setTypes] = useState([])
    const [load, setLoad] = useState(null)
    const [work, setWork] = useState(null)
    const [index, setIndex] = useState(0)
    const [mode, setMode] = useState('')
    const [error, setError] = useState('')
    const [message, setMessage] = useState('')
    const [busy, setBusy] = useState(false)
    const [loaded, setLoaded] = useState(false)
    const [view, setView] = useState(initialView)
    const [search, setSearch] = useState('')
    const [planningTruck, setPlanningTruck] = useState(null)
    const [dispatchRevision, setDispatchRevision] = useState(0)
    const [processFilter, setProcessFilter] = useState('all')
    const [date, setDate] = useState(todayInputValue())
    const [assetTruck, setAssetTruck] = useState(null)
    const [report, setReport] = useState(null)
    const [users, setUsers] = useState([])
    const [audit, setAudit] = useState(null)
    const [voiceQty, setVoiceQty] = useState({ b: '', u: '' })
    const [, tick] = useState(0)
    useEffect(() => { const timer = setInterval(() => tick(x => x + 1), 1000); return () => clearInterval(timer) }, [])

    async function refresh() {
        const [t, s, o, a] = await Promise.all(['trucks', 'sources', 'operators', 'asset-types'].map(p => api.get(`${base}/${p}`, { params: p === 'trucks' && !picker ? { date } : {} })))
        setTrucks(t.data); setSources(s.data); setOperators(o.data); setTypes(a.data); setLoaded(true)
    }
    async function act(fn) {
        if (busy) return
        setBusy(true); setError(''); setMessage('')
        try { await fn() } catch (err) { setError(err.response?.data?.error || 'No se pudo completar la operación. Revisá la conexión y reintentá.') }
        finally { setBusy(false) }
    }
    useEffect(() => { act(refresh) }, [date])
    useEffect(() => { if (work || busy || view !== 'loads') return; const timer = setInterval(() => refresh().catch(() => setError('No se pudo actualizar. Revisá la conexión.')), 10000); return () => clearInterval(timer) }, [!!work, busy, view, date])
    useEffect(() => { setVoiceQty({ b: '', u: '' }) }, [index, mode])
    async function openLoad(id) {
        const { data } = await api.get(`${base}/loads/${id}`)
        setLoad(data); setWork(null); setMode(''); setAudit(null)
    }
    async function activate(id) {
        const { data } = await api.post(`${base}/sources/${id}`)
        await refresh(); await openLoad(data.id)
    }
    async function begin(court, stage) {
        const { data } = await api.post(`${base}/loads/${load.id}/courts/${court.numero}/start/${stage}`)
        const effectiveCourt = [0, 4].includes(stage) && data.products ? { ...court, productos: data.products } : court
        setWork({ court: effectiveCourt, check: data }); setMode('')
        const next = effectiveCourt.productos.findIndex(p => !data.answers[p.sku]); setIndex(next < 0 ? 0 : next)
    }
    const workPath = work ? `${base}/loads/${load.id}/courts/${work.court.numero}/checks/${work.check.stage}/${work.check.id}` : ''
    async function sendAnswer(data) {
        const response = await api.post(`${workPath}/answer`, { sku: work.court.productos[index].sku, ...data })
        setWork({ ...work, check: response.data }); setMode('')
        if (index < work.court.productos.length - 1) setIndex(index + 1)
    }
    // Comandos de voz: "correcto" confirma, "faltante"/"error corregido" abren el formulario,
    // "bultos/unidades" completan el faltante. El envío final del faltante sigue siendo un toque.
    function handleVoice(cmd) {
        if (!work) return
        const total = work.court.productos.length
        const p = work.court.productos[index]
        if (cmd.action === 'ok') { if (!mode && work.check.timer_started_at) act(() => sendAnswer({ result: 'ok' })); return }
        if (cmd.action === 'shortage' && work.check.timer_started_at) { setMode('shortage'); return }
        if (cmd.action === 'corrected' && [1, 2].includes(work.check.stage) && work.check.timer_started_at) { setMode('corrected'); return }
        if (cmd.action === 'repeat') { speak(voicePrompt(p, index, total, work?.check?.stage)); return }
        if (cmd.action === 'next' && index < total - 1) { setIndex(index + 1); setMode(''); return }
        if (cmd.action === 'prev' && index > 0) { setIndex(index - 1); setMode(''); return }
        if (cmd.action === 'quantities' && mode === 'shortage') {
            setVoiceQty(q => ({ b: cmd.bultos ?? q.b, u: cmd.unidades ?? q.u }))
        }
    }
    async function finish() {
        await api.post(`${workPath}/finish`)
        if (picker) { setWork(null); setLoad(null); setMode(''); setProcessFilter('all'); setSearch(''); await refresh() }
        else { await refresh(); await openLoad(load.id) }
        setMessage('Proceso finalizado. Tiempo y responsable guardados.')
    }
    async function reopen(court) {
        const reason = window.prompt('Motivo de reapertura. Se reinician los dos controles y se invalidan los activos; el historial y los tiempos quedan guardados.')
        if (reason === null) return
        await api.post(`${base}/loads/${load.id}/courts/${court.numero}/reopen`, { reason })
        await refresh(); await openLoad(load.id)
    }
    async function go(viewName) {
        setLoad(null); setWork(null); setAssetTruck(null); setAudit(null); setView(viewName)
        if (viewName === 'performance') setReport((await api.get(`${base}/performance`)).data)
        if (viewName === 'users') setUsers((await api.get(`${base}/users`)).data)
        if (viewName === 'loads') await refresh()
    }
    const matches = (truck, reparto = '') => (picker || !date || truck.load_date === date) && `${truck.truck} ${reparto} ${truck.branch}`.toLowerCase().includes(search.toLowerCase())
    const allGroups = useMemo(() => groupControlTrucks(trucks, sources), [trucks, sources])
    const groupedTrucks = filterProcessGroups(allGroups, visibleStages, processFilter).filter(t => matches(t, [...t.loads, ...t.pending].map(l => l.reparto).join(' ')))
    const shortages = trucks.flatMap(t => t.status.shortages.map(s => ({ ...s, truck: t })))
    const selectedGroup = load && allGroups.find(t => t.loads.some(l => l.id === load.id))
    const nextLoad = selectedGroup?.loads.find(l => l.id !== load?.id && !l.canchas.every(c => c.status.done))
    const selectedTruck = load && trucks.find(t => t.loads.some(l => l.id === load.id))

    return <div className={`load-control mx-auto space-y-5 p-3 pb-24 sm:p-5 md:p-8 ${work ? "max-w-3xl" : "max-w-7xl"}`}>
        <header className={`flex flex-wrap items-start justify-between gap-4 ${work ? "hidden md:flex" : ""}`}>
            <div><p className="text-sm font-medium text-brand-600">Operación de depósito</p><h1 className="text-2xl font-bold">{{ loads: palletizer ? 'Pallets completos' : picker ? "Picking" : controller ? "Controles y activos" : "Camiones y controles", shortages: "Supervisión de faltantes", performance: "Tiempos y errores", users: "Administración de usuarios" }[view]}</h1><p className="mt-1 text-sm text-slate-500">{picker ? 'Terminá tus canchas de todos los repartos del camión actual. Después aparece el siguiente.' : 'Doble control por cancha y activos de salida.'}</p></div>
            <button className={secondary} disabled={busy} onClick={() => act(() => go(view))}>Actualizar</button>
        </header>
        {supervisorOnly && <nav className="flex flex-wrap gap-3" aria-label="Supervisión"><Link className={secondary} to="/supervision">Seguimiento</Link><Link className={secondary} to="/supervision/cargas">Planificar cargas</Link><Link className={secondary} to="/supervision/faltantes">Faltantes y autorizaciones</Link></nav>}
        {!supervisorOnly && manager && <nav className={`grid gap-3 ${manager ? "grid-cols-2 lg:grid-cols-4" : "grid-cols-1"} ${work ? "hidden" : ""}`} aria-label="Secciones de control de cargas">
            {[['loads', 'Control operativo', 'Camiones y cargas'], ...(manager ? [['shortages', 'Supervisión', 'Faltantes y autorizaciones'], ['performance', 'Rendimiento', 'Tiempos y errores'], ...(user?.role === 'administrador' ? [['users', 'Administración', 'Usuarios y roles']] : [])] : [])].map(([key, label, description]) => <button key={key} disabled={busy} aria-current={view === key ? "page" : undefined} className={`${view === key ? button : secondary} text-left p-4`} onClick={() => act(() => go(key))}><span className="block font-semibold">{label}</span><span className="mt-1 block text-xs opacity-80">{description}</span></button>)}
        </nav>}
        {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}
        {message && <div role="status" className="rounded-xl bg-emerald-50 p-4 text-emerald-800">{message}</div>}
        {busy && <p role="status" className="text-sm text-slate-500">Procesando…</p>}
        <fieldset disabled={busy} className="min-w-0 space-y-5 disabled:opacity-75">
        {manager && planningTruck && <PalletPlanning key={planningTruck.id} truck={planningTruck} onClose={() => { setPlanningTruck(null); setDispatchRevision(n => n + 1); act(refresh) }} />}
        {picker && load && !work && <TruckWorkSummary summary={load.truck_summary} />}
        {view === 'loads' && !work && <label className="block max-w-sm text-sm">Estado del proceso
            <select className={input} value={processFilter} onChange={e => setProcessFilter(e.target.value)}>
                <option value="all">Todos</option><option value="running">En curso</option>
                <option value="not_started">Sin iniciar</option><option value="paused">Pausados</option><option value="done">Finalizados</option>
            </select>
        </label>}
        {view === 'loads' && !load && !assetTruck && <>
            <div className="flex flex-wrap gap-3"><label className="min-w-48 flex-1 text-sm">Buscar camión o reparto<input className={input} value={search} onChange={e => setSearch(e.target.value)} placeholder="Patente, reparto o depósito" /></label>{!picker && <label className="text-sm">Fecha de reparto<input type="date" className={input} value={date} onChange={e => setDate(e.target.value)} /></label>}</div>
        {manager && view === 'loads' && !load && <DispatchBoard key={`${date}:${dispatchRevision}`} date={date} onSaved={refresh} onPlan={setPlanningTruck} />}
            {!picker && <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[
                ['Camiones', groupedTrucks.length],
                ['Cargas del filtro', groupedTrucks.reduce((n, t) => n + t.total, 0)],
                ['Cargas controladas', groupedTrucks.reduce((n, t) => n + t.completed, 0)],
                ['Camiones liberados', groupedTrucks.filter(t => t.released).length],
            ].map(([label, value]) => <div className="rounded-2xl border border-slate-200 bg-white p-4" key={label}><p className="text-sm text-slate-500">{label}</p><p className="mt-1 text-3xl font-bold">{value}</p></div>)}</div>}
            <div className="flex flex-wrap items-center justify-between gap-3"><p className="max-w-2xl text-sm text-slate-600">{picker ? 'Abrí una carga para preparar sus productos por cancha, con voz o con botones.' : 'Cada carga se controla por separado. El camión queda liberado al completar todas sus cargas, los activos y las autorizaciones de faltantes.'}</p>{!picker && <div className="flex gap-2"><button className={secondary} onClick={() => setDate(todayInputValue())}>Hoy</button><button className={secondary} onClick={() => { setDate(''); setSearch('') }}>Ver todas las fechas</button></div>}</div>
            <div className="grid items-start gap-5 xl:grid-cols-2">{groupedTrucks.map(t => <ControlTruckCard key={t.key} truck={t} manager={manager} pickingOnly={picker}
                onOpen={id => act(() => openLoad(id))} onActivate={id => act(() => activate(id))} onPlan={() => { setPlanningTruck(t); window.scrollTo({ top: 0, behavior: 'smooth' }) }}
                onAssets={() => act(async () => { const { data } = await api.post(`${base}/trucks/${t.id}/assets/start`); setAssetTruck({ ...t, check: data }) })}
                onAudit={() => act(async () => setAudit({ truck: t.truck, rows: (await api.get(`${base}/trucks/${t.id}/audit`)).data }))} />)}</div>
            {loaded && !groupedTrucks.length && <section className={`${card} text-center`}><h2 className="font-semibold">No hay camiones para este filtro</h2><p className="mt-2 text-sm text-slate-500">Probá otra fecha o consultá los PDFs ya importados.</p>{manager && <Link className="mt-4 inline-block min-h-12 py-3 font-semibold text-brand-600" to="/upload">Ir a Carga PDF</Link>}</section>}
            {audit && <section className={card}><div className="flex justify-between"><h2 className="font-semibold">Trazabilidad · {audit.truck}</h2><button className={secondary} onClick={() => setAudit(null)}>Cerrar</button></div><div className="mt-4 max-h-96 overflow-auto">{audit.rows.map(r => <details key={r.id} className="border-t py-2 text-sm"><summary>{localTime(r.at + 'Z')} · {r.username} · {r.action.replaceAll('_', ' ')}</summary><pre className="overflow-auto whitespace-pre-wrap p-2 text-xs">{JSON.stringify(r.details, null, 2)}</pre></details>)}</div></section>}
        </>}
        {view === 'loads' && load && !work && <>
            <button className={secondary} onClick={() => { setLoad(null); setWork(null) }}>← Camiones</button>
            {!picker && selectedGroup && <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-brand-100 bg-brand-50 p-4"><p className="text-sm"><b>Camión {selectedGroup.truck}</b> · {selectedGroup.completed} de {selectedGroup.total} cargas controladas</p>{load.canchas.every(c => c.status.done) && (nextLoad || selectedGroup.pending.length > 0) && <button className={button} onClick={() => act(() => nextLoad ? openLoad(nextLoad.id) : activate(selectedGroup.pending[0].id))}>Continuar con la siguiente carga</button>}</div>}
            <section className={card}><h2 className="text-lg font-semibold">Reparto {load.reparto} · {load.camion}</h2><p className="text-sm text-slate-500">{load.fecha} · {load.chofer} · {load.deposito}</p><p className="mt-3 text-sm">{picker ? 'Seleccioná una cancha para iniciar o retomar el picking.' : 'Seleccioná una cancha. Cada proceso registra su operador y tiempo activo.'}</p></section>
            <div className="grid gap-4 md:grid-cols-2">{load.canchas.filter(c => matchesProcess(c, visibleStages, processFilter)).map(c => <section key={c.numero} className={card}>
                {picker && <FullPalletInfo items={c.full_pallets_info} />}
                {picker && !c.productos.length && c.full_pallet_count > 0 && <p className="mb-3 text-sm">Esta cancha solo tiene pallets completos; no requiere picking de sueltos.</p>}
                <h3 className="text-lg font-semibold">Cancha {c.numero}</h3><p className="mb-3 text-sm text-slate-500">{c.productos.length} productos · {picker ? (c.status.checks.some(ch => ch.stage === 0 && ch.status === 'done') ? 'Picking finalizado' : 'Picking pendiente') : c.status.done ? 'Doble control completo' : 'Pendiente'}</p>
                {stages.map((label, stage) => { if (!visibleStages.includes(stage) || (processFilter !== 'all' && processState(c.status.checks.find(ch => ch.stage === stage)) !== processFilter)) return null; const check = c.status.checks.find(ch => ch.stage === stage); const first = c.status.checks.find(ch => ch.stage === 1); const pick = c.status.checks.find(ch => ch.stage === 0); const available = [0, 4].includes(stage) ? !first && (!picker || c.productos.length > 0) : stage === 1 ? pick?.status !== 'active' && c.status.checks.find(ch => ch.stage === 4)?.status !== 'active' : first?.status === 'done' && first.user_id !== user.id; return <div className="mb-3 rounded-xl bg-slate-50 p-3" key={stage}><div className="flex flex-wrap items-center justify-between gap-2"><b className="text-sm">{label}</b>{check ? <span className="text-xs text-slate-500">{check.username} · {check.status === 'done' ? 'Finalizado' : check.timer_started_at ? 'En curso' : 'Pausado'} · {duration(liveSeconds(check))}</span> : <span className="text-xs text-slate-500">Sin iniciar</span>}</div>{!selectedTruck?.status.released_at && available && (!check || (check.status === 'active' && (check.user_id == null || check.user_id === user.id))) && <button className={`${secondary} mt-2`} onClick={() => act(() => begin(c, stage))}>{check ? 'Retomar' : 'Iniciar'} {label.toLowerCase()}</button>}{stage === 2 && first?.user_id === user.id && <p className="mt-1 text-xs text-slate-500">Debe realizarlo otra persona.</p>}</div> })}
                {manager && !selectedTruck?.status.released_at && c.status.checks.length > 0 && <button className={secondary} onClick={() => act(() => reopen(c))}>Reabrir / liberar reserva</button>}
            </section>)}</div>
        </>}
        {view === 'loads' && work && <>
            <button className={secondary} onClick={() => act(async () => { if (work.check.timer_started_at) await api.post(`${workPath}/pause`); await refresh(); await openLoad(load.id) })}>← Pausar y volver a canchas</button>
            <section className={`${card} sticky top-2 z-10 ring-1 ring-slate-100`}><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-lg font-semibold">{stages[work.check.stage]} · Cancha {work.court.numero}</h2><p className="text-sm text-slate-500">Reparto {load.reparto} · {work.check.username}</p></div><div className="text-right"><p className="font-mono text-xl">{duration(liveSeconds(work.check))}</p><p className="text-xs text-slate-500">{work.check.timer_started_at ? 'Tiempo activo' : 'Pausado'}</p></div></div><button className={`${secondary} mt-3`} onClick={() => act(async () => { if (work.check.timer_started_at) { const r = await api.post(`${workPath}/pause`); setWork({ ...work, check: r.data }) } else await begin(work.court, work.check.stage) })}>{work.check.timer_started_at ? 'Pausar tiempo' : 'Reanudar proceso'}</button></section>
            {(() => {
                const p = work.court.productos[index], confirmation = work.check.stage === 2 && mode === 'shortage' && work.court.status.shortages.some(s => s.sku === p.sku), done = Object.keys(work.check.answers).length, total = work.court.productos.length, saved = work.check.answers[p.sku]
                return <><section className={card}><div className="flex justify-between text-sm text-slate-500"><span>Producto {index + 1}/{total}</span><span>{done}/{total} registrados</span></div><progress className="my-3 w-full accent-emerald-600" value={done} max={total} aria-label="Productos controlados" /><div className="mb-3"><VoiceControl prompt={voicePrompt(p, index, total, work?.check?.stage)} onCommand={handleVoice} /></div>{p.pallets > 0 && <p className="text-2xl font-bold">Prepará {p.pallets} pallets completos</p>}<p className="text-sm text-slate-500">SKU {p.sku} · {p.almacen}</p><h3 className="my-2 text-xl font-semibold">{p.descripcion}</h3><div className="my-4 grid grid-cols-2 gap-3">{[['Bultos', p.bultos], ['Unidades', p.unidades]].map(([label, value]) => <div key={label} className="rounded-xl bg-slate-100 p-4 text-center"><p className="text-xs uppercase text-slate-500">{label} de la planilla</p><b className="text-4xl sm:text-5xl">{value}</b></div>)}</div>{work.check.stage === 0 && p.full_pallets_count > 0 && <FullPalletInfo items={[{ sku: p.sku, descripcion: p.descripcion, pallets: p.full_pallets_count, bultos: p.full_pallets_bultos }]} />}{saved && <p className="mb-3 rounded-xl bg-emerald-50 p-2 text-sm text-emerald-800">Guardado: {{ ok: 'Correcto', corrected: 'Error corregido', shortage: 'Faltante' }[saved.result]}</p>}
                    {!mode ? <div className="grid grid-cols-1 gap-3 sm:grid-cols-3"><button disabled={!work.check.timer_started_at} className={`${button} min-h-16 bg-emerald-600 text-base`} onClick={() => act(() => sendAnswer({ result: 'ok' }))}>Correcto →</button>{[1, 2].includes(work.check.stage) && <button disabled={!work.check.timer_started_at} className={`${secondary} min-h-16 border-amber-300 bg-amber-50 text-amber-900`} onClick={() => setMode('corrected')}>Error corregido</button>}<button disabled={!work.check.timer_started_at} className={`${secondary} min-h-16 border-red-200 bg-red-50 text-red-800`} onClick={() => setMode('shortage')}>Faltante real</button></div> : <form key={`${p.sku}-${mode}`} className="space-y-3" onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); act(() => sendAnswer({ result: mode, note: f.get('note'), physical_b: Number(f.get('b')), physical_u: Number(f.get('u')), responsible_user_id: Number(f.get('responsible')), origin: f.get('origin') })) }}>
                        <h4 className="font-semibold">{mode === 'shortage' ? 'Registrar faltante' : 'Registrar error corregido'}</h4>
                        {mode === 'shortage' && <div className="grid grid-cols-2 gap-3"><label className="text-sm">Bultos físicos<input name="b" className={input} inputMode="numeric" type="number" min="0" max={p.bultos} step="1" required value={voiceQty.b} onChange={e => setVoiceQty(q => ({ ...q, b: e.target.value }))} /></label><label className="text-sm">Unidades físicas<input name="u" className={input} inputMode="numeric" type="number" min="0" max={p.unidades} step="1" required value={voiceQty.u} onChange={e => setVoiceQty(q => ({ ...q, u: e.target.value }))} /></label></div>}
                        {!confirmation && [1, 2].includes(work.check.stage) && <div className="grid gap-3 md:grid-cols-2"><label className="text-sm">Proceso al que corresponde<select className={input} name="origin" required defaultValue=""><option value="" disabled>Seleccionar proceso</option><option value="picking">Picking</option><option value="control">Control</option></select></label><label className="text-sm">Responsable del error<select className={input} name="responsible" required defaultValue=""><option value="" disabled>Seleccionar persona</option>{operators.map(o => <option key={o.id} value={o.id}>{o.username} · {o.role}</option>)}</select></label></div>}{confirmation && <p className="text-sm text-slate-500">Confirmación del faltante del primer control: se mantiene el responsable registrado y no se cuenta como un nuevo error.</p>}<p className="text-xs text-slate-500">Detectado por: {user.username}. El responsable indicado queda registrado por separado.</p>
                        <label className="block text-sm">Observación<textarea className={input} name="note" required={mode === 'corrected'} maxLength={2000} /></label><button disabled={!work.check.timer_started_at} className={button}>Guardar y continuar</button> <button type="button" className={secondary} onClick={() => setMode('')}>Cancelar</button>
                    </form>}
                    <div className="mt-5 flex justify-between"><button className={secondary} disabled={index === 0} onClick={() => { setIndex(index - 1); setMode('') }}>← Anterior</button><button className={secondary} disabled={index === total - 1} onClick={() => { setIndex(index + 1); setMode('') }}>Siguiente →</button></div></section><section className={card}><details><summary className="mb-3 min-h-12 cursor-pointer py-3 font-medium">Ver avance de todos los productos</summary><div className="mb-4 flex flex-wrap gap-2">{work.court.productos.map((product, i) => <button key={product.sku} aria-label={`Producto ${i + 1}: ${product.descripcion}`} className={work.check.answers[product.sku] ? button : secondary} onClick={() => { setIndex(i); setMode('') }}>{i + 1}</button>)}</div></details><button className={`${button} w-full min-h-14`} disabled={[1, 2].includes(work.check.stage) && done !== total} onClick={() => act(finish)}>Finalizar {stages[work.check.stage].toLowerCase()}</button></section></>
            })()}
        </>}
        {assetTruck && <section className={card}><button className={secondary} onClick={() => setAssetTruck(null)}>← Camiones</button><h2 className="my-4 text-lg font-semibold">Activos de salida · {assetTruck.truck}</h2><p className="mb-4 text-sm text-slate-500">Contá los activos físicos. Completá todos los campos, incluido cero.</p><form className="space-y-4" onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); act(async () => { await api.post(`${base}/trucks/${assetTruck.id}/assets`, { quantities: Object.fromEntries(types.map(t => [t, Number(f.get(t))])) }); setAssetTruck(null); await refresh(); setMessage('Activos registrados. El camión se libera en la aplicación cuando todos los faltantes están autorizados.') }) }}><div className="grid gap-3 sm:grid-cols-2">{types.map(t => <label key={t} className="text-sm">{t}<input className={input} name={t} required inputMode="numeric" type="number" min="0" step="1" /></label>)}</div><button className={button}>Confirmar activos</button></form></section>}
        {view === 'shortages' && <><p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">Autorizar un faltante permite la salida con menos mercadería. El ajuste en Chess es manual y se confirma por separado.</p>{!shortages.length && <p className={card}>No hay faltantes registrados.</p>}{shortages.map(s => <section key={`${s.load_id}-${s.court}-${s.sku}`} className={card}><h2 className="font-semibold">Camión {s.truck.truck} · Reparto {s.reparto} · Cancha {s.court}</h2><p className="my-2">{s.sku} · {s.descripcion}</p><p className="text-sm">Planilla: {s.expected_b} bultos + {s.expected_u} unidades. Viajan: <b>{s.actual_b} bultos + {s.actual_u} unidades.</b></p><p className="my-2 text-sm text-slate-500">{s.note} · Responsable: {s.incident?.responsible_username || '—'} ({s.incident?.origin})</p><button className={s.adjusted_by ? secondary : button} disabled={Boolean(s.adjusted_by)} onClick={() => act(async () => { await api.post(`${base}/loads/${s.load_id}/courts/${s.court}/shortages/${encodeURIComponent(s.sku)}/${s.approved_by ? 'adjusted' : 'approve'}`); await refresh() })}>{s.adjusted_by ? 'Ajuste Chess confirmado' : s.approved_by ? 'Confirmar ajuste manual en Chess' : 'Autorizar salida con faltante'}</button></section>)}</>}
        {view === 'performance' && report && <Performance report={report} operators={operators} />}
        {view === 'users' && <><section className={card}><h2 className="mb-3 font-semibold">Usuarios de Picking</h2><p className="mb-3 text-sm text-slate-500">Son las mismas cuentas para toda la aplicación. Cada empleado debe usar su propio usuario para registrar tiempos y controles.</p>{users.map(u => <p key={u.id} className="border-t py-2 text-sm">{u.username} · {u.role} · {u.active ? 'Activo' : 'Inactivo'}</p>)}</section>{user.role === 'administrador' && <form className={`${card} space-y-3`} onSubmit={e => { e.preventDefault(); const form = e.currentTarget; const data = Object.fromEntries(new FormData(form)); act(async () => { await api.post('/auth/register', data); form.reset(); await refresh(); setUsers((await api.get(`${base}/users`)).data); setMessage('Usuario creado.') }) }}><h2 className="font-semibold">Crear usuario</h2><div className="grid gap-3 sm:grid-cols-2"><label className="text-sm">Usuario<input name="username" className={input} maxLength={128} required /></label><label className="text-sm">Email<input name="email" type="email" className={input} required /></label><label className="text-sm">Contraseña<input name="password" type="password" autoComplete="new-password" minLength={10} className={input} required /></label><label className="text-sm">Rol<select name="role" className={input} defaultValue="controlador"><option value="controlador">Controlador</option><option value="operador">Operador / pickeador</option><option value="supervisor">Supervisor</option><option value="administrador">Administrador</option></select></label></div><button className={button}>Crear usuario</button></form>}</>}
        </fieldset>
    </div>
}

function Performance({ report, operators }) {
    const [person, setPerson] = useState('')
    const [date, setDate] = useState('')
    const processes = report.processes.filter(p => (!person || p.user_id === Number(person)) && (!date || p.date === date))
    const incidents = report.incidents.filter(i => (!person || i.incident.responsible_user_id === Number(person)) && (!date || i.date === date))
    const people = [...new Set([...processes.map(p => p.user_id), ...incidents.map(i => i.incident.responsible_user_id)])]
    return <><div className="flex flex-wrap gap-3"><label className="text-sm">Usuario<select className={input} value={person} onChange={e => setPerson(e.target.value)}><option value="">Todos</option>{operators.map(o => <option key={o.id} value={o.id}>{o.username}</option>)}</select></label><label className="text-sm">Fecha de reparto<input className={input} type="date" value={date} onChange={e => setDate(e.target.value)} /></label></div>
        <p className="text-sm text-slate-500">El tiempo activo excluye las pausas explícitas. Si se cierra el navegador sin pausar, el proceso sigue en curso. Las reaperturas conservan el tiempo consumido.</p>
        <section className={`${card} overflow-x-auto`}><h2 className="mb-3 font-semibold">Resumen por usuario</h2><table className="w-full text-left text-sm"><thead><tr>{['Usuario', 'Picking', 'Control 1', 'Control 2', 'Activos', 'Incidencias asignadas'].map(h => <th className="p-2" key={h}>{h}</th>)}</tr></thead><tbody>{people.map(id => <tr key={id} className="border-t"><td className="p-2">{operators.find(o => o.id === id)?.username || processes.find(p => p.user_id === id)?.username || incidents.find(i => i.incident.responsible_user_id === id)?.incident.responsible_username}</td>{[0, 1, 2, 3].map(stage => <td key={stage} className="whitespace-nowrap p-2">{duration(processes.filter(p => p.user_id === id && p.stage === stage).reduce((sum, p) => sum + liveSeconds(p), 0))}</td>)}<td className="p-2">{incidents.filter(i => i.incident.responsible_user_id === id).length}</td></tr>)}</tbody></table>{!people.length && <p className="p-3 text-slate-500">Todavía no hay procesos registrados para este filtro.</p>}</section>
        <section className={`${card} overflow-x-auto`}><h2 className="mb-3 font-semibold">Procesos y tiempos</h2><table className="w-full text-left text-sm"><thead><tr>{['Usuario', 'Proceso', 'Camión / cancha', 'Inicio', 'Fin', 'Tiempo activo', 'Estado'].map(h => <th className="p-2" key={h}>{h}</th>)}</tr></thead><tbody>{processes.map(p => <tr key={p.id} className="border-t"><td className="p-2">{p.username}</td><td className="p-2">{stages[p.stage]}</td><td className="p-2">{p.truck} / {p.court}</td><td className="p-2">{localTime(p.started_at)}</td><td className="p-2">{localTime(p.finished_at)}</td><td className="whitespace-nowrap p-2">{duration(liveSeconds(p))}</td><td className="p-2">{p.status === 'done' ? 'Finalizado' : p.status === 'reopened' ? 'Reabierto' : p.timer_started_at ? 'En curso' : 'Pausado'}</td></tr>)}</tbody></table></section>
        <section className={card}><h2 className="mb-3 font-semibold">Errores y responsables</h2>{!incidents.length && <p className="text-sm text-slate-500">Sin incidencias registradas para este filtro.</p>}{incidents.map((i, n) => <div key={n} className="border-t py-3 text-sm"><b>SKU {i.sku} · {i.truck} · Cancha {i.court}</b><p>{i.result === 'shortage' ? 'Faltante' : 'Error corregido'} · Proceso responsable: {i.incident.origin} · <strong>{i.incident.responsible_username}</strong></p><p className="text-slate-500">Detectado por {i.incident.detected_username} en {stages[i.stage]} · {localTime(i.saved_at)}{i.process_status === 'reopened' ? ' · Control reabierto' : ''}</p><p>{i.note}</p></div>)}</section>
    </>
}
