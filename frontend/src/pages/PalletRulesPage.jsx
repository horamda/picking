import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'

const field = 'min-h-12 w-full rounded-xl border bg-white p-3'
const button = 'min-h-11 rounded-xl border bg-white px-4 font-medium disabled:opacity-40'
const blank = rule => ({ business_unit: rule.business_unit, caliber: rule.caliber, can_be_base: false, stable: false, allow_incomplete_floor: false, size_rank: 0, enabled: true, units_per_case: '', length_cm: '', width_cm: '', height_cm: '', missing_physical: ['units_per_case', 'length_cm', 'width_cm'] })

function Badge({ rule }) {
    if (rule.missing_rule) return <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-800">Falta configurar</span>
    if (rule.missing_floor) return <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">Faltan pisos</span>
    if (rule.missing_physical?.length) return <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">Faltan medidas</span>
    return <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">Listo</span>
}

export default function PalletRulesPage() {
    const [data, setData] = useState({ stacking_rules: [], pending_rules: [] })
    const [query, setQuery] = useState(''), [status, setStatus] = useState('all')
    const [editing, setEditing] = useState(null), [busy, setBusy] = useState(false)
    const [excelFile, setExcelFile] = useState(null), [excelResult, setExcelResult] = useState(null)
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
        ready: allRows.filter(rule => !rule.missing_rule && !rule.missing_floor && !rule.missing_physical?.length).length,
        pending: allRows.filter(rule => rule.missing_rule || rule.missing_floor || rule.missing_physical?.length).length,
    }), [allRows])
    const rows = useMemo(() => allRows
        .filter(rule => `${rule.business_unit} ${rule.caliber}`.toLowerCase().includes(query.trim().toLowerCase()))
        .filter(rule => status === 'all' || (status === 'ready' ? !rule.missing_rule && !rule.missing_floor && !rule.missing_physical?.length : rule.missing_rule || rule.missing_floor || rule.missing_physical?.length)), [allRows, query, status])

    async function save(event) {
        event.preventDefault(); setBusy(true); setError(''); setMessage('')
        const number = value => value === '' || value == null ? null : Number(value)
        const payload = { business_unit: editing.business_unit, caliber: editing.caliber, can_be_base: editing.can_be_base, stable: editing.stable, allow_incomplete_floor: editing.allow_incomplete_floor, size_rank: Number(editing.size_rank), enabled: editing.enabled, units_per_case: number(editing.units_per_case), length_cm: number(editing.length_cm), width_cm: number(editing.width_cm), height_cm: number(editing.height_cm) }
        try { await api.put('/pallet-rules/stacking', payload); setEditing(null); setMessage('Criterio guardado.'); await load() }
        catch (requestError) { setError(requestError.response?.data?.error || 'No se pudo guardar el criterio.') }
        finally { setBusy(false) }
    }
    async function exportExcel() {
        setBusy(true); setError(''); setMessage('')
        try { const response = await api.get('/pallet-rules/stacking.xlsx', { responseType: 'blob' }); const url = URL.createObjectURL(response.data), anchor = document.createElement('a'); anchor.href = url; anchor.download = 'reglas-mezclador.xlsx'; document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url); setMessage('Excel generado con los datos actuales.') }
        catch (requestError) { setError(requestError.response?.data?.error || 'No se pudo exportar el Excel.') }
        finally { setBusy(false) }
    }
    async function importExcel(apply) {
        if (!excelFile) return
        setBusy(true); setError(''); setMessage('')
        try { const form = new FormData(); form.append('file', excelFile); form.append('apply', String(apply)); const response = await api.post('/pallet-rules/stacking.xlsx', form); setExcelResult(response.data); if (apply) { setMessage(`${response.data.updated} reglas actualizadas.`); await load() } }
        catch (requestError) { setError(requestError.response?.data?.error || 'No se pudo procesar el Excel.') }
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
        <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div><Link className="text-sm font-semibold text-brand-600 underline" to="/administracion">← Volver a administración</Link><h1 className="mt-3 text-2xl font-bold">Reglas del mezclador</h1><p className="mt-1 max-w-3xl text-slate-600">Configurá cómo se apilan los calibres. Incluye mercadería activa y no anulada aunque no esté habilitada para dispositivos móviles.</p></div><div className="flex flex-wrap gap-2"><button type="button" disabled={busy} className={button} onClick={exportExcel}>Exportar Excel</button><button type="button" disabled={busy || !data.incomplete_articles} className={button} onClick={exportIncomplete}>Exportar artículos incompletos</button></div></header>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-700">{error}</p>}{message && <p className="rounded-xl bg-emerald-50 p-3 text-emerald-800">{message}</p>}

        <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {[['Combinaciones', allRows.length, 'bg-white'], ['Listas', counts.ready, 'bg-emerald-50'], ['Pendientes', counts.pending, 'bg-amber-50'], ['Artículos incompletos', data.incomplete_articles || 0, 'bg-amber-50']].map(([label, value, color]) => <div key={label} className={`rounded-2xl border p-4 ${color}`}><p className="text-sm text-slate-600">{label}</p><b className="text-2xl">{value}</b></div>)}
        </section>

        <details className="rounded-2xl border bg-white p-4"><summary className="cursor-pointer font-semibold">Cómo se usan estas reglas</summary><ul className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-2"><li><b>Base:</b> puede iniciar el pallet cuando completa el piso.</li><li><b>Estable:</b> soporta productos arriba.</li><li><b>Orden:</b> el valor mayor se ubica debajo.</li><li><b>Faltan pisos:</b> completalos con la plantilla logística.</li></ul></details>

        <section className="rounded-2xl border bg-white p-4 sm:p-5"><h2 className="font-semibold">Completar reglas con Excel</h2><p className="mt-1 text-sm text-slate-600">Exportá el archivo actual, completá unidades por bulto y medidas en centímetros, y volvé a importarlo. Las celdas vacías conservan el dato existente.</p><div className="mt-4 flex flex-wrap items-center gap-3"><input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={busy} onChange={event => { setExcelFile(event.target.files?.[0] || null); setExcelResult(null) }} /><button type="button" className={button} disabled={!excelFile || busy} onClick={() => importExcel(false)}>Vista previa</button><button type="button" className="min-h-11 rounded-xl bg-brand-500 px-4 font-semibold text-white disabled:opacity-40" disabled={!excelFile || busy || !excelResult || excelResult.applied || !excelResult.updated} onClick={() => importExcel(true)}>Aplicar cambios</button></div>{excelResult && <div className="mt-4 grid gap-3 sm:grid-cols-3"><div className="rounded-xl bg-slate-50 p-3"><p className="text-sm text-slate-500">Filas</p><b className="text-xl">{excelResult.total}</b></div><div className="rounded-xl bg-amber-50 p-3"><p className="text-sm text-amber-800">Cambiarían</p><b className="text-xl">{excelResult.updated}</b></div><div className="rounded-xl bg-emerald-50 p-3"><p className="text-sm text-emerald-800">Sin cambios</p><b className="text-xl">{excelResult.unchanged}</b></div></div>}</section>

        <section className={`grid items-start gap-5 ${editing ? 'lg:grid-cols-[minmax(0,1fr)_minmax(340px,410px)]' : ''}`}>
            <div className="min-w-0 rounded-2xl border bg-white p-4 sm:p-5">
                <div className="space-y-3"><label className="block"><span className="sr-only">Buscar reglas</span><input className={field} value={query} onChange={event => setQuery(event.target.value)} placeholder="Buscar unidad de negocio o calibre" /></label><div className="grid grid-cols-1 gap-2 min-[420px]:grid-cols-3" role="group" aria-label="Filtrar reglas por estado">{[['all', `Todos ${allRows.length}`], ['ready', `Listos ${counts.ready}`], ['pending', `Pendientes ${counts.pending}`]].map(([key, label]) => <button type="button" key={key} aria-pressed={status === key} className={`${button} min-h-12 px-3 ${status === key ? 'border-brand-500 bg-brand-50 text-brand-700 ring-2 ring-brand-100' : ''}`} onClick={() => setStatus(key)}>{label}</button>)}</div></div>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-b pb-3"><p className="text-sm font-medium text-slate-600">{rows.length} combinaciones visibles</p>{editing && <p className="text-sm text-brand-700">Editor abierto: {editing.caliber}</p>}</div>
                <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{rows.map(rule => <article className={`flex min-h-72 flex-col rounded-2xl border p-4 transition ${editing?.business_unit === rule.business_unit && editing?.caliber === rule.caliber ? 'border-brand-500 ring-2 ring-brand-100' : 'hover:border-brand-200'}`} key={`${rule.business_unit}-${rule.caliber}`}>
                    <div className="flex items-start justify-between gap-2"><Badge rule={rule} /><span className="text-xs text-slate-500">{rule.articles || 0} artículos</span></div><p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">{rule.business_unit}</p><h2 className="mt-1 text-lg font-bold">{rule.caliber}</h2>
                    <dl className="mt-4 grid grid-cols-3 gap-2 text-center text-sm"><div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-xs text-slate-500">Base</dt><dd className="mt-1 font-semibold">{rule.can_be_base ? 'Sí' : 'No'}</dd></div><div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-xs text-slate-500">Estable</dt><dd className="mt-1 font-semibold">{rule.stable ? 'Sí' : 'No'}</dd></div><div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-xs text-slate-500">Orden</dt><dd className="mt-1 font-semibold tabular-nums">{rule.size_rank}</dd></div></dl>
                    <div className={`mt-4 rounded-xl p-3 text-sm ${(rule.missing_floor || rule.missing_physical?.length) ? 'bg-amber-50 font-medium text-amber-900' : 'bg-emerald-50 text-emerald-900'}`}>{rule.missing_floor ? `Falta piso en ${rule.missing_floor} artículo(s).` : rule.missing_physical?.length ? `Falta completar: ${rule.missing_physical.map(item => ({ units_per_case: 'unidades/bulto', length_cm: 'largo', width_cm: 'ancho' }[item] || item)).join(', ')}.` : `Bulto: ${rule.length_cm} × ${rule.width_cm}${rule.height_cm ? ` × ${rule.height_cm}` : ''} cm · ${rule.units_per_case} un.`}</div><button className={`${button} mt-auto w-full min-h-12`} onClick={() => setEditing({ ...rule })}>{rule.missing_rule ? 'Configurar regla' : 'Editar regla'}</button>
                </article>)}{!rows.length && <p className="col-span-full rounded-xl bg-slate-50 p-6 text-center text-slate-500">No hay resultados para estos filtros.</p>}</div>
            </div>

            {editing && <form onSubmit={save} className="rounded-2xl border border-brand-200 bg-white shadow-lg lg:sticky lg:top-24 lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto" aria-label={`Editar regla ${editing.caliber}`}><div className="sticky top-0 z-10 flex items-start justify-between gap-3 rounded-t-2xl border-b bg-white p-5"><div className="min-w-0"><p className="text-xs font-semibold uppercase text-brand-600">Editando regla</p><h2 className="mt-1 truncate text-lg font-bold">{editing.caliber}</h2><p className="text-sm text-slate-500">{editing.business_unit} · {editing.articles || 0} artículos</p></div><button type="button" aria-label="Cerrar editor" className="min-h-11 min-w-11 rounded-xl border text-xl" onClick={() => setEditing(null)}>×</button></div><div className="space-y-4 p-5">
                <label className="block font-medium">Orden físico del calibre<span className="mt-1 block text-xs font-normal text-slate-500">Los valores mayores se colocan debajo.</span><input className={`${field} mt-2`} type="number" min="0" required value={editing.size_rank} onChange={event => setEditing({ ...editing, size_rank: event.target.value })} /></label>
                <fieldset className="rounded-xl border p-3"><legend className="px-2 font-semibold">Medidas del bulto</legend><div className="grid grid-cols-2 gap-3"><label className="text-sm">Unidades por bulto<input className={`${field} mt-1`} type="number" min="1" step="1" value={editing.units_per_case ?? ''} onChange={event => setEditing({ ...editing, units_per_case: event.target.value })} /></label><label className="text-sm">Largo (cm)<input className={`${field} mt-1`} type="number" min="0.01" step="0.01" value={editing.length_cm ?? ''} onChange={event => setEditing({ ...editing, length_cm: event.target.value })} /></label><label className="text-sm">Ancho (cm)<input className={`${field} mt-1`} type="number" min="0.01" step="0.01" value={editing.width_cm ?? ''} onChange={event => setEditing({ ...editing, width_cm: event.target.value })} /></label><label className="text-sm">Alto opcional (cm)<input className={`${field} mt-1`} type="number" min="0.01" step="0.01" value={editing.height_cm ?? ''} onChange={event => setEditing({ ...editing, height_cm: event.target.value })} /></label></div></fieldset>
                <div className="space-y-2">{[['can_be_base', 'Puede formar la base'], ['stable', 'Es estable'], ['allow_incomplete_floor', 'Permite piso incompleto'], ['enabled', 'Regla activa']].map(([key, label]) => <label key={key} className="flex min-h-12 items-center gap-3 rounded-xl border p-3"><input type="checkbox" checked={editing[key]} onChange={event => setEditing({ ...editing, [key]: event.target.checked })} /><span className="font-medium">{label}</span></label>)}</div>
                </div><div className="sticky bottom-0 z-10 grid gap-2 rounded-b-2xl border-t bg-white p-4"><button disabled={busy} className="min-h-12 w-full rounded-xl bg-brand-500 px-5 font-semibold text-white">{busy ? 'Guardando…' : 'Guardar criterio'}</button><button type="button" className={`${button} w-full min-h-12`} onClick={() => setEditing(null)}>Cancelar</button></div>
            </form>}
        </section>
    </div>
}
