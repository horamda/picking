import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'
import ArticleVoiceEditor from '../components/ArticleVoiceEditor'
import VoiceBackupTable from '../components/VoiceBackupTable'
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
    const [editing, setEditing] = useState(null)
    const [showBackup, setShowBackup] = useState(false)
    const [articles, setArticles] = useState([])
    const [articleMeta, setArticleMeta] = useState({ total: 0, page: 1, pages: 1, per_page: 50 })
    const [query, setQuery] = useState('')
    const [activeFilter, setActiveFilter] = useState('1')
    const [loadingArticles, setLoadingArticles] = useState(false)
    const [articlesError, setArticlesError] = useState('')
    const role = localStorage.getItem('role')
    const canImport = ['administrador', 'supervisor'].includes(role)

    const loadArticles = async (page = articleMeta.page, search = query, active = activeFilter) => {
        setLoadingArticles(true)
        setArticlesError('')
        try {
            const response = await axiosClient.get('/articles', {
                params: {
                    page,
                    per_page: articleMeta.per_page,
                    q: search || undefined,
                    activo: active || undefined,
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

    return (
        <div className="bg-slate-50 p-4 sm:p-6">
            {editing && <ArticleVoiceEditor key={editing.id} article={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); loadArticles() }} />}
            <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Articulos</h1>
                    <p className="mt-1 text-sm text-slate-500">Maestro logistico para calcular bultos equivalentes y pallets.</p>
                </div>
                {canImport && <button className="min-h-12 rounded-xl border bg-white px-4" onClick={() => { setEditing(null); setShowBackup(true) }}>Respaldo de voz</button>}
            </div>

            {showBackup && <VoiceBackupTable onClose={() => setShowBackup(false)} />}

            <section className="rounded-3xl border border-slate-200 bg-white shadow-sm">
                <div className="flex flex-col gap-4 border-b border-slate-100 px-6 py-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <h2 className="font-semibold text-slate-900">Maestro de articulos</h2>
                        <span className="text-sm text-slate-400">
                            {articleMeta.total} articulos - pagina {articleMeta.page} de {articleMeta.pages || 1}
                        </span>
                    </div>
                    <form onSubmit={handleSearch} className="flex flex-col gap-2 sm:flex-row sm:items-center">
                        <select aria-label="Estado del artículo" value={activeFilter} onChange={e => { setActiveFilter(e.target.value); loadArticles(1, query, e.target.value) }} className="min-h-12 rounded-xl border px-3"><option value="1">Activos</option><option value="0">Inactivos</option><option value="">Todos</option></select>
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
                                    <th className={headerCellClass}>Estado</th><th className={headerCellClass}>Voz y datos</th>
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
                                        <td className={cellClass}><ActiveBadge activo={article.activo} /></td><td className={cellClass}>{canImport && <button className="min-h-12 text-brand-600 underline" onClick={() => setEditing(article)}>Editar voz / ver datos</button>}</td>
                                    </tr>
                                ))}
                                {!loadingArticles && articles.length === 0 && !articlesError && (
                                    <tr>
                                        <td colSpan={8} className="border border-slate-200 py-8 text-center text-sm text-slate-500">
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
