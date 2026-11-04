import { useState } from 'react'
import api from '../api/axiosClient'

export default function LogisticsImport() {
    const [file, setFile] = useState(null), [result, setResult] = useState(null)
    const [busy, setBusy] = useState(false), [error, setError] = useState('')
    async function send(apply) {
        if (!file || busy) return
        setBusy(true); setError('')
        const data = new FormData(); data.append('file', file); data.append('apply', apply ? '1' : '0')
        try { setResult((await api.post('/articles/import-logistics-xlsx', data)).data) }
        catch (e) { setResult(e.response?.data || null); setError(e.response?.data?.error || 'No se pudo analizar la plantilla.') }
        finally { setBusy(false) }
    }
    return <section className="max-w-4xl rounded-2xl border bg-white p-4 sm:p-6"><h2 className="text-lg font-semibold">Importar datos logísticos y palletizado</h2>
        <p className="my-3 text-sm text-slate-600">Complementa artículos existentes por SKU. Actualiza unidades por bulto, bultos por pallet, pisos, bultos por piso, apilabilidad, HL y códigos de barras. No modifica estado, clasificación ni descripción de voz.</p>
        <label className="block">Plantilla de artículos XLSX<input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={busy} onChange={e => { setFile(e.target.files?.[0] || null); setResult(null); setError('') }} className="mt-2 block w-full" /></label>
        <div className="mt-4 flex flex-wrap gap-3"><button type="button" disabled={!file || busy} onClick={() => send(false)} className="min-h-12 rounded-xl border px-5 disabled:opacity-50">{busy?'Analizando…':'Vista previa'}</button><button type="button" disabled={!file || busy || !result || result.applied || result.errors?.length} onClick={() => send(true)} className="min-h-12 rounded-xl bg-brand-500 px-5 text-white disabled:opacity-50">Aplicar actualización</button></div>
        {error && <p role="alert" className="mt-4 text-red-700">{error}</p>}
        {result && <div className="mt-5" aria-live="polite"><p className="font-semibold">{result.applied?'Actualización aplicada':'Vista previa'}</p><dl className="my-3 grid grid-cols-2 gap-3 sm:grid-cols-5">{[['Filas',result.total],['Coinciden',result.matched],['Cambiarían',result.updated],['Sin cambios',result.unchanged],['Desconocidos',result.unknown?.length]].map(([label,n])=><div key={label} className="rounded-xl bg-slate-50 p-3"><dt className="text-sm">{label}</dt><dd className="text-2xl font-bold">{n??0}</dd></div>)}</dl>
            {!!result.warnings?.length && <div className="rounded-xl bg-amber-50 p-3 text-amber-900"><b>{result.warnings.length} advertencias de palletizado</b>{result.warnings.slice(0,20).map(w=><p key={`${w.row}-${w.sku}`}>Fila {w.row} · SKU {w.sku}: {w.warning}</p>)}</div>}
            {!!result.unknown?.length && <div className="mt-3 rounded-xl bg-slate-50 p-3"><b>SKU no creados automáticamente</b><p className="mt-1 text-sm">{result.unknown.slice(0,30).map(x=>x.sku).join(', ')}</p></div>}
            {!!result.errors?.length && result.errors.slice(0,20).map(e=><p className="text-red-700" key={`${e.row}-${e.sku}`}>Fila {e.row} · {e.sku}: {e.error}</p>)}</div>}
    </section>
}
