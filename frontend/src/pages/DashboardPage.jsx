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
import { formatNumber, todayInputValue } from '../utils/format'

const KPI_CONFIG = [
    { key: 'pdfs_procesados', label: 'PDFs procesados', color: 'bg-brand-50 text-brand-500' },
    { key: 'repartos_procesados', label: 'Repartos', color: 'bg-violet-50 text-violet-500' },
    { key: 'camiones_procesados', label: 'Camiones', color: 'bg-sky-50 text-sky-500' },
    { key: 'bultos_manuales', label: 'Bultos picking equiv.', color: 'bg-orange-50 text-orange-500' },
    { key: 'bultos_palletizados', label: 'Bultos pallets', color: 'bg-emerald-50 text-emerald-500' },
    { key: 'total_bultos', label: 'Total bultos', color: 'bg-brand-50 text-brand-600' },
    { key: 'pct_pallets_completos', label: 'Eficiencia pallets', color: 'bg-teal-50 text-teal-600', suffix: '%' },
    { key: 'skus_no_encontrados', label: 'SKUs sin maestro', color: 'bg-amber-50 text-amber-500' },
]

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
    const [filters, setFilters] = useState({ desde: '', hasta: '' })
    const [error, setError] = useState(null)

    useEffect(() => {
        async function loadDashboard() {
            try {
                const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value))
                const [summaryResponse, chartsResponse] = await Promise.all([
                    axiosClient.get('/dashboard/summary', { params }),
                    axiosClient.get('/dashboard/charts', { params }),
                ])
                setMetrics(summaryResponse.data)
                setCharts(chartsResponse.data)
                setError(null)
            } catch {
                setError('No se pudo cargar el resumen operativo.')
            }
        }
        loadDashboard()
    }, [filters])

    const setFilter = (key) => (event) => {
        setFilters((prev) => ({ ...prev, [key]: event.target.value }))
    }

    const clearFilters = () => {
        setFilters({ desde: '', hasta: '' })
    }

    const selectToday = () => {
        const today = todayInputValue()
        setFilters({ desde: today, hasta: today })
    }

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            <div className="mb-8">
                <h1 className="text-2xl font-semibold text-slate-900">Dashboard operativo</h1>
                <p className="mt-1 text-sm text-slate-500">KPIs en bultos equivalentes: picking, pallets completos y total operativo.</p>
            </div>

            <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="grid gap-x-4 gap-y-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto_auto] sm:items-end">
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

            {error && (
                <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                    {error}
                </div>
            )}

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {KPI_CONFIG.map((config) => (
                    <KpiCard key={config.key} config={config} metrics={metrics} />
                ))}
            </div>

            <div className="mt-6 grid gap-6 xl:grid-cols-3">
                <div className="xl:col-span-2">
                    <RatioPanel ratio={metrics?.operacion_ratio || charts?.pallets_vs_picking} />
                </div>
                <BarList
                    title="Bultos picking equiv. por division"
                    subtitle="Separacion operativa por complejidad de producto."
                    rows={charts?.picking_por_division || []}
                    labelKey="division"
                />
            </div>

            <div className="mt-6 grid gap-6 xl:grid-cols-2">
                <BarList
                    title="Bultos picking equiv. por sucursal"
                    subtitle="Comparacion por deposito o sucursal de origen."
                    rows={charts?.picking_por_sucursal || []}
                    labelKey="sucursal"
                />
                <SeasonPanel rows={charts?.productividad_por_temporada || []} />
            </div>
        </div>
    )
}

export default DashboardPage
