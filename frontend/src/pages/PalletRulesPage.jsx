import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'

const field = 'min-h-12 w-full rounded-xl border p-3'
const button = 'min-h-12 rounded-xl border bg-white px-4 font-medium disabled:opacity-40'
const blank = r => ({ business_unit: r.business_unit, caliber: r.caliber, can_be_base: false, stable: false, allow_incomplete_floor: false, size_rank: 0, enabled: true })

export default function PalletRulesPage() {
    const [data, setData] = useState({ stacking_rules: [], pending_rules: [] })
    const [query, setQuery] = useState(''), [status, setStatus] = useState('all')
    const [editing, setEditing] = useState(null), [busy, setBusy] = useState(false)
    const [error, setError] = useState(''), [message, setMessage] = useState('')
    async function load() { setData((await api.get('/pallet-rules')).data) }
    useEffect(() => { load().catch(() => setError('No se pudieron cargar los criterios.')) }, [])
    const rows = useMemo(() => {
        const pending = new Map((data.pending_rules || []).map(r => [`${r.business_unit}\0${r.caliber}`, r]))
        const configured = (data.stacking_rules || []).map(r => { const p = pending.get(`${r.business_unit}\0${r.caliber}`); return { ...r, missing_rule: false, missing_floor: p?.missing_floor || Math.max((r.articles || 0) - (r.with_floor || 0), 0) } })
        const keys = new Set(configured.map(r => `${r.business_unit}\0${r.caliber}`))
        return [...configured, ...(data.pending_rules || []).filter(r => !keys.has(`${r.business_unit}\0${r.caliber}`)).map(r => ({ ...blank(r), ...r }))]
            .filter(r => `${r.business_unit} ${r.caliber}`.toLowerCase().includes(query.toLowerCase()))
            .filter(r => status === 'all' || (status === 'ready' ? !r.missing_rule && !r.missing_floor : r.missing_rule || r.missing_floor))
            .sort((a,b) => a.business_unit.localeCompare(b.business_unit) || b.size_rank-a.size_rank || a.caliber.localeCompare(b.caliber))
    }, [data, query, status])
    const ready = rows.filter(r => !r.missing_rule && !r.missing_floor).length
    async function save(event) {
        event.preventDefault(); setBusy(true); setError(''); setMessage('')
        const payload = { business_unit: editing.business_unit, caliber: editing.caliber, can_be_base: editing.can_be_base, stable: editing.stable, allow_incomplete_floor: editing.allow_incomplete_floor, size_rank: Number(editing.size_rank), enabled: editing.enabled }
        try { await api.put('/pallet-rules/stacking', payload); setEditing(null); setMessage('Criterio guardado.'); await load() }
        catch(e) { setError(e.response?.data?.error || 'No se pudo guardar el criterio.') }
        finally { setBusy(false) }
    }
    return <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-8"><header><Link className="text-brand-600 underline" to="/administracion">Volver a administración</Link><h1 className="mt-3 text-2xl font-bold">Criterios físicos de palletizado</h1><p className="mt-2 text-slate-600">Una regla por unidad de negocio y calibre. Se colocan primero los calibres mayores; nunca se mezclan repartos ni camiones.</p></header>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-700">{error}</p>}{message && <p className="rounded-xl bg-emerald-50 p-3 text-emerald-800">{message}</p>}
        <section className="grid gap-3 sm:grid-cols-3"><div className="rounded-2xl border bg-white p-4"><p className="text-sm text-slate-500">Combinaciones visibles</p><b className="text-3xl">{rows.length}</b></div><div className="rounded-2xl border bg-emerald-50 p-4"><p className="text-sm text-emerald-800">Listas para calcular</p><b className="text-3xl">{ready}</b></div><div className="rounded-2xl border bg-amber-50 p-4"><p className="text-sm text-amber-900">Pendientes</p><b className="text-3xl">{rows.length-ready}</b></div></section>
        <section className="rounded-2xl border bg-white p-5"><h2 className="font-bold">Cómo se interpreta</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600"><li><b>Base:</b> puede iniciar el pallet solamente cuando completa el piso.</li><li><b>Estable:</b> puede soportar productos arriba.</li><li><b>Orden:</b> tamaño físico; el valor mayor se coloca debajo.</li><li><b>Falta piso:</b> corregir el artículo importando la plantilla logística.</li></ul></section>
        <section className="rounded-2xl border bg-white p-5"><div className="flex flex-wrap gap-3"><input className={`${field} sm:max-w-md`} value={query} onChange={e => setQuery(e.target.value)} placeholder="Buscar unidad de negocio o calibre" />{[['all','Todos'],['ready','Listos'],['pending','Pendientes']].map(([key,label]) => <button type="button" key={key} className={`${button} ${status===key?'border-brand-500 bg-brand-50':''}`} onClick={() => setStatus(key)}>{label}</button>)}</div>
            <div className="mt-4 overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left"><th className="p-2">Unidad de negocio</th><th className="p-2">Calibre</th><th className="p-2">Artículos</th><th className="p-2">Piso</th><th className="p-2">Base</th><th className="p-2">Estable</th><th className="p-2">Orden</th><th className="p-2">Estado</th><th className="p-2">Acción</th></tr></thead><tbody>{rows.map(r => <tr className="border-b align-top" key={`${r.business_unit}-${r.caliber}`}><td className="p-2">{r.business_unit}</td><td className="p-2 font-semibold">{r.caliber}</td><td className="p-2">{r.articles || 0}</td><td className="p-2">{r.missing_floor ? <span className="text-amber-800">Falta en {r.missing_floor}</span> : 'Completo'}</td><td className="p-2">{r.can_be_base?'Sí':'No'}</td><td className="p-2">{r.stable?'Sí':'No'}</td><td className="p-2">{r.size_rank}</td><td className="p-2">{r.missing_rule ? <span className="rounded bg-red-100 px-2 py-1 text-red-800">Falta regla</span> : r.missing_floor ? <span className="rounded bg-amber-100 px-2 py-1 text-amber-900">Falta piso</span> : <span className="rounded bg-emerald-100 px-2 py-1 text-emerald-800">Listo</span>}</td><td className="p-2"><button className={button} onClick={() => setEditing({...r})}>{r.missing_rule?'Configurar':'Editar'}</button></td></tr>)}{!rows.length && <tr><td colSpan="9" className="p-5 text-center text-slate-500">No hay resultados.</td></tr>}</tbody></table></div></section>
        {editing && <form onSubmit={save} className="space-y-4 rounded-2xl border bg-white p-5"><h2 className="text-lg font-bold">{editing.business_unit} · {editing.caliber}</h2><p className="text-sm text-slate-600">Afecta {editing.articles || 0} artículos activos.</p><label>Orden físico del calibre<input className={field} type="number" min="0" required value={editing.size_rank} onChange={e => setEditing({...editing,size_rank:e.target.value})} /></label><div className="grid gap-3 sm:grid-cols-2"><label className="flex min-h-12 items-center gap-2"><input type="checkbox" checked={editing.can_be_base} onChange={e => setEditing({...editing,can_be_base:e.target.checked})} />Puede formar la base</label><label className="flex min-h-12 items-center gap-2"><input type="checkbox" checked={editing.stable} onChange={e => setEditing({...editing,stable:e.target.checked})} />Es estable</label><label className="flex min-h-12 items-center gap-2"><input type="checkbox" checked={editing.allow_incomplete_floor} onChange={e => setEditing({...editing,allow_incomplete_floor:e.target.checked})} />Permite piso incompleto</label><label className="flex min-h-12 items-center gap-2"><input type="checkbox" checked={editing.enabled} onChange={e => setEditing({...editing,enabled:e.target.checked})} />Regla activa</label></div><div className="flex gap-2"><button disabled={busy} className="min-h-12 rounded-xl bg-brand-500 px-5 text-white">Guardar criterio</button><button type="button" className={button} onClick={() => setEditing(null)}>Cancelar</button></div></form>}
    </div>
}
