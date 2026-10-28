import { useState } from 'react'
import api from '../api/axiosClient'

export default function VoiceCsvImport() {
    const [file, setFile] = useState(null), [result, setResult] = useState(null)
    const [busy, setBusy] = useState(false), [error, setError] = useState('')
    async function download() {
        setBusy(true); setError('')
        try {
            const response = await api.get('/articles/voice-csv', { responseType: 'blob' })
            const url = URL.createObjectURL(response.data), link = document.createElement('a')
            link.href = url; link.download = 'descripciones-voz.csv'
            document.body.appendChild(link); link.click(); link.remove()
            setTimeout(() => URL.revokeObjectURL(url), 1000)
        } catch { setError('No se pudo exportar. Reintentá.') }
        finally { setBusy(false) }
    }
    async function upload(apply) {
        if (!file || busy) return
        setBusy(true); setError('')
        const data = new FormData(); data.append('file', file); data.append('apply', apply ? '1' : '0')
        try { const response = await api.post('/articles/voice-csv', data); setResult(response.data) }
        catch (e) { setResult(null); setError(e.response?.data?.error || 'No se aplicaron cambios. Reintentá.') }
        finally { setBusy(false) }
    }
    return <section className="max-w-5xl rounded-2xl border bg-white p-4 sm:p-6">
        <h2 className="text-lg font-semibold">Modificar descripciones de voz masivamente</h2>
        <ol className="my-4 list-decimal space-y-2 pl-5 text-sm text-slate-600">
            <li>Exportá todos los artículos, activos e inactivos, incluso los que todavía no tienen voz personalizada.</li>
            <li>Abrí el CSV en Excel como UTF-8 y la columna Código como texto para conservar ceros iniciales. Modificá «Descripcion para voz» y guardá como CSV UTF-8.</li>
            <li>Conservá los encabezados, códigos y la columna «Control (no editar)». Podés quitar filas que no quieras actualizar. Una descripción vacía conserva la actual; para eliminarla, escribí SI en «Borrar voz».</li>
            <li>Subí el archivo, revisá los cambios y confirmá. Si hay un error, se rechaza el archivo completo.</li>
        </ol>
        <button disabled={busy} onClick={download} className="min-h-12 rounded-xl border px-4 disabled:opacity-50">Exportar CSV editable</button>
        <label className="my-4 block">Archivo editado<input disabled={busy} type="file" accept=".csv,text/csv" className="mt-2 block w-full min-w-0" onChange={e => { setFile(e.target.files?.[0] || null); setResult(null); setError('') }} /></label>
        <button disabled={busy || !file} onClick={() => upload(false)} className="min-h-12 rounded-xl border px-4 disabled:opacity-50">{busy ? 'Procesando…' : 'Validar y ver cambios'}</button>
        {error && <p role="alert" className="mt-4 text-red-700">{error}</p>}
        {result && <div className="mt-4" aria-live="polite">
            <p className="font-semibold">{result.applied ? 'Importación aplicada' : 'Archivo validado'}: {result.updated} cambios y {result.unchanged} sin cambios.</p>
            {!!result.changes.length && <div className="my-4 max-h-96 overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">Código</th><th className="p-2">Voz anterior</th><th className="p-2">Nueva voz</th></tr></thead><tbody>{result.changes.map(c => <tr key={c.sku} className="border-t"><td className="p-2">{c.sku}</td><td className="p-2 whitespace-pre-wrap">{c.before || 'Descripción original'}</td><td className="p-2 whitespace-pre-wrap">{c.after || 'Usar descripción original'}</td></tr>)}</tbody></table></div>}
            {!result.applied && result.updated > 0 && <button disabled={busy} onClick={() => upload(true)} className="min-h-12 rounded-xl bg-brand-500 px-5 text-white disabled:opacity-50">Confirmar {result.updated} cambios</button>}
        </div>}
        <p className="mt-4 text-sm text-slate-500">Se registra quién hizo cada cambio y el valor anterior. El maestro de artículos y los reportes se conservan.</p>
    </section>
}
