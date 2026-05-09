import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'
import { EstadoBadge } from '../components/Badge'
import {
    cellClass,
    headerCellClass,
    headerNumberCellClass,
    headerRowClass,
    numberCellClass,
    rowClass,
    selectedRowClass,
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
import { formatDate, formatNumber } from '../utils/format'

function HistoryPage() {
    const [items, setItems] = useState([])
    const [selected, setSelected] = useState(null)
    const [loading, setLoading] = useState(false)
    const [confirmDeleteId, setConfirmDeleteId] = useState(null)
    const [deleting, setDeleting] = useState(false)

    const loadHistory = async () => {
        const response = await axiosClient.get('/history/search')
        setItems(response.data)
    }

    useEffect(() => {
        loadHistory()
    }, [])

    const loadDetail = async (id) => {
        if (confirmDeleteId === id) return
        setLoading(true)
        try {
            const response = await axiosClient.get(`/history/${id}`)
            setSelected(response.data)
        } finally {
            setLoading(false)
        }
    }

    const handleDeleteClick = (e, id) => {
        e.stopPropagation()
        setConfirmDeleteId(id)
    }

    const handleCancelDelete = (e) => {
        e.stopPropagation()
        setConfirmDeleteId(null)
    }

    const handleConfirmDelete = async (e, id) => {
        e.stopPropagation()
        setDeleting(true)
        try {
            await axiosClient.delete(`/history/${id}`)
            setItems((prev) => prev.filter((item) => item.id !== id))
            if (selected?.id === id) setSelected(null)
            setConfirmDeleteId(null)
        } finally {
            setDeleting(false)
        }
    }

    const selectedDetails = selected?.detalles || []
    const totalPickingBultos = selectedDetails.reduce((acc, row) => acc + (row.bultos_picking_equivalentes || 0), 0)
    const totalPalletBultos = selectedDetails.reduce((acc, row) => acc + (row.bultos_palletizados || 0), 0)
    const totalBultos = selectedDetails.reduce((acc, row) => acc + (row.total_bultos || 0), 0)
    const totalEquiv = selectedDetails.reduce((acc, row) => acc + (row.bultos_equivalentes || 0), 0)

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            <div className="mb-6 flex items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Historial</h1>
                    <p className="mt-1 text-sm text-slate-500">Repartos procesados y renglones extraidos del PDF.</p>
                </div>
                <button
                    type="button"
                    onClick={loadHistory}
                    className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
                    title="Actualizar historial"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Actualizar
                </button>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
                <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
                    <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                        <h2 className="font-semibold text-slate-900">Repartos</h2>
                        <span className="text-sm text-slate-400">{items.length} registros</span>
                    </div>
                    <div className="p-4">
                        {items.length === 0 ? (
                            <div className="py-10 text-center text-sm text-slate-400">
                                No hay repartos procesados aun.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className={tableClass}>
                                    <thead>
                                        <tr className={headerRowClass}>
                                            <th className={headerCellClass}>Reparto</th>
                                            <th className={headerCellClass}>Fecha reparto</th>
                                            <th className={headerCellClass}>Camion</th>
                                            <th className={headerCellClass}>Chofer</th>
                                            <th className={headerCellClass}></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {items.map((item) => (
                                            <tr
                                                key={item.id}
                                                className={`cursor-pointer ${rowClass} ${selected?.id === item.id ? selectedRowClass : ''}`}
                                                onClick={() => loadDetail(item.id)}
                                            >
                                                <td className={strongCellClass}>{item.reparto}</td>
                                                <td className={cellClass}>{formatDate(item.fecha_reparto)}</td>
                                                <td className={cellClass}>{item.camion}</td>
                                                <td className={cellClass}>{item.chofer}</td>
                                                <td className={`${cellClass} text-right`}>
                                                    {confirmDeleteId === item.id ? (
                                                        <span className="inline-flex items-center gap-1">
                                                            <span className="mr-1 text-xs text-slate-500">¿Eliminar?</span>
                                                            <button
                                                                onClick={(e) => handleConfirmDelete(e, item.id)}
                                                                disabled={deleting}
                                                                className="rounded-lg bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                                                            >
                                                                Si
                                                            </button>
                                                            <button
                                                                onClick={handleCancelDelete}
                                                                className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                                                            >
                                                                No
                                                            </button>
                                                        </span>
                                                    ) : (
                                                        <button
                                                            onClick={(e) => handleDeleteClick(e, item.id)}
                                                            className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-400 hover:border-red-300 hover:text-red-500"
                                                        >
                                                            Eliminar
                                                        </button>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </section>

                <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
                    <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                        <h2 className="font-semibold text-slate-900">Detalle</h2>
                        <span className="text-sm text-slate-400">
                            {selected ? `${selected.detalles.length} items` : loading ? 'Cargando...' : 'Sin seleccion'}
                        </span>
                    </div>
                    <div className="p-4">
                        {!selected && !loading && (
                            <div className="py-10 text-center text-sm text-slate-400">
                                Selecciona un reparto para ver los articulos.
                            </div>
                        )}
                        {selected && (
                            <div className="overflow-x-auto">
                                <table className={tableClass}>
                                    <thead>
                                        <tr className={headerRowClass}>
                                            <th className={headerCellClass}>SKU</th>
                                            <th className={headerCellClass}>Descripcion</th>
                                            <th className={headerCellClass}>Almacen</th>
                                            <th className={headerNumberCellClass}>Bultos picking equiv.</th>
                                            <th className={headerNumberCellClass}>Bultos pallets</th>
                                            <th className={totalHeaderCellClass}>Total bultos</th>
                                            <th className={headerNumberCellClass}>Bultos equiv.</th>
                                            <th className={headerCellClass}>Estado</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {selected.detalles.map((item) => (
                                            <tr key={item.id} className={rowClass}>
                                                <td className={strongCellClass}>{item.sku}</td>
                                                <td className={cellClass}>{item.descripcion}</td>
                                                <td className={cellClass}>{item.almacen}</td>
                                                <td className={strongNumberCellClass}>{formatNumber(item.bultos_picking_equivalentes)}</td>
                                                <td className={numberCellClass}>{formatNumber(item.bultos_palletizados)}</td>
                                                <td className={totalCellClass}>{formatNumber(item.total_bultos)}</td>
                                                <td className={numberCellClass}>{formatNumber(item.bultos_equivalentes)}</td>
                                                <td className={cellClass}><EstadoBadge estado={item.sku_estado} /></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                    <tfoot>
                                        <tr className={totalRowClass}>
                                            <td className={totalLabelCellClass} colSpan={3}>TOTAL</td>
                                            <td className={totalNumberCellClass}>{formatNumber(totalPickingBultos)}</td>
                                            <td className={totalNumberCellClass}>{formatNumber(totalPalletBultos)}</td>
                                            <td className={totalRowValueCellClass}>{formatNumber(totalBultos)}</td>
                                            <td className={totalNumberCellClass}>{formatNumber(totalEquiv)}</td>
                                            <td></td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                        )}
                    </div>
                </section>
            </div>
        </div>
    )
}

export default HistoryPage
