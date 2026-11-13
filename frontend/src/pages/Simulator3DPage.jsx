import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axiosClient'
import TruckScene3D from '../components/TruckScene3D'
import { caliberKey, caliberLabel, expandPallets, stackPallet } from '../utils/palletGeometry'

// Solo lectura: esta pantalla consulta y simula, nunca guarda ni aprueba un plan.
const PALETTE = ['#3B82F6', '#F59E0B', '#10B981', '#8B5CF6', '#EC4899', '#22D3EE', '#A3E635', '#A16207', '#94A3B8', '#6366F1']
const today = () => { const now = new Date(); return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10) }
const decimal = (value, digits = 1) => Number(value).toLocaleString('es-AR', { maximumFractionDigits: digits })
const input = 'rounded-lg border px-3 py-2 text-sm'
const quiet = 'btn-quiet rounded-lg px-3 text-[13px] font-medium disabled:opacity-40'

export default function Simulator3DPage() {
    const [date, setDate] = useState(today()), [trucks, setTrucks] = useState([]), [truckId, setTruckId] = useState('')
    const [plan, setPlan] = useState(null), [source, setSource] = useState(''), [config, setConfig] = useState({}), [dimensions, setDimensions] = useState(new Map())
    const [rowsAcross, setRowsAcross] = useState(2), [long, setLong] = useState(120), [short, setShort] = useState(100)
    const [selected, setSelected] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [resetSignal, setResetSignal] = useState(0)

    useEffect(() => {
        let active = true
        setError(''); setTrucks([]); setTruckId(''); setPlan(null); setSelected(null)
        api.get('/load-control/trucks', { params: { date } })
            .then(response => { if (!active) return; const rows = (response.data || []).filter(truck => truck.loads?.length); setTrucks(rows); setTruckId(rows[0] ? String(rows[0].id) : '') })
            .catch(e => { if (active) setError(e.response?.data?.error || 'No se pudieron consultar los camiones.') })
        return () => { active = false }
    }, [date])

    const truck = trucks.find(item => String(item.id) === truckId)
    useEffect(() => {
        if (!truck) return
        let active = true
        async function load() {
            setBusy(true); setError(''); setPlan(null); setSelected(null)
            try {
                const [settings, saved, rules] = await Promise.all([
                    api.get('/load-control/settings'), api.get(`/load-control/trucks/${truck.id}/planning`),
                    api.get('/pallet-rules').catch(() => null),
                ])
                if (!active) return
                const depot = settings.data.depots.find(item => item.branch === truck.branch) || {}
                const entry = settings.data.trucks.find(item => item.branch === truck.branch && item.truck === truck.truck) || {}
                setConfig({ ...depot, ...entry })
                const sizes = new Map()
                for (const rule of rules?.data?.stacking_rules || []) {
                    const length = Number(rule.length_cm), width = Number(rule.width_cm)
                    if (length > 0 && width > 0) sizes.set(caliberKey({ business_unit: rule.business_unit, calibre: rule.caliber }), { length, width })
                }
                setDimensions(sizes)
                if (saved.data.plan) { setPlan(saved.data.plan); setSource('approved'); return }
                const capacity = saved.data.configured_capacity ?? entry.capacity
                if (!capacity) throw new Error('Este camión no tiene capacidad registrada. Cargala en «Camiones y capacidad» para poder simular.')
                const response = await api.post(`/load-control/trucks/${truck.id}/planning/simulate`, { capacity, mix_courts: Boolean(depot.mix_courts_default), compact_load_ids: [], merge_allowed_load_ids: [] }, { timeout: 20000 })
                if (active) { setPlan(response.data); setSource('simulated') }
            } catch (e) { if (active) setError(e.response?.data?.error || e.message || 'No se pudo calcular la simulación.') }
            finally { if (active) setBusy(false) }
        }
        load()
        return () => { active = false }
    }, [truck?.id])

    const sizeX = Math.max(40, Number(short) || 100), sizeZ = Math.max(40, Number(long) || 120)
    const pallets = useMemo(() => plan ? expandPallets(plan).map(pallet => ({ ...pallet, stack: stackPallet(pallet, config, dimensions, sizeX, sizeZ) })) : [], [plan, config, dimensions, sizeX, sizeZ])
    const legend = useMemo(() => {
        const groups = new Map()
        pallets.forEach(pallet => pallet.items.forEach(item => {
            const key = caliberKey(item), group = groups.get(key) || { key, label: caliberLabel(item), unit: item.business_unit || 'Unidad sin informar', bultos: 0 }
            group.bultos += Number(item.bultos || 0); groups.set(key, group)
        }))
        return [...groups.values()].map((group, index) => ({ ...group, color: PALETTE[index % PALETTE.length] }))
    }, [pallets])
    const colors = useMemo(() => new Map(legend.map(group => [group.key, group.color])), [legend])
    const current = pallets.find(pallet => pallet.id === selected)
    const capacity = Number(plan?.capacity) || 0
    const overHeight = pallets.filter(pallet => pallet.heightExceeded).length, overWeight = pallets.filter(pallet => pallet.weightExceeded).length
    const noGeometry = pallets.filter(pallet => pallet.stack.missing.length).length
    const schematic = pallets.some(pallet => !pallet.stack.realFootprint), estimatedHeights = pallets.some(pallet => !pallet.stack.exactHeights)
    const summary = plan ? [
        ['Pallets', pallets.length], ['Capacidad', capacity || '—'],
        [plan.excess_positions ? 'Posiciones que faltan' : 'Posiciones libres', plan.excess_positions || plan.free_positions || 0, plan.excess_positions ? 'bad' : ''],
        ['Superan altura', overHeight, overHeight ? 'bad' : ''], ['Superan peso', overWeight, overWeight ? 'bad' : ''],
        ['Peso del camión', `${decimal(plan.weight_complete ? plan.truck_weight_kg : plan.truck_weight_known_kg, 0)} kg`, plan.truck_weight_exceeded ? 'bad' : '', plan.weight_complete ? (plan.truck_weight_limit_kg != null ? `límite ${decimal(plan.truck_weight_limit_kg, 0)} kg` : '') : 'incompleto'],
    ] : []
    const status = pallet => pallet.heightExceeded ? 'Supera altura' : pallet.weightExceeded ? 'Supera peso' : pallet.stack.missing.length ? 'Sin geometría' : ''

    return <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
            <div>
                <h1 className="text-[26px] font-semibold leading-8">Simulador 3D de carga</h1>
                <p className="text-muted mt-2 max-w-3xl text-[15px] leading-[22px]">Mirá cómo quedan armados los pallets de un camión según el plan calculado. Es una vista de consulta: no guarda ni modifica la planificación.</p>
            </div>
            <Link to="/supervision/cargas" className={`${quiet} inline-flex min-h-10 items-center`}>Ir a planificar cargas</Link>
        </header>

        <section className="tile is-static flex flex-wrap items-end gap-x-5 gap-y-3 rounded-2xl p-5" aria-label="Opciones de la simulación">
            <label className="text-sm font-medium">Fecha de reparto<input type="date" className={`${input} mt-1.5 block`} value={date} onChange={event => setDate(event.target.value)} /></label>
            <label className="min-w-0 text-sm font-medium">Camión<select className={`${input} mt-1.5 block min-w-56`} value={truckId} onChange={event => setTruckId(event.target.value)} disabled={!trucks.length}>
                {!trucks.length && <option value="">Sin camiones con cargas</option>}
                {trucks.map(item => <option key={item.id} value={item.id}>{item.truck} · {item.branch} · {item.loads.length} {item.loads.length === 1 ? 'carga' : 'cargas'}</option>)}
            </select></label>
            <div className="text-sm font-medium"><span className="block">Pallets a lo ancho</span><div className="segmented mt-1.5" role="group" aria-label="Pallets a lo ancho del camión">{[1, 2, 3].map(value => <button type="button" key={value} aria-pressed={rowsAcross === value} onClick={() => setRowsAcross(value)}>{value}</button>)}</div></div>
            <fieldset className="text-sm font-medium"><legend>Tarima (cm)</legend><div className="mt-1.5 flex items-center gap-2">
                <input type="number" min="40" max="200" aria-label="Largo de la tarima en centímetros" className={`${input} w-20`} value={long} onChange={event => setLong(event.target.value)} /><span className="text-muted">×</span>
                <input type="number" min="40" max="200" aria-label="Ancho de la tarima en centímetros" className={`${input} w-20`} value={short} onChange={event => setShort(event.target.value)} />
            </div></fieldset>
        </section>

        {error && <p role="alert" className="note note--danger">{error}</p>}
        {busy && <p role="status" className="text-muted text-sm">Calculando la simulación…</p>}
        {!busy && !error && !trucks.length && <p className="note">No hay camiones con cargas incorporadas para esta fecha.</p>}

        {plan && <>
            <div className="flex flex-wrap items-center gap-2 text-[13px]">
                <span className={`badge ${source === 'approved' ? 'badge--success' : 'badge--info'}`}>{source === 'approved' ? 'Plan aprobado' : 'Simulación con la configuración guardada'}</span>
                <span className="text-muted">Camión {plan.truck} · {plan.branch} · {plan.date}</span>
            </div>
            <section className="stat-strip grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6" aria-label="Resumen del camión">
                {summary.map(([label, value, tone, hint]) => <div key={label} className="px-4 py-4">
                    <p className="text-muted text-[13px]">{label}</p>
                    <p className={`mt-1 text-[24px] font-medium leading-8 tabular-nums ${tone === 'bad' ? 'text-red-700' : ''}`}>{value}</p>
                    {hint && <p className="text-muted text-xs">{hint}</p>}
                </div>)}
            </section>

            <section className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
                <div className="tile is-static overflow-hidden rounded-2xl">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2.5">
                        <p className="text-muted text-[13px]">{current ? `Pallet ${current.id} aislado. Arrastrá para girar.` : 'Arrastrá para girar, rueda para acercar, clic en un pallet para aislarlo.'}</p>
                        <div className="flex shrink-0 gap-2">
                            {current && <button type="button" className={quiet} onClick={() => setSelected(null)}>Ver todo el camión</button>}
                            <button type="button" className={quiet} onClick={() => { setSelected(null); setResetSignal(value => value + 1) }}>Reencuadrar</button>
                        </div>
                    </div>
                    <div className="h-[560px]"><TruckScene3D pallets={pallets} capacity={capacity} rowsAcross={rowsAcross} sizeX={sizeX} sizeZ={sizeZ} colors={colors} selectedId={selected} onSelect={setSelected} resetSignal={resetSignal} /></div>
                    <div className="flex flex-wrap gap-x-5 gap-y-2 border-t px-4 py-3" aria-label="Referencias de color por calibre">
                        {legend.map(group => <span key={group.key} className="inline-flex items-center gap-2 text-[13px]"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: group.color }} /><span className="font-medium">{group.label}</span><span className="text-muted">{group.unit} · {decimal(group.bultos, 0)} bultos</span></span>)}
                    </div>
                </div>

                <aside className="tile is-static thin-scroll rounded-2xl lg:max-h-[676px] lg:overflow-y-auto" aria-label="Detalle de pallets">
                    {current ? <div>
                        <div className="panel-head sticky top-0 flex items-start justify-between gap-3 border-b px-4 py-3">
                            <div><h2 className="text-base font-semibold">Pallet {current.id}</h2><p className="text-muted text-[13px]">Carga {current.reparto} · Cancha {current.court} · {current.kind === 'full' ? 'completo' : 'picking'}</p></div>
                            <button type="button" className={quiet} onClick={() => setSelected(null)}>Cerrar</button>
                        </div>
                        <dl className="rule-facts mx-4 mt-4 grid grid-cols-3 text-[13px]">
                            <div><dt className="text-muted text-xs">Ocupación</dt><dd className="font-medium tabular-nums">{decimal(current.occupancy * 100)} %</dd></div>
                            <div><dt className="text-muted text-xs">Altura</dt><dd className={`font-medium tabular-nums ${current.heightExceeded ? 'text-red-700' : ''}`}>{current.heightCm != null ? `${decimal(current.heightCm)} cm` : 'Sin dato'}{current.heightLimitCm != null && <span className="text-muted block text-xs font-normal">de {decimal(current.heightLimitCm)} cm</span>}</dd></div>
                            <div><dt className="text-muted text-xs">Peso</dt><dd className={`font-medium tabular-nums ${current.weightExceeded ? 'text-red-700' : ''}`}>{current.weightKg != null ? `${decimal(current.weightKg)} kg` : 'Sin dato'}{current.weightLimitKg != null && <span className="text-muted block text-xs font-normal">de {decimal(current.weightLimitKg)} kg</span>}</dd></div>
                        </dl>
                        {!!current.stack.missing.length && <p className="note note--warning mx-4 mt-3">Sin bultos por piso o pisos por pallet: {current.stack.missing.join(', ')}. Esos artículos no se dibujan.</p>}
                        <table className="pallet-mix mx-4 mb-4 mt-4 w-[calc(100%-2rem)] text-[13px]" aria-label="Pisos del pallet, de arriba hacia abajo">
                            <thead><tr><th scope="col" className="text-left">Piso</th><th scope="col" className="text-left">Calibre</th><th scope="col">Bultos</th></tr></thead>
                            <tbody>{[...current.stack.floors].reverse().map(floor => <tr key={floor.number}>
                                <th scope="row" className="text-left font-medium">{floor.number}<span className="text-muted block text-xs font-normal">{floor.used} de {floor.perFloor}</span></th>
                                <td className="text-left">{floor.parts.map((part, index) => <span key={index} className="flex items-center gap-1.5"><span className="h-2 w-2 shrink-0 rounded-sm" style={{ background: colors.get(caliberKey(part.item)) }} />{caliberLabel(part.item)}<span className="text-muted">· {part.item.sku}</span></span>)}</td>
                                <td>{floor.parts.map((part, index) => <span key={index} className="block">{part.count}</span>)}</td>
                            </tr>)}</tbody>
                        </table>
                    </div> : <div>
                        <div className="border-b px-4 py-3"><h2 className="text-[15px] font-semibold">Pallets del camión</h2><p className="text-muted text-[13px]">En el orden de carga, desde la cabina.</p></div>
                        <ul className="check-list px-2 py-1">
                            {pallets.map((pallet, index) => <li key={pallet.id}><button type="button" className="nav-item flex w-full items-center justify-between gap-3 rounded-lg px-2 py-2 text-left text-[13px]" onClick={() => setSelected(pallet.id)}>
                                <span className="min-w-0"><span className="block font-medium">{index + 1}. Pallet {pallet.id}</span><span className="text-muted block text-xs">Carga {pallet.reparto} · {pallet.kind === 'full' ? 'completo' : 'picking'}{capacity && index >= capacity ? ' · sin lugar' : ''}</span></span>
                                <span className="shrink-0 text-right tabular-nums">{pallet.heightCm != null ? `${decimal(pallet.heightCm, 0)} cm` : '—'}<span className="text-muted block text-xs">{pallet.weightKg != null ? `${decimal(pallet.weightKg, 0)} kg` : '—'}</span>{status(pallet) && <span className="block text-xs text-red-700">{status(pallet)}</span>}</span>
                            </button></li>)}
                        </ul>
                    </div>}
                </aside>
            </section>

            <div className="text-muted space-y-1 text-[13px]">
                <p>Las alturas y los pesos son los del cálculo de planificación. La tarima de {sizeZ} × {sizeX} cm y la cantidad de pallets a lo ancho son supuestos de esta vista: ajustalos arriba si tu camión es distinto.</p>
                {schematic && <p>La ubicación de los bultos dentro de cada piso es esquemática cuando el calibre no tiene largo y ancho cargados, o cuando esas medidas no entran en la grilla del piso.</p>}
                {estimatedHeights && <p>Falta la altura de tarima o la de referencia del depósito: la altura dibujada es aproximada.</p>}
                {!!noGeometry && <p>{noGeometry} {noGeometry === 1 ? 'pallet tiene' : 'pallets tienen'} artículos sin bultos por piso o pisos por pallet, que no se pueden dibujar.</p>}
            </div>
        </>}
    </div>
}
