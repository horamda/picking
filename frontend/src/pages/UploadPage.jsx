import { useState } from 'react'
import axiosClient from '../api/axiosClient'

function UploadPage() {
    const [files, setFiles] = useState([])
    const [status, setStatus] = useState('')
    const [result, setResult] = useState(null)

    const handleFiles = (event) => {
        setFiles(Array.from(event.target.files))
    }

    const handleUpload = async () => {
        if (!files.length) return
        const formData = new FormData()
        files.forEach((file) => formData.append('files', file))
        setStatus('Subiendo archivos...')
        setResult(null)
        try {
            const response = await axiosClient.post('/uploads/pdf', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            setResult(response.data)
            setStatus(`Repartos procesados: ${response.data.processed.length}`)
        } catch (error) {
            setStatus('Error durante la carga')
        }
    }

    return (
        <div className="min-h-screen bg-slate-50 p-6">
            <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-2xl font-semibold text-slate-900">Carga de PDFs</h2>
                <p className="mt-2 text-slate-600">Arrastra y suelta archivos o selecciona varios PDFs para procesar consolidados.</p>
                <div className="mt-6 flex flex-col gap-4">
                    <label className="block rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-500">
                        <input type="file" multiple accept="application/pdf" className="hidden" onChange={handleFiles} />
                        <span className="cursor-pointer">Haz clic aquí o arrastra tus archivos</span>
                    </label>
                    <button onClick={handleUpload} className="rounded-2xl bg-brand-500 px-6 py-3 text-white transition hover:bg-brand-600" type="button">
                        Subir y procesar
                    </button>
                    {status && <div className="text-slate-700">{status}</div>}
                    {result?.processed?.length > 0 && (
                        <div className="rounded-3xl border border-slate-200 bg-white p-4">
                            <h3 className="text-lg font-semibold">Resultado</h3>
                            <ul className="mt-3 space-y-2 text-slate-700">
                                {result.processed.map((item) => (
                                    <li key={`${item.filename}-${item.reparto}`} className="rounded-2xl bg-slate-50 px-4 py-3">
                                        Reparto {item.reparto}: {item.items} items
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    {result?.errors?.length > 0 && (
                        <div className="rounded-3xl border border-red-200 bg-red-50 p-4 text-red-800">
                            <h3 className="text-lg font-semibold">Errores</h3>
                            <ul className="mt-3 list-disc space-y-1 pl-5">
                                {result.errors.map((item) => (<li key={`${item.filename}-${item.error}`}>{item.filename}: {item.error}</li>))}
                            </ul>
                        </div>
                    )}
                    {files.length > 0 && (
                        <div className="rounded-3xl border border-slate-200 bg-white p-4">
                            <h3 className="text-lg font-semibold">Archivos seleccionados</h3>
                            <ul className="mt-3 list-disc space-y-1 pl-5 text-slate-700">
                                {files.map((file) => (<li key={file.name}>{file.name}</li>))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default UploadPage
