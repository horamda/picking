import { useState } from 'react'
import api from '../api/axiosClient'
import { todayInputValue, formatNumber } from '../utils/format'

const field = 'mt-1 min-h-12 w-full rounded-xl border border-slate-300 p-3'
const card = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm'
const button = 'min-h-12 rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white disabled:opacity-50'

export default function CapacityReportsPage() {
    const today = todayInputValue()
    const [values, setValues] = useState({ operators: 5, hours: 8, productivity: 40, demand: 1500 })
    const [range, setRange] = useState({ desde: today, hasta: today })
    const [result, setResult] = useState(null)
    const [busy, setBusy] = useState(false), [error, setError] = useState('')
    async function simulate(event) {
        event.preventDefault(); setBusy(true); setError('')
        try { setResult((await api.post('/dashboard/capacity-simulator', Object.fromEntries(Object.entries(values).map(([key, value]) => [key, Number(value)])))).data) }
        catch (reason) { setError(reason.response?.data?.error || 'No se pudo calcular el escenario.') }
        finally { setBusy(false) }
    }
    async function download(report) {
        setBusy(true); setError('')
        try {
            const response = await api.get(`/dashboard/export/${report}.csv`, { params: range, responseType: 'blob' })
            const url = URL.createObjectURL(response.data), link = document.createElement('a')
            link.href = url; link.download = `pickearya-${report}-${range.desde}-${range.hasta}.csv`; link.click()
            URL.revokeObjectURL(url)
        } catch (reason) { setError(reason.response?.data?.error || 'No se pudo exportar el reporte.') }
        finally { setBusy(false) }
    }
    const metrics = result ? [['Capacidad', `${formatNumber(result.capacity)} bultos`], ['Cobertura', result.coverage_pct == null ? 'No calculable' : `${formatNumber(result.coverage_pct)}%`], ['Diferencia', `${formatNumber(result.difference)} bultos`], ['Operarios adicionales', result.additional_operators ?? 'No calculable'], ['Horas necesarias', result.required_hours == null ? 'No calculable' : `${formatNumber(result.required_hours)} h`]] : []
    return <div className="mx-auto max-w-6xl space-y-5 p-4 sm:p-8"><header><p className="text-sm font-semibold text-brand-600">Planificación analítica</p><h1 className="mt-1 text-2xl font-bold">Simulador de capacidad y exportaciones</h1><p className="mt-2 text-slate-600">Los escenarios son hipótesis independientes: no modifican cargas, personas, objetivos ni planificación de pallets.</p></header>{error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}<form className={card} onSubmit={simulate}><h2 className="text-lg font-bold">Escenario en bultos</h2><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[['operators','Operarios',1],['hours','Horas efectivas',0.25],['productivity','Productividad bultos/h',0.1],['demand','Demanda en bultos',0.1]].map(([key,label,step]) => <label key={key}>{label}<input className={field} type="number" min="0" step={step} value={values[key]} onChange={event => setValues(previous => ({ ...previous, [key]: event.target.value }))} required /></label>)}</div><button disabled={busy} className={`${button} mt-4`}>Calcular escenario</button>{result && <><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{metrics.map(([label,value]) => <div key={label} className="rounded-xl bg-slate-50 p-4 text-center"><p className="text-xs text-slate-500">{label}</p><strong className="text-xl">{value}</strong></div>)}</div><p className="mt-3 text-xs text-slate-500">{result.assumptions}</p></>}</form><section className={card}><h2 className="text-lg font-bold">Exportaciones reconciliadas</h2><p className="mt-1 text-sm text-slate-500">CSV UTF-8 separado por punto y coma. Usa las mismas fórmulas y filtros de operación, productividad y calidad.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><label>Desde<input className={field} type="date" value={range.desde} onChange={event => setRange(previous => ({ ...previous, desde: event.target.value }))} /></label><label>Hasta<input className={field} type="date" value={range.hasta} onChange={event => setRange(previous => ({ ...previous, hasta: event.target.value }))} /></label></div><div className="mt-4 flex flex-wrap gap-3">{[['operations','Operación'],['productivity','Productividad'],['quality','Calidad e incidencias']].map(([key,label]) => <button type="button" disabled={busy} key={key} className={button} onClick={() => download(key)}>Descargar {label}</button>)}</div><p className="mt-3 text-xs text-slate-500">El rango es obligatorio y no puede superar 366 días. Las celdas que podrían interpretarse como fórmulas se neutralizan.</p></section></div>
}
