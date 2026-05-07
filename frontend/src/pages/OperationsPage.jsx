import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'
import { EstadoBadge } from '../components/Badge'

const tabs = [
    { id: 'trucks', label: 'Camiones' },
    { id: 'picking-by-cancha', label: 'Picking x cancha' },
    { id: 'by-court', label: 'Por cancha' },
    { id: 'picking', label: 'Picking' },
    { id: 'pallets', label: 'Pallets completos' },
]

function OperationsPage() {
    const [activeTab, setActiveTab] = useState('trucks')
    const [rows, setRows] = useState([])
    const [loading, setLoading] = useState(false)
    const [filters, setFilters] = useState({ desde: '', hasta: '', camion: '', reparto: '', cancha: '' })

    useEffect(() => {
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

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Operacion</h1>
                    <p className="mt-1 text-sm text-slate-500">Separacion automatica entre pallets completos y picking manual.</p>
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
                <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 xl:grid-cols-5">
                    {[
                        { key: 'desde', label: 'Desde', type: 'date' },
                        { key: 'hasta', label: 'Hasta', type: 'date' },
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
                    {['picking', 'pallets'].includes(activeTab) && <DetailTable rows={rows} mode={activeTab} />}
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
    const totalPallets = rows.reduce((acc, r) => acc + (r.pallets_completos || 0), 0)
    const totalBultos = rows.reduce((acc, r) => acc + (r.bultos_pickear || 0), 0)
    const totalUnidades = rows.reduce((acc, r) => acc + (r.unidades_sueltas || 0), 0)

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-slate-100 text-xs font-medium uppercase tracking-wide text-slate-400">
                        <th className="pb-3 pr-4">Cancha</th>
                        <th className="pb-3 pr-4 text-right">SKUs</th>
                        <th className="pb-3 pr-4 text-right">Bultos equiv.</th>
                        <th className="pb-3 pr-4 text-right">Pallets</th>
                        <th className="pb-3 pr-4 text-right">Bultos picking</th>
                        <th className="pb-3 text-right">Unid. sueltas</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                    {rows.map((row) => (
                        <tr key={row.cancha} className="hover:bg-slate-50">
                            <td className="py-3 pr-4 font-medium text-slate-900">{row.cancha || '—'}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.skus}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{(row.bultos_equivalentes || 0).toFixed(2)}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.pallets_completos}</td>
                            <td className="py-3 pr-4 text-right font-semibold text-slate-900">{row.bultos_pickear}</td>
                            <td className="py-3 text-right text-slate-600">{row.unidades_sueltas}</td>
                        </tr>
                    ))}
                </tbody>
                <tfoot>
                    <tr className="border-t-2 border-slate-200 font-semibold text-slate-700">
                        <td className="pt-3 pr-4">TOTAL</td>
                        <td className="pt-3 pr-4 text-right">{rows.reduce((acc, r) => acc + (r.skus || 0), 0)}</td>
                        <td className="pt-3 pr-4 text-right">{totalEquiv.toFixed(2)}</td>
                        <td className="pt-3 pr-4 text-right">{totalPallets}</td>
                        <td className="pt-3 pr-4 text-right text-slate-900">{totalBultos}</td>
                        <td className="pt-3 text-right">{totalUnidades}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    )
}

function CourtTable({ rows }) {
    if (!rows.length) return <EmptyRows />
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-slate-100 text-xs font-medium uppercase tracking-wide text-slate-400">
                        <th className="pb-3 pr-4">Cancha</th>
                        <th className="pb-3 pr-4">Almacen</th>
                        <th className="pb-3 pr-4 text-right">SKUs</th>
                        <th className="pb-3 pr-4 text-right">Bultos equiv.</th>
                        <th className="pb-3 pr-4 text-right">Pallets</th>
                        <th className="pb-3 pr-4 text-right">Picking</th>
                        <th className="pb-3 text-right">Unid.</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                    {rows.map((row) => (
                        <tr key={`${row.cancha}-${row.almacen}`} className="hover:bg-slate-50">
                            <td className="py-3 pr-4 font-medium text-slate-900">{row.cancha}</td>
                            <td className="py-3 pr-4 text-slate-600">{row.almacen}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.skus}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.bultos_equivalentes}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.pallets_completos}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.bultos_pickear}</td>
                            <td className="py-3 text-right text-slate-600">{row.unidades_sueltas}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function TruckTable({ rows }) {
    if (!rows.length) return <EmptyRows />
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-slate-100 text-xs font-medium uppercase tracking-wide text-slate-400">
                        <th className="pb-3 pr-4">Reparto</th>
                        <th className="pb-3 pr-4">Camion</th>
                        <th className="pb-3 pr-4">Chofer</th>
                        <th className="pb-3 pr-4 text-right">SKUs</th>
                        <th className="pb-3 pr-4 text-right">Bultos</th>
                        <th className="pb-3 pr-4 text-right">Unidades</th>
                        <th className="pb-3 pr-4 text-right">Pallets</th>
                        <th className="pb-3 pr-4 text-right">Bultos pick</th>
                        <th className="pb-3 text-right">Unid. sueltas</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                    {rows.map((row) => (
                        <tr key={row.id} className="hover:bg-slate-50">
                            <td className="py-3 pr-4 font-medium text-slate-900">{row.reparto}</td>
                            <td className="py-3 pr-4 text-slate-600">{row.camion}</td>
                            <td className="py-3 pr-4 text-slate-600">{row.chofer}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.skus}</td>
                            <td className="py-3 pr-4 text-right font-semibold text-slate-900">{row.bultos}</td>
                            <td className="py-3 pr-4 text-right font-semibold text-slate-900">{row.unidades}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.pallets_completos}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.bultos_pickear}</td>
                            <td className="py-3 text-right text-slate-600">{row.unidades_sueltas}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function DetailTable({ rows, mode }) {
    if (!rows.length) return <EmptyRows />
    const totalBultos = rows.reduce((acc, r) => acc + (r.bultos || 0), 0)
    const totalUnidades = rows.reduce((acc, r) => acc + (r.unidades || 0), 0)
    const totalPick = rows.reduce((acc, r) => acc + (mode === 'pallets' ? (r.pallets_completos || 0) : (r.bultos_pickear || 0)), 0)
    const totalUnidadesSueltas = rows.reduce((acc, r) => acc + (r.unidades_sueltas || 0), 0)

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-slate-100 text-xs font-medium uppercase tracking-wide text-slate-400">
                        <th className="pb-3 pr-4">SKU</th>
                        <th className="pb-3 pr-4">Descripcion</th>
                        <th className="pb-3 pr-4">Reparto</th>
                        <th className="pb-3 pr-4">Cancha</th>
                        <th className="pb-3 pr-4">Almacen</th>
                        <th className="pb-3 pr-4 text-right">Bultos</th>
                        <th className="pb-3 pr-4 text-right">Unidades</th>
                        <th className="pb-3 pr-4 text-right">{mode === 'pallets' ? 'Pallets' : 'Bultos pick'}</th>
                        <th className="pb-3 pr-4 text-right">Unid. sueltas</th>
                        <th className="pb-3">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                    {rows.map((row) => (
                        <tr key={row.id} className="hover:bg-slate-50">
                            <td className="py-3 pr-4 font-medium text-slate-900">{row.sku}</td>
                            <td className="py-3 pr-4 text-slate-600">{row.descripcion}</td>
                            <td className="py-3 pr-4 text-slate-600">{row.reparto}</td>
                            <td className="py-3 pr-4 text-slate-600">{row.cancha}</td>
                            <td className="py-3 pr-4 text-slate-600">{row.almacen}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.bultos}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.unidades}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{mode === 'pallets' ? row.pallets_completos : row.bultos_pickear}</td>
                            <td className="py-3 pr-4 text-right text-slate-600">{row.unidades_sueltas}</td>
                            <td className="py-3"><EstadoBadge estado={row.sku_estado} /></td>
                        </tr>
                    ))}
                </tbody>
                <tfoot>
                    <tr className="border-t-2 border-slate-200 font-semibold text-slate-700">
                        <td className="pt-3 pr-4" colSpan={5}>TOTAL</td>
                        <td className="pt-3 pr-4 text-right text-slate-900">{totalBultos}</td>
                        <td className="pt-3 pr-4 text-right text-slate-900">{totalUnidades}</td>
                        <td className="pt-3 pr-4 text-right">{totalPick}</td>
                        <td className="pt-3 pr-4 text-right">{totalUnidadesSueltas}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        </div>
    )
}

export default OperationsPage
