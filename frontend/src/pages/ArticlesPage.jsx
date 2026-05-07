import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'

function ArticlesPage() {
    const [articles, setArticles] = useState([])
    const [csvFile, setCsvFile] = useState(null)
    const [importMode, setImportMode] = useState('merge')
    const [importResult, setImportResult] = useState(null)
    const [status, setStatus] = useState('')

    const loadArticles = async () => {
        const response = await axiosClient.get('/articles')
        setArticles(response.data)
    }

    useEffect(() => {
        loadArticles()
    }, [])

    const importCsv = async () => {
        if (!csvFile) return
        const formData = new FormData()
        formData.append('file', csvFile)
        formData.append('mode', importMode)
        setStatus('Importando CSV...')
        try {
            const response = await axiosClient.post('/articles/import-csv', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            setImportResult(response.data)
            setStatus(response.data.applied ? 'CSV aplicado' : 'CSV rechazado')
            await loadArticles()
        } catch (error) {
            const payload = error.response?.data || {
                applied: false,
                deleted: 0,
                created: 0,
                updated: 0,
                unchanged: 0,
                inactive: 0,
                duplicates: [],
                errors: [{ row: null, error: 'No se pudo conectar con el backend. Verifica que Flask este corriendo en el puerto 5000.' }],
            }
            setImportResult({
                deleted: 0,
                created: 0,
                updated: 0,
                unchanged: 0,
                inactive: 0,
                duplicates: [],
                errors: [],
                ...payload,
                duplicates: payload.duplicates || [],
                errors: payload.errors || [{ row: null, error: payload.error || 'Error importando CSV' }],
            })
            setStatus('CSV rechazado')
        }
    }

    return (
        <div className="min-h-screen bg-slate-50 p-6">
            <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                <div>
                    <h1 className="text-3xl font-semibold text-slate-900">Articulos</h1>
                    <p className="text-slate-600">Maestro logistico para calcular bultos equivalentes y pallets.</p>
                </div>
                <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                        <input type="file" accept=".csv,text/csv" onChange={(event) => setCsvFile(event.target.files?.[0] || null)} className="text-sm text-slate-600" />
                        <select value={importMode} onChange={(event) => setImportMode(event.target.value)} className="rounded-2xl border border-slate-300 px-4 py-2 text-sm text-slate-700">
                            <option value="merge">Actualizar maestro</option>
                            <option value="replace">Reemplazar maestro</option>
                        </select>
                        <button type="button" onClick={importCsv} className="rounded-2xl bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600">
                            Importar CSV
                        </button>
                    </div>
                    {importMode === 'replace' && (
                        <div className="mt-3 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
                            Reemplazar borra el maestro actual y carga solo el CSV. Si el archivo tiene errores o SKUs duplicados, no se aplica ningun cambio.
                        </div>
                    )}
                    {status && <div className="mt-2 text-sm text-slate-600">{status}</div>}
                </div>
            </div>

            {importResult && (
                <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
                    {[
                        ['Borrados', importResult.deleted],
                        ['Nuevos', importResult.created],
                        ['Modificados', importResult.updated],
                        ['Sin cambios', importResult.unchanged],
                        ['Inactivos', importResult.inactive],
                        ['Errores', importResult.errors.length + importResult.duplicates.length],
                    ].map(([label, value]) => (
                        <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{label}</p>
                            <p className="mt-2 text-2xl font-semibold text-slate-900">{value}</p>
                        </div>
                    ))}
                </div>
            )}

            {importResult && (importResult.errors.length > 0 || importResult.duplicates.length > 0) && (
                <div className="mb-6 rounded-3xl border border-red-200 bg-red-50 p-5 text-sm text-red-900">
                    <h2 className="font-semibold">Errores del CSV</h2>
                    <ul className="mt-3 list-disc space-y-1 pl-5">
                        {importResult.errors.slice(0, 10).map((item) => (
                            <li key={`error-${item.row}-${item.sku || ''}`}>Fila {item.row || '-'} {item.sku ? `SKU ${item.sku}: ` : ''}{item.error}</li>
                        ))}
                        {importResult.duplicates.slice(0, 10).map((item) => (
                            <li key={`dup-${item.row}-${item.sku}`}>Fila {item.row}: SKU duplicado {item.sku}</li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-xl font-semibold text-slate-900">Maestro</h2>
                    <span className="text-sm text-slate-500">{articles.length} articulos</span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-slate-700">
                        <thead>
                            <tr className="border-b border-slate-200 text-slate-500">
                                <th className="px-4 py-3">SKU</th>
                                <th className="px-4 py-3">Descripcion</th>
                                <th className="px-4 py-3">Division</th>
                                <th className="px-4 py-3">Calibre</th>
                                <th className="px-4 py-3">Uds/Bulto</th>
                                <th className="px-4 py-3">Bultos/Pallet</th>
                                <th className="px-4 py-3">Activo</th>
                            </tr>
                        </thead>
                        <tbody>
                            {articles.map((article) => (
                                <tr key={article.id} className="border-b border-slate-100 hover:bg-slate-50">
                                    <td className="px-4 py-3 font-medium text-slate-900">{article.sku}</td>
                                    <td className="px-4 py-3">{article.descripcion}</td>
                                    <td className="px-4 py-3">{article.division}</td>
                                    <td className="px-4 py-3">{article.calibre}</td>
                                    <td className="px-4 py-3">{article.unidades_por_bulto}</td>
                                    <td className="px-4 py-3">{article.bultos_por_pallet}</td>
                                    <td className="px-4 py-3">{article.activo ? 'Si' : 'No'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}

export default ArticlesPage
