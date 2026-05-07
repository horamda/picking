import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'
import { EstadoBadge } from '../components/Badge'

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
                                <table className="w-full text-left text-sm">
                                    <thead>
                                        <tr className="border-b border-slate-100 text-xs font-medium uppercase tracking-wide text-slate-400">
                                            <th className="pb-3 pr-4">Reparto</th>
                                            <th className="pb-3 pr-4">Camion</th>
                                            <th className="pb-3 pr-4">Chofer</th>
                                            <th className="pb-3"></th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-50">
                                        {items.map((item) => (
                                            <tr
                                                key={item.id}
                                                className={`cursor-pointer hover:bg-slate-50 ${selected?.id === item.id ? 'bg-brand-50' : ''}`}
                                                onClick={() => loadDetail(item.id)}
                                            >
                                                <td className="py-3 pr-4 font-medium text-slate-900">{item.reparto}</td>
                                                <td className="py-3 pr-4 text-slate-600">{item.camion}</td>
                                                <td className="py-3 pr-4 text-slate-600">{item.chofer}</td>
                                                <td className="py-3 text-right">
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
                                <table className="w-full text-left text-sm">
                                    <thead>
                                        <tr className="border-b border-slate-100 text-xs font-medium uppercase tracking-wide text-slate-400">
                                            <th className="pb-3 pr-4">SKU</th>
                                            <th className="pb-3 pr-4">Descripcion</th>
                                            <th className="pb-3 pr-4 text-right">Bultos</th>
                                            <th className="pb-3 pr-4 text-right">Unid.</th>
                                            <th className="pb-3 pr-4">Almacen</th>
                                            <th className="pb-3">Estado</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-50">
                                        {selected.detalles.map((item) => (
                                            <tr key={item.id} className="hover:bg-slate-50">
                                                <td className="py-3 pr-4 font-medium text-slate-900">{item.sku}</td>
                                                <td className="py-3 pr-4 text-slate-600">{item.descripcion}</td>
                                                <td className="py-3 pr-4 text-right text-slate-600">{item.bultos}</td>
                                                <td className="py-3 pr-4 text-right text-slate-600">{item.unidades}</td>
                                                <td className="py-3 pr-4 text-slate-600">{item.almacen}</td>
                                                <td className="py-3"><EstadoBadge estado={item.sku_estado} /></td>
                                            </tr>
                                        ))}
                                    </tbody>
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
