import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'

function HistoryPage() {
    const [items, setItems] = useState([])
    const [selected, setSelected] = useState(null)
    const [loading, setLoading] = useState(false)
    const [confirmDeleteId, setConfirmDeleteId] = useState(null)
    const [deleting, setDeleting] = useState(false)

    useEffect(() => {
        async function loadHistory() {
            const response = await axiosClient.get('/history/search')
            setItems(response.data)
        }
        loadHistory()
    }, [])

    const loadDetail = async (id) => {
        if (confirmDeleteId) return
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
        <div className="min-h-screen bg-slate-50 p-6">
            <div className="mb-6">
                <h1 className="text-3xl font-semibold text-slate-900">Historial</h1>
                <p className="text-slate-600">Repartos procesados y renglones extraidos del PDF.</p>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
                <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-xl font-semibold text-slate-900">Repartos</h2>
                    <div className="mt-4 overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 text-slate-500">
                                    <th className="px-3 py-3">Reparto</th>
                                    <th className="px-3 py-3">Camion</th>
                                    <th className="px-3 py-3">Chofer</th>
                                    <th className="px-3 py-3"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {items.map((item) => (
                                    <tr
                                        key={item.id}
                                        className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 ${selected?.id === item.id ? 'bg-brand-50' : ''}`}
                                        onClick={() => loadDetail(item.id)}
                                    >
                                        <td className="px-3 py-3 font-medium text-slate-900">{item.reparto}</td>
                                        <td className="px-3 py-3 text-slate-700">{item.camion}</td>
                                        <td className="px-3 py-3 text-slate-700">{item.chofer}</td>
                                        <td className="px-3 py-3 text-right">
                                            {confirmDeleteId === item.id ? (
                                                <span className="inline-flex items-center gap-1">
                                                    <span className="text-xs text-slate-500 mr-1">¿Eliminar?</span>
                                                    <button
                                                        onClick={(e) => handleConfirmDelete(e, item.id)}
                                                        disabled={deleting}
                                                        className="rounded-lg bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                                                    >
                                                        Sí
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
                </section>

                <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div className="flex items-center justify-between gap-4">
                        <h2 className="text-xl font-semibold text-slate-900">Detalle</h2>
                        <span className="text-sm text-slate-500">
                            {selected ? `${selected.detalles.length} items` : loading ? 'Cargando...' : 'Sin seleccion'}
                        </span>
                    </div>

                    {!selected && !loading && (
                        <div className="mt-8 rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500">
                            Selecciona un reparto para ver los articulos extraidos.
                        </div>
                    )}

                    {selected && (
                        <div className="mt-4 overflow-x-auto">
                            <table className="w-full text-left text-sm">
                                <thead>
                                    <tr className="border-b border-slate-200 text-slate-500">
                                        <th className="px-3 py-3">SKU</th>
                                        <th className="px-3 py-3">Descripcion</th>
                                        <th className="px-3 py-3">Bultos</th>
                                        <th className="px-3 py-3">Unid.</th>
                                        <th className="px-3 py-3">Almacen</th>
                                        <th className="px-3 py-3">Estado</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {selected.detalles.map((item) => (
                                        <tr key={item.id} className="border-b border-slate-100 hover:bg-slate-50">
                                            <td className="px-3 py-3 font-medium text-slate-900">{item.sku}</td>
                                            <td className="px-3 py-3 text-slate-700">{item.descripcion}</td>
                                            <td className="px-3 py-3 text-slate-700">{item.bultos}</td>
                                            <td className="px-3 py-3 text-slate-700">{item.unidades}</td>
                                            <td className="px-3 py-3 text-slate-700">{item.almacen}</td>
                                            <td className="px-3 py-3 text-slate-700">{item.sku_estado}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>
            </div>
        </div>
    )
}

export default HistoryPage
