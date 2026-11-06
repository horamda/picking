import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'

const field = 'min-h-12 w-full rounded-xl border bg-white p-3'
const button = 'min-h-11 rounded-xl border bg-white px-4 font-medium disabled:opacity-40'
const blank = rule => ({ business_unit: rule.business_unit, caliber: rule.caliber, can_be_base: false, stable: false, allow_incomplete_floor: false, size_rank: 0, enabled: true })

function Badge({ rule }) {
    if (rule.missing_rule) return <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-800">Falta configurar</span>
    if (rule.missing_floor) return <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">Faltan pisos</span>
    return <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">Listo</span>
}

export default function PalletRulesPage() {
    const [data, setData] = useState({ stacking_rules: [], pending_rules: [] })
    const [query, setQuery] = useState(''), [status, setStatus] = useState('all')
    const [editing, setEditing] = useState(null), [busy, setBusy] = useState(false)
    const [error, setError] = useState(''), [message, setMessage] = useState('')
    async function load() { setData((await api.get('/pallet-rules')).data) }
    useEffect(() => { load().catch(() => setError('No se pudieron cargar los criterios.')) }, [])

    const allRows = useMemo(() => {
        const pending = new Map((data.pending_rules || []).map(rule => [`${rule.business_unit}\0${rule.caliber}`, rule]))
        const configured = (data.stacking_rules || []).map(rule => {
            const item = pending.get(`${rule.business_unit}\0${rule.caliber}`)
            return { ...rule, missing_rule: false, missing_floor: item?.missing_floor || Math.max((rule.articles || 0) - (rule.with_floor || 0), 0) }
        })
        const keys = new Set(configured.map(rule => `${rule.business_unit}\0${rule.caliber}`))
        return [...configured, ...(data.pending_rules || []).filter(rule => !keys.has(`${rule.business_unit}\0${rule.caliber}`)).map(rule => ({ ...blank(rule), ...rule }))]
            .sort((a, b) => a.business_unit.localeCompare(b.business_unit) || b.size_rank - a.size_rank || a.caliber.localeCompare(b.caliber))
    }, [data])
    const counts = useMemo(() => ({
        ready: allRows.filter(rule => !rule.missing_rule && !rule.missing_floor).length,
        pending: allRows.filter(rule => rule.missing_rule || rule.missing_floor).length,
    }), [allRows])
    const rows = useMemo(() => allRows
        .filter(rule => `${rule.business_unit} ${rule.caliber}`.toLowerCase().includes(query.trim().toLowerCase()))
        .filter(rule => status === 'all' || (status === 'ready' ? !rule.missing_rule && !rule.missing_floor : rule.missing_rule || rule.missing_floor)), [allRows, query, status])

    async function save(event) {
        event.preventDefault(); setBusy(true); setError(''); setMessage('')
        const payload = { business_unit: editing.business_unit, caliber: editing.caliber, can_be_base: editing.can_be_base, stable: editing.stable, allow_incomplete_floor: editing.allow_incomplete_floor, size_rank: Number(editing.size_rank), enabled: editing.enabled }
        try { await api.put('/pallet-rules/stacking', payload); setEditing(null); setMessage('Criterio guardado.'); await load() }
        catch (requestError) { setError(requestError.response?.data?.error || 'No se pudo guardar el criterio.') }
        finally { setBusy(false) }
    }
    async function exportIncomplete() {
        setBusy(true); setError(''); setMessage('')
        try {
            const response = await api.get('/pallet-rules/incomplete-articles.csv', { responseType: 'blob' })
            const url = URL.createObjectURL(response.data), anchor = document.createElement('a')
            anchor.href = url; anchor.download = 'articulos-incompletos-mezclador.csv'; document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url)
            setMessage('Exportación generada.')
        } catch (requestError) { setError(requestError.response?.data?.error || 'No se pudo exportar el listado.') }
        finally { setBusy(false) }
    }

    return <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><Link className="text-sm font-semibold text-brand-600 underline" to="/administracion">← Volver a administración</Link><h1 className="mt-3 text-2xl font-bold">Reglas del mezclador</h1><p className="mt-1 max-w-3xl text-slate-600">Configurá cómo se apilan los calibres. Incluye mercadería activa y no anulada aunque no esté habilitada para dispositivos móviles.</p></div><button type="button" disabled={busy || !data.incomplete_articles} className={button} onClick={exportIncomplete}>Exportar artículos incompletos</button></header>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-700">{error}</p>}{message && <p className="rounded-xl bg-emerald-50 p-3 text-emerald-800">{message}</p>}

        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[['Combinaciones', allRows.length, 'bg-white'], ['Listas', counts.ready, 'bg-emerald-50'], ['Pendientes', counts.pending, 'bg-amber-50'], ['Artículos incompletos', data.incomplete_articles || 0, 'bg-amber-50']].map(([label, value, color]) => <div key={label} className={`rounded-2xl border p-4 ${color}`}><p className="text-sm text-slate-600">{label}</p><b className="text-2xl">{value}</b></div>)}
        </section>

        <details className="rounded-2xl border bg-white p-4"><summary className="cursor-pointer font-semibold">Cómo se usan estas reglas</summary><ul className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-2"><li><b>Base:</b> puede iniciar el pallet cuando completa el piso.</li><li><b>Estable:</b> soporta productos arriba.</li><li><b>Orden:</b> el valor mayor se ubica debajo.</li><li><b>Faltan pisos:</b> completalos con la plantilla logística.</li></ul></details>

        <section className={`grid gap-5 ${editing ? 'lg:grid-cols-[minmax(0,1fr)_380px]' : ''}`}>
            <div className="min-w-0 rounded-2xl border bg-white p-4 sm:p-5">
                <div className="grid gap-3 md:grid-cols-[minmax(240px,1fr)_auto]"><input className={field} value={query} onChange={event => setQuery(event.target.value)} placeholder="Buscar unidad de negocio o calibre" /><div className="grid grid-cols-3 gap-2">{[['all', `Todos ${allRows.length}`], ['ready', `Listos ${counts.ready}`], ['pending', `Pendientes ${counts.pending}`]].map(([key, label]) => <button type="button" key={key} className={`${button} px-3 ${status === key ? 'border-brand-500 bg-brand-50 text-brand-700' : ''}`} onClick={() => setStatus(key)}>{label}</button>)}</div></div>
                <p className="mt-3 text-sm text-slate-500">{rows.length} combinaciones visibles</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{rows.map(rule => <article className={`flex min-h-56 flex-col rounded-2xl border p-4 ${editing?.business_unit === rule.business_unit && editing?.caliber === rule.caliber ? 'border-brand-500 ring-2 ring-brand-100' : ''}`} key={`${rule.business_unit}-${rule.caliber}`}>
                    <div className="flex items-start justify-between gap-2"><Badge rule={rule} /><span className="text-xs text-slate-500">{rule.articles || 0} artículos</span></div><p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">{rule.business_unit}</p><h2 className="mt-1 text-lg font-bold">{rule.caliber}</h2>
                    <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-sm"><div className="rounded-lg bg-slate-50 p-2"><dt className="text-xs text-slate-500">Base</dt><dd className="font-semibold">{rule.can_be_base ? 'Sí' : 'No'}</dd></div><div className="rounded-lg bg-slate-50 p-2"><dt className="text-xs text-slate-500">Estable</dt><dd className="font-semibold">{rule.stable ? 'Sí' : 'No'}</dd></div><div className="rounded-lg bg-slate-50 p-2"><dt className="text-xs text-slate-500">Orden</dt><dd className="font-semibold">{rule.size_rank}</dd></div></dl>
                    <p className={`mt-3 text-sm ${rule.missing_floor ? 'font-medium text-amber-800' : 'text-slate-500'}`}>{rule.missing_floor ? `Falta piso en ${rule.missing_floor} artículo(s).` : 'Datos físicos completos.'}</p><button className={`${button} mt-auto w-full`} onClick={() => setEditing({ ...rule })}>{rule.missing_rule ? 'Configurar regla' : 'Editar regla'}</button>
                </article>)}{!rows.length && <p className="col-span-full rounded-xl bg-slate-50 p-6 text-center text-slate-500">No hay resultados para estos filtros.</p>}</div>
            </div>

            {editing && <form onSubmit={save} className="h-fit space-y-4 rounded-2xl border border-brand-200 bg-white p-5 lg:sticky lg:top-4"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase text-brand-600">Editando regla</p><h2 className="mt-1 text-lg font-bold">{editing.caliber}</h2><p className="text-sm text-slate-500">{editing.business_unit} · {editing.articles || 0} artículos</p></div><button type="button" aria-label="Cerrar editor" className="rounded-lg border px-3 py-1" onClick={() => setEditing(null)}>×</button></div>
                <label className="block font-medium">Orden físico del calibre<span className="mt-1 block text-xs font-normal text-slate-500">Los valores mayores se colocan debajo.</span><input className={`${field} mt-2`} type="number" min="0" required value={editing.size_rank} onChange={event => setEditing({ ...editing, size_rank: event.target.value })} /></label>
                <div className="space-y-2">{[['can_be_base', 'Puede formar la base'], ['stable', 'Es estable'], ['allow_incomplete_floor', 'Permite piso incompleto'], ['enabled', 'Regla activa']].map(([key, label]) => <label key={key} className="flex min-h-12 items-center gap-3 rounded-xl border p-3"><input type="checkbox" checked={editing[key]} onChange={event => setEditing({ ...editing, [key]: event.target.checked })} /><span className="font-medium">{label}</span></label>)}</div>
                <button disabled={busy} className="min-h-12 w-full rounded-xl bg-brand-500 px-5 font-semibold text-white">{busy ? 'Guardando…' : 'Guardar criterio'}</button><button type="button" className={`${button} w-full`} onClick={() => setEditing(null)}>Cancelar</button>
            </form>}
        </section>
    </div>
}
