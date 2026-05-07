import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'

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
        <div className="min-h-screen bg-slate-50 p-6">
            <div className="mb-6">
                <h1 className="text-3xl font-semibold text-slate-900">Exclusiones</h1>
                <p className="text-slate-600">SKUs que no deben entrar en calculos de picking ni pallets.</p>
            </div>

            <form onSubmit={save} className="mb-6 grid gap-3 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm xl:grid-cols-[160px_1fr_1fr_auto]">
                <input value={sku} onChange={(event) => setSku(event.target.value)} placeholder="SKU" className="rounded-2xl border border-slate-300 px-4 py-3" />
                <input value={descripcion} onChange={(event) => setDescripcion(event.target.value)} placeholder="Descripcion" className="rounded-2xl border border-slate-300 px-4 py-3" />
                <input value={motivo} onChange={(event) => setMotivo(event.target.value)} placeholder="Motivo" className="rounded-2xl border border-slate-300 px-4 py-3" />
                <button type="submit" className="rounded-2xl bg-brand-500 px-5 py-3 font-medium text-white hover:bg-brand-600">Agregar</button>
            </form>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="border-b border-slate-200 text-slate-500">
                                <th className="px-3 py-3">SKU</th>
                                <th className="px-3 py-3">Descripcion</th>
                                <th className="px-3 py-3">Motivo</th>
                                <th className="px-3 py-3">Estado</th>
                                <th className="px-3 py-3"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row) => (
                                <tr key={row.id} className="border-b border-slate-100 hover:bg-slate-50">
                                    <td className="px-3 py-3 font-medium text-slate-900">{row.sku}</td>
                                    <td className="px-3 py-3 text-slate-700">{row.descripcion}</td>
                                    <td className="px-3 py-3 text-slate-700">{row.motivo}</td>
                                    <td className="px-3 py-3 text-slate-700">{row.activo ? 'Activo' : 'Inactivo'}</td>
                                    <td className="px-3 py-3 text-right">
                                        <button type="button" onClick={() => toggle(row)} className="rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">
                                            {row.activo ? 'Desactivar' : 'Activar'}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    )
}

export default ExclusionsPage
