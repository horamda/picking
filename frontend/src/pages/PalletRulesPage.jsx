import { useEffect, useMemo, useState } from 'react'
import api from '../api/axiosClient'

import { NavIcon } from '../components/NavIcon'

const field = 'w-full rounded-lg border bg-white px-3 py-2'
const button = 'btn-quiet rounded-lg px-4 text-sm font-medium disabled:opacity-40'
const primary = 'btn-primary rounded-lg px-4 text-sm font-medium disabled:opacity-40'
const blank = rule => ({ business_unit: rule.business_unit, caliber: rule.caliber, can_be_base: false, stable: false, allow_incomplete_floor: false, size_rank: 0, enabled: true, units_per_case: '', length_cm: '', width_cm: '', height_cm: '', missing_physical: ['units_per_case', 'length_cm', 'width_cm'] })
const PHYSICAL = { units_per_case: 'unidades/bulto', length_cm: 'largo', width_cm: 'ancho' }

const COLUMNS = [['caliber', 'Calibre', 'text-left'], ['business_unit', 'Unidad', 'text-left'], ['articles', 'Artículos', 'text-center col-opt'], ['can_be_base', 'Base', 'text-center'], ['stable', 'Estable', 'text-center'], ['size_rank', 'Orden', 'text-center'], ['status', 'Estado', 'text-left']]

function Badge({ rule }) {
    if (rule.missing_rule) return <span className="badge badge--danger">Falta configurar</span>
    if (rule.missing_floor) return <span className="badge badge--warning">Faltan pisos</span>
    if (rule.missing_physical?.length) return <span className="badge badge--warning">Faltan medidas</span>
    return <span className="badge badge--success">Listo</span>
}

function detail(rule) {
    if (rule.missing_floor) return `Falta piso en ${rule.missing_floor} artículo(s).`
    if (rule.missing_physical?.length) return `Falta completar: ${rule.missing_physical.map(item => PHYSICAL[item] || item).join(', ')}.`
    return `${rule.length_cm} × ${rule.width_cm}${rule.height_cm ? ` × ${rule.height_cm}` : ''} cm · ${rule.units_per_case} un.`
}

export default function PalletRulesPage() {
    const [data, setData] = useState({ stacking_rules: [], pending_rules: [] })
    const [query, setQuery] = useState(''), [status, setStatus] = useState('all')
    const [editing, setEditing] = useState(null), [busy, setBusy] = useState(false)
    const [sort, setSort] = useState({ key: '', dir: 1 })
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

    const sortedRows = useMemo(() => {
        const value = rule => sort.key === 'status' ? (rule.missing_rule ? 0 : rule.missing_floor ? 1 : rule.missing_physical?.length ? 2 : 3) : sort.key === 'can_be_base' || sort.key === 'stable' ? Number(Boolean(rule[sort.key])) : rule[sort.key]
        if (!sort.key) return rows
        return [...rows].sort((a, b) => { const x = value(a), y = value(b); return (typeof x === 'number' && typeof y === 'number' ? x - y : String(x ?? '').localeCompare(String(y ?? ''), 'es', { numeric: true })) * sort.dir })
    }, [rows, sort])
    const isEditing = rule => editing?.business_unit === rule.business_unit && editing?.caliber === rule.caliber
    const summary = [['Combinaciones', allRows.length], ['Listas', counts.ready], ['Pendientes', counts.pending], ['Artículos incompletos', data.incomplete_articles || 0]]
    const filters = [['all', 'Todos', allRows.length], ['ready', 'Listos', counts.ready], ['pending', 'Pendientes', counts.pending]]
    const toggles = [['can_be_base', 'Puede formar la base'], ['stable', 'Es estable'], ['allow_incomplete_floor', 'Permite piso incompleto'], ['enabled', 'Regla activa']]

    return <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
                <h1 className="text-[26px] font-semibold leading-8">Reglas del mezclador</h1>
                <p className="text-muted mt-2 max-w-3xl text-[15px] leading-[22px]">Configurá cómo se apilan los calibres. Incluye mercadería activa y no anulada aunque no esté habilitada para dispositivos móviles.</p>
            </div>
            <div className="flex flex-wrap gap-2">
                <button type="button" disabled={busy} className={button} onClick={exportExcel}>Exportar Excel</button>
                <button type="button" disabled={busy || !data.incomplete_articles} className={button} onClick={exportIncomplete}>Exportar artículos incompletos</button>
            </div>
        </header>
        {error && <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        {message && <p className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</p>}

        <section className="stat-strip grid grid-cols-2 lg:grid-cols-4" aria-label="Resumen">
            {summary.map(([label, value]) => <div key={label} className="px-5 py-4">
                <p className="text-muted text-[13px]">{label}</p>
                <p className="mt-1 text-[26px] font-medium leading-8 tabular-nums">{value}</p>
            </div>)}
        </section>

        <details className="tile rounded-2xl px-5 py-3">
            <summary className="flex cursor-pointer items-center text-sm font-medium">Cómo se usan estas reglas</summary>
            <ul className="text-muted grid gap-2 pb-2 pt-1 text-sm sm:grid-cols-2">
                <li><span className="font-medium text-slate-900">Base:</span> puede iniciar el pallet cuando completa el piso.</li>
                <li><span className="font-medium text-slate-900">Estable:</span> soporta productos arriba.</li>
                <li><span className="font-medium text-slate-900">Orden:</span> el valor mayor se ubica debajo.</li>
                <li><span className="font-medium text-slate-900">Faltan pisos:</span> completalos con la plantilla logística.</li>
            </ul>
        </details>

        <section className="tile rounded-2xl p-5">
            <h2 className="text-[15px] font-semibold">Completar reglas con Excel</h2>
            <p className="text-muted mt-1 text-sm">Exportá el archivo actual, completá unidades por bulto y medidas en centímetros, y volvé a importarlo. Las celdas vacías conservan el dato existente.</p>
            <div className="mt-4 flex flex-wrap items-center gap-2">
                <label className={`${button} inline-flex min-h-10 cursor-pointer items-center gap-2 ${busy ? 'pointer-events-none opacity-40' : ''}`}>
                    <NavIcon name="imports" size={16} />Elegir archivo
                    <input type="file" className="sr-only" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={busy} onChange={event => { setExcelFile(event.target.files?.[0] || null); setExcelResult(null) }} />
                </label>
                <span className="text-muted mr-2 min-w-0 truncate text-sm">{excelFile ? excelFile.name : 'Ningún archivo seleccionado'}</span>
                <button type="button" className={button} disabled={!excelFile || busy} onClick={() => importExcel(false)}>Vista previa</button>
                <button type="button" className={primary} disabled={!excelFile || busy || !excelResult || excelResult.applied || !excelResult.updated} onClick={() => importExcel(true)}>Aplicar cambios</button>
            </div>
            {excelResult && <div className="stat-strip mt-4 grid sm:grid-cols-3">
                {[['Filas', excelResult.total], ['Cambiarían', excelResult.updated], ['Sin cambios', excelResult.unchanged]].map(([label, value]) => <div key={label} className="px-4 py-3">
                    <p className="text-muted text-[13px]">{label}</p>
                    <p className="mt-0.5 text-xl font-medium tabular-nums">{value}</p>
                </div>)}
            </div>}
        </section>

        <section className={`grid items-start gap-6 ${editing ? 'lg:grid-cols-[minmax(0,1fr)_minmax(320px,380px)]' : ''}`}>
            <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3">
                    <label className="min-w-0 flex-1 basis-64"><span className="sr-only">Buscar reglas</span><input className={field} value={query} onChange={event => setQuery(event.target.value)} placeholder="Buscar unidad de negocio o calibre" /></label>
                    <div className="segmented" role="group" aria-label="Filtrar reglas por estado">
                        {filters.map(([key, label, count]) => <button type="button" key={key} aria-pressed={status === key} onClick={() => setStatus(key)}>{label}<span className="tabular-nums opacity-70">{count}</span></button>)}
                    </div>
                </div>
                <p className="text-muted mt-3 text-[13px]">{rows.length} combinaciones visibles</p>
                <div className="tile thin-scroll mt-3 overflow-x-auto rounded-2xl">
                    <table className={`rule-table w-full border-collapse text-sm ${editing ? 'is-narrow' : ''}`}>
                        <thead>
                            <tr>
                                {COLUMNS.map(([key, label, align]) => <th key={key} scope="col" aria-sort={sort.key === key ? (sort.dir > 0 ? 'ascending' : 'descending') : 'none'} className={align}>
                                    <button type="button" className="rule-sort" onClick={() => setSort(current => ({ key, dir: current.key === key ? -current.dir : 1 }))}>{label}<span aria-hidden="true" className="w-2 text-[10px]">{sort.key === key ? (sort.dir > 0 ? '▲' : '▼') : ''}</span></button>
                                </th>)}
                                <th scope="col" className="col-opt text-left">Bulto</th>
                                <th scope="col"><span className="sr-only">Acciones</span></th>
                            </tr>
                        </thead>
                        <tbody>
                            {sortedRows.map(rule => <tr key={`${rule.business_unit}-${rule.caliber}`} className={isEditing(rule) ? 'is-selected' : ''} onClick={() => setEditing({ ...rule })}>
                                <th scope="row" className="text-left font-medium">{rule.caliber}</th>
                                <td className="text-muted text-left capitalize">{String(rule.business_unit || '').toLowerCase()}</td>
                                <td className="col-opt text-center tabular-nums">{rule.articles || 0}</td>
                                <td className="text-center">{rule.can_be_base ? 'Sí' : 'No'}</td>
                                <td className="text-center">{rule.stable ? 'Sí' : 'No'}</td>
                                <td className="text-center tabular-nums">{rule.size_rank}</td>
                                <td className="text-left"><Badge rule={rule} /></td>
                                <td className="col-opt text-muted text-left text-[13px] tabular-nums" title={detail(rule)}>{rule.missing_floor || rule.missing_physical?.length ? '—' : detail(rule)}</td>
                                <td className="text-right"><button type="button" className="rule-edit" onClick={() => setEditing({ ...rule })}>{rule.missing_rule ? 'Configurar' : 'Editar'}</button></td>
                            </tr>)}
                            {!rows.length && <tr><td colSpan={9} className="text-muted py-10 text-center">No hay resultados para estos filtros.</td></tr>}
                        </tbody>
                    </table>
                </div>
            </div>

            {editing && <form onSubmit={save} className="tile thin-scroll rounded-2xl lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto" aria-label={`Editar regla ${editing.caliber}`}>
                <div className="panel-head sticky top-0 z-10 flex items-start justify-between gap-3 rounded-t-2xl border-b px-5 py-4">
                    <div className="min-w-0">
                        <p className="text-muted text-xs">Editando regla</p>
                        <h2 className="mt-0.5 truncate text-base font-semibold">{editing.caliber}</h2>
                        <p className="text-muted text-[13px]"><span className="capitalize">{String(editing.business_unit || '').toLowerCase()}</span> · {editing.articles || 0} artículos</p>
                    </div>
                    <button type="button" aria-label="Cerrar editor" className="btn-quiet flex h-10 w-10 shrink-0 items-center justify-center rounded-lg" onClick={() => setEditing(null)}><NavIcon name="close" size={16} /></button>
                </div>
                <div className="space-y-5 px-5 py-5">
                    <label className="block text-sm font-medium">Orden físico del calibre<span className="text-muted mt-0.5 block text-xs font-normal">Los valores mayores se colocan debajo.</span><input className={`${field} mt-2`} type="number" min="0" required value={editing.size_rank} onChange={event => setEditing({ ...editing, size_rank: event.target.value })} /></label>
                    <fieldset>
                        <legend className="text-sm font-medium">Medidas del bulto</legend>
                        <div className="mt-2 grid grid-cols-2 gap-3">
                            <label className="text-muted text-[13px]">Unidades por bulto<input className={`${field} mt-1`} type="number" min="1" step="1" value={editing.units_per_case ?? ''} onChange={event => setEditing({ ...editing, units_per_case: event.target.value })} /></label>
                            <label className="text-muted text-[13px]">Largo (cm)<input className={`${field} mt-1`} type="number" min="0.01" step="0.01" value={editing.length_cm ?? ''} onChange={event => setEditing({ ...editing, length_cm: event.target.value })} /></label>
                            <label className="text-muted text-[13px]">Ancho (cm)<input className={`${field} mt-1`} type="number" min="0.01" step="0.01" value={editing.width_cm ?? ''} onChange={event => setEditing({ ...editing, width_cm: event.target.value })} /></label>
                            <label className="text-muted text-[13px]">Alto opcional (cm)<input className={`${field} mt-1`} type="number" min="0.01" step="0.01" value={editing.height_cm ?? ''} onChange={event => setEditing({ ...editing, height_cm: event.target.value })} /></label>
                        </div>
                    </fieldset>
                    <div className="check-list">
                        {toggles.map(([key, label]) => <label key={key} className="flex min-h-11 cursor-pointer items-center gap-3 text-sm"><input type="checkbox" checked={editing[key]} onChange={event => setEditing({ ...editing, [key]: event.target.checked })} />{label}</label>)}
                    </div>
                </div>
                <div className="panel-head sticky bottom-0 z-10 flex gap-2 rounded-b-2xl border-t px-5 py-4">
                    <button disabled={busy} className={`${primary} flex-1`}>{busy ? 'Guardando…' : 'Guardar criterio'}</button>
                    <button type="button" className={button} onClick={() => setEditing(null)}>Cancelar</button>
                </div>
            </form>}
        </section>
    </div>
}
