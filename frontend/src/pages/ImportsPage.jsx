import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../api/axiosClient'
import UploadPage from './UploadPage'
import VoiceCsvImport from '../components/VoiceCsvImport'

export default function ImportsPage() {
    const [params, setParams] = useSearchParams()
    const tab = ['articulos', 'voz'].includes(params.get('tipo')) ? params.get('tipo') : 'pdf'
    const [file, setFile] = useState(null)
    const [mode, setMode] = useState('merge')
    const [busy, setBusy] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState('')
    async function upload(event) {
        event.preventDefault(); if (!file || busy) return
        setBusy(true); setResult(null); setError('')
        const data = new FormData(); data.append('file', file); data.append('mode', mode)
        try { const r = await api.post('/articles/import-csv', data); setResult(r.data) }
        catch (e) { setResult(e.response?.data || null); setError(e.response?.data?.error || 'No se aplicó la importación. Revisá los errores.') }
        finally { setBusy(false) }
    }
    return <div className="p-4 sm:p-6">
        <h1 className="text-2xl font-semibold">Importaciones</h1>
        <p className="mt-2 text-slate-500">Carga de archivos para actualizar el sistema.</p>
        <nav className="my-4 flex flex-wrap gap-3" aria-label="Tipo de importación">{[['pdf', 'Consolidados PDF'], ['articulos', 'Artículos CSV'], ['voz', 'Descripciones de voz']].map(([id, label]) => <button disabled={busy} key={id} onClick={() => setParams({ tipo: id })} className={`min-h-12 rounded-xl px-4 ${tab === id ? 'bg-brand-500 text-white' : 'border bg-white'}`}>{label}</button>)}</nav>
        {tab === 'pdf' ? <UploadPage /> : tab === 'voz' ? <VoiceCsvImport /> : <section className="max-w-3xl rounded-2xl border bg-white p-4 sm:p-6">
            <h2 className="text-lg font-semibold">Importar maestro de artículos</h2>
            <p className="my-3 text-sm text-slate-600">Se activan únicamente mercaderías con Activo = SI, Usado en dispositivo móvil = SI y Anulado = NO. Se conservan todos los campos del CSV y las descripciones de voz editadas.</p>
            <form className="space-y-4" onSubmit={upload}>
                <label className="block">Archivo CSV<input required disabled={busy} type="file" accept=".csv,text/csv" onChange={e => setFile(e.target.files?.[0] || null)} className="mt-2 block w-full min-w-0" /></label>
                <label className="block">Modo<select disabled={busy} value={mode} onChange={e => setMode(e.target.value)} className="mt-2 block min-h-12 w-full rounded-xl border p-3"><option value="merge">Actualizar artículos incluidos en el archivo</option><option value="replace">Sincronizar maestro completo</option></select></label>
                <p className="text-sm text-slate-500">{mode === 'replace' ? 'También se desactivan los artículos ausentes del CSV. No se borran registros ni historial.' : 'Los artículos excluidos por el filtro se desactivan si ya existían. Los ausentes del CSV no cambian.'} Si hay errores o SKU duplicados, no se aplica ningún cambio.</p>
                <button disabled={busy || !file} className="min-h-12 rounded-xl bg-brand-500 px-5 text-white disabled:opacity-50">{busy ? 'Importando…' : 'Importar CSV'}</button>
            </form>
            {error && <p role="alert" className="mt-4 text-red-700">{error}</p>}
            {result && <div className="mt-4" aria-live="polite"><p className="font-semibold">{result.applied ? 'Importación aplicada' : 'Importación rechazada'}</p><dl className="my-3 grid grid-cols-2 gap-3 sm:grid-cols-3">{[['Elegibles', result.eligible], ['Excluidos', result.excluded], ['Nuevos', result.created], ['Actualizados', result.updated], ['Sin cambios', result.unchanged], ['Desactivados', result.inactive]].map(([label, n]) => <div key={label} className="rounded-xl bg-slate-50 p-3"><dt>{label}</dt><dd className="text-2xl font-bold">{n ?? 0}</dd></div>)}</dl>{[...(result.errors || []), ...(result.duplicates || []).map(d => ({ ...d, error: 'SKU duplicado' }))].slice(0, 20).map((e, i) => <p key={i} className="text-red-700">Fila {e.row}: {e.sku} {e.error}</p>)}</div>}
            <Link className="mt-5 inline-block min-h-12 py-3 text-brand-600 underline" to="/articulos">Consultar artículos y editar voz</Link>
        </section>}
    </div>
}
