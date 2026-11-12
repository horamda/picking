import { useState } from 'react'
import api from '../api/axiosClient'

function displayFilename(name = '') {
    return name.replace(/^\d{14}/, '') || name
}

function fileDate(file) {
    const prefix = file?.name?.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/)
    if (prefix) {
        const [, year, month, day, hour, minute, second] = prefix
        const parsed = new Date(Number(year), Number(month) - 1, Number(day), Number(hour), Number(minute), Number(second))
        if (!Number.isNaN(parsed.getTime())) return new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' }).format(parsed)
    }
    if (!file?.lastModified) return ''
    return new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(file.lastModified))
}

const resultCards = [
    ['Filas', 'total', ''],
    ['Coinciden', 'matched', 'result-card--success'],
    ['Cambiarían', 'updated', 'result-card--warning'],
    ['Sin cambios', 'unchanged', ''],
    ['Desconocidos', 'unknown', 'result-card--danger'],
]

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
    const canApply = Boolean(file && result && !result.applied && Number(result.updated) > 0 && !result.errors?.length)
    return <section className="imports-surface max-w-4xl rounded-2xl border p-4 sm:p-6"><h2 className="text-lg font-semibold">Importar datos logísticos y palletizado</h2>
        <p className="imports-muted my-3">Complementa artículos existentes por SKU. Actualiza unidades por bulto, bultos por pallet, pisos, bultos por piso, apilabilidad, HL y códigos de barras. No modifica estado, clasificación ni descripción de voz.</p>
        <label className="block font-medium">Plantilla de artículos XLSX<input type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={busy} onChange={e => { setFile(e.target.files?.[0] || null); setResult(null); setError('') }} className="mt-2 block w-full" /></label>
        {file && <div className="imports-surface mt-3 rounded-xl border p-3" aria-live="polite"><p className="break-all text-sm font-semibold">{displayFilename(file.name)}</p><p className="imports-muted mt-1">Fecha del archivo: {fileDate(file)}</p></div>}
        <div className="mt-4 flex flex-wrap gap-3"><button type="button" disabled={!file || busy} onClick={() => send(false)} className="min-h-11 rounded-xl border px-5 disabled:opacity-50">{busy ? 'Analizando…' : 'Vista previa'}</button><button type="button" disabled={!canApply || busy} onClick={() => send(true)} className="action-primary min-h-11 rounded-xl px-5 font-semibold">Aplicar actualización</button></div>
        {error && <p role="alert" className="mt-4 text-red-700">{error}</p>}
        {result && <div className="mt-5" aria-live="polite"><p className="font-semibold">{result.applied ? 'Actualización aplicada' : 'Vista previa'}</p><dl className="my-3 grid grid-cols-2 gap-3 sm:grid-cols-5">{resultCards.map(([label, key, tone]) => { const value = key === 'unknown' ? result.unknown?.length : result[key]; return <div key={label} className={`result-card rounded-xl p-3 text-center ${tone}`}><dt className="imports-muted">{label}</dt><dd className="text-2xl font-bold">{value ?? 0}</dd></div> })}</dl>
            {!!result.warnings?.length && <div className="rounded-xl bg-amber-50 p-3 text-amber-900"><b>{result.warnings.length} advertencias de palletizado</b>{result.warnings.slice(0, 20).map(w => <p className="mt-1 text-sm" key={`${w.row}-${w.sku}`}>Fila {w.row} · SKU {w.sku}: {w.warning}</p>)}</div>}
            {!!result.unknown?.length && <div className="unknown-panel mt-3 rounded-xl border p-3"><b className="unknown-panel-title">SKU no creados automáticamente ({result.unknown.length})</b><div className="mt-3 flex flex-wrap gap-2">{result.unknown.slice(0, 30).map((item, index) => <span className="sku-chip inline-flex min-h-9 items-center rounded-full px-3 text-sm tabular-nums" key={`${item.row}-${item.sku}-${index}`}>{item.sku}<span className="future-sku-action" aria-hidden="true" /></span>)}</div></div>}
            {!!result.errors?.length && result.errors.slice(0, 20).map(e => <p className="mt-2 text-red-700" key={`${e.row}-${e.sku}`}>Fila {e.row} · {e.sku}: {e.error}</p>)}</div>}
    </section>
}
