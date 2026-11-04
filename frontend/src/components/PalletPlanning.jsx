import { useEffect, useState } from 'react'
import api from '../api/axiosClient'
import { Link } from 'react-router-dom'
import { getStoredUser } from '../utils/auth'

export default function PalletPlanning({ truck, onClose }) {
    const [capacity, setCapacity] = useState('')
    const [configuredCapacity, setConfiguredCapacity] = useState(null)
    const [defaultMix, setDefaultMix] = useState(false)
    const [message, setMessage] = useState('')
    const admin = getStoredUser()?.role === 'administrador'
    const [mix, setMix] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState('')
    const [reviewed, setReviewed] = useState(false)
    const [approved, setApproved] = useState(false)
    const [locked, setLocked] = useState(false)
    const [busy, setBusy] = useState(false)
    const [loads, setLoads] = useState([]), [compact, setCompact] = useState([])
    useEffect(() => {
        let active = true
        async function load() {
            setBusy(true)
            try {
                const [configuration, saved] = await Promise.all([api.get('/load-control/settings'), api.get(`/load-control/trucks/${truck.id}/planning`)])
                if (!active) return
                const entry = configuration.data.trucks.find(t => t.branch === truck.branch && t.truck === truck.truck)
                setConfiguredCapacity(saved.data.configured_capacity ?? entry?.capacity ?? null)
                setDefaultMix(configuration.data.depots.find(d => d.branch === truck.branch)?.mix_courts_default || false)
                setLocked(saved.data.locked)
                setLoads(saved.data.loads || [])
                setCompact(saved.data.plan?.compact_load_ids || [])
                if (saved.data.locked && saved.data.plan) {
                    setResult(saved.data.plan); setApproved(true); setCapacity(String(saved.data.plan.capacity)); setMix(saved.data.plan.mix_courts)
                } else {
                    if(saved.data.configured_capacity ?? entry?.capacity) setCapacity(String(saved.data.configured_capacity ?? entry.capacity))
                    setMix(configuration.data.depots.find(d => d.branch === truck.branch)?.mix_courts_default || false)
                    if(!saved.data.locked) await api.post(`/load-control/trucks/${truck.id}/planning/start`)
                }
            } catch (e) { if(active) setError(e.response?.data?.error || 'No se pudo cargar la planificación.') }
            finally { if(active) setBusy(false) }
        }
        load(); return () => { active = false }
    }, [truck.id])
    const button = 'min-h-12 rounded-xl border border-slate-300 bg-white px-4 py-2 font-medium disabled:opacity-40'
    const capacityMatches = configuredCapacity !== null && result?.capacity === configuredCapacity
    const loadPlanTotal = result?.load_plans?.reduce((sum, plan) => sum + plan.total_pallets, 0) || 0
    async function simulate(event) {
        event.preventDefault(); setBusy(true); setError(''); setMessage(''); setResult(null); setReviewed(false); setApproved(false)
        try {
            const value = Number(capacity)
            if (!Number.isInteger(value) || value <= 0) throw new Error('Ingresá una capacidad física entera positiva.')
            if (value !== configuredCapacity) {
                if (!admin) throw new Error('El administrador debe registrar la capacidad real de este camión antes de calcular.')
                await api.put('/load-control/settings', { branch: truck.branch, truck: truck.truck, capacity: value, mix_courts_default: defaultMix }, { timeout: 15000 })
                setConfiguredCapacity(value)
            }
            const response = await api.post(`/load-control/trucks/${truck.id}/planning/simulate`, { capacity: Number(capacity), mix_courts: mix, compact_load_ids: compact }, { timeout: 15000 })
            setResult(response.data)
        } catch (e) { setError(e.response?.data?.error || e.message || 'No se pudo calcular. Reintentá.') }
        finally { setBusy(false) }
    }
    return <section className="space-y-4 rounded-2xl border border-blue-200 bg-blue-50 p-5" aria-label="Simulación de pallets">
        <div className="flex items-center justify-between gap-3"><h2 className="text-xl font-semibold">Planificar pallets · {truck.truck}</h2><button className={button} onClick={onClose}>Cerrar</button></div>
        <p>Revisá el armado y aprobalo para entregar las tareas a los operarios.</p>
        <p className="rounded-xl bg-white p-3 font-semibold">Cada reparto se arma separado. Ningún pallet puede contener mercadería de otro reparto ni de otro camión.</p>
        {locked && result?.separation_policy !== 'reparto_v1' && <p role="alert" className="rounded-xl bg-amber-100 p-3">Plan anterior ya iniciado: revisar físicamente la separación entre repartos. Sus instrucciones no se reemplazan durante el armado.</p>}
        {locked && <p className="rounded-xl bg-amber-100 p-3">El trabajo ya comenzó. Se conserva el plan aprobado y no se pueden cambiar sus cantidades.</p>}
        <form className="flex flex-wrap items-end gap-4" onSubmit={simulate}>
            <fieldset disabled={busy || locked} className="min-w-0 w-full space-y-3"><legend className="mb-2 font-semibold">Tipo de armado de cada reparto</legend>
                {loads.map(l => <label key={l.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-white p-3"><span>Reparto {l.reparto}</span><select aria-label={`Armado del reparto ${l.reparto}`} className="min-h-12 min-w-0 w-full max-w-full rounded-xl border p-2 text-sm sm:w-auto" value={compact.includes(l.id) ? 'compact' : 'normal'} onChange={e => { setCompact(current => e.target.value === 'compact' ? [...current.filter(n => n !== l.id), l.id] : current.filter(n => n !== l.id)); setResult(null); setReviewed(false); setApproved(false) }}><option value="normal">Normal · por canchas</option><option value="compact">Supermercado / autoelevador · reducir pallets</option></select></label>)}
                <p className="text-sm">Supermercado: combina canchas y productos compatibles dentro de ese reparto para reducir la cantidad estimada de pallets.</p>
            </fieldset>
            <label className="text-sm">Capacidad del camión en pallets físicos<input className="mt-1 block min-h-12 rounded-xl border p-3" type="number" min="1" step="1" required value={capacity} disabled={busy || locked} onChange={e => { setCapacity(e.target.value); setResult(null) }} /></label>
            <label className="flex min-h-12 items-center gap-2"><input type="checkbox" checked={mix} disabled={busy || locked} onChange={e => { setMix(e.target.checked); setResult(null) }} />Combinar canchas dentro de cada reparto normal, aunque entren separadas</label>
            <button className={button} disabled={busy || locked}>{busy ? 'Procesando…' : admin && Number(capacity) !== configuredCapacity ? 'Guardar capacidad y calcular armado' : 'Calcular armado'}</button>
        </form>
        {!locked && <div className={`space-y-3 rounded-xl p-4 ${configuredCapacity === null ? 'bg-amber-100' : 'bg-white'}`}>
            <p className="font-semibold">{configuredCapacity === null ? 'Ingresá la capacidad real del camión y guardala al calcular el armado.' : `Capacidad registrada: ${configuredCapacity} pallets físicos.`}</p>
            <p className="text-sm">Depósito {truck.branch} · Camión {truck.truck}. Usá su capacidad física real; no la cantidad de pallets calculada para esta carga.</p>
            {admin ? <p>El botón «Guardar capacidad y calcular armado» registra este valor en el depósito de la carga. <Link className="underline" to="/configuracion">Ver configuración</Link></p> : <p>Si falta la capacidad o es incorrecta, pedile al administrador que la registre en «Camiones y capacidad».</p>}
        </div>}
        {message && <p role="status" className="rounded-xl bg-emerald-100 p-4">{message}</p>}
        {error && <p role="alert" className="text-red-800">{error}</p>}
        {approved && !locked && <p role="status" className="rounded-xl bg-emerald-100 p-4">Carga aprobada. Cada operario la verá cuando le corresponda en la cola de camiones; primero debe terminar sus tareas anteriores.</p>}
        {result && <>
            <div role="status" className={`rounded-2xl border-2 p-5 ${result.fits_estimate ? 'border-emerald-400 bg-emerald-50' : 'border-red-400 bg-red-50'}`}>
                <p className="text-sm font-semibold uppercase tracking-wide">Resultado del camión</p><b className="mt-1 block text-4xl">{result.total_pallets} pallets físicos finales</b>
                <p className="mt-2">{result.full_count} completos + {result.mixed_count} armados con picking = <b>{result.total_pallets}</b>.</p>
                <p>Capacidad: <b>{result.capacity}</b>. {result.excess_positions ? `Faltan ${result.excess_positions} posiciones.` : `Quedan ${result.free_positions} posiciones libres.`}</p>
                {loadPlanTotal !== result.total_pallets && <p className="mt-2 font-bold text-red-700">Inconsistencia interna: la suma por reparto da {loadPlanTotal}. No apruebes este cálculo.</p>}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">{result.load_plans?.map(p => <div className="rounded-xl border bg-white p-3" key={p.load_id}><b>Reparto {p.reparto} · {p.total_pallets} pallets estimados</b><p>{p.assembly_mode === 'compact' ? 'Supermercado / autoelevador · armado compacto' : 'Reparto normal'}</p><p>{p.full_count} completos + {p.mixed_count} de picking</p><p>Pallets exclusivos: {p.pallet_ids.join(', ') || 'Sin pallets'}</p></div>)}</div>
            <p className="rounded-xl bg-white p-3">{result.automatic_mix ? `Sin combinar canchas normales: ${result.separate_pallets} pallets. Superan la capacidad de ${result.capacity}; combinando canchas dentro de cada reparto: ${result.total_pallets} pallets.` : 'Los supermercados combinan canchas dentro de su propio reparto. En los repartos normales, las canchas se mantienen separadas salvo que elijas combinarlas.'}</p>
            {!!result.missing_caliber_rules?.length && <p role="alert" className="rounded-xl bg-amber-100 p-3"><b>Criterios físicos pendientes:</b> {result.missing_caliber_rules.join(', ')}. Esos productos no se combinan automáticamente. <Link className="underline" to="/reglas-pallets">Revisar criterios</Link>.</p>}
            {!locked && !approved && <p role="status" className="rounded-xl bg-amber-100 p-3">{!capacityMatches ? (configuredCapacity === null ? 'Para aprobar: ingresá la capacidad real y pulsá «Guardar capacidad y calcular armado».' : `Simulaste con ${result.capacity} pallets, pero el camión tiene ${configuredCapacity} registrados. Corregí la capacidad y volvé a simular.`) : !result.fits_estimate ? 'No se puede aprobar: el armado supera la capacidad del camión. Revisá la selección y el armado de sus repartos.' : !reviewed ? 'Para habilitar la aprobación, confirmá abajo la revisión de altura, estabilidad y compatibilidad.' : 'La propuesta está lista para aprobar y enviar al equipo.'}</p>}
            <label className="flex min-h-12 items-center gap-3"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />Revisé altura, estabilidad y compatibilidad del armado propuesto.</label>
            <button className={button} disabled={busy || locked || approved || !reviewed || !result.fits_estimate || !capacityMatches} onClick={async () => { setBusy(true); setError(''); try { await api.post(`/load-control/trucks/${truck.id}/planning/approve`, { ...result, physical_review: reviewed }); setApproved(true) } catch(e) { setError(e.response?.data?.error || 'No se pudo aprobar.') } finally { setBusy(false) } }}>Aprobar y enviar al equipo</button>
            <p className="rounded-xl bg-amber-100 p-3 text-sm">{result.warning}</p>
            <details className="rounded-xl border bg-white p-4"><summary className="cursor-pointer font-semibold">Ver detalle de productos y armado</summary><div className="mt-4 space-y-3"><h3 className="font-semibold">Trabajo de pallets completos</h3>
            {!result.full_pallets.length && <p>Sin pallets completos.</p>}
            {result.full_pallets.map((p, i) => <p key={i}>Reparto {p.reparto} · Cancha {p.court} · {p.sku} {p.descripcion}: <b>{p.pallets} pallets ({p.bultos} bultos)</b></p>)}
            <h3 className="font-semibold">Picking restante, en orden de la carga</h3>
            {result.picking_tasks.map((p, i) => <p key={i}>{p.order}. Reparto {p.reparto} · Cancha {p.court} · {p.sku} {p.descripcion}: <b>{p.bultos} bultos + {p.unidades} unidades</b></p>)}
            <h3 className="font-semibold">Contenido propuesto de pallets mixtos</h3>
            {result.mixed_pallets.map(p => <div key={p.id} className="rounded-xl border bg-white p-3"><b>{p.id} · Reparto {p.reparto || p.items[0]?.reparto} · Canchas {p.courts.join(', ')} · Ocupación estimada {(p.occupancy * 100).toFixed(1)}%</b>
                {(p.layers || p.items).map((item, i) => <p key={i}><b>{item.placement === 'base' || i === 0 ? 'Base' : `Arriba ${i}`}:</b> Cancha {item.court} · {item.calibre || 'Sin calibre'} · {item.sku} {item.descripcion}: {item.bultos} bultos + {item.unidades} unidades</p>)}
            </div>)}</div></details>
        </>}
    </section>
}
