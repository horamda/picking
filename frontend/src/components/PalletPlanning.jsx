import { useEffect, useState } from 'react'
import api from '../api/axiosClient'
import { Link } from 'react-router-dom'
import { getStoredUser } from '../utils/auth'
import PalletCardEditor from './PalletCardEditor'

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
    const [mergeAllowed, setMergeAllowed] = useState([])
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
                setMergeAllowed(saved.data.plan?.merge_allowed_load_ids || saved.data.plan?.compact_load_ids || [])
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
    const phase = approved || locked ? 3 : result ? 2 : 1
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
            const response = await api.post(`/load-control/trucks/${truck.id}/planning/simulate`, { capacity: Number(capacity), mix_courts: mix, compact_load_ids: compact, merge_allowed_load_ids: mergeAllowed }, { timeout: 15000 })
            setResult(response.data)
        } catch (e) { setError(e.response?.data?.error || e.message || 'No se pudo calcular. Reintentá.') }
        finally { setBusy(false) }
    }
    function updatePallets(pallets) {
        setReviewed(false)
        setResult(current => {
            const loadPlans = current.load_plans.map(load => {
                const own = pallets.filter(pallet => pallet.load_id === load.load_id)
                return { ...load, mixed_count: own.length, total_pallets: load.full_count + own.length,
                    pallet_ids: [...current.full_pallets.filter(pallet => pallet.load_id === load.load_id).map(pallet => pallet.id), ...own.map(pallet => pallet.id)] }
            })
            const total = current.full_count + pallets.length
            return { ...current, mixed_pallets: pallets, mixed_count: pallets.length, total_pallets: total,
                free_positions: Math.max(0, current.capacity - total), excess_positions: Math.max(0, total - current.capacity),
                fits_estimate: total <= current.capacity, load_plans: loadPlans, manual_edition: true }
        })
    }
    return <section className="space-y-5 rounded-2xl border bg-white p-4 sm:p-6" aria-label="Simulación de pallets">
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-4"><div><button className="mb-3 text-sm font-semibold text-brand-600 hover:underline" onClick={onClose}>← Volver a selección de cargas</button><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Camión {truck.truck} · {truck.branch}</p><h2 className="mt-1 text-2xl font-bold">Planificación y aprobación de pallets</h2><p className="mt-1 text-sm text-slate-600">Configurá el armado, revisá la simulación y recién después enviala al equipo.</p></div><button className={button} onClick={onClose}>Salir</button></header>
        <ol className="grid gap-2 sm:grid-cols-3" aria-label="Etapas de planificación">{[['1', 'Configurar'], ['2', 'Revisar pallets'], ['3', 'Aprobar y enviar']].map(([number, label], index) => { const step=index+1, active=phase===step, complete=phase>step; return <li key={number} className={`flex items-center gap-3 rounded-xl border-2 px-3 py-2 ${active ? 'border-brand-500 bg-brand-50' : complete ? 'border-emerald-300 bg-emerald-50' : 'border-slate-200 bg-slate-50'}`}><span className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold ${active ? 'bg-brand-500 text-white' : complete ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'}`}>{complete ? '✓' : number}</span><span className="font-semibold">{label}</span></li>})}</ol>
        <p className="rounded-xl border border-blue-200 bg-blue-50 p-3 font-semibold">Regla fija: cada reparto se arma separado. Ningún pallet puede contener mercadería de otro reparto ni de otro camión.</p>
        {locked && result?.separation_policy !== 'reparto_v1' && <p role="alert" className="rounded-xl bg-amber-100 p-3">Plan anterior ya iniciado: revisar físicamente la separación entre repartos. Sus instrucciones no se reemplazan durante el armado.</p>}
        {locked && <p className="rounded-xl bg-amber-100 p-3">El trabajo ya comenzó. Se conserva el plan aprobado y no se pueden cambiar sus cantidades.</p>}
        <details open={!result} className="rounded-2xl border border-slate-200 bg-slate-50">
            <summary className="flex min-h-14 cursor-pointer items-center justify-between gap-3 px-4 py-3 font-semibold"><span>1. Configuración del armado</span>{result && <span className="text-sm font-normal text-slate-500">{loads.length} repartos · capacidad {capacity} pallets</span>}</summary>
            <div className="space-y-4 border-t border-slate-200 p-4">
        <form className="flex flex-wrap items-end gap-4" onSubmit={simulate}>
            <fieldset disabled={busy || locked} className="min-w-0 w-full space-y-3"><legend className="mb-2 font-semibold">Tipo de armado de cada reparto</legend>
                {loads.map(l => <div key={l.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-white p-3"><b>Reparto {l.reparto}</b><div className="flex flex-wrap items-center gap-4"><select aria-label={`Armado del reparto ${l.reparto}`} className="min-h-12 min-w-0 rounded-xl border p-2 text-sm" value={compact.includes(l.id) ? 'compact' : 'normal'} onChange={e => { const enabled = e.target.value === 'compact'; setCompact(current => enabled ? [...current.filter(n => n !== l.id), l.id] : current.filter(n => n !== l.id)); setMergeAllowed(current => enabled ? [...current.filter(n => n !== l.id), l.id] : current.filter(n => n !== l.id)); setResult(null); setReviewed(false); setApproved(false) }}><option value="normal">Normal · por canchas</option><option value="compact">Supermercado / autoelevador · reducir pallets</option></select><label className="flex min-h-12 items-center gap-2"><input type="checkbox" checked={mergeAllowed.includes(l.id)} onChange={e => { setMergeAllowed(current => e.target.checked ? [...current.filter(n => n !== l.id), l.id] : current.filter(n => n !== l.id)); setResult(null); setReviewed(false) }} />Permitir unir pallets</label></div></div>)}
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
            </div>
        </details>
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
            <PalletCardEditor pallets={result.mixed_pallets} fullPallets={result.full_pallets} mergeAllowedLoadIds={result.merge_allowed_load_ids || mergeAllowed} disabled={locked || approved || busy} onChange={updatePallets} />
            {!locked && !approved && <p role="status" className="rounded-xl bg-amber-100 p-3">{!capacityMatches ? (configuredCapacity === null ? 'Para aprobar: ingresá la capacidad real y pulsá «Guardar capacidad y calcular armado».' : `Simulaste con ${result.capacity} pallets, pero el camión tiene ${configuredCapacity} registrados. Corregí la capacidad y volvé a simular.`) : !result.fits_estimate ? 'No se puede aprobar: el armado supera la capacidad del camión. Revisá la selección y el armado de sus repartos.' : !reviewed ? 'Para habilitar la aprobación, confirmá abajo la revisión de altura, estabilidad y compatibilidad.' : 'La propuesta está lista para aprobar y enviar al equipo.'}</p>}
            <label className="flex min-h-12 items-center gap-3"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />Revisé altura, estabilidad y compatibilidad del armado propuesto.</label>
            <button className={button} disabled={busy || locked || approved || !reviewed || !result.fits_estimate || !capacityMatches} onClick={async () => { setBusy(true); setError(''); try { await api.post(`/load-control/trucks/${truck.id}/planning/approve`, { ...result, physical_review: reviewed }); setApproved(true) } catch(e) { setError(e.response?.data?.error || 'No se pudo aprobar.') } finally { setBusy(false) } }}>Aprobar y enviar al equipo</button>
            <p className="rounded-xl bg-amber-100 p-3 text-sm">{result.warning}</p>
            <details className="rounded-xl border bg-white p-4"><summary className="cursor-pointer font-semibold">Ver detalle de productos y armado</summary><div className="mt-4 space-y-3"><h3 className="font-semibold">Trabajo de pallets completos</h3>
            {!result.full_pallets.length && <p>Sin pallets completos.</p>}
            {result.full_pallets.map((p, i) => <p key={i}>Reparto {p.reparto} · Cancha {p.court} · {p.sku} {p.descripcion}: <b>{p.pallets} pallets ({p.bultos} bultos)</b></p>)}
            <h3 className="font-semibold">Picking restante, en orden de la carga</h3>
            {result.picking_tasks.map((p, i) => <p key={i}>{p.order}. Reparto {p.reparto} · Cancha {p.court} · {p.sku} {p.descripcion}: <b>{p.bultos} bultos + {p.unidades} unidades</b></p>)}
            </div></details>
        </>}
    </section>
}
