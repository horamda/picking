import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { todayInputValue } from '../utils/format'
import { getStoredUser } from '../utils/auth'
import WeeklyStaffing from '../components/WeeklyStaffing'
import DailyAssistance from '../components/DailyAssistance'
import Personnel from '../components/Personnel'

const field = 'mt-1 min-h-12 w-full rounded-xl border border-slate-300 bg-white p-3'
const button = 'min-h-12 rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white disabled:opacity-50'
const card = 'rounded-2xl border border-slate-200 bg-white p-5'
const roles = { operador: 'Pickeador', palletizador: 'Pallets completos', controlador: 'Controlador', supervisor: 'Supervisor', administrador: 'Administrador' }
const courts = text => text.trim() ? text.split(',').map(s => Number(s.trim())) : []
const emptyPlanningConfig = { branch: '', truck: '', capacity: '', mix_courts_default: false,
    pallet_base_height_cm: '', reference_pallet_height_cm: '', max_pallet_height_cm: '',
    empty_pallet_weight_kg: '', max_pallet_weight_kg: '', safety_margin_pct: '',
    height_excess_mode: 'inform', pallet_weight_excess_mode: 'inform', truck_weight_excess_mode: 'inform',
    share_floor_remainders: false, weight_tiebreaker: false, max_payload_kg: '', max_height_cm: '' }
const optionalNumber = value => value === '' || value == null ? null : Number(value)

function AlertsPanel({ alerts, busy, act }) {
    const [status, setStatus] = useState('activas')
    const visible = alerts.filter(alert => status === 'todas'
        || (status === 'activas' ? ['abierta', 'reconocida'].includes(alert.status) : alert.status === status))
    const transition = (alert, action) => {
        let reason = ''
        if (action !== 'acknowledge') {
            reason = window.prompt(action === 'resolve' ? '¿Cómo se resolvió la alerta?'
                : action === 'dismiss' ? '¿Por qué se descarta la alerta?'
                    : 'Motivo de reapertura')
            if (reason === null) return
        }
        act(() => api.post(`/load-control/trucks/${alert.truck_id}/alerts/${encodeURIComponent(alert.key)}/${action}`, { reason }))
    }
    return <section className={card}>
        <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-lg font-bold">Alertas operativas</h2><p className="mt-1 text-sm text-slate-500">Una alerta por entidad y tipo. Resolver o descartar exige motivo y conserva historial.</p></div><label className="text-sm">Estado<select className={field} value={status} onChange={event => setStatus(event.target.value)}><option value="activas">Activas</option><option value="resuelta">Resueltas</option><option value="descartada">Descartadas</option><option value="todas">Todas</option></select></label></div>
        <div className="mt-4 grid gap-3">{visible.map(alert => <article key={`${alert.truck_id}:${alert.key}`} className="tile rounded-xl p-4"><div className="flex flex-wrap justify-between gap-2"><div><p className={`badge ${alert.severity === 'alta' ? 'badge--danger' : 'badge--warning'} capitalize`}>{alert.severity} · {alert.status.replaceAll('_', ' ')}</p><h3 className="mt-2 font-semibold">{alert.title}</h3></div><p className="text-sm font-medium">Camión {alert.truck}{alert.reparto ? ` · ${alert.reparto}` : ''}</p></div><p className="mt-2 text-sm text-slate-700">{alert.detail}</p>{alert.review_status && <p className="mt-1 text-xs text-slate-500">Revisión del faltante: {alert.review_status.replaceAll('_', ' ')}</p>}<div className="mt-3 flex flex-wrap gap-2">{alert.status === 'abierta' && <button disabled={busy} className="rounded-lg border bg-white px-3 py-2 text-sm" onClick={() => transition(alert, 'acknowledge')}>Reconocer</button>}{['abierta', 'reconocida'].includes(alert.status) && <><button disabled={busy} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-medium text-white" onClick={() => transition(alert, 'resolve')}>Resolver</button><button disabled={busy} className="rounded-lg border bg-white px-3 py-2 text-sm" onClick={() => transition(alert, 'dismiss')}>Descartar</button></>}{['resuelta', 'descartada'].includes(alert.status) && <button disabled={busy} className="rounded-lg border bg-white px-3 py-2 text-sm" onClick={() => transition(alert, 'reopen')}>Reabrir</button>}</div>{alert.history?.length > 0 && <p className="mt-3 text-xs text-slate-500">Último cambio: {alert.history.at(-1).username} · {new Date(alert.history.at(-1).at).toLocaleString('es-AR')}{alert.history.at(-1).reason ? ` · ${alert.history.at(-1).reason}` : ''}</p>}</article>)}{!visible.length && <p className="rounded-xl bg-slate-50 p-5 text-center text-sm text-slate-500">No hay alertas en este estado.</p>}</div>
    </section>
}

function DeviceDiagnostics({ data }) {
    if (!data) return null
    const recognized = data.counts?.recognition_accepted || 0
    const rejected = data.counts?.recognition_rejected || 0
    const totalRecognition = recognized + rejected
    return <section className={card}><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-lg font-bold">Diagnóstico de voz y dispositivos</h2><p className="mt-1 text-sm text-slate-500">Eventos técnicos de los últimos {data.days} días. No incluye audio, frases reconocidas ni tokens del teléfono.</p></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${data.enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>{data.enabled ? 'Captura habilitada' : 'Captura deshabilitada'}</span></div><div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{[['Eventos', data.total], ['Activaciones listas', data.counts?.voice_ready || 0], ['Fallos de activación', data.counts?.voice_activation_failed || 0], ['Reconocimiento aceptado', totalRecognition ? `${Math.round(recognized / totalRecognition * 100)}%` : 'No medido']].map(([label, value]) => <div key={label} className="rounded-xl bg-slate-50 p-3 text-center"><p className="text-xs text-slate-500">{label}</p><strong className="text-xl">{value}</strong></div>)}</div></section>
}

export default function WarehousePage({ section = 'overview', supervision = false }) {
    const admin = getStoredUser()?.role === 'administrador'
    const [date, setDate] = useState(todayInputValue()), [overview, setOverview] = useState(null)
    const [users, setUsers] = useState([]), [trucks, setTrucks] = useState([])
    const [diagnostics, setDiagnostics] = useState(null)
    const [settings, setSettings] = useState({ depots: [], trucks: [] })
    const [error, setError] = useState(''), [message, setMessage] = useState(''), [busy, setBusy] = useState(false)
    const [filter, setFilter] = useState('running'), [updated, setUpdated] = useState(null)
    const [assignment, setAssignment] = useState(null)
    const [config, setConfig] = useState(emptyPlanningConfig)
    async function refresh(signal) {
        if (section === 'overview') {
            const r = await api.get('/load-control/monitor', { params: { date }, signal, timeout: 12000 })
            if (signal?.aborted) return
            setOverview(r.data); setUsers(r.data.operators); setTrucks(r.data.trucks)
            try {
                const diagnosticResponse = await api.get('/load-control/device-diagnostics', { params: { days: 7 }, signal, timeout: 12000 })
                if (!signal?.aborted) setDiagnostics(diagnosticResponse.data)
            } catch { if (!signal?.aborted) setDiagnostics(null) }
        } else if (section === 'team') {
            const r = await api.get('/load-control/users', { signal }); if (!signal?.aborted) setUsers(r.data)
        } else {
            const r = await api.get('/load-control/settings', { signal }); if (!signal?.aborted) setSettings(r.data)
        }
        setUpdated(new Date()); setError('')
    }
    useEffect(() => {
        let active = true, timer
        const controller = new AbortController()
        async function update() {
            try { await refresh(controller.signal) }
            catch { if (active) setError('Sin conexión. Los datos pueden estar desactualizados.') }
            finally { if (active && section === 'overview') timer = setTimeout(update, 5000) }
        }
        update()
        return () => { active = false; clearTimeout(timer); controller.abort() }
    }, [section, date])
    async function save(fn) {
        if (busy) return
        setBusy(true); setError(''); setMessage('')
        try { await fn(); await refresh(); setMessage('Cambios guardados.') }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar. Reintentá.') }
        finally { setBusy(false) }
    }
    const processes = overview?.processes || []
    const state = p => p.status
    const supervisorArea = supervision || section === 'overview' || !admin
    return <div className="mx-auto max-w-6xl space-y-5 p-4 pb-20 sm:p-8">
        <header><h1 className="text-2xl font-bold">{{ overview: 'Depósito en vivo', team: 'Equipo y canchas', settings: 'Camiones y capacidad' }[section]}</h1></header>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}
        {message && <p role="status" className="rounded-xl bg-emerald-50 p-4 text-emerald-800">{message}</p>}
        {section === 'overview' && <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">{[['En curso', processes.filter(p => state(p) === 'running').length], ['Pausados', processes.filter(p => state(p) === 'paused').length], ['Alertas activas', (overview?.alerts || []).filter(a => ['abierta', 'reconocida'].includes(a.status)).length], ['Por aprobar', trucks.filter(t => t.planning === 'pending' && !t.released).length], ['Sin canchas', users.filter(u => ['operador', 'controlador', 'palletizador'].includes(u.role) && !u.courts.length).length]].map(([label, value]) => <div className={`${card} text-center`} key={label}><p className="text-sm text-slate-500">{label}</p><strong className="text-3xl">{value}</strong></div>)}</div>
            <AlertsPanel alerts={overview?.alerts || []} busy={busy} act={save} />
            <DeviceDiagnostics data={diagnostics} />
            <div className="flex flex-wrap items-end justify-between gap-3"><label>Fecha de reparto<input type="date" className={field} value={date} onChange={e => e.target.value && setDate(e.target.value)} /></label><label>Estado<select className={field} value={filter} onChange={e => setFilter(e.target.value)}><option value="running">En curso</option><option value="pending">Sin iniciar</option><option value="paused">Pausados</option><option value="done">Finalizados</option><option value="all">Todos</option></select></label><p className="text-sm text-slate-500">Actualización cada 5 segundos · {updated?.toLocaleTimeString('es-AR')}</p></div>
            <div className="grid gap-3 md:grid-cols-2">{processes.filter(p => filter === 'all' || state(p) === filter).map(p => <article className={card} key={p.id}><div className="flex justify-between gap-3"><h2 className="font-bold">{p.username} · Cancha {p.court}</h2><span>{{ running: 'En curso', pending: 'Sin iniciar', paused: 'Pausado', done: 'Finalizado' }[state(p)]}</span></div><p className="mt-2 text-sm text-slate-600">{['Picking', 'Control 1', 'Control 2', 'Activos', 'Pallets completos'][p.stage]} · Camión {p.truck} · Reparto {p.reparto}</p><p className="mt-3">{p.answered || 0} productos registrados · {Math.floor(p.elapsed_seconds / 60)} min activos</p><Link className="mt-3 inline-block py-2 text-brand-600 underline" to="/supervision/equipo">Asignar recursos</Link></article>)}</div>
            {!processes.some(p => filter === 'all' || state(p) === filter) && <p className={card}>No hay procesos en este estado. Las cargas pendientes se preparan en «Planificar cargas».</p>}
        </>}
        {section === 'team' && <>
            <p className="text-slate-600">Asigná una o varias canchas por persona. Al retirar una cancha, su proceso activo se pausa y queda disponible para otro operario; el historial se conserva.</p>
            <Personnel users={users} refresh={refresh} canEdit={admin && !supervisorArea} assign={u => { setAssignment({ id: u.id, username: u.username, text: u.courts.join(', ') }); requestAnimationFrame(() => document.getElementById('assignment-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' })) }} />
            {assignment && <section id="assignment-form" className={card}><form onSubmit={e => { e.preventDefault(); save(async () => { await api.put(`/load-control/users/${assignment.id}/courts`, { courts: courts(assignment.text) }); setAssignment(null) }) }}><h2 className="text-lg font-bold">Canchas de {assignment.username}</h2><label className="mt-3 block">Números separados por coma<input autoFocus className={field} value={assignment.text} onChange={e => setAssignment({ ...assignment, text: e.target.value })} placeholder="1, 2, 3" /></label><p className="my-3 text-sm">Dejar vacío quita el acceso a todas las canchas.</p><button disabled={busy} className={button}>Guardar asignación</button><button type="button" className="ml-3 min-h-12 px-4" onClick={() => setAssignment(null)}>Cancelar</button></form></section>}
            {admin && !supervisorArea && <form className={`${card} space-y-3`} onSubmit={e => { e.preventDefault(); const form = e.currentTarget, f = new FormData(form); save(async () => { await api.post('/load-control/users', { first_name: f.get('first_name'), last_name: f.get('last_name'), employee_number: f.get('employee_number'), username: f.get('username'), email: f.get('email'), password: f.get('password'), role: f.get('role'), courts: courts(f.get('courts')) }); form.reset() }) }}><h2 className="text-lg font-bold">Dar de alta una persona</h2><div className="grid gap-3 sm:grid-cols-2">{[['first_name','Nombre',100],['last_name','Apellido',100],['employee_number','Legajo',50]].map(([name,label,max]) => <label key={name}>{label}<input name={name} maxLength={max} className={field} /></label>)}<label>Usuario<input name="username" required className={field} autoComplete="off" /></label><label>Email<input name="email" type="email" required className={field} /></label><label>Contraseña inicial<input name="password" type="password" minLength="10" required className={field} autoComplete="new-password" /></label><label>Trabajo<select name="role" className={field}>{Object.entries(roles).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Canchas<input name="courts" placeholder="1, 2, 3" className={field} /></label></div><button disabled={busy} className={button}>Crear usuario</button></form>}
            <WeeklyStaffing users={users} />
            <DailyAssistance users={users} />
        </>}
        {section === 'settings' && admin && <>
            <form className={`${card} space-y-5`} onSubmit={e => { e.preventDefault(); const numeric = ['pallet_base_height_cm','reference_pallet_height_cm','max_pallet_height_cm','empty_pallet_weight_kg','max_pallet_weight_kg','safety_margin_pct','max_payload_kg','max_height_cm']; save(() => api.put('/load-control/settings', { ...config, capacity: Number(config.capacity), ...Object.fromEntries(numeric.map(key => [key, optionalNumber(config[key])])) })) }}>
                <div><h2 className="font-bold">Planificación física del depósito y camión</h2><p className="mt-1 text-sm text-slate-500">Los límites vacíos solo dejan el cálculo como informativo. Las alturas se miden desde el piso.</p></div>
                <div className="grid gap-3 sm:grid-cols-3">{[['branch', 'Depósito'], ['truck', 'Camión / patente'], ['capacity', 'Posiciones de pallets']].map(([name, label]) => <label key={name}>{label}<input required className={field} type={name === 'capacity' ? 'number' : 'text'} min="1" step="1" value={config[name]} onChange={e => setConfig({ ...config, [name]: e.target.value })} /></label>)}</div>
                <fieldset className="rounded-xl border p-4"><legend className="px-2 font-semibold">Altura y peso del depósito</legend><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{[
                    ['pallet_base_height_cm','Altura de tarima','cm'],['reference_pallet_height_cm','Altura de referencia','cm'],['max_pallet_height_cm','Altura máxima','cm'],
                    ['empty_pallet_weight_kg','Peso de tarima vacía','kg'],['max_pallet_weight_kg','Peso máximo por pallet','kg'],['safety_margin_pct','Margen de seguridad','%']
                ].map(([name,label,unit]) => <label key={name}>{label} ({unit})<input className={field} type="number" min="0" step="0.01" value={config[name]} onChange={e => setConfig({ ...config, [name]: e.target.value })} /></label>)}</div></fieldset>
                <fieldset className="rounded-xl border p-4"><legend className="px-2 font-semibold">Límites propios del camión</legend><div className="grid gap-3 sm:grid-cols-2"><label>Carga útil máxima (kg)<input className={field} type="number" min="0" step="0.01" value={config.max_payload_kg} onChange={e => setConfig({ ...config, max_payload_kg: e.target.value })} /></label><label>Altura máxima del camión (cm, reemplaza depósito)<input className={field} type="number" min="0" step="0.01" value={config.max_height_cm} onChange={e => setConfig({ ...config, max_height_cm: e.target.value })} /></label></div></fieldset>
                <fieldset className="rounded-xl border p-4"><legend className="px-2 font-semibold">Comportamiento ante excesos</legend><div className="grid gap-3 sm:grid-cols-3">{[['height_excess_mode','Altura'],['pallet_weight_excess_mode','Peso por pallet'],['truck_weight_excess_mode','Peso del camión']].map(([name,label]) => <label key={name}>{label}<select className={field} value={config[name]} onChange={e => setConfig({ ...config, [name]: e.target.value })}><option value="inform">Solo informar</option><option value="block">Bloquear aprobación</option></select></label>)}</div></fieldset>
                <div className="grid gap-2 sm:grid-cols-2"><label className="flex min-h-12 items-center gap-3"><input type="checkbox" checked={config.mix_courts_default} onChange={e => setConfig({ ...config, mix_courts_default: e.target.checked })} />Permitir mezcla entre canchas por defecto</label><label className="flex min-h-12 items-center gap-3"><input type="checkbox" checked={config.share_floor_remainders} onChange={e => setConfig({ ...config, share_floor_remainders: e.target.checked })} />Permitir compartir piso entre restos de igual huella</label><label className="flex min-h-12 items-center gap-3"><input type="checkbox" checked={config.weight_tiebreaker} onChange={e => setConfig({ ...config, weight_tiebreaker: e.target.checked })} />Usar peso como desempate de apilado</label></div>
                <p className="text-sm text-slate-500">Usá el mismo depósito y camión que aparecen en las cargas. El supervisor puede cambiar la mezcla al planificar.</p><button disabled={busy} className={button}>Guardar configuración</button>
            </form>
            <div className="grid gap-3 md:grid-cols-2">{settings.trucks.map(t => <button key={`${t.branch}:${t.truck}`} className={`${card} text-left`} onClick={() => { const depot=settings.depots.find(d => d.branch === t.branch) || {}; setConfig({ ...emptyPlanningConfig, ...depot, ...t }) }}><b>{t.truck} · {t.branch}</b><p>{t.capacity} posiciones{t.max_payload_kg ? ` · ${t.max_payload_kg} kg` : ''} · Editar</p></button>)}</div>
        </>}
    </div>
}
