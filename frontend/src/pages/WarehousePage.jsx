import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { getStoredUser } from '../utils/auth'

const field = 'mt-1 min-h-12 w-full rounded-xl border border-slate-300 bg-white p-3'
const button = 'min-h-12 rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white disabled:opacity-50'
const card = 'rounded-2xl border border-slate-200 bg-white p-5'
const roles = { operador: 'Pickeador', palletizador: 'Pallets completos', controlador: 'Controlador', supervisor: 'Supervisor', administrador: 'Administrador' }
const courts = text => text.trim() ? text.split(',').map(s => Number(s.trim())) : []

export default function WarehousePage({ section = 'overview' }) {
    const admin = getStoredUser()?.role === 'administrador'
    const [users, setUsers] = useState([]), [trucks, setTrucks] = useState([])
    const [settings, setSettings] = useState({ depots: [], trucks: [] })
    const [error, setError] = useState(''), [message, setMessage] = useState(''), [busy, setBusy] = useState(false)
    const [filter, setFilter] = useState('running'), [updated, setUpdated] = useState(null)
    const [assignment, setAssignment] = useState(null)
    const [config, setConfig] = useState({ branch: '', truck: '', capacity: '', mix_courts_default: false })
    async function refresh() {
        const [u, t, s] = await Promise.all(['users', 'trucks', 'settings'].map(p => api.get(`/load-control/${p}`)))
        setUsers(u.data); setTrucks(t.data); setSettings(s.data); setUpdated(new Date())
    }
    useEffect(() => {
        let active = true
        const update = () => { if (active) refresh().catch(() => active && setError('No se pudo actualizar. Revisá la conexión.')) }
        update(); const timer = setInterval(update, 10000)
        return () => { active = false; clearInterval(timer) }
    }, [])
    async function save(fn) {
        if (busy) return
        setBusy(true); setError(''); setMessage('')
        try { await fn(); await refresh(); setMessage('Cambios guardados.') }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar. Reintentá.') }
        finally { setBusy(false) }
    }
    const processes = trucks.flatMap(t => t.loads.flatMap(l => l.canchas.flatMap(c => c.status.checks.map(ch => ({ ...ch, truck: t.truck, reparto: l.reparto, court: c.numero, total: c.cantidad })))))
    const state = p => p.status === 'done' ? 'done' : p.timer_started_at ? 'running' : 'paused'
    return <div className="mx-auto max-w-6xl space-y-5 p-4 pb-20 sm:p-8">
        <header><p className="text-sm text-brand-600">Del Palacio · {admin ? 'Administración' : 'Supervisión'}</p><h1 className="mt-1 text-2xl font-bold">{{ overview: 'Depósito en vivo', team: 'Equipo y canchas', settings: 'Camiones y capacidad' }[section]}</h1></header>
        <nav className="flex gap-2 overflow-x-auto pb-2" aria-label="Gestión del depósito">{[['/tiempos', 'Tiempos y actividad'], ['/monitor', 'Pantalla de depósito'], ['/supervision', 'Seguimiento'], ['/equipo', 'Equipo y canchas'], ...(admin ? [['/configuracion', 'Camiones']] : []), ['/operacion?tab=control', 'Planificar cargas'], ['/importaciones', 'Subir PDF']].map(([to, label]) => <Link key={to} to={to} className="min-h-12 shrink-0 rounded-xl border bg-white px-4 py-3 text-sm font-medium">{label}</Link>)}</nav>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}
        {message && <p role="status" className="rounded-xl bg-emerald-50 p-4 text-emerald-800">{message}</p>}
        {section === 'overview' && <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{[['En curso', processes.filter(p => state(p) === 'running').length], ['Pausados', processes.filter(p => state(p) === 'paused').length], ['Por aprobar', trucks.filter(t => t.planning_status !== 'approved' && !t.status.released_at).length], ['Sin canchas', users.filter(u => ['operador', 'controlador', 'palletizador'].includes(u.role) && !u.courts.length).length]].map(([label, value]) => <div className={card} key={label}><p className="text-sm text-slate-500">{label}</p><strong className="text-3xl">{value}</strong></div>)}</div>
            <div className="flex flex-wrap items-end justify-between gap-3"><label>Estado<select className={field} value={filter} onChange={e => setFilter(e.target.value)}><option value="running">En curso</option><option value="paused">Pausados</option><option value="done">Finalizados</option><option value="all">Todos</option></select></label><p className="text-sm text-slate-500">Actualización cada 10 segundos · {updated?.toLocaleTimeString('es-AR')}</p></div>
            <div className="grid gap-3 md:grid-cols-2">{processes.filter(p => filter === 'all' || state(p) === filter).map(p => <article className={card} key={p.id}><div className="flex justify-between gap-3"><h2 className="font-bold">{p.username} · Cancha {p.court}</h2><span>{{ running: 'En curso', paused: 'Pausado', done: 'Finalizado' }[state(p)]}</span></div><p className="mt-2 text-sm text-slate-600">{['Picking', 'Control 1', 'Control 2', 'Activos', 'Pallets completos'][p.stage]} · Camión {p.truck} · Reparto {p.reparto}</p><p className="mt-3">{p.answered || 0} productos registrados · {Math.floor(p.elapsed_seconds / 60)} min activos</p><Link className="mt-3 inline-block py-2 text-brand-600 underline" to="/equipo">Asignar recursos</Link></article>)}</div>
            {!processes.some(p => filter === 'all' || state(p) === filter) && <p className={card}>No hay procesos en este estado. Las cargas pendientes se preparan en «Planificar cargas».</p>}
        </>}
        {section === 'team' && <>
            <p className="text-slate-600">Asigná una o varias canchas por persona. Al retirar una cancha, su proceso activo se pausa y queda disponible para otro operario; el historial se conserva.</p>
            <div className="grid gap-3 md:grid-cols-2">{users.map(u => <article key={u.id} className={card}><h2 className="font-bold">{u.username}</h2><p className="text-sm text-slate-500">{roles[u.role]}{!u.active && ' · Inactivo'}</p><p className="my-3">Canchas: {u.courts.join(', ') || 'Sin asignar'}</p>{['operador', 'controlador', 'palletizador'].includes(u.role) && <button className={button} onClick={() => { setAssignment({ id: u.id, username: u.username, text: u.courts.join(', ') }); requestAnimationFrame(() => document.getElementById('assignment-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' })) }}>Asignar canchas</button>}</article>)}</div>
            {assignment && <section id="assignment-form" className={card}><form onSubmit={e => { e.preventDefault(); save(async () => { await api.put(`/load-control/users/${assignment.id}/courts`, { courts: courts(assignment.text) }); setAssignment(null) }) }}><h2 className="text-lg font-bold">Canchas de {assignment.username}</h2><label className="mt-3 block">Números separados por coma<input autoFocus className={field} value={assignment.text} onChange={e => setAssignment({ ...assignment, text: e.target.value })} placeholder="1, 2, 3" /></label><p className="my-3 text-sm">Dejar vacío quita el acceso a todas las canchas.</p><button disabled={busy} className={button}>Guardar asignación</button><button type="button" className="ml-3 min-h-12 px-4" onClick={() => setAssignment(null)}>Cancelar</button></form></section>}
            {admin && <form className={`${card} space-y-3`} onSubmit={e => { e.preventDefault(); const form = e.currentTarget, f = new FormData(form); save(async () => { await api.post('/load-control/users', { username: f.get('username'), email: f.get('email'), password: f.get('password'), role: f.get('role'), courts: courts(f.get('courts')) }); form.reset() }) }}><h2 className="text-lg font-bold">Dar de alta una persona</h2><div className="grid gap-3 sm:grid-cols-2"><label>Usuario<input name="username" required className={field} autoComplete="off" /></label><label>Email<input name="email" type="email" required className={field} /></label><label>Contraseña inicial<input name="password" type="password" minLength="10" required className={field} autoComplete="new-password" /></label><label>Trabajo<select name="role" className={field}>{Object.entries(roles).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Canchas<input name="courts" placeholder="1, 2, 3" className={field} /></label></div><button disabled={busy} className={button}>Crear usuario</button></form>}
        </>}
        {section === 'settings' && admin && <>
            <form className={`${card} space-y-4`} onSubmit={e => { e.preventDefault(); save(() => api.put('/load-control/settings', { ...config, capacity: Number(config.capacity) })) }}><h2 className="font-bold">Capacidad física del camión</h2><div className="grid gap-3 sm:grid-cols-3">{[['branch', 'Depósito'], ['truck', 'Camión / patente'], ['capacity', 'Posiciones de pallets']].map(([name, label]) => <label key={name}>{label}<input required className={field} type={name === 'capacity' ? 'number' : 'text'} min="1" step="1" value={config[name]} onChange={e => setConfig({ ...config, [name]: e.target.value })} /></label>)}</div><label className="flex min-h-12 items-center gap-3"><input type="checkbox" checked={config.mix_courts_default} onChange={e => setConfig({ ...config, mix_courts_default: e.target.checked })} />Permitir mezcla entre canchas por defecto en este depósito</label><p className="text-sm text-slate-500">Usá el mismo depósito y camión que aparecen en las cargas. El supervisor puede cambiar la mezcla al planificar.</p><button disabled={busy} className={button}>Guardar configuración</button></form>
            <div className="grid gap-3 md:grid-cols-2">{settings.trucks.map(t => <button key={`${t.branch}:${t.truck}`} className={`${card} text-left`} onClick={() => setConfig({ ...t, mix_courts_default: settings.depots.find(d => d.branch === t.branch)?.mix_courts_default || false })}><b>{t.truck} · {t.branch}</b><p>{t.capacity} posiciones de pallets · Editar</p></button>)}</div>
        </>}
    </div>
}
