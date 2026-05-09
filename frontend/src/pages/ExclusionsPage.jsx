import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'
import { ActiveBadge } from '../components/Badge'
import {
    cellClass,
    headerCellClass,
    headerRowClass,
    rowClass,
    strongCellClass,
    tableClass,
} from '../components/tableStyles'

function ExclusionsPage() {
    const [rows, setRows] = useState([])
    const [sku, setSku] = useState('')
    const [descripcion, setDescripcion] = useState('')
    const [motivo, setMotivo] = useState('')

    const loadRows = async () => {
        const response = await axiosClient.get('/exclusions/')
        setRows(response.data)
    }

    useEffect(() => {
        loadRows()
    }, [])

    const save = async (event) => {
        event.preventDefault()
        await axiosClient.post('/exclusions/', { sku, descripcion, motivo, activo: true })
        setSku('')
        setDescripcion('')
        setMotivo('')
        await loadRows()
    }

    const toggle = async (row) => {
        await axiosClient.put(`/exclusions/${row.id}`, { activo: !row.activo })
        await loadRows()
    }

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            <div className="mb-6">
                <h1 className="text-2xl font-semibold text-slate-900">Exclusiones</h1>
                <p className="mt-1 text-sm text-slate-500">SKUs que no entran en calculos de picking ni pallets.</p>
            </div>

            <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="mb-4 text-sm font-medium text-slate-700">Agregar exclusion</p>
                <form onSubmit={save} className="grid gap-3 xl:grid-cols-[160px_1fr_1fr_auto]">
                    <label className="flex flex-col gap-1">
                        <span className="text-xs font-medium text-slate-500">SKU</span>
                        <input
                            value={sku}
                            onChange={(e) => setSku(e.target.value)}
                            placeholder="ej. 2731"
                            required
                            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                    </label>
                    <label className="flex flex-col gap-1">
                        <span className="text-xs font-medium text-slate-500">Descripcion</span>
                        <input
                            value={descripcion}
                            onChange={(e) => setDescripcion(e.target.value)}
                            placeholder="Descripcion del articulo"
                            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                    </label>
                    <label className="flex flex-col gap-1">
                        <span className="text-xs font-medium text-slate-500">Motivo</span>
                        <input
                            value={motivo}
                            onChange={(e) => setMotivo(e.target.value)}
                            placeholder="Motivo de exclusion"
                            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                    </label>
                    <div className="flex items-end">
                        <button
                            type="submit"
                            className="w-full rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-600"
                        >
                            Agregar
                        </button>
                    </div>
                </form>
            </div>

            <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
                    <h2 className="font-semibold text-slate-900">SKUs excluidos</h2>
                    <span className="text-sm text-slate-400">{rows.length} registros</span>
                </div>
                <div className="p-4">
                    <div className="overflow-x-auto">
                        <table className={tableClass}>
                            <thead>
                                <tr className={headerRowClass}>
                                    <th className={headerCellClass}>SKU</th>
                                    <th className={headerCellClass}>Descripcion</th>
                                    <th className={headerCellClass}>Motivo</th>
                                    <th className={headerCellClass}>Estado</th>
                                    <th className={headerCellClass}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.map((row) => (
                                    <tr key={row.id} className={rowClass}>
                                        <td className={strongCellClass}>{row.sku}</td>
                                        <td className={cellClass}>{row.descripcion}</td>
                                        <td className={cellClass}>{row.motivo}</td>
                                        <td className={cellClass}><ActiveBadge activo={row.activo} /></td>
                                        <td className={`${cellClass} text-right`}>
                                            <button
                                                type="button"
                                                onClick={() => toggle(row)}
                                                className="rounded-xl border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                                            >
                                                {row.activo ? 'Desactivar' : 'Activar'}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>
        </div>
    )
}

export default ExclusionsPage
