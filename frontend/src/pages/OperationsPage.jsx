import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'

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
            setLoading(true)
            try {
                const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value))
                const response = await axiosClient.get(`/operations/${activeTab}`, { params })
                setRows(response.data)
            } finally {
                setLoading(false)
            }
        }
        loadRows()
    }, [activeTab, filters])

    return (
        <div className="min-h-screen bg-slate-50 p-6">
            <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                <div>
                    <h1 className="text-3xl font-semibold text-slate-900">Operacion</h1>
                    <p className="text-slate-600">Separacion automatica entre pallets completos y picking manual.</p>
                </div>
                <div className="flex flex-wrap gap-2 rounded-2xl bg-white p-2 shadow-sm ring-1 ring-slate-200">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            type="button"
                            onClick={() => setActiveTab(tab.id)}
                            className={`rounded-xl px-4 py-2 text-sm font-medium ${activeTab === tab.id ? 'bg-brand-500 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="mb-6 grid gap-3 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-5">
                <input type="date" value={filters.desde} onChange={(event) => setFilters({ ...filters, desde: event.target.value })} className="rounded-2xl border border-slate-300 px-4 py-3 text-sm" />
                <input type="date" value={filters.hasta} onChange={(event) => setFilters({ ...filters, hasta: event.target.value })} className="rounded-2xl border border-slate-300 px-4 py-3 text-sm" />
                <input placeholder="Camion" value={filters.camion} onChange={(event) => setFilters({ ...filters, camion: event.target.value })} className="rounded-2xl border border-slate-300 px-4 py-3 text-sm" />
                <input placeholder="Reparto" value={filters.reparto} onChange={(event) => setFilters({ ...filters, reparto: event.target.value })} className="rounded-2xl border border-slate-300 px-4 py-3 text-sm" />
                <input placeholder="Cancha" value={filters.cancha} onChange={(event) => setFilters({ ...filters, cancha: event.target.value })} className="rounded-2xl border border-slate-300 px-4 py-3 text-sm" />
            </div>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-xl font-semibold text-slate-900">{tabs.find((tab) => tab.id === activeTab)?.label}</h2>
                    <span className="text-sm text-slate-500">{loading ? 'Cargando...' : `${rows.length} registros`}</span>
                </div>
                {activeTab === 'trucks' && <TruckTable rows={rows} />}
                {activeTab === 'picking-by-cancha' && <PickingByCanchaTable rows={rows} />}
                {activeTab === 'by-court' && <CourtTable rows={rows} />}
                {['picking', 'pallets'].includes(activeTab) && <DetailTable rows={rows} mode={activeTab} />}
            </section>
        </div>
    )
}

function PickingByCanchaTable({ rows }) {
    const totalEquiv = rows.reduce((acc, r) => acc + r.bultos_equivalentes, 0)
    const totalPallets = rows.reduce((acc, r) => acc + r.pallets_completos, 0)
    const totalBultos = rows.reduce((acc, r) => acc + r.bultos_pickear, 0)
    const totalUnidades = rows.reduce((acc, r) => acc + r.unidades_sueltas, 0)

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                        <th className="px-3 py-3">Cancha</th>
                        <th className="px-3 py-3 text-right">SKUs</th>
                        <th className="px-3 py-3 text-right">Bultos equiv.</th>
                        <th className="px-3 py-3 text-right">Pallets</th>
                        <th className="px-3 py-3 text-right">Bultos picking</th>
                        <th className="px-3 py-3 text-right">Unid. sueltas</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.cancha} className="border-b border-slate-100 hover:bg-slate-50">
                            <td className="px-3 py-3 font-medium text-slate-900">{row.cancha || '—'}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.skus}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.bultos_equivalentes}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.pallets_completos}</td>
                            <td className="px-3 py-3 text-right font-semibold text-slate-900">{row.bultos_pickear}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.unidades_sueltas}</td>
                        </tr>
                    ))}
                </tbody>
                {rows.length > 0 && (
                    <tfoot>
                        <tr className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
                            <td className="px-3 py-3 text-slate-700">TOTAL</td>
                            <td className="px-3 py-3 text-right text-slate-700">{rows.reduce((acc, r) => acc + r.skus, 0)}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{totalEquiv.toFixed(2)}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{totalPallets}</td>
                            <td className="px-3 py-3 text-right text-slate-900">{totalBultos}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{totalUnidades}</td>
                        </tr>
                    </tfoot>
                )}
            </table>
        </div>
    )
}

function CourtTable({ rows }) {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                        <th className="px-3 py-3">Cancha</th>
                        <th className="px-3 py-3">Almacen</th>
                        <th className="px-3 py-3">SKUs</th>
                        <th className="px-3 py-3">Bultos equiv.</th>
                        <th className="px-3 py-3">Pallets</th>
                        <th className="px-3 py-3">Picking</th>
                        <th className="px-3 py-3">Unid.</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={`${row.cancha}-${row.almacen}`} className="border-b border-slate-100 hover:bg-slate-50">
                            <td className="px-3 py-3 font-medium text-slate-900">{row.cancha}</td>
                            <td className="px-3 py-3 text-slate-700">{row.almacen}</td>
                            <td className="px-3 py-3 text-slate-700">{row.skus}</td>
                            <td className="px-3 py-3 text-slate-700">{row.bultos_equivalentes}</td>
                            <td className="px-3 py-3 text-slate-700">{row.pallets_completos}</td>
                            <td className="px-3 py-3 text-slate-700">{row.bultos_pickear}</td>
                            <td className="px-3 py-3 text-slate-700">{row.unidades_sueltas}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function TruckTable({ rows }) {
    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                        <th className="px-3 py-3">Reparto</th>
                        <th className="px-3 py-3">Camion</th>
                        <th className="px-3 py-3">Chofer</th>
                        <th className="px-3 py-3 text-right">SKUs</th>
                        <th className="px-3 py-3 text-right">Bultos</th>
                        <th className="px-3 py-3 text-right">Unidades</th>
                        <th className="px-3 py-3 text-right">Pallets</th>
                        <th className="px-3 py-3 text-right">Bultos pick</th>
                        <th className="px-3 py-3 text-right">Unid. sueltas</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50">
                            <td className="px-3 py-3 font-medium text-slate-900">{row.reparto}</td>
                            <td className="px-3 py-3 text-slate-700">{row.camion}</td>
                            <td className="px-3 py-3 text-slate-700">{row.chofer}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.skus}</td>
                            <td className="px-3 py-3 text-right font-semibold text-slate-900">{row.bultos}</td>
                            <td className="px-3 py-3 text-right font-semibold text-slate-900">{row.unidades}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.pallets_completos}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.bultos_pickear}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.unidades_sueltas}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function DetailTable({ rows, mode }) {
    const totalBultos = rows.reduce((acc, r) => acc + (r.bultos || 0), 0)
    const totalUnidades = rows.reduce((acc, r) => acc + (r.unidades || 0), 0)
    const totalPick = rows.reduce((acc, r) => acc + (mode === 'pallets' ? r.pallets_completos : r.bultos_pickear), 0)
    const totalUnidadesSueltas = rows.reduce((acc, r) => acc + r.unidades_sueltas, 0)

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                        <th className="px-3 py-3">SKU</th>
                        <th className="px-3 py-3">Descripcion</th>
                        <th className="px-3 py-3">Reparto</th>
                        <th className="px-3 py-3">Cancha</th>
                        <th className="px-3 py-3">Almacen</th>
                        <th className="px-3 py-3 text-right">Bultos</th>
                        <th className="px-3 py-3 text-right">Unidades</th>
                        <th className="px-3 py-3 text-right">{mode === 'pallets' ? 'Pallets' : 'Bultos pick'}</th>
                        <th className="px-3 py-3 text-right">Unid. sueltas</th>
                        <th className="px-3 py-3">Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50">
                            <td className="px-3 py-3 font-medium text-slate-900">{row.sku}</td>
                            <td className="px-3 py-3 text-slate-700">{row.descripcion}</td>
                            <td className="px-3 py-3 text-slate-700">{row.reparto}</td>
                            <td className="px-3 py-3 text-slate-700">{row.cancha}</td>
                            <td className="px-3 py-3 text-slate-700">{row.almacen}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.bultos}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.unidades}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{mode === 'pallets' ? row.pallets_completos : row.bultos_pickear}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{row.unidades_sueltas}</td>
                            <td className="px-3 py-3 text-slate-700">{row.sku_estado}</td>
                        </tr>
                    ))}
                </tbody>
                {rows.length > 0 && (
                    <tfoot>
                        <tr className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
                            <td className="px-3 py-3 text-slate-700" colSpan={5}>TOTAL</td>
                            <td className="px-3 py-3 text-right text-slate-900">{totalBultos}</td>
                            <td className="px-3 py-3 text-right text-slate-900">{totalUnidades}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{totalPick}</td>
                            <td className="px-3 py-3 text-right text-slate-700">{totalUnidadesSueltas}</td>
                            <td></td>
                        </tr>
                    </tfoot>
                )}
            </table>
        </div>
    )
}

export default OperationsPage
