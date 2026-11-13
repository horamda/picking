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
    const [physicalConfig, setPhysicalConfig] = useState({})
    useEffect(() => {
        let active = true
        async function load() {
            setBusy(true)
            try {
                const [configuration, saved] = await Promise.all([api.get('/load-control/settings'), api.get(`/load-control/trucks/${truck.id}/planning`)])
                if (!active) return
                const entry = configuration.data.trucks.find(t => t.branch === truck.branch && t.truck === truck.truck)
                const depotEntry = configuration.data.depots.find(d => d.branch === truck.branch) || {}
                setPhysicalConfig({ ...depotEntry, ...entry })
                setConfiguredCapacity(saved.data.configured_capacity ?? entry?.capacity ?? null)
                setDefaultMix(depotEntry.mix_courts_default || false)
                setLocked(saved.data.locked)
                setLoads(saved.data.loads || [])
                setCompact(saved.data.plan?.compact_load_ids || [])
                setMergeAllowed(saved.data.plan?.merge_allowed_load_ids || saved.data.plan?.compact_load_ids || [])
                if (saved.data.locked && saved.data.plan) {
                    setResult(saved.data.plan); setApproved(true); setCapacity(String(saved.data.plan.capacity)); setMix(saved.data.plan.mix_courts)
                } else {
                    if(saved.data.configured_capacity ?? entry?.capacity) setCapacity(String(saved.data.configured_capacity ?? entry.capacity))
                    setMix(depotEntry.mix_courts_default || false)
                    if(!saved.data.locked) await api.post(`/load-control/trucks/${truck.id}/planning/start`)
                }
            } catch (e) { if(active) setError(e.response?.data?.error || 'No se pudo cargar la planificación.') }
            finally { if(active) setBusy(false) }
        }
        load(); return () => { active = false }
    }, [truck.id])
    const button = 'btn-quiet rounded-lg px-4 text-sm font-medium disabled:opacity-40'
    const primary = 'btn-primary rounded-lg px-5 text-sm font-medium disabled:opacity-40'
    const input = 'rounded-lg border px-3 py-2 text-sm'
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
                await api.put('/load-control/settings', { ...physicalConfig, branch: truck.branch, truck: truck.truck, capacity: value, mix_courts_default: defaultMix }, { timeout: 15000 })
                setConfiguredCapacity(value)
            }
            const response = await api.post(`/load-control/trucks/${truck.id}/planning/simulate`, { capacity: Number(capacity), mix_courts: mix, compact_load_ids: compact, merge_allowed_load_ids: mergeAllowed }, { timeout: 15000 })
            setResult(response.data)
        } catch (e) { setError(e.response?.data?.error || e.message || 'No se pudo calcular. Reintentá.') }
        finally { setBusy(false) }
    }
    async function updatePallets(pallets) {
        setReviewed(false); setBusy(true); setError('')
        try {
            const response = await api.post(`/load-control/trucks/${truck.id}/planning/simulate`, {
                capacity: Number(capacity), mix_courts: mix, compact_load_ids: compact,
                merge_allowed_load_ids: mergeAllowed, manual_edition: true, mixed_pallets: pallets,
            }, { timeout: 15000 })
            setResult(response.data)
            return response.data
        } catch (e) {
            const detail = e.response?.data?.error || e.message || 'No se pudo validar el movimiento.'
            setError(detail)
            throw new Error(detail)
        } finally { setBusy(false) }
    }
    const steps = ['Configurar', 'Revisar pallets', 'Aprobar y enviar']
    const resetReview = () => { setResult(null); setReviewed(false); setApproved(false) }
    const toggleId = (setter, id, enabled) => setter(current => enabled ? [...current.filter(n => n !== id), id] : current.filter(n => n !== id))
    async function approve() {
        setBusy(true); setError('')
        try { await api.post(`/load-control/trucks/${truck.id}/planning/approve`, { ...result, physical_review: reviewed }); setApproved(true) }
        catch (e) { setError(e.response?.data?.error || 'No se pudo aprobar.') }
        finally { setBusy(false) }
    }
    const approvalHint = !result ? '' : !capacityMatches ? (configuredCapacity === null ? 'Para aprobar: ingresá la capacidad real y pulsá «Guardar capacidad y calcular armado».' : `Simulaste con ${result.capacity} pallets, pero el camión tiene ${configuredCapacity} registrados. Corregí la capacidad y volvé a simular.`) : !result.fits_estimate ? 'No se puede aprobar: el armado supera un límite configurado de posiciones, altura o peso.' : !reviewed ? 'Para habilitar la aprobación, confirmá la revisión de estabilidad y advertencias pendientes.' : 'La propuesta está lista para aprobar y enviar al equipo.'
    const summary = result ? [
        ['Pallets finales', result.total_pallets],
        ['Completos', result.full_count],
        ['Con picking', result.mixed_count],
        ['Capacidad', result.capacity],
        [result.excess_positions ? 'Posiciones que faltan' : 'Posiciones libres', result.excess_positions || result.free_positions, result.excess_positions ? 'bad' : ''],
        ['Peso del camión', result.weight_complete ? `${result.truck_weight_kg} kg` : `${result.truck_weight_known_kg} kg`, result.truck_weight_exceeded ? 'bad' : '', result.weight_complete ? (result.truck_weight_limit_kg != null ? `límite ${result.truck_weight_limit_kg} kg` : '') : 'incompleto'],
    ] : []
    const optimizationLabels = { mezcla_por_cancha: 'mezcla priorizando canchas', mezcla_mejor_ajuste: 'mezcla por mejor ocupación', pisos_por_cancha: 'pisos completos priorizando canchas', pisos_mejor_ajuste: 'pisos completos por mejor ocupación' }

    return <section className="planning space-y-6" aria-label="Simulación de pallets">
        <header className="flex flex-wrap items-end justify-between gap-4">
            <div>
                <button type="button" className="planning-back text-[13px] font-medium" onClick={onClose}>← Volver a selección de cargas</button>
                <h2 className="mt-2 text-[26px] font-semibold leading-8">Planificación y aprobación de pallets</h2>
                <p className="text-muted mt-1 text-[15px]">Camión {truck.truck} · <span className="capitalize">{String(truck.branch || '').toLowerCase()}</span>. Configurá el armado, revisá la simulación y recién después enviala al equipo.</p>
            </div>
            <button type="button" className={button} onClick={onClose}>Salir</button>
        </header>

        <ol className="stepper" aria-label="Etapas de planificación">
            {steps.map((label, index) => { const step = index + 1; return <li key={label} className={phase === step ? 'is-active' : phase > step ? 'is-done' : ''} aria-current={phase === step ? 'step' : undefined}>
                <span className="stepper-mark">{phase > step ? <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg> : step}</span>
                <span>{label}</span>
            </li> })}
        </ol>

        <p className="note">Regla fija: cada reparto se arma separado. Ningún pallet puede contener mercadería de otro reparto ni de otro camión.</p>
        {locked && result?.separation_policy !== 'reparto_v1' && <p role="alert" className="note note--warning">Plan anterior ya iniciado: revisar físicamente la separación entre repartos. Sus instrucciones no se reemplazan durante el armado.</p>}
        {locked && <p className="note note--warning">El trabajo ya comenzó. Se conserva el plan aprobado y no se pueden cambiar sus cantidades.</p>}

        <details open={!result} className="tile rounded-2xl">
            <summary className="flex min-h-12 cursor-pointer items-center justify-between gap-3 px-5 text-[15px] font-semibold"><span>Configuración del armado</span>{result && <span className="text-muted text-[13px] font-normal">{loads.length} repartos · capacidad {capacity} pallets</span>}</summary>
            <div className="space-y-5 border-t px-5 py-5">
                <form className="space-y-5" onSubmit={simulate}>
                    <fieldset disabled={busy || locked} className="min-w-0">
                        <legend className="text-sm font-medium">Tipo de armado de cada reparto</legend>
                        <div className="check-list mt-2">
                            {loads.map(l => <div key={l.id} className="flex flex-wrap items-center justify-between gap-3 py-2.5">
                                <span className="text-sm font-medium">Reparto {l.reparto}</span>
                                <div className="flex flex-wrap items-center gap-4">
                                    <select aria-label={`Armado del reparto ${l.reparto}`} className={`${input} min-w-0`} value={compact.includes(l.id) ? 'compact' : 'normal'} onChange={e => { const enabled = e.target.value === 'compact'; toggleId(setCompact, l.id, enabled); toggleId(setMergeAllowed, l.id, enabled); resetReview() }}>
                                        <option value="normal">Normal · por canchas</option>
                                        <option value="compact">Supermercado / autoelevador · reducir pallets</option>
                                    </select>
                                    <label className="flex min-h-10 cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={mergeAllowed.includes(l.id)} onChange={e => { toggleId(setMergeAllowed, l.id, e.target.checked); setResult(null); setReviewed(false) }} />Permitir unir pallets</label>
                                </div>
                            </div>)}
                        </div>
                        <p className="text-muted mt-2 text-[13px]">Supermercado: combina canchas y productos compatibles dentro de ese reparto para reducir la cantidad estimada de pallets.</p>
                    </fieldset>
                    <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
                        <label className="text-sm font-medium">Capacidad del camión en pallets físicos<input className={`${input} mt-1.5 block w-40`} type="number" min="1" step="1" required value={capacity} disabled={busy || locked} onChange={e => { setCapacity(e.target.value); setResult(null) }} /></label>
                        <label className="flex min-h-10 cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={mix} disabled={busy || locked} onChange={e => { setMix(e.target.checked); setResult(null) }} />Combinar canchas dentro de cada reparto normal, aunque entren separadas</label>
                    </div>
                    <button className={primary} disabled={busy || locked}>{busy ? 'Procesando…' : admin && Number(capacity) !== configuredCapacity ? 'Guardar capacidad y calcular armado' : 'Calcular armado'}</button>
                </form>
                {!locked && <div className={`note ${configuredCapacity === null ? 'note--warning' : ''}`}>
                    <p className="font-medium">{configuredCapacity === null ? 'Ingresá la capacidad real del camión y guardala al calcular el armado.' : `Capacidad registrada: ${configuredCapacity} pallets físicos.`}</p>
                    <p className="mt-1">Depósito {truck.branch} · Camión {truck.truck}. Usá su capacidad física real; no la cantidad de pallets calculada para esta carga.</p>
                    {admin ? <p className="mt-1">El botón «Guardar capacidad y calcular armado» registra este valor en el depósito de la carga. <Link className="underline" to="/configuracion">Ver configuración</Link></p> : <p className="mt-1">Si falta la capacidad o es incorrecta, pedile al administrador que la registre en «Camiones y capacidad».</p>}
                </div>}
            </div>
        </details>

        {message && <p role="status" className="note note--success">{message}</p>}
        {error && <p role="alert" className="note note--danger">{error}</p>}
        {approved && !locked && <p role="status" className="note note--success">Carga aprobada. Cada operario la verá cuando le corresponda en la cola de camiones; primero debe terminar sus tareas anteriores.</p>}

        {result && <>
            <section role="status" aria-label="Resultado del camión">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-[15px] font-semibold">Resultado del camión</h3>
                    <span className={`badge ${result.fits_estimate ? 'badge--success' : 'badge--danger'}`}>{result.fits_estimate ? 'Entra en el camión' : 'Supera un límite'}</span>
                </div>
                <div className="stat-strip grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6">
                    {summary.map(([label, value, tone, hint]) => <div key={label} className="px-4 py-4">
                        <p className="text-muted text-[13px]">{label}</p>
                        <p className={`mt-1 text-[24px] font-medium leading-8 tabular-nums ${tone === 'bad' ? 'text-red-700' : ''}`}>{value}</p>
                        {hint && <p className="text-muted text-xs">{hint}</p>}
                    </div>)}
                </div>
                {result.truck_weight_exceeded && <p className="note note--danger mt-3">Exceso de carga útil: {result.truck_weight_excess_kg} kg.</p>}
                {loadPlanTotal !== result.total_pallets && <p className="note note--danger mt-3">Inconsistencia interna: la suma por reparto da {loadPlanTotal}. No apruebes este cálculo.</p>}
            </section>

            <div className="grid gap-3 sm:grid-cols-2">
                {result.load_plans?.map(p => <div className="tile rounded-2xl p-4" key={p.load_id}>
                    <div className="flex flex-wrap items-baseline justify-between gap-2"><h3 className="text-sm font-semibold">Reparto {p.reparto}</h3><span className="text-sm tabular-nums">{p.total_pallets} {p.total_pallets === 1 ? 'pallet' : 'pallets'}</span></div>
                    <p className="text-muted mt-1 text-[13px]">{p.assembly_mode === 'compact' ? 'Supermercado / autoelevador · armado compacto' : 'Reparto normal'} · {p.full_count} completos + {p.mixed_count} de picking</p>
                    <p className="text-muted mt-1 text-[13px]">Pallets: {p.pallet_ids.join(', ') || 'sin pallets'}</p>
                </div>)}
            </div>
            <p className="text-muted text-[13px]">{result.automatic_mix ? `Sin combinar canchas normales: ${result.separate_pallets} pallets. Superan la capacidad de ${result.capacity}; combinando canchas dentro de cada reparto: ${result.total_pallets} pallets.` : 'Los supermercados combinan canchas dentro de su propio reparto. En los repartos normales, las canchas se mantienen separadas salvo que elijas combinarlas.'}</p>
            {result.automatic_mix && result.optimization_strategy && <p className="note note--success"><span className="font-medium">Optimización seleccionada:</span> {optimizationLabels[result.optimization_strategy] || result.optimization_strategy}. Se compararon {result.optimization_alternatives?.length || 1} alternativas y se ahorraron {result.saved_positions} posiciones.</p>}
            {!!result.missing_caliber_rules?.length && <p role="alert" className="note note--warning"><span className="font-medium">Criterios físicos pendientes:</span> {result.missing_caliber_rules.join(', ')}. Esos productos no se combinan automáticamente. <Link className="underline" to="/reglas-pallets">Revisar criterios</Link>.</p>}
            {!!result.missing_weights?.length && <p role="alert" className="note note--warning"><span className="font-medium">Pesos faltantes:</span> {result.missing_weights.join(', ')}. El peso total queda incompleto.</p>}
            {!!result.missing_dimensions?.length && <p role="alert" className="note note--warning"><span className="font-medium">Geometría faltante:</span> {result.missing_dimensions.join(', ')}. Revisá pisos y bultos por piso.</p>}

            <PalletCardEditor pallets={result.mixed_pallets} fullPallets={result.full_pallets} mergeAllowedLoadIds={result.merge_allowed_load_ids || mergeAllowed} disabled={locked || approved || busy} onChange={updatePallets} />

            <section className="tile space-y-3 rounded-2xl p-5">
                <h3 className="text-[15px] font-semibold">Aprobar y enviar</h3>
                {!locked && !approved && <p role="status" className="text-muted text-sm">{approvalHint}</p>}
                {result.warning && <p className="note note--warning">{result.warning}</p>}
                <label className="flex min-h-10 cursor-pointer items-center gap-3 text-sm"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />Revisé estabilidad, compatibilidad y datos físicos pendientes del armado.</label>
                <button type="button" className={primary} disabled={busy || locked || approved || !reviewed || !result.fits_estimate || !capacityMatches} onClick={approve}>Aprobar y enviar al equipo</button>
            </section>

            <details className="tile rounded-2xl px-5">
                <summary className="flex min-h-12 cursor-pointer items-center text-sm font-medium">Ver detalle de productos y armado</summary>
                <div className="space-y-2 pb-5 text-sm">
                    <h3 className="font-semibold">Trabajo de pallets completos</h3>
                    {!result.full_pallets.length && <p className="text-muted">Sin pallets completos.</p>}
                    {result.full_pallets.map((p, i) => <p key={i}>Reparto {p.reparto} · Cancha {p.court} · {p.sku} {p.descripcion}: <span className="font-medium">{p.pallets} pallets ({p.bultos} bultos)</span></p>)}
                    <h3 className="pt-3 font-semibold">Picking restante, en orden de la carga</h3>
                    {result.picking_tasks.map((p, i) => <p key={i}>{p.order}. Reparto {p.reparto} · Cancha {p.court} · {p.sku} {p.descripcion}: <span className="font-medium">{p.bultos} bultos + {p.unidades} unidades</span></p>)}
                </div>
            </details>
        </>}
    </section>
}
