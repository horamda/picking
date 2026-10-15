import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import LoadControlPage from './LoadControlPage'
import axiosClient from '../api/axiosClient'
import { EstadoBadge } from '../components/Badge'
import {
    cellClass,
    headerCellClass,
    headerNumberCellClass,
    headerRowClass,
    numberCellClass,
    rowClass,
    strongCellClass,
    strongNumberCellClass,
    tableClass,
    totalCellClass,
    totalHeaderCellClass,
    totalLabelCellClass,
    totalNumberCellClass,
    totalRowClass,
    totalRowValueCellClass,
} from '../components/tableStyles'
import { formatDate, formatNumber, todayInputValue } from '../utils/format'

const tabs = [
    { id: 'control', label: 'Control de cargas' },
    { id: 'trucks', label: 'Camiones' },
    { id: 'picking-by-cancha', label: 'Picking x cancha' },
    { id: 'by-court', label: 'Por cancha' },
    { id: 'picking', label: 'Picking' },
    { id: 'pallets', label: 'Bultos pallets' },
]

function OperationsPage() {
    const [searchParams, setSearchParams] = useSearchParams()
    const selectedTab = searchParams.get('tab')
    const activeTab = tabs.some(tab => tab.id === selectedTab) ? selectedTab : 'control'
    const setActiveTab = tab => setSearchParams(tab === 'control' ? {} : { tab })
    const [rows, setRows] = useState([])
    const [loading, setLoading] = useState(false)
    const [filters, setFilters] = useState({ desde: '', hasta: '', camion: '', reparto: '', cancha: '' })

    useEffect(() => {
        if (activeTab === 'control') return
        async function loadRows() {
            setRows([])
            setLoading(true)
            try {
                const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
                const response = await axiosClient.get(`/operations/${activeTab}`, { params })
                setRows(response.data)
            } finally {
                setLoading(false)
            }
        }
        loadRows()
    }, [activeTab, filters])

    const setFilter = (key) => (e) => setFilters((prev) => ({ ...prev, [key]: e.target.value }))
    const selectToday = () => {
        const today = todayInputValue()
        setFilters((prev) => ({ ...prev, desde: today, hasta: today }))
    }
    const clearDateFilters = () => {
        setFilters((prev) => ({ ...prev, desde: '', hasta: '' }))
    }

    if (activeTab === 'control') return (
        <div>
            <details className="mx-3 mt-4 rounded-xl border border-slate-200 bg-white px-4 sm:mx-5">
                <summary className="min-h-12 cursor-pointer py-3 text-sm font-medium text-slate-600">Consultar informes de cantidades y picking</summary>
                <div className="flex flex-wrap gap-2 pb-4">{tabs.filter(tab => tab.id !== 'control').map(tab => <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)} className="min-h-12 rounded-xl border border-slate-300 px-4 py-2 text-sm">{tab.label}</button>)}</div>
            </details>
            <LoadControlPage />
        </div>
    )

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Operacion</h1>
                    <p className="mt-1 text-sm text-slate-500">Bultos equivalentes de picking, bultos de pallets completos y total operativo.</p>
                </div>
                <div className="flex gap-1.5 overflow-x-auto rounded-2xl bg-white p-1.5 shadow-sm ring-1 ring-slate-200">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            type="button"
                            onClick={() => setActiveTab(tab.id)}
                            className={`shrink-0 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors ${
                                activeTab === tab.id
                                    ? 'bg-brand-500 text-white shadow-sm'
                                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 xl:grid-cols-[repeat(5,minmax(0,1fr))_auto_auto] xl:items-end">
                    {[
                        { key: 'desde', label: 'Desde reparto', type: 'date' },
                        { key: 'hasta', label: 'Hasta reparto', type: 'date' },
                        { key: 'camion', label: 'Camion', type: 'text' },
                        { key: 'reparto', label: 'Reparto', type: 'text' },
                        { key: 'cancha', label: 'Cancha', type: 'text' },
                    ].map(({ key, label, type }) => (
                        <label key={key} className="flex flex-col gap-1">
                            <span className="text-xs font-medium text-slate-500">{label}</span>
                            <input
                                type={type}
                                value={filters[key]}
                                onChange={setFilter(key)}
                                className="rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                            />
                        </label>
                    ))}
                    <button
                        type="button"
                        onClick={selectToday}
                        className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
                    >
                        Hoy
                    </button>
                    <button
                        type="button"
                        onClick={clearDateFilters}
                        disabled={!filters.desde && !filters.hasta}
                        className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                    >
                        Limpiar fecha
                    </button>
                </div>
            </div>

            <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                    <h2 className="font-semibold text-slate-900">{tabs.find((t) => t.id === activeTab)?.label}</h2>
                    <span className="text-sm text-slate-500">{loading ? 'Cargando...' : `${rows.length} registros`}</span>
                </div>
                <div className="p-4 sm:p-6">
                    {activeTab === 'trucks' && <TruckTable rows={rows} />}
                    {activeTab === 'picking-by-cancha' && <PickingByCanchaTable rows={rows} />}
                    {activeTab === 'by-court' && <CourtTable rows={rows} />}
                    {['picking', 'pallets'].includes(activeTab) && <DetailTable rows={rows} />}
                </div>
            </section>
        </div>
    )
}

function EmptyRows() {
    return (
        <div className="py-12 text-center text-sm text-slate-400">Sin datos para los filtros seleccionados.</div>
    )
}

function PickingByCanchaTable({ rows }) {
    if (!rows.length) return <EmptyRows />
    const totalEquiv = rows.reduce((acc, r) => acc + (r.bultos_equivalentes || 0), 0)
    const totalPalletBultos = rows.reduce((acc, r) => acc + (r.bultos_palletizados || 0), 0)
    const totalPickingBultos = rows.reduce((acc, r) => acc + (r.bultos_picking_equivalentes || 0), 0)
    const totalBultos = rows.reduce((acc, r) => acc + (r.total_bultos || 0), 0)

    return (
        <div className="overflow-x-auto">
            <table className={tableClass}>
                <thead>
                    <tr className={headerRowClass}>
                        <th className={headerCellClass}>Cancha</th>
                        <th className={headerNumberCellClass}>SKUs</th>
                        <th className={headerNumberCellClass}>Bultos picking equiv.</th>
                        <th className={headerNumberCellClass}>Bultos pallets</th>
                        <th className={totalHeaderCellClass}>Total bultos</th>
                        <th className={headerNumberCellClass}>Bultos equiv.</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.cancha} className={rowClass}>
                            <td className={strongCellClass}>{row.cancha || '-'}</td>
                            <td className={numberCellClass}>{formatNumber(row.skus)}</td>
                            <td className={strongNumberCellClass}>{formatNumber(row.bultos_picking_equivalentes)}</td>
                            <td className={numberCellClass}>{formatNumber(row.bultos_palletizados)}</td>
                            <td className={totalCellClass}>{formatNumber(row.total_bultos)}</td>
                            <td className={numberCellClass}>{formatNumber(row.bultos_equivalentes)}</td>
                        </tr>
                    ))}
                </tbody>
                <tfoot>
                    <tr className={totalRowClass}>
                        <td className={totalLabelCellClass}>TOTAL</td>
                        <td className={totalNumberCellClass}>{formatNumber(rows.reduce((acc, r) => acc + (r.skus || 0), 0))}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalPickingBultos)}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalPalletBultos)}</td>
                        <td className={totalRowValueCellClass}>{formatNumber(totalBultos)}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalEquiv)}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    )
}

function CourtTable({ rows }) {
    if (!rows.length) return <EmptyRows />
    const totalEquiv = rows.reduce((acc, r) => acc + (r.bultos_equivalentes || 0), 0)
    const totalPalletBultos = rows.reduce((acc, r) => acc + (r.bultos_palletizados || 0), 0)
    const totalPickingBultos = rows.reduce((acc, r) => acc + (r.bultos_picking_equivalentes || 0), 0)
    const totalBultos = rows.reduce((acc, r) => acc + (r.total_bultos || 0), 0)
    return (
        <div className="overflow-x-auto">
            <table className={tableClass}>
                <thead>
                    <tr className={headerRowClass}>
                        <th className={headerCellClass}>Cancha</th>
                        <th className={headerCellClass}>Almacen</th>
                        <th className={headerNumberCellClass}>SKUs</th>
                        <th className={headerNumberCellClass}>Bultos picking equiv.</th>
                        <th className={headerNumberCellClass}>Bultos pallets</th>
                        <th className={totalHeaderCellClass}>Total bultos</th>
                        <th className={headerNumberCellClass}>Bultos equiv.</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={`${row.cancha}-${row.almacen}`} className={rowClass}>
                            <td className={strongCellClass}>{row.cancha || '-'}</td>
                            <td className={cellClass}>{row.almacen || '-'}</td>
                            <td className={numberCellClass}>{formatNumber(row.skus)}</td>
                            <td className={strongNumberCellClass}>{formatNumber(row.bultos_picking_equivalentes)}</td>
                            <td className={numberCellClass}>{formatNumber(row.bultos_palletizados)}</td>
                            <td className={totalCellClass}>{formatNumber(row.total_bultos)}</td>
                            <td className={numberCellClass}>{formatNumber(row.bultos_equivalentes)}</td>
                        </tr>
                    ))}
                </tbody>
                <tfoot>
                    <tr className={totalRowClass}>
                        <td className={totalLabelCellClass} colSpan={2}>TOTAL</td>
                        <td className={totalNumberCellClass}>{formatNumber(rows.reduce((acc, r) => acc + (r.skus || 0), 0))}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalPickingBultos)}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalPalletBultos)}</td>
                        <td className={totalRowValueCellClass}>{formatNumber(totalBultos)}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalEquiv)}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    )
}

function TruckTable({ rows }) {
    if (!rows.length) return <EmptyRows />
    const totalEquiv = rows.reduce((acc, r) => acc + (r.bultos_equivalentes || 0), 0)
    const totalPalletBultos = rows.reduce((acc, r) => acc + (r.bultos_palletizados || 0), 0)
    const totalPickingBultos = rows.reduce((acc, r) => acc + (r.bultos_picking_equivalentes || 0), 0)
    const totalBultos = rows.reduce((acc, r) => acc + (r.total_bultos || 0), 0)
    return (
        <div className="overflow-x-auto">
            <table className={tableClass}>
                <thead>
                    <tr className={headerRowClass}>
                        <th className={headerCellClass}>Reparto</th>
                        <th className={headerCellClass}>Fecha reparto</th>
                        <th className={headerCellClass}>Camion</th>
                        <th className={headerCellClass}>Chofer</th>
                        <th className={headerNumberCellClass}>SKUs</th>
                        <th className={headerNumberCellClass}>Bultos picking equiv.</th>
                        <th className={headerNumberCellClass}>Bultos pallets</th>
                        <th className={totalHeaderCellClass}>Total bultos</th>
                        <th className={headerNumberCellClass}>Bultos equiv.</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.id} className={rowClass}>
                            <td className={strongCellClass}>{row.reparto}</td>
                            <td className={cellClass}>{formatDate(row.fecha_reparto)}</td>
                            <td className={cellClass}>{row.camion}</td>
                            <td className={cellClass}>{row.chofer}</td>
                            <td className={numberCellClass}>{formatNumber(row.skus)}</td>
                            <td className={strongNumberCellClass}>{formatNumber(row.bultos_picking_equivalentes)}</td>
                            <td className={numberCellClass}>{formatNumber(row.bultos_palletizados)}</td>
                            <td className={totalCellClass}>{formatNumber(row.total_bultos)}</td>
                            <td className={numberCellClass}>{formatNumber(row.bultos_equivalentes)}</td>
                        </tr>
                    ))}
                </tbody>
                <tfoot>
                    <tr className={totalRowClass}>
                        <td className={totalLabelCellClass} colSpan={4}>TOTAL</td>
                        <td className={totalNumberCellClass}>{formatNumber(rows.reduce((acc, r) => acc + (r.skus || 0), 0))}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalPickingBultos)}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalPalletBultos)}</td>
                        <td className={totalRowValueCellClass}>{formatNumber(totalBultos)}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalEquiv)}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    )
}

function DetailTable({ rows }) {
    if (!rows.length) return <EmptyRows />
    const totalEquiv = rows.reduce((acc, r) => acc + (r.bultos_equivalentes || 0), 0)
    const totalPalletBultos = rows.reduce((acc, r) => acc + (r.bultos_palletizados || 0), 0)
    const totalPickingBultos = rows.reduce((acc, r) => acc + (r.bultos_picking_equivalentes || 0), 0)
    const totalBultos = rows.reduce((acc, r) => acc + (r.total_bultos || 0), 0)

    return (
        <div className="overflow-x-auto">
            <table className={tableClass}>
                <thead>
                    <tr className={headerRowClass}>
                        <th className={headerCellClass}>SKU</th>
                        <th className={headerCellClass}>Descripcion</th>
                        <th className={headerCellClass}>Reparto</th>
                        <th className={headerCellClass}>Fecha reparto</th>
                        <th className={headerCellClass}>Cancha</th>
                        <th className={headerCellClass}>Almacen</th>
                        <th className={headerNumberCellClass}>Bultos picking equiv.</th>
                        <th className={headerNumberCellClass}>Bultos pallets</th>
                        <th className={totalHeaderCellClass}>Total bultos</th>
                        <th className={headerNumberCellClass}>Bultos equiv.</th>
                        <th className={headerCellClass}>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.id} className={rowClass}>
                            <td className={strongCellClass}>{row.sku}</td>
                            <td className={cellClass}>{row.descripcion}</td>
                            <td className={cellClass}>{row.reparto}</td>
                            <td className={cellClass}>{formatDate(row.fecha_reparto)}</td>
                            <td className={cellClass}>{row.cancha}</td>
                            <td className={cellClass}>{row.almacen}</td>
                            <td className={strongNumberCellClass}>{formatNumber(row.bultos_picking_equivalentes)}</td>
                            <td className={numberCellClass}>{formatNumber(row.bultos_palletizados)}</td>
                            <td className={totalCellClass}>{formatNumber(row.total_bultos)}</td>
                            <td className={numberCellClass}>{formatNumber(row.bultos_equivalentes)}</td>
                            <td className={cellClass}><EstadoBadge estado={row.sku_estado} /></td>
                        </tr>
                    ))}
                </tbody>
                <tfoot>
                    <tr className={totalRowClass}>
                        <td className={totalLabelCellClass} colSpan={6}>TOTAL</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalPickingBultos)}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalPalletBultos)}</td>
                        <td className={totalRowValueCellClass}>{formatNumber(totalBultos)}</td>
                        <td className={totalNumberCellClass}>{formatNumber(totalEquiv)}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        </div>
    )
}

export default OperationsPage
