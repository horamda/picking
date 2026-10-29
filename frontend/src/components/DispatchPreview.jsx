import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import { getStoredUser } from '../utils/auth'
const number = value => value == null ? 'Pendiente' : Number(value).toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export default function DispatchPreview({ sourceIds }) {
    const [data, setData] = useState(null), [error, setError] = useState('')
    const ids = [...sourceIds].sort((a, b) => a - b).join(',')
    useEffect(() => {
        setData(null); setError('')
        if (!ids) return
        let active = true
        const controller = new AbortController()
        const timer = setTimeout(() => api.post('/load-control/dispatch/preview', { source_ids: ids.split(',').map(Number) }, { signal: controller.signal })
            .then(r => { if (active) setData(r.data) })
            .catch(e => { if (active) setError(e.response?.data?.error || 'No se pudo calcular. Cambiá la selección o actualizá para reintentar.') }), 300)
        return () => { active = false; clearTimeout(timer); controller.abort() }
    }, [ids])
    if (!ids) return null
    if (error) return <p role="alert" className="my-3 text-sm text-red-700">{error}</p>
    if (!data) return <p role="status" className="my-3 text-sm">Calculando pallets y HL…</p>
    const partial = data.pallets == null
    return <section aria-label="Cálculo de la selección" className="my-3 space-y-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
        <div className="grid gap-3 sm:grid-cols-3">
            <div><p className="text-sm">Volumen</p><b className="text-xl">{number(data.hl ?? data.hl_known)} HL{data.hl == null ? ' parciales' : ''}</b></div>
            <div><p className="text-sm">Pallets físicos estimados{partial ? ' (parcial)' : ''}</p><b className="text-xl">{number(data.pallets ?? data.pallets_known)}</b><p className="text-sm">{data.full_pallets_known} completos + {data.picking_pallets_known} de picking</p></div>
            <div><p className="text-sm">Capacidad del camión</p><b>{data.capacity == null ? 'Sin configurar' : `${data.capacity} pallets`}</b>{data.fits != null && <p className={`text-sm ${data.fits ? 'text-emerald-800' : 'font-bold text-red-700'}`}>{data.fits ? 'Dentro de la capacidad estimada' : 'Supera la capacidad del camión'}</p>}</div>
        </div>
        <p className="text-xs text-slate-600">Mezcla entre canchas: {data.mix_courts ? 'permitida' : 'no permitida'}. Estimación por equivalencia de bultos; requiere revisión y aprobación del supervisor.</p>
        {data.capacity == null && <p className="text-sm">{getStoredUser()?.role === 'administrador' ? <>Configurá la capacidad física en <Link className="font-semibold underline" to="/configuracion">Camiones y capacidad</Link> para verificar si entra.</> : 'Solicitá al administrador la capacidad física del camión para verificar si entra.'}</p>}
        {!!data.missing.length && <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"><b>Datos pendientes para completar el cálculo</b><p>Los valores parciales excluyen los artículos sin el factor correspondiente:</p><ul className="mt-2 space-y-1">{data.missing.map(p => <li key={p.sku}>SKU {p.sku} · {p.descripcion}: {[p.hl && 'factor HL / unidades por bulto', p.pallets && 'artículo activo / bultos por pallet'].filter(Boolean).join('; ')}.</li>)}</ul><Link className="mt-2 inline-block font-semibold underline" to="/articulos">Revisar catálogo de artículos</Link></div>}
        <div className="overflow-x-auto">
            <table className="w-full text-left text-sm"><caption className="mb-2 text-left font-semibold">Resumen por cancha (unidades convertidas a bultos)</caption>
                <thead><tr><th className="p-2">Cancha</th><th className="p-2">Bultos equiv.</th><th className="p-2">HL</th><th className="p-2">Pallets equiv.</th></tr></thead>
                <tbody>{data.court_totals?.map(c => <tr key={c.court} className="border-t border-blue-200"><td className="p-2">{c.court}</td><td className="p-2">{number(c.bultos_equiv)}</td><td className="p-2">{number(c.hl ?? c.hl_known)}{c.hl == null ? ' parcial' : ''}</td><td className="p-2">{number(c.pallets_equiv)}</td></tr>)}</tbody>
                <tfoot><tr className="border-t font-bold"><td className="p-2">Total</td><td className="p-2">{number(data.bultos_equiv)}</td><td className="p-2">{number(data.hl ?? data.hl_known)}{data.hl == null ? ' parcial' : ''}</td><td className="p-2">{number(data.pallets_equiv)}</td></tr></tfoot>
            </table>
        </div>
        <p className="text-xs">Pallets equivalentes = bultos equivalentes / bultos por pallet de cada producto. Los pallets físicos cuentan posiciones enteras.</p>
        <details className="rounded-lg bg-white p-3"><summary className="cursor-pointer font-semibold">Ver cómo se arman los pallets{partial ? ' (parcial)' : ''}</summary>
            <div className="mt-3 space-y-3">{data.assembly?.map(p => <div key={p.id} className="rounded-lg border p-3"><b>{p.id} · {p.count} pallet{p.count === 1 ? '' : 's'} {p.id.startsWith('F') ? 'completos' : 'de picking'}</b><ul className="mt-2 space-y-2 text-sm">{p.items.map((item, index) => <li key={index}>Cancha {item.court} · Reparto {item.reparto} · {item.descripcion}: <b>{number(item.bultos_equiv)} bultos equiv.</b> · {number(item.pallets_equiv)} pallets equiv.</li>)}</ul></div>)}</div>
        </details>
    </section>
}
