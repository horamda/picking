import { useEffect, useMemo, useState } from 'react'

const percentage = pallet => Math.round(Number(pallet.occupancy || 0) * 10000) / 100

const palletProfiles = items => [...new Map(items.map(item => {
    const businessUnit = String(item.business_unit || '').trim() || 'Unidad sin informar'
    const caliber = String(item.calibre || '').trim() || 'Calibre sin informar'
    return [`${businessUnit.toLocaleUpperCase('es-AR')}|${caliber.toLocaleUpperCase('es-AR')}`, { businessUnit, caliber }]
})).values()]

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
        const profiles = palletProfiles(items)
        return <article key={pallet.cardId || pallet.id} draggable={!full && !disabled && canMerge(pallet)} onDragStart={event => event.dataTransfer.setData('text/pallet-id', pallet.id)} onDragOver={event => { if (!full) event.preventDefault() }} onDrop={event => { if (!full) { event.preventDefault(); merge(event.dataTransfer.getData('text/pallet-id'), pallet.id) } }} className={`pallet-tone ${toneFor(pallet.load_id)} flex min-h-72 flex-col rounded-2xl border-2 p-4 ${isSelected ? 'ring-4 ring-blue-500' : ''}`}>
            <div className="flex items-start justify-between gap-3"><div><h4 className="text-xl font-bold">Pallet {pallet.cardId || pallet.id}</h4><span className="pallet-reparto-badge mt-1 inline-flex rounded-full px-3 py-1 text-sm font-bold">Carga {pallet.reparto}</span></div><span className={`rounded-full px-3 py-1 font-bold ${pct >= 90 ? 'bg-emerald-700 text-white' : 'bg-amber-600 text-white'}`}>{pct.toFixed(2)}%</span></div>
            <p className="mt-2">Responsable: <b>Cancha {owner}</b></p><p>{items.length} {items.length === 1 ? 'artículo' : 'artículos'}</p>
            <div className="mt-2 flex flex-wrap gap-2" aria-label="Unidades de negocio y calibres del pallet">{profiles.map(({ businessUnit, caliber }) => <span key={`${businessUnit}-${caliber}`} className="inline-flex max-w-full rounded-lg border border-white/30 bg-black/20 px-2.5 py-1 text-sm font-semibold"><span className="truncate">{businessUnit} · {caliber}</span></span>)}</div>
            <p className={`${pallet.height_exceeded ? 'font-bold text-red-700' : ''}`}>Altura: {pallet.height_cm == null ? 'No calculable' : `${pallet.height_cm} cm`}{pallet.height_limit_cm != null ? ` / ${pallet.height_limit_cm} cm` : ''}</p>
            <p className={`${pallet.weight_exceeded ? 'font-bold text-red-700' : ''}`}>Peso: {pallet.weight_complete === false ? `${pallet.weight_kg ?? 0} kg conocidos` : pallet.weight_kg == null ? 'No calculable' : `${pallet.weight_kg} kg`}{pallet.weight_limit_kg != null ? ` / ${pallet.weight_limit_kg} kg` : ''}</p>
            <div className="mt-3 h-3 overflow-hidden rounded-full bg-white/80"><div className="h-full bg-emerald-500" style={{ width: `${Math.min(100, pct)}%` }} /></div>
            <div className="mt-auto grid gap-2 sm:grid-cols-2"><button type="button" className="min-h-11 rounded-xl border bg-white px-3 font-semibold" onClick={() => setViewing({ ...pallet, items, occupancy: pct / 100, owner })}>Ver artículos</button>
                {!full && !disabled && <button type="button" className="min-h-11 rounded-xl border bg-white px-3 disabled:opacity-50" disabled={!canMerge(pallet)} title={canMerge(pallet) ? '' : 'La unión está desactivada para este reparto'} onClick={() => { setSelected(pallet.id); setNotice(`Seleccionaste ${pallet.id}. Ahora elegí el pallet destino.`) }}>{isSelected ? 'Seleccionado' : canMerge(pallet) ? 'Mover pallet' : 'No combinable'}</button>}
                {!full && !disabled && selected && selected !== pallet.id && <button type="button" className="min-h-11 rounded-xl bg-blue-700 px-3 text-white sm:col-span-2" onClick={() => merge(selected, pallet.id)}>Unir aquí</button>}
            </div>
        </article>
    }

    const completeCards = fullPallets.flatMap(group => Array.from({ length: group.pallets }, (_, index) => ({ ...group, cardId: `${group.id}${group.pallets > 1 ? `-${index + 1}` : ''}`, bultos: group.bultos_por_pallet, unidades: 0 })))
    return <section className="space-y-4" aria-label="Editor de pallets de picking">
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4"><h3 className="text-lg font-semibold">Ajustar pallets de picking</h3><p className="mt-1">Los colores identifican cada carga. Solo se pueden unir pallets de la misma carga, con la unión habilitada y sin superar el 100%.</p><div className="mt-3 flex flex-wrap gap-2" aria-label="Referencias de color por carga">{loadIds.map(loadId => <span key={loadId} className={`pallet-tone ${toneFor(loadId)} inline-flex items-center rounded-full border-2 px-3 py-1 font-bold`}><span className="pallet-tone-dot mr-2 h-3 w-3 rounded-full" />Carga {repartoFor(loadId)}</span>)}</div><div className="mt-3 flex flex-wrap gap-2"><button type="button" className="min-h-11 rounded-xl border bg-white px-4 disabled:opacity-40" disabled={!history.length || disabled} onClick={undo}>Deshacer último cambio</button>{selected && <button type="button" className="min-h-11 rounded-xl border bg-white px-4" onClick={() => setSelected(null)}>Cancelar selección</button>}</div>{notice && <p role="status" className="mt-3 rounded-lg bg-white p-3">{notice}</p>}</div>
        <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">{completeCards.map(item => card(item, true))}{pallets.map(item => card(item))}</div>
        {viewing && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4" role="dialog" aria-modal="true" onClick={() => setViewing(null)}><div className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-2xl bg-white p-5 text-slate-900 shadow-2xl" onClick={event => event.stopPropagation()}><div className="flex items-start justify-between gap-4"><div><h3 className="text-2xl font-bold">Pallet {viewing.cardId || viewing.id}</h3><p>Reparto {viewing.reparto} · Responsable: cancha {viewing.owner}</p></div><button type="button" className="min-h-11 rounded-xl border px-4" onClick={() => setViewing(null)}>Cerrar</button></div><div className="mt-4 space-y-3">{viewing.items.map((item, index) => <div key={`${item.order}-${item.sku}-${index}`} className="rounded-xl bg-slate-100 p-4"><p className="font-bold">{item.sku} · {item.descripcion}</p><p>{item.bultos} bultos + {item.unidades || 0} unidades · origen cancha {item.court}</p><p>{item.business_unit || 'Unidad sin informar'} · {item.calibre || 'Calibre sin informar'}</p></div>)}</div></div></div>}
    </section>
}
