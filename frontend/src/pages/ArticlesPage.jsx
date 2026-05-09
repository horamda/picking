import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'
import { ActiveBadge } from '../components/Badge'
import {
    cellClass,
    headerCellClass,
    headerNumberCellClass,
    headerRowClass,
    numberCellClass,
    rowClass,
    strongCellClass,
    tableClass,
} from '../components/tableStyles'
import { formatNumber } from '../utils/format'

function ArticlesPage() {
    const [articles, setArticles] = useState([])
    const [articleMeta, setArticleMeta] = useState({ total: 0, page: 1, pages: 1, per_page: 50 })
    const [query, setQuery] = useState('')
    const [loadingArticles, setLoadingArticles] = useState(false)
    const [articlesError, setArticlesError] = useState('')
    const [csvFile, setCsvFile] = useState(null)
    const [importMode, setImportMode] = useState('merge')
    const [importResult, setImportResult] = useState(null)
    const [diagnostics, setDiagnostics] = useState(null)
    const [status, setStatus] = useState('')
    const role = localStorage.getItem('role')
    const canImport = ['administrador', 'supervisor'].includes(role)

    const loadArticles = async (page = articleMeta.page, search = query) => {
        setLoadingArticles(true)
        setArticlesError('')
        try {
            const response = await axiosClient.get('/articles', {
                params: {
                    page,
                    per_page: articleMeta.per_page,
                    q: search || undefined,
                },
            })
            const payload = Array.isArray(response.data)
                ? { items: response.data, total: response.data.length, page: 1, pages: 1, per_page: response.data.length || 50 }
                : response.data
            setArticles(payload.items || [])
            setArticleMeta({
                total: payload.total || 0,
                page: payload.page || 1,
                pages: payload.pages || 1,
                per_page: payload.per_page || 50,
            })
        } catch (error) {
            setArticles([])
            setArticlesError(error.response?.data?.error_detail || error.response?.data?.error || 'No se pudieron cargar los articulos')
        } finally {
            setLoadingArticles(false)
        }
    }

    useEffect(() => {
        loadArticles(1, '')
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const handleSearch = (event) => {
        event.preventDefault()
        loadArticles(1, query)
    }

    const importCsv = async () => {
        if (!csvFile) return
        const formData = new FormData()
        formData.append('file', csvFile)
        formData.append('mode', importMode)
        setStatus('Importando CSV...')
        try {
            const response = await axiosClient.post('/articles/import-csv', formData)
            setImportResult(response.data)
            setStatus(response.data.applied ? 'CSV aplicado correctamente' : 'CSV rechazado')
            await loadArticles()
        } catch (error) {
            const payload = error.response?.data || {}
            setImportResult({
                deleted: 0,
                created: 0,
                updated: 0,
                unchanged: 0,
                inactive: 0,
                ...payload,
                duplicates: payload.duplicates || [],
                errors: payload.errors || [{ row: null, error: payload.error || 'Error importando CSV' }],
            })
            setStatus(payload.error || 'CSV rechazado')
        }
    }

    const loadDiagnostics = async () => {
        try {
            const response = await axiosClient.get('/articles/import-diagnostics')
            setDiagnostics(response.data)
        } catch (error) {
            setDiagnostics({
                error: error.response?.data?.error || 'No se pudo obtener diagnostico',
            })
        }
    }

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Articulos</h1>
                    <p className="mt-1 text-sm text-slate-500">Maestro logistico para calcular bultos equivalentes y pallets.</p>
                </div>
                <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm xl:w-auto">
                    <p className="mb-3 text-sm font-medium text-slate-700">Importar maestro CSV</p>
                    {!canImport && (
                        <div className="mb-3 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                            Tu rol actual no permite importar maestros. Necesitas administrador o supervisor.
                        </div>
                    )}
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                        <input
                            type="file"
                            accept=".csv,text/csv"
                            onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                            className="text-sm text-slate-600 file:mr-3 file:rounded-xl file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-slate-700"
                        />
                        <select
                            value={importMode}
                            onChange={(e) => setImportMode(e.target.value)}
                            className="rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-700 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        >
                            <option value="merge">Actualizar maestro</option>
                            <option value="replace">Reemplazar maestro</option>
                        </select>
                        <button
                            type="button"
                            onClick={importCsv}
                            disabled={!csvFile || !canImport}
                            className="rounded-xl bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-40"
                        >
                            Importar
                        </button>
                        <button
                            type="button"
                            onClick={loadDiagnostics}
                            disabled={!canImport}
                            className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                        >
                            Diagnostico
                        </button>
                    </div>
                    {importMode === 'replace' && (
                        <div className="mt-3 flex items-start gap-2 rounded-2xl bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
                            <svg xmlns="http://www.w3.org/2000/svg" className="mt-0.5 h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                            </svg>
                            Reemplazar borra el maestro actual. Si el archivo tiene errores o SKUs duplicados, no se aplica ningun cambio.
                        </div>
                    )}
                    {status && (
                        <p className={`mt-2 text-sm ${status.includes('aplicado') ? 'text-emerald-700' : 'text-slate-600'}`}>
                            {status}
                        </p>
                    )}
                </div>
            </div>

            {diagnostics && (
                <div className="mb-6 rounded-3xl border border-slate-200 bg-white p-5 text-sm shadow-sm">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                            <p className="font-semibold text-slate-900">Diagnostico de importacion</p>
                            {diagnostics.error ? (
                                <p className="mt-1 text-red-700">{diagnostics.error}</p>
                            ) : (
                                <p className="mt-1 text-slate-500">
                                    DB {diagnostics.database.dialect}/{diagnostics.database.driver} - Rol {diagnostics.user.role} - {diagnostics.article_count} articulos
                                </p>
                            )}
                        </div>
                        {!diagnostics.error && (
                            <span className={`rounded-full px-3 py-1 text-xs font-medium ${
                                diagnostics.database.is_postgresql ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                            }`}>
                                {diagnostics.database.is_postgresql ? 'PostgreSQL persistente' : 'No es PostgreSQL'}
                            </span>
                        )}
                    </div>
                    {!diagnostics.error && diagnostics.last_csv_upload && (
                        <p className="mt-3 text-xs text-slate-500">
                            Ultimo CSV: {diagnostics.last_csv_upload.status} - {diagnostics.last_csv_upload.original_filename} - {diagnostics.last_csv_upload.size_bytes} bytes
                            {diagnostics.last_csv_upload.error_message ? ` - ${diagnostics.last_csv_upload.error_message}` : ''}
                        </p>
                    )}
                </div>
            )}

            {importResult && (
                <div className="mb-6 grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
                    {[
                        ['Borrados', importResult.deleted, importResult.deleted > 0 ? 'text-red-700' : ''],
                        ['Nuevos', importResult.created, importResult.created > 0 ? 'text-emerald-700' : ''],
                        ['Modificados', importResult.updated, importResult.updated > 0 ? 'text-brand-600' : ''],
                        ['Sin cambios', importResult.unchanged, ''],
                        ['Inactivos', importResult.inactive, ''],
                        ['Errores', importResult.errors.length + importResult.duplicates.length, (importResult.errors.length + importResult.duplicates.length) > 0 ? 'text-red-700' : ''],
                    ].map(([label, value, color]) => (
                        <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                            <p className="text-xs font-medium uppercase tracking-[0.15em] text-slate-400">{label}</p>
                            <p className={`mt-2 text-2xl font-semibold ${color || 'text-slate-900'}`}>{value}</p>
                        </div>
                    ))}
                </div>
            )}

            {importResult && (importResult.errors.length > 0 || importResult.duplicates.length > 0) && (
                <div className="mb-6 rounded-3xl border border-red-200 bg-red-50 p-5 text-sm text-red-900">
                    <p className="font-semibold">Errores del CSV</p>
                    <ul className="mt-3 list-disc space-y-1 pl-5">
                        {importResult.errors.slice(0, 10).map((item) => (
                            <li key={`error-${item.row}-${item.sku || ''}`}>
                                Fila {item.row || '-'} {item.sku ? `SKU ${item.sku}: ` : ''}{item.error}
                            </li>
                        ))}
                        {importResult.duplicates.slice(0, 10).map((item) => (
                            <li key={`dup-${item.row}-${item.sku}`}>Fila {item.row}: SKU duplicado {item.sku}</li>
                        ))}
                    </ul>
                </div>
            )}

            <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
                <div className="flex flex-col gap-4 border-b border-slate-100 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <h2 className="font-semibold text-slate-900">Maestro de articulos</h2>
                        <span className="text-sm text-slate-400">
                            {articleMeta.total} articulos - pagina {articleMeta.page} de {articleMeta.pages || 1}
                        </span>
                    </div>
                    <form onSubmit={handleSearch} className="flex flex-col gap-2 sm:flex-row sm:items-center">
                        <input
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="Buscar SKU o descripcion"
                            className="rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-700 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                        />
                        <button
                            type="submit"
                            className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                        >
                            Buscar
                        </button>
                        {query && (
                            <button
                                type="button"
                                onClick={() => {
                                    setQuery('')
                                    loadArticles(1, '')
                                }}
                                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
                            >
                                Limpiar
                            </button>
                        )}
                    </form>
                </div>
                <div className="p-4">
                    {articlesError && (
                        <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                            {articlesError}
                        </div>
                    )}
                    {loadingArticles && (
                        <div className="mb-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-500">
                            Cargando articulos...
                        </div>
                    )}
                    <div className="overflow-x-auto">
                        <table className={tableClass}>
                            <thead>
                                <tr className={headerRowClass}>
                                    <th className={headerCellClass}>SKU</th>
                                    <th className={headerCellClass}>Descripcion</th>
                                    <th className={headerCellClass}>Division</th>
                                    <th className={headerCellClass}>Calibre</th>
                                    <th className={headerNumberCellClass}>Uds/Bulto</th>
                                    <th className={headerNumberCellClass}>Bultos/Pallet</th>
                                    <th className={headerCellClass}>Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {!loadingArticles && articles.map((article) => (
                                    <tr key={article.id} className={rowClass}>
                                        <td className={strongCellClass}>{article.sku}</td>
                                        <td className={cellClass}>{article.descripcion}</td>
                                        <td className={cellClass}>{article.division}</td>
                                        <td className={cellClass}>{article.calibre}</td>
                                        <td className={numberCellClass}>{formatNumber(article.unidades_por_bulto)}</td>
                                        <td className={numberCellClass}>{formatNumber(article.bultos_por_pallet)}</td>
                                        <td className={cellClass}><ActiveBadge activo={article.activo} /></td>
                                    </tr>
                                ))}
                                {!loadingArticles && articles.length === 0 && !articlesError && (
                                    <tr>
                                        <td colSpan={7} className="border border-slate-200 py-8 text-center text-sm text-slate-500">
                                            No hay articulos para mostrar.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                    <div className="mt-4 flex items-center justify-between gap-3">
                        <button
                            type="button"
                            disabled={!articleMeta.page || articleMeta.page <= 1 || loadingArticles}
                            onClick={() => loadArticles(articleMeta.page - 1)}
                            className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                        >
                            Anterior
                        </button>
                        <span className="text-xs text-slate-400">
                            Mostrando {articles.length} de {articleMeta.total}
                        </span>
                        <button
                            type="button"
                            disabled={articleMeta.page >= articleMeta.pages || loadingArticles}
                            onClick={() => loadArticles(articleMeta.page + 1)}
                            className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                        >
                            Siguiente
                        </button>
                    </div>
                </div>
            </section>
        </div>
    )
}

export default ArticlesPage
