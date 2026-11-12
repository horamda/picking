import { useEffect, useMemo, useState } from 'react'

const percentage = pallet => Math.round(Number(pallet.occupancy || 0) * 10000) / 100

// Agrupa los artículos del pallet por unidad de negocio y calibre, con sus bultos y la fracción de pallet que ocupan.
const palletProfiles = items => {
    const groups = new Map()
    items.forEach(item => {
        const businessUnit = String(item.business_unit || '').trim() || 'Unidad sin informar'
        const caliber = String(item.calibre || '').trim() || 'Calibre sin informar'
        const key = `${businessUnit.toLocaleUpperCase('es-AR')}|${caliber.toLocaleUpperCase('es-AR')}`
        const group = groups.get(key) || { businessUnit, caliber, bultos: 0, unidades: 0, share: 0, shareKnown: true }
        const bultos = Number(item.bultos || 0), unidades = Number(item.unidades || 0)
        const perPallet = Number(item.bultos_por_pallet || 0), perCase = Number(item.unidades_por_bulto || 0)
        group.bultos += bultos; group.unidades += unidades
        if (perPallet > 0 && (!unidades || perCase > 0)) group.share += bultos / perPallet + (unidades ? unidades / (perPallet * perCase) : 0)
        else group.shareKnown = false
        groups.set(key, group)
    })
    return [...groups.values()]
}
const decimal = (value, digits = 1) => Number(value).toLocaleString('es-AR', { maximumFractionDigits: digits })

export default function PalletCardEditor({ pallets, fullPallets = [], mergeAllowedLoadIds = [], disabled, onChange }) {
    const [selected, setSelected] = useState(null), [viewing, setViewing] = useState(null)
    const [history, setHistory] = useState([]), [notice, setNotice] = useState('')
    const loadIds = useMemo(() => [...new Set([...fullPallets, ...pallets].map(item => item.load_id))], [fullPallets, pallets])
    const toneFor = loadId => `pallet-tone-${Math.max(0, loadIds.indexOf(loadId)) % 6}`
    const repartoFor = loadId => [...fullPallets, ...pallets].find(item => item.load_id === loadId)?.reparto
    const canMerge = pallet => mergeAllowedLoadIds.includes(pallet.load_id)
    useEffect(() => { setSelected(null); setHistory([]); setNotice('') }, [pallets.length && pallets[0]?.load_id])

    function merge(sourceId, targetId) {
        if (!sourceId || sourceId === targetId || disabled) return
        const source = pallets.find(p => p.id === sourceId), target = pallets.find(p => p.id === targetId)
        if (!source || !target) return
        if (source.load_id !== target.load_id) { setNotice('No se pueden unir pallets de repartos distintos.'); return }
        if (!canMerge(target)) { setNotice(`El reparto ${target.reparto} no permite unir pallets.`); return }
        const occupancy = Number(source.occupancy) + Number(target.occupancy)
        if (occupancy > 1.000001) { setNotice(`No entran juntos: sumarían ${(occupancy * 100).toFixed(2)}%.`); return }
        setHistory(current => [...current, pallets])
        const owner = target.owner_court || target.items[0]?.court
        const items = [...target.items, ...source.items].sort((a, b) => Number(b.size_rank || 0) - Number(a.size_rank || 0) || Number(b.base_priority || 0) - Number(a.base_priority || 0) || Number(a.order) - Number(b.order))
        onChange(pallets.filter(p => p.id !== sourceId).map(p => p.id === targetId ? { ...p, owner_court: owner, items, layers: items.map((item, index) => ({ ...item, position: index + 1, placement: index ? 'arriba' : 'base' })), courts: [...new Set(items.map(item => item.court))].sort((a, b) => a - b), shared: new Set(items.map(item => item.court)).size > 1, occupancy: Math.round(occupancy * 1000000) / 1000000 } : p))
        setSelected(null); setNotice(`${sourceId} se unió a ${targetId}. La cancha ${owner} armará el pallet completo.`)
    }

    function undo() {
        const previous = history.at(-1)
        if (!previous) return
        onChange(previous); setHistory(current => current.slice(0, -1)); setSelected(null); setNotice('Se deshizo el último cambio.')
    }

    function card(pallet, full = false) {
        const pct = full ? 100 : percentage(pallet), isSelected = selected === pallet.id
        const items = full ? [pallet] : pallet.items, owner = pallet.owner_court || pallet.court || pallet.items?.[0]?.court
        const profiles = palletProfiles(items), mergeable = canMerge(pallet)
        const height = pallet.height_cm == null ? 'Sin dato' : `${pallet.height_cm} cm`
        const weight = pallet.weight_complete === false ? `${pallet.weight_kg ?? 0} kg parcial` : pallet.weight_kg == null ? 'Sin dato' : `${pallet.weight_kg} kg`
        return <article key={pallet.cardId || pallet.id} draggable={!full && !disabled && mergeable} onDragStart={event => event.dataTransfer.setData('text/pallet-id', pallet.id)} onDragOver={event => { if (!full) event.preventDefault() }} onDrop={event => { if (!full) { event.preventDefault(); merge(event.dataTransfer.getData('text/pallet-id'), pallet.id) } }} className={`pallet-card pallet-tone ${toneFor(pallet.load_id)} flex flex-col rounded-2xl p-4 ${isSelected ? 'is-selected' : ''}`}>
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <h4 className="text-base font-semibold leading-6">Pallet {pallet.cardId || pallet.id}</h4>
                    <p className="text-muted flex items-center gap-1.5 text-[13px]"><span className="pallet-tone-dot h-2 w-2 shrink-0 rounded-full" />Carga {pallet.reparto} · Cancha {owner}</p>
                </div>
                <p className={`text-right text-xl font-medium leading-6 tabular-nums ${pct >= 90 ? 'text-emerald-700' : 'text-amber-700'}`}>{decimal(pct, 2)}<span className="ml-0.5 text-sm font-normal">%</span></p>
            </div>
            <div className="pallet-bar mt-3" role="img" aria-label={`Ocupación ${decimal(pct, 2)} %`}><div className={pct >= 90 ? 'is-full' : ''} style={{ width: `${Math.min(100, pct)}%` }} /></div>
            <table className="pallet-mix mt-3 w-full text-[13px]" aria-label="Calibres del pallet">
                <thead><tr><th scope="col" className="text-left">Calibre</th><th scope="col">Bultos</th><th scope="col">% pallet</th></tr></thead>
                <tbody>{profiles.map(profile => <tr key={`${profile.businessUnit}-${profile.caliber}`}>
                    <th scope="row" className="text-left font-normal"><span className="font-medium">{profile.caliber}</span><span className="text-muted block text-xs">{profile.businessUnit}</span></th>
                    <td>{profile.bultos}{profile.unidades > 0 && <span className="text-muted block text-xs">+ {profile.unidades} un.</span>}</td>
                    <td>{profile.shareKnown ? `${decimal(profile.share * 100)} %` : '—'}</td>
                </tr>)}</tbody>
            </table>
            <dl className="pallet-facts mb-3 mt-3 grid grid-cols-3 text-center text-[13px]">
                <div><dt className="text-muted text-xs">Artículos</dt><dd className="font-medium tabular-nums">{items.length}</dd></div>
                <div><dt className="text-muted text-xs">Altura</dt><dd className={`font-medium tabular-nums ${pallet.height_exceeded ? 'text-red-700' : ''}`}>{height}{pallet.height_limit_cm != null && <span className="text-muted block text-xs font-normal">de {pallet.height_limit_cm} cm</span>}</dd></div>
                <div><dt className="text-muted text-xs">Peso</dt><dd className={`font-medium tabular-nums ${pallet.weight_exceeded ? 'text-red-700' : ''}`}>{weight}{pallet.weight_limit_kg != null && <span className="text-muted block text-xs font-normal">de {pallet.weight_limit_kg} kg</span>}</dd></div>
            </dl>
            <div className="mt-auto flex flex-wrap gap-2">
                <button type="button" className="btn-quiet flex-1 rounded-lg px-3 text-[13px] font-medium" onClick={() => setViewing({ ...pallet, items, occupancy: pct / 100, owner })}>Ver artículos</button>
                {!full && !disabled && <button type="button" className="btn-quiet flex-1 rounded-lg px-3 text-[13px] disabled:opacity-50" disabled={!mergeable} title={mergeable ? '' : 'La unión está desactivada para este reparto'} onClick={() => { setSelected(pallet.id); setNotice(`Seleccionaste ${pallet.id}. Ahora elegí el pallet destino.`) }}>{isSelected ? 'Seleccionado' : mergeable ? 'Mover pallet' : 'No combinable'}</button>}
                {!full && !disabled && selected && selected !== pallet.id && <button type="button" className="btn-primary w-full rounded-lg px-3 text-[13px] font-medium" onClick={() => merge(selected, pallet.id)}>Unir aquí</button>}
            </div>
        </article>
    }

    const completeCards = fullPallets.flatMap(group => Array.from({ length: group.pallets }, (_, index) => ({ ...group, cardId: `${group.id}${group.pallets > 1 ? `-${index + 1}` : ''}`, bultos: group.bultos_por_pallet, unidades: 0 })))
    return <section className="space-y-4" aria-label="Editor de pallets de picking">
        <div>
            <h3 className="text-[15px] font-semibold">Ajustar pallets de picking</h3>
            <p className="text-muted mt-1 text-[13px]">El color identifica cada carga. Solo se pueden unir pallets de la misma carga, con la unión habilitada y sin superar el 100 %.</p>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
                <div className="flex flex-wrap gap-x-4 gap-y-1" aria-label="Referencias de color por carga">{loadIds.map(loadId => <span key={loadId} className={`pallet-legend ${toneFor(loadId)} inline-flex items-center gap-1.5 text-[13px]`}><span className="pallet-tone-dot h-2 w-2 rounded-full" />Carga {repartoFor(loadId)}</span>)}</div>
                <div className="ml-auto flex flex-wrap gap-2">
                    <button type="button" className="btn-quiet rounded-lg px-3 text-[13px] disabled:opacity-40" disabled={!history.length || disabled} onClick={undo}>Deshacer último cambio</button>
                    {selected && <button type="button" className="btn-quiet rounded-lg px-3 text-[13px]" onClick={() => setSelected(null)}>Cancelar selección</button>}
                </div>
            </div>
            {notice && <p role="status" className="note mt-3">{notice}</p>}
        </div>
        <div className="pallet-grid grid items-start gap-3">{completeCards.map(item => card(item, true))}{pallets.map(item => card(item))}</div>
        {viewing && <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={`Artículos del pallet ${viewing.cardId || viewing.id}`} onMouseDown={event => { if (event.target === event.currentTarget) setViewing(null) }}>
            <div className="modal-panel thin-scroll max-h-[calc(100vh-2rem)] w-full max-w-3xl overflow-auto rounded-2xl">
                <div className="panel-head sticky top-0 flex items-start justify-between gap-4 border-b px-5 py-4">
                    <div><h3 className="text-base font-semibold">Pallet {viewing.cardId || viewing.id}</h3><p className="text-muted text-[13px]">Reparto {viewing.reparto} · Responsable: cancha {viewing.owner} · {decimal(viewing.occupancy * 100, 2)} % ocupado</p></div>
                    <button type="button" className="btn-quiet rounded-lg px-3 text-[13px]" onClick={() => setViewing(null)}>Cerrar</button>
                </div>
                <table className="rule-table w-full border-collapse text-sm">
                    <thead><tr><th scope="col" className="text-left">SKU</th><th scope="col" className="text-left">Descripción</th><th scope="col" className="text-left">Calibre</th><th scope="col" className="text-center">Bultos</th><th scope="col" className="text-center">Unidades</th><th scope="col" className="text-center">Cancha</th></tr></thead>
                    <tbody>{viewing.items.map((item, index) => <tr key={`${item.order}-${item.sku}-${index}`} style={{ cursor: 'default' }}>
                        <th scope="row" className="text-left font-medium tabular-nums">{item.sku}</th>
                        <td className="text-left" style={{ whiteSpace: 'normal' }}>{item.descripcion}</td>
                        <td className="text-muted text-left">{item.calibre || 'Sin informar'}<span className="block text-xs">{item.business_unit || 'Unidad sin informar'}</span></td>
                        <td className="text-center tabular-nums">{item.bultos}</td>
                        <td className="text-center tabular-nums">{item.unidades || 0}</td>
                        <td className="text-center tabular-nums">{item.court}</td>
                    </tr>)}</tbody>
                </table>
            </div>
        </div>}
    </section>
}
