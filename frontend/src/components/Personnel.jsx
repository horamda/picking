import { useState } from 'react'
import api from '../api/axiosClient'

const roles = { operador: 'Pickeador', palletizador: 'Pallets completos', controlador: 'Controlador', supervisor: 'Supervisor', administrador: 'Administrador' }
const field = 'mt-1 min-h-12 w-full rounded-xl border border-slate-300 bg-white p-3'
const button = 'min-h-12 rounded-xl border px-4 py-3 disabled:opacity-50'

export default function Personnel({ users, refresh, canEdit, assign }) {
    const [query, setQuery] = useState(''), [role, setRole] = useState(''), [status, setStatus] = useState('active')
    const [edit, setEdit] = useState(null), [password, setPassword] = useState(''), [busy, setBusy] = useState(false)
    const [error, setError] = useState(''), [message, setMessage] = useState('')
    const filtered = users.filter(u => (!role || u.role === role) && (!status || Boolean(u.active) === (status === 'active')) &&
        [u.username, u.email, u.first_name, u.last_name, u.employee_number].join(' ').toLocaleLowerCase('es').includes(query.trim().toLocaleLowerCase('es')))
    function open(user, mode) {
        setEdit({ ...user, mode }); setPassword(''); setError(''); setMessage('')
        requestAnimationFrame(() => document.getElementById('personnel-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
    }
    async function submit(e) {
        e.preventDefault(); if (busy) return
        setBusy(true); setError(''); setMessage('')
        const data = edit.mode === 'password' ? { password } : edit.mode === 'status' ? { active: !edit.active } :
            Object.fromEntries(['username','email','first_name','last_name','employee_number','role'].map(k => [k, edit[k] || '']))
        try { await api.put(`/load-control/users/${edit.id}`, data); setEdit(null); setPassword(''); await refresh(); setMessage('Cambios guardados. El historial se conserva.') }
        catch (e) { setError(e.response?.data?.error || 'No se pudo guardar. Reintentá.') }
        finally { setBusy(false) }
    }
    return <section className="space-y-4" aria-label="Personal">
        <h2 className="text-xl font-bold">Personal</h2>
        <div className="grid gap-3 sm:grid-cols-3">
            <label>Buscar persona<input className={field} value={query} onChange={e => setQuery(e.target.value)} placeholder="Nombre, usuario, email o legajo" /></label>
            <label>Rol<select aria-label="Filtrar por rol" className={field} value={role} onChange={e => setRole(e.target.value)}><option value="">Todos</option>{Object.entries(roles).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label>Estado<select aria-label="Estado" className={field} value={status} onChange={e => setStatus(e.target.value)}><option value="active">Activos</option><option value="inactive">Inactivos</option><option value="">Todos</option></select></label>
        </div>
        {message && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-emerald-800">{message}</p>}
        <p className="text-sm text-slate-500">{filtered.length} personas · La baja desactiva el acceso y conserva los registros.</p>
        <div className="grid gap-3 md:grid-cols-2">{filtered.map(u => <article key={u.id} className="rounded-2xl border bg-white p-5">
            <h3 className="font-bold">{[u.first_name,u.last_name].filter(Boolean).join(' ') || u.username}</h3>
            <p className="break-words text-sm text-slate-500">{u.username} · {roles[u.role]} · {u.active ? 'Activo' : 'Inactivo'}</p>
            <p className="break-words text-sm">Legajo: {u.employee_number || 'Sin cargar'} · {u.email}</p>
            <p className="my-3">Canchas: {u.courts.join(', ') || 'Sin asignar'}</p>
            <div className="flex flex-wrap gap-2">
                {u.active && ['operador','controlador','palletizador'].includes(u.role) && <button className={button} onClick={() => assign(u)}>Asignar canchas</button>}
                {canEdit && <><button className={button} onClick={() => open(u,'profile')}>Editar</button><button className={button} onClick={() => open(u,'password')}>Restablecer contraseña</button><button className={button} onClick={() => open(u,'status')}>{u.active ? 'Desactivar' : 'Reactivar'}</button></>}
            </div>
        </article>)}</div>
        {!filtered.length && <p>No hay personas que coincidan con los filtros.</p>}
        {edit && <form id="personnel-form" onSubmit={submit} className="space-y-4 rounded-2xl border bg-white p-5">
            <h3 className="text-lg font-bold">{edit.mode === 'password' ? 'Restablecer contraseña' : edit.mode === 'status' ? (edit.active ? 'Desactivar persona' : 'Reactivar persona') : 'Editar persona'} · {edit.username}</h3>
            {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-800">{error}</p>}
            {edit.mode === 'profile' && <div className="grid gap-3 sm:grid-cols-2">{[['first_name','Nombre',100],['last_name','Apellido',100],['employee_number','Legajo',50],['username','Usuario',128],['email','Email',255]].map(([key,label,max]) => <label key={key}>{label}<input className={field} type={key === 'email' ? 'email' : 'text'} required={['username','email'].includes(key)} maxLength={max} value={edit[key] || ''} onChange={e => setEdit({ ...edit, [key]: e.target.value })} /></label>)}<label>Rol<select className={field} value={edit.role} onChange={e => setEdit({ ...edit, role:e.target.value })}>{Object.entries(roles).map(([key,label]) => <option key={key} value={key}>{label}</option>)}</select></label></div>}
            {edit.mode === 'password' && <><label className="block">Nueva contraseña<input className={field} required type="password" autoComplete="new-password" minLength={10} maxLength={256} value={password} onChange={e => setPassword(e.target.value)} /></label><p>Se cerrarán las sesiones anteriores. Comunicá la nueva contraseña a la persona por un canal privado.</p></>}
            {edit.mode === 'status' && <p>{edit.active ? 'La persona perderá el acceso. Primero debe finalizar o reasignar sus procesos activos y ayudas. Sus tiempos e historial se conservan.' : 'La persona recuperará el acceso con sus canchas actuales. Revisá también su planificación semanal.'}</p>}
            <div className="flex flex-wrap gap-3"><button disabled={busy} className={`${button} bg-brand-500 font-semibold text-white`}>{busy ? 'Guardando…' : 'Confirmar cambios'}</button><button type="button" disabled={busy} className={button} onClick={() => { setEdit(null); setPassword('') }}>Cancelar</button></div>
        </form>}
    </section>
}
