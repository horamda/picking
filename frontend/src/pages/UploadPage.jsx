import { useState } from 'react'
import axiosClient from '../api/axiosClient'
import { formatDate } from '../utils/format'

function UploadPage() {
    const [files, setFiles] = useState([])
    const [status, setStatus] = useState('')
    const [result, setResult] = useState(null)
    const [dragging, setDragging] = useState(false)

    const addFiles = (incoming) => {
        const pdfs = Array.from(incoming).filter((f) => f.type === 'application/pdf' || f.name.endsWith('.pdf'))
        setFiles((prev) => {
            const existing = new Set(prev.map((f) => f.name))
            return [...prev, ...pdfs.filter((f) => !existing.has(f.name))]
        })
    }

    const handleDrop = (e) => {
        e.preventDefault()
        setDragging(false)
        addFiles(e.dataTransfer.files)
    }

    const handleUpload = async () => {
        if (!files.length) return
        const formData = new FormData()
        files.forEach((file) => formData.append('files', file))
        setStatus('Subiendo archivos...')
        setResult(null)
        try {
            const response = await axiosClient.post('/uploads/pdf', formData)
            setResult(response.data)
            setFiles([])
            const processed = response.data.processed?.length || 0
            const errors = response.data.errors?.length || 0
            setStatus(errors ? `Repartos procesados: ${processed}. Rechazados: ${errors}` : `Repartos procesados: ${processed}`)
        } catch (error) {
            setStatus(error.response?.data?.error || 'Error durante la carga')
        }
    }

    const handleReset = () => {
        setFiles([])
        setResult(null)
        setStatus('')
    }

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-2xl font-semibold text-slate-900">Carga de PDFs</h2>
                <p className="mt-2 text-slate-600">Arrastra y suelta archivos o selecciona varios PDFs para procesar consolidados.</p>
                <div className="mt-6 flex flex-col gap-4">
                    <label
                        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                        onDragLeave={() => setDragging(false)}
                        onDrop={handleDrop}
                        className={`block cursor-pointer rounded-3xl border-2 border-dashed p-10 text-center transition-colors ${
                            dragging ? 'border-brand-500 bg-brand-50 text-brand-500' : 'border-slate-300 bg-slate-50 text-slate-500 hover:border-slate-400'
                        }`}
                    >
                        <input type="file" multiple accept="application/pdf" className="hidden" onChange={(e) => addFiles(e.target.files)} />
                        <svg xmlns="http://www.w3.org/2000/svg" className="mx-auto mb-3 h-8 w-8 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <span className="text-sm font-medium">Arrastra PDFs aqui o haz clic para seleccionar</span>
                    </label>

                    {files.length > 0 && (
                        <div className="rounded-3xl border border-slate-200 bg-white p-4">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-semibold text-slate-700">{files.length} archivo{files.length !== 1 ? 's' : ''} seleccionado{files.length !== 1 ? 's' : ''}</h3>
                                <button type="button" onClick={() => setFiles([])} className="text-xs text-slate-400 hover:text-slate-600">Limpiar</button>
                            </div>
                            <ul className="space-y-1 text-sm text-slate-600">
                                {files.map((file) => (<li key={file.name} className="truncate">{file.name}</li>))}
                            </ul>
                        </div>
                    )}

                    <div className="flex gap-3">
                        <button
                            onClick={handleUpload}
                            disabled={!files.length}
                            className="flex-1 rounded-2xl bg-brand-500 px-6 py-3 font-medium text-white transition hover:bg-brand-600 disabled:opacity-40"
                            type="button"
                        >
                            Subir y procesar
                        </button>
                        {result && (
                            <button
                                onClick={handleReset}
                                type="button"
                                className="rounded-2xl border border-slate-300 px-5 py-3 text-sm font-medium text-slate-600 hover:bg-slate-50"
                            >
                                Nueva carga
                            </button>
                        )}
                    </div>

                    {status && <div className="text-sm text-slate-700">{status}</div>}

                    {result?.processed?.length > 0 && (
                        <div className="rounded-3xl border border-slate-200 bg-white p-4">
                            <h3 className="text-lg font-semibold">Resultado</h3>
                            <ul className="mt-3 space-y-2 text-slate-700">
                                {result.processed.map((item) => (
                                    <li key={`${item.filename}-${item.reparto}`} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm">
                                        Reparto {item.reparto} - Fecha {formatDate(item.fecha_reparto)}: {item.items} items
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {result?.errors?.length > 0 && (
                        <div className="rounded-3xl border border-red-200 bg-red-50 p-4 text-red-800">
                            <h3 className="text-lg font-semibold">Errores</h3>
                            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                                {result.errors.map((item) => (<li key={`${item.filename}-${item.error}`}>{item.filename}: {item.error}</li>))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default UploadPage
