import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'
import {
    headerCellClass,
    headerNumberCellClass,
    headerRowClass,
    numberCellClass,
    strongCellClass,
    tableClass,
    totalCellClass,
    totalHeaderCellClass,
    totalLabelCellClass,
    totalNumberCellClass,
    totalRowClass,
    totalRowValueCellClass,
} from '../components/tableStyles'
import { formatDate, formatNumber, todayInputValue } from '../utils/format'

const KPI_CONFIG = [
    { key: 'pdfs_procesados', label: 'PDFs procesados', color: 'bg-brand-50 text-brand-500' },
    { key: 'repartos_procesados', label: 'Repartos', color: 'bg-blue-50 text-brand-600' },
    { key: 'camiones_procesados', label: 'Camiones', color: 'bg-sky-50 text-sky-500' },
    { key: 'bultos_manuales', label: 'Bultos picking equiv.', color: 'bg-orange-50 text-orange-500' },
    { key: 'bultos_palletizados', label: 'Bultos pallets', color: 'bg-emerald-50 text-emerald-500' },
    { key: 'total_bultos', label: 'Total bultos', color: 'bg-brand-50 text-brand-600' },
    { key: 'pct_pallets_completos', label: 'Eficiencia pallets', color: 'bg-teal-50 text-teal-600', suffix: '%' },
    { key: 'skus_no_encontrados', label: 'SKUs sin maestro', color: 'bg-amber-50 text-amber-500' },
]

const OPERATIONS_KPIS = [
    { key: 'planillas_programadas', label: 'Planillas programadas' },
    { key: 'planillas_pendientes', label: 'Planillas pendientes' },
    { key: 'planillas_en_preparacion', label: 'En preparación' },
    { key: 'planillas_finalizadas', label: 'Planillas finalizadas' },
    { key: 'avance_pct', label: 'Avance operativo', suffix: '%' },
    { key: 'operarios_en_proceso', label: 'Operarios en proceso' },
    { key: 'operarios_disponibles', label: 'Operarios disponibles' },
    { key: 'bultos_confirmados', label: 'Bultos confirmados' },
    { key: 'bultos_pendientes', label: 'Bultos pendientes' },
    { key: 'productividad_bultos_hora', label: 'Productividad', suffix: ' b/h' },
    { key: 'diferencias_detectadas', label: 'Diferencias detectadas' },
    { key: 'cargas_liberadas', label: 'Cargas liberadas' },
    { key: 'cargas_demoradas', label: 'Cargas demoradas' },
    { key: 'alertas_operativas', label: 'Alertas operativas' },
]

const COVERAGE_KEYS = {
    operarios_disponibles: 'operarios_disponibles',
    bultos_pendientes: 'bultos_pendientes',
    cargas_demoradas: 'cargas_demoradas',
}

function OperationsCard({ config, data }) {
    const value = data?.metrics?.[config.key]
    const unavailable = value === null || value === undefined
    const reason = data?.coverage?.[COVERAGE_KEYS[config.key]]
    return <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className={`text-2xl font-semibold ${unavailable ? 'text-slate-400' : 'text-slate-900'}`}>
            {unavailable ? 'No medido' : `${formatNumber(value)}${config.suffix || ''}`}
        </p>
        <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{config.label}</p>
        {reason && <p className="mt-2 text-xs leading-4 text-amber-700">{reason}</p>}
    </article>
}

function OperationsCenter({ data, lastUpdated }) {
    const coverage = data?.coverage?.respuestas_medibles_pct
    return <section className="mb-8">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
                <p className="text-xs font-semibold uppercase tracking-[.18em] text-brand-600">Centro de operaciones</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-900">Seguimiento de preparación real</h2>
                <p className="mt-1 text-sm text-slate-500">Datos confirmados por el servidor. No incluye los controles como producción adicional.</p>
            </div>
            <div className="text-right text-xs text-slate-500">
                <p>{lastUpdated ? `Actualizado ${lastUpdated.toLocaleTimeString('es-AR')}` : 'Cargando operación…'}</p>
                <p>{coverage == null ? 'Sin respuestas en el período' : `${formatNumber(coverage)}% de respuestas con cantidad medible`}</p>
            </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-7">
            {OPERATIONS_KPIS.map(config => <OperationsCard key={config.key} config={config} data={data} />)}
        </div>
        <div className="mt-5 overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>
                    {['Fecha', 'Sucursal', 'Camión', 'Planilla', 'Estado', 'Avance'].map(label => <th key={label} className="px-4 py-3">{label}</th>)}
                </tr></thead>
                <tbody>{(data?.rows || []).map(row => <tr key={row.id} className="border-t border-slate-100">
                    <td className="px-4 py-3">{formatDate(row.fecha)}</td><td className="px-4 py-3">{row.sucursal}</td>
                    <td className="px-4 py-3 font-medium">{row.camion}</td><td className="px-4 py-3">{row.reparto}</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${row.estado === 'finalizado' ? 'bg-emerald-50 text-emerald-700' : row.estado === 'en_preparacion' ? 'bg-sky-50 text-sky-700' : 'bg-amber-50 text-amber-700'}`}>{row.estado.replaceAll('_', ' ')}</span></td>
                    <td className="px-4 py-3">{row.avance == null ? 'Sin tareas' : `${formatNumber(row.avance)}% · ${row.completados}/${row.total} ${row.unidad}`}</td>
                </tr>)}</tbody>
            </table>
            {data && !data.rows.length && <p className="p-6 text-center text-sm text-slate-500">No hay planillas para los filtros elegidos.</p>}
            {data?.rows_total > data?.rows?.length && <p className="border-t p-3 text-center text-xs text-slate-500">Se muestran las primeras {data.rows.length} de {data.rows_total} planillas.</p>}
        </div>
    </section>
}

function duration(seconds) {
    if (seconds == null) return '—'
    const minutes = Math.round(Number(seconds) / 60)
    return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`
}

function ProductivityPanel({ data }) {
    const rate = value => value == null ? 'No medido' : `${formatNumber(value)} b/h`
    return <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
            <div><p className="text-xs font-semibold uppercase tracking-[.18em] text-brand-600">Productividad</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Rendimiento por operario</h2><p className="mt-1 max-w-3xl text-sm text-slate-500">Bultos confirmados por hora activa. Picking y pallets completos se muestran separados porque su complejidad no es equivalente.</p></div>
            <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">Las diferencias de stock no se atribuyen al operario.</p>
        </div>
        <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[1100px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>
                    {['Operario', 'Bultos', 'Líneas', 'Tiempo activo', 'Pausas', 'Total b/h', 'Picking b/h', 'Pallets b/h', 'Tareas finalizadas', 'Diferencias', 'Cobertura'].map(label => <th key={label} className="px-3 py-3">{label}</th>)}
                </tr></thead>
                <tbody>{(data?.rows || []).map(row => <tr key={row.user_id} className="border-t border-slate-100">
                    <td className="px-3 py-3 font-semibold text-slate-900">{row.username}</td>
                    <td className="px-3 py-3 tabular-nums">{formatNumber(row.bultos)}</td><td className="px-3 py-3 tabular-nums">{formatNumber(row.lineas)}</td>
                    <td className="px-3 py-3 whitespace-nowrap">{duration(row.tiempo_efectivo_segundos)}</td><td className="px-3 py-3 whitespace-nowrap">{duration(row.tiempo_pausa_segundos)}</td>
                    <td className="px-3 py-3 whitespace-nowrap font-semibold">{rate(row.productividad_bultos_hora)}</td>
                    <td className="px-3 py-3 whitespace-nowrap">{rate(row.modalidades?.picking?.productividad_bultos_hora)}</td>
                    <td className="px-3 py-3 whitespace-nowrap">{rate(row.modalidades?.pallets_completos?.productividad_bultos_hora)}</td>
                    <td className="px-3 py-3 tabular-nums">{row.tareas_finalizadas}</td><td className="px-3 py-3 tabular-nums">{row.diferencias_atribuidas}</td>
                    <td className="px-3 py-3">{row.cobertura_pct == null ? 'Sin respuestas' : `${formatNumber(row.cobertura_pct)}%`}</td>
                </tr>)}</tbody>
            </table>
            {data && !data.rows.length && <p className="py-8 text-center text-sm text-slate-500">No hay trabajo de preparación para estos filtros.</p>}
        </div>
        <p className="mt-4 text-xs text-slate-500">“Líneas” representa productos respondidos en tareas de preparación. El total combinado es informativo; para comparar personas debe usarse la misma modalidad y una complejidad equivalente.</p>
    </section>
}

function QualityPanel({ data }) {
    const metrics = data?.metrics || {}
    const percentage = value => value == null ? 'No medido' : `${formatNumber(value)}%`
    const cards = [
        ['Exactitud de picking', metrics.exactitud_picking_pct],
        ['Diferencias de stock', metrics.diferencias_stock_pct],
        ['Retrabajo', metrics.retrabajo_pct],
        ['Exactitud segundo control', metrics.exactitud_segundo_control_lineas_pct],
        ['Exactitud por unidades', metrics.exactitud_segundo_control_unidades_pct],
    ]
    return <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
            <div><p className="text-xs font-semibold uppercase tracking-[.18em] text-brand-600">Calidad y diferencias</p><h2 className="mt-1 text-xl font-semibold text-slate-900">Exactitud, causas y revisiones</h2><p className="mt-1 max-w-3xl text-sm text-slate-500">Los errores atribuibles al picking se muestran separados de las diferencias de stock. Una confirmación correcta de faltante no penaliza al segundo control.</p></div>
            <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">La exactitud actual es por productos respondidos, no por líneas originales del PDF.</p>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{cards.map(([label, value]) => <article key={label} className="rounded-xl bg-slate-50 p-4"><p className={`text-2xl font-semibold ${value == null ? 'text-slate-400' : 'text-slate-900'}`}>{percentage(value)}</p><p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p></article>)}</div>
        <div className="mt-5 flex flex-wrap gap-2">{(data?.causes || []).map(row => <span key={row.cause} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">{row.cause}: <b>{row.count}</b></span>)}{data && !data.causes.length && <span className="text-sm text-slate-500">Sin diferencias para los filtros elegidos.</span>}</div>
        <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[1050px] text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr>{['Fecha', 'Camión', 'Planilla', 'SKU', 'Origen', 'Causa', 'Esperado', 'Real', 'Responsable', 'Detectó', 'Estado'].map(label => <th key={label} className="px-3 py-3">{label}</th>)}</tr></thead>
                <tbody>{(data?.incidents || []).map((row, index) => <tr key={`${row.load_id}-${row.product_key}-${row.saved_at || index}`} className="border-t border-slate-100"><td className="px-3 py-3 whitespace-nowrap">{formatDate(row.fecha)}</td><td className="px-3 py-3">{row.camion}</td><td className="px-3 py-3">{row.reparto}</td><td className="px-3 py-3 font-medium">{row.sku}</td><td className="px-3 py-3">{row.origin}</td><td className="px-3 py-3">{row.cause}</td><td className="px-3 py-3 whitespace-nowrap">{row.expected_b ?? '—'} b + {row.expected_u ?? '—'} u</td><td className="px-3 py-3 whitespace-nowrap">{row.actual_b ?? '—'} b + {row.actual_u ?? '—'} u</td><td className="px-3 py-3">{row.responsible_username || '—'}</td><td className="px-3 py-3">{row.detected_username || '—'}</td><td className="px-3 py-3"><span className="rounded-full bg-slate-100 px-2 py-1 text-xs">{row.status?.replaceAll('_', ' ')}</span></td></tr>)}</tbody>
            </table>
        </div>
        <p className="mt-4 text-xs text-slate-500">La exactitud del segundo control por unidades permanece “No medido” hasta contar con cantidades esperadas y verificadas consistentes para todo el período.</p>
    </section>
}

function KpiCard({ config, metrics }) {
    const value = metrics ? `${formatNumber(metrics[config.key])}${config.suffix || ''}` : null
    return (
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className={`inline-flex h-9 w-9 items-center justify-center rounded-xl ${config.color}`}>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75h16.5v16.5H3.75V3.75zm4.5 12h7.5m-7.5-4.5h7.5m-7.5-4.5h7.5" />
                </svg>
            </div>
            {metrics ? (
                <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
            ) : (
                <div className="mt-3 h-8 w-16 animate-pulse rounded-xl bg-slate-100" />
            )}
            <p className="mt-1 text-xs font-medium uppercase tracking-[0.15em] text-slate-400">{config.label}</p>
        </div>
    )
}

function RatioPanel({ ratio }) {
    const pctPallets = ratio?.pct_pallets || 0
    const pctPicking = ratio?.pct_picking || 0
    return (
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <h2 className="text-lg font-semibold text-slate-900">Bultos pallets vs bultos picking</h2>
                    <p className="mt-1 text-sm text-slate-500">Base en bultos equivalentes: picking + pallets = total bultos.</p>
                </div>
                <div className="text-left lg:text-right">
                    <p className="text-3xl font-semibold text-slate-900">{formatNumber(pctPallets)}%</p>
                    <p className="text-xs font-medium uppercase tracking-[0.15em] text-slate-400">palletizado</p>
                </div>
            </div>
            <div className="mt-5 h-4 overflow-hidden rounded-full bg-orange-100">
                <div className="h-full bg-emerald-500" style={{ width: `${Math.min(pctPallets, 100)}%` }} />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl bg-emerald-50 px-4 py-3">
                    <p className="text-sm font-semibold text-emerald-800">{formatNumber(pctPallets)}% bultos pallets</p>
                    <p className="mt-1 text-xs text-emerald-700">{formatNumber(ratio?.bultos_palletizados)} bultos</p>
                </div>
                <div className="rounded-2xl bg-orange-50 px-4 py-3">
                    <p className="text-sm font-semibold text-orange-800">{formatNumber(pctPicking)}% picking equiv.</p>
                    <p className="mt-1 text-xs text-orange-700">{formatNumber(ratio?.bultos_manuales)} bultos</p>
                </div>
                <div className="rounded-2xl bg-brand-50 px-4 py-3">
                    <p className="text-sm font-semibold text-brand-800">Total bultos</p>
                    <p className="mt-1 text-xs text-brand-700">{formatNumber(ratio?.total_bultos)} bultos</p>
                </div>
            </div>
        </section>
    )
}

function BarList({ title, subtitle, rows, labelKey, valueKey = 'bultos_pick' }) {
    const maxValue = Math.max(...(rows || []).map((row) => Number(row[valueKey] || 0)), 0)
    return (
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5">
                <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
                <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
            </div>
            <div className="space-y-4">
                {(rows || []).map((row) => {
                    const value = Number(row[valueKey] || 0)
                    const width = maxValue > 0 ? (value / maxValue) * 100 : 0
                    return (
                        <div key={row[labelKey]}>
                            <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                                <span className="truncate font-medium text-slate-700">{row[labelKey]}</span>
                                <span className="shrink-0 text-slate-500">{formatNumber(value)}</span>
                            </div>
                            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                                <div className="h-full rounded-full bg-brand-500" style={{ width: `${width}%` }} />
                            </div>
                            <p className="mt-1 text-xs text-slate-400">{formatNumber(row.porcentaje)}% del picking equivalente</p>
                        </div>
                    )
                })}
                {(!rows || rows.length === 0) && (
                    <div className="rounded-2xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                        Sin datos procesados.
                    </div>
                )}
            </div>
        </section>
    )
}

function SeasonPanel({ rows }) {
    const totalPalletBultos = (rows || []).reduce((acc, row) => acc + (row.bultos_palletizados || 0), 0)
    const totalPickingBultos = (rows || []).reduce((acc, row) => acc + (row.bultos_manuales || 0), 0)
    const totalBultos = (rows || []).reduce((acc, row) => acc + (row.total_bultos || 0), 0)
    return (
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-5">
                <h2 className="text-lg font-semibold text-slate-900">Productividad por temporada</h2>
                <p className="mt-1 text-sm text-slate-500">Compara bultos de picking equivalente, pallets completos y total por periodo.</p>
            </div>
            <div className="overflow-x-auto">
                <table className={tableClass}>
                    <thead>
                        <tr className={headerRowClass}>
                            <th className={headerCellClass}>Temporada</th>
                            <th className={headerNumberCellClass}>% pallets</th>
                            <th className={headerNumberCellClass}>% picking</th>
                            <th className={headerNumberCellClass}>Bultos picking equiv.</th>
                            <th className={headerNumberCellClass}>Bultos pallets</th>
                            <th className={totalHeaderCellClass}>Total bultos</th>
                        </tr>
                    </thead>
                    <tbody>
                        {(rows || []).map((row) => (
                            <tr key={row.temporada}>
                                <td className={strongCellClass}>{row.temporada}</td>
                                <td className={numberCellClass}>{formatNumber(row.pct_pallets)}%</td>
                                <td className={numberCellClass}>{formatNumber(row.pct_picking)}%</td>
                                <td className={numberCellClass}>{formatNumber(row.bultos_manuales)}</td>
                                <td className={numberCellClass}>{formatNumber(row.bultos_palletizados)}</td>
                                <td className={totalCellClass}>{formatNumber(row.total_bultos)}</td>
                            </tr>
                        ))}
                        {(!rows || rows.length === 0) && (
                            <tr>
                                <td colSpan={6} className="border border-slate-200 py-8 text-center text-sm text-slate-500">Sin datos procesados.</td>
                            </tr>
                        )}
                    </tbody>
                    {(rows || []).length > 0 && (
                        <tfoot>
                            <tr className={totalRowClass}>
                                <td className={totalLabelCellClass} colSpan={3}>TOTAL</td>
                                <td className={totalNumberCellClass}>{formatNumber(totalPickingBultos)}</td>
                                <td className={totalNumberCellClass}>{formatNumber(totalPalletBultos)}</td>
                                <td className={totalRowValueCellClass}>{formatNumber(totalBultos)}</td>
                            </tr>
                        </tfoot>
                    )}
                </table>
            </div>
        </section>
    )
}

function DashboardPage() {
    const [metrics, setMetrics] = useState(null)
    const [charts, setCharts] = useState(null)
    const [operations, setOperations] = useState(null)
    const [productivity, setProductivity] = useState(null)
    const [quality, setQuality] = useState(null)
    const [lastUpdated, setLastUpdated] = useState(null)
    const [filters, setFilters] = useState({ desde: '', hasta: '', sucursal: '', camion: '', reparto: '', operario: '', estado: '' })
    const [error, setError] = useState(null)

    useEffect(() => {
        let active = true, timer, controller
        async function loadDashboard() {
            controller?.abort()
            controller = new AbortController()
            try {
                const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value))
                const legacyParams = Object.fromEntries(['desde', 'hasta', 'sucursal', 'reparto']
                    .map(key => [key, filters[key]]).filter(([, value]) => value))
                const [summaryResponse, chartsResponse, operationsResponse, productivityResponse, qualityResponse] = await Promise.all([
                    axiosClient.get('/dashboard/summary', { params: legacyParams, signal: controller.signal }),
                    axiosClient.get('/dashboard/charts', { params: legacyParams, signal: controller.signal }),
                    axiosClient.get('/dashboard/operations', { params, signal: controller.signal }),
                    axiosClient.get('/dashboard/productivity', { params, signal: controller.signal }),
                    axiosClient.get('/dashboard/quality', { params, signal: controller.signal }),
                ])
                if (active) {
                    setMetrics(summaryResponse.data); setCharts(chartsResponse.data); setOperations(operationsResponse.data)
                    setProductivity(productivityResponse.data)
                    setQuality(qualityResponse.data)
                    setLastUpdated(new Date()); setError(null)
                }
            } catch {
                if (active && !controller.signal.aborted) setError('No se pudo cargar el resumen operativo. Se conservaron los últimos datos recibidos.')
            } finally {
                if (active) timer = setTimeout(loadDashboard, 15000)
            }
        }
        loadDashboard()
        return () => { active = false; clearTimeout(timer); controller?.abort() }
    }, [filters])

    const setFilter = (key) => (event) => {
        setFilters((prev) => ({ ...prev, [key]: event.target.value }))
    }

    const clearFilters = () => {
        setFilters({ desde: '', hasta: '', sucursal: '', camion: '', reparto: '', operario: '', estado: '' })
    }

    const selectToday = () => {
        const today = todayInputValue()
        setFilters((previous) => ({ ...previous, desde: today, hasta: today }))
    }

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            <div className="mb-8">
                <h1 className="text-2xl font-semibold text-slate-900">Dashboard operativo</h1>
                <p className="mt-1 text-sm text-slate-500">KPIs en bultos equivalentes: picking, pallets completos y total operativo.</p>
            </div>

            <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 xl:grid-cols-4">
                    <label className="flex flex-col gap-1">
                        <span className="text-xs font-medium text-slate-500">Desde reparto</span>
                        <input
                            type="date"
                            value={filters.desde}
                            onChange={setFilter('desde')}
                            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                    </label>
                    <label className="flex flex-col gap-1">
                        <span className="text-xs font-medium text-slate-500">Hasta reparto</span>
                        <input
                            type="date"
                            value={filters.hasta}
                            onChange={setFilter('hasta')}
                            className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                    </label>
                    <label className="flex flex-col gap-1"><span className="text-xs font-medium text-slate-500">Sucursal</span><select value={filters.sucursal} onChange={setFilter('sucursal')} className="rounded-xl border border-slate-300 px-3 py-2 text-sm"><option value="">Todas</option>{operations?.options?.sucursales.map(value => <option key={value}>{value}</option>)}</select></label>
                    <label className="flex flex-col gap-1"><span className="text-xs font-medium text-slate-500">Camión</span><select value={filters.camion} onChange={setFilter('camion')} className="rounded-xl border border-slate-300 px-3 py-2 text-sm"><option value="">Todos</option>{operations?.options?.camiones.map(value => <option key={value}>{value}</option>)}</select></label>
                    <label className="flex flex-col gap-1"><span className="text-xs font-medium text-slate-500">Planilla</span><select value={filters.reparto} onChange={setFilter('reparto')} className="rounded-xl border border-slate-300 px-3 py-2 text-sm"><option value="">Todas</option>{operations?.options?.repartos.map(value => <option key={value}>{value}</option>)}</select></label>
                    <label className="flex flex-col gap-1"><span className="text-xs font-medium text-slate-500">Operario</span><select value={filters.operario} onChange={setFilter('operario')} className="rounded-xl border border-slate-300 px-3 py-2 text-sm"><option value="">Todos</option>{operations?.options?.operarios.map(value => <option key={value.id} value={value.id}>{value.username}</option>)}</select></label>
                    <label className="flex flex-col gap-1"><span className="text-xs font-medium text-slate-500">Estado</span><select value={filters.estado} onChange={setFilter('estado')} className="rounded-xl border border-slate-300 px-3 py-2 text-sm"><option value="">Todos</option><option value="pendiente">Pendiente</option><option value="en_preparacion">En preparación</option><option value="finalizado">Finalizado</option></select></label>
                    <div className="flex gap-2 self-end">
                    <button
                        type="button"
                        onClick={selectToday}
                        className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
                    >
                        Hoy
                    </button>
                    <button
                        type="button"
                        onClick={clearFilters}
                        disabled={!filters.desde && !filters.hasta}
                        className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                    >
                        Limpiar
                    </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                    {error}
                </div>
            )}

            <OperationsCenter data={operations} lastUpdated={lastUpdated} />
            <ProductivityPanel data={productivity} />
            <QualityPanel data={quality} />

            <div className="mb-4">
                <h2 className="text-xl font-semibold text-slate-900">Volumen planificado e importado</h2>
                <p className="mt-1 text-sm text-slate-500">Datos de planillas y maestro. Los filtros de estado, operario y camión se aplican únicamente al centro de operaciones.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {KPI_CONFIG.map((config) => (
                    <KpiCard key={config.key} config={config} metrics={metrics} />
                ))}
            </div>

            <div className="mt-6 grid items-start gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
                <div className="space-y-6">
                    <RatioPanel ratio={metrics?.operacion_ratio || charts?.pallets_vs_picking} />
                    <BarList
                        title="Bultos picking equiv. por sucursal"
                        subtitle="Comparacion por deposito o sucursal de origen."
                        rows={charts?.picking_por_sucursal || []}
                        labelKey="sucursal"
                    />
                </div>
                <div className="space-y-6">
                    <BarList
                        title="Bultos picking equiv. por division"
                        subtitle="Separacion operativa por complejidad de producto."
                        rows={charts?.picking_por_division || []}
                        labelKey="division"
                    />
                    <SeasonPanel rows={charts?.productividad_por_temporada || []} />
                </div>
            </div>
        </div>
    )
}

export default DashboardPage
