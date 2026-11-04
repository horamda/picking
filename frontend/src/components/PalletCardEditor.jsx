import { useEffect, useState } from 'react'

const percentage = pallet => Math.round(Number(pallet.occupancy || 0) * 10000) / 100

export default function PalletCardEditor({ pallets, fullPallets = [], disabled, onChange }) {
    const [selected, setSelected] = useState(null)
    const [history, setHistory] = useState([])
    const [notice, setNotice] = useState('')
    useEffect(() => { setSelected(null); setHistory([]); setNotice('') }, [pallets.length && pallets[0]?.load_id])

    function merge(sourceId, targetId) {
        if (!sourceId || sourceId === targetId || disabled) return
        const source = pallets.find(p => p.id === sourceId), target = pallets.find(p => p.id === targetId)
        if (!source || !target) return
        if (source.load_id !== target.load_id) {
            setNotice('No se pueden unir pallets de repartos distintos.'); return
        }
        const occupancy = Number(source.occupancy) + Number(target.occupancy)
        if (occupancy > 1.000001) {
            setNotice(`No entran juntos: sumarían ${(occupancy * 100).toFixed(2)}%.`); return
        }
        setHistory(current => [...current, pallets])
        const owner = target.owner_court || target.items[0]?.court
        const items = [...target.items, ...source.items].sort((a, b) =>
            Number(b.size_rank || 0) - Number(a.size_rank || 0) || Number(b.base_priority || 0) - Number(a.base_priority || 0) || Number(a.order) - Number(b.order))
        onChange(pallets.filter(p => p.id !== sourceId).map(p => p.id === targetId ? {
            ...p, owner_court: owner, items, layers: items.map((item, index) => ({ ...item, position: index + 1, placement: index ? 'arriba' : 'base' })),
            courts: [...new Set(items.map(item => item.court))].sort((a, b) => a - b), shared: new Set(items.map(item => item.court)).size > 1,
            occupancy: Math.round(occupancy * 1000000) / 1000000,
        } : p))
        setSelected(null)
        setNotice(`${sourceId} se unió a ${targetId}. La cancha ${owner} armará el pallet completo.`)
    }

    function undo() {
        const previous = history.at(-1)
        if (!previous) return
        onChange(previous); setHistory(current => current.slice(0, -1)); setSelected(null); setNotice('Se deshizo el último cambio.')
    }

    return <section className="space-y-4" aria-label="Editor de pallets de picking">
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <h3 className="text-lg font-semibold">Ajustar pallets de picking</h3>
            <p className="mt-1">Cada tarjeta es un pallet físico. Para unir dos, elegí primero el pallet que querés mover y después pulsá <b>Unir aquí</b> en el pallet destino.</p>
            <p className="mt-1 text-sm">Solo se unen pallets del mismo reparto y cuya suma no supere el 100%. El operario de la cancha destino recibirá todos sus artículos.</p>
            <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className="min-h-11 rounded-xl border bg-white px-4 disabled:opacity-40" disabled={!history.length || disabled} onClick={undo}>Deshacer último cambio</button>
                {selected && <button type="button" className="min-h-11 rounded-xl border bg-white px-4" onClick={() => setSelected(null)}>Cancelar selección</button>}
            </div>
            {notice && <p role="status" className="mt-3 rounded-lg bg-white p-3">{notice}</p>}
        </div>
        {!!fullPallets.length && <details className="rounded-xl border bg-white p-4">
            <summary className="cursor-pointer font-semibold">Ver pallets completos al 100% ({fullPallets.reduce((sum, item) => sum + item.pallets, 0)})</summary>
            <div className="mt-4 grid gap-3 lg:grid-cols-2 2xl:grid-cols-3">
                {fullPallets.flatMap(group => Array.from({ length: group.pallets }, (_, index) =>
                    <article key={`${group.id}-${index}`} className="rounded-2xl border-2 border-emerald-300 bg-white p-4">
                        <div className="flex justify-between gap-3"><div><h4 className="text-lg font-bold">Pallet {group.id}{group.pallets > 1 ? `-${index + 1}` : ''}</h4><p>Reparto {group.reparto} · Cancha {group.court}</p></div><span className="rounded-full bg-emerald-100 px-3 py-1 font-bold text-emerald-800">100,00%</span></div>
                        <p className="mt-3 font-semibold">{group.sku} · {group.descripcion}</p><p>{group.bultos_por_pallet} bultos</p>
                    </article>))}
            </div>
        </details>}
        <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
            {pallets.map(pallet => {
                const pct = percentage(pallet), isSelected = selected === pallet.id
                return <article key={pallet.id}
                    draggable={!disabled}
                    onDragStart={event => event.dataTransfer.setData('text/pallet-id', pallet.id)}
                    onDragOver={event => event.preventDefault()}
                    onDrop={event => { event.preventDefault(); merge(event.dataTransfer.getData('text/pallet-id'), pallet.id) }}
                    className={`rounded-2xl border-2 bg-white p-4 shadow-sm ${isSelected ? 'border-blue-600 ring-2 ring-blue-200' : 'border-slate-200'}`}>
                    <div className="flex items-start justify-between gap-3">
                        <div><h4 className="text-xl font-bold">Pallet {pallet.id}</h4><p>Reparto {pallet.reparto} · Responsable: <b>Cancha {pallet.owner_court || pallet.items[0]?.court}</b></p></div>
                        <span className={`rounded-full px-3 py-1 font-bold ${pct > 100 ? 'bg-red-100 text-red-800' : pct >= 90 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'}`}>{pct.toFixed(2)}%</span>
                    </div>
                    <div className="mt-3 h-3 overflow-hidden rounded-full bg-slate-200"><div className="h-full bg-emerald-500" style={{ width: `${Math.min(100, pct)}%` }} /></div>
                    <div className="mt-4 space-y-2">
                        {pallet.items.map((item, index) => <div key={`${item.order}-${item.sku}-${index}`} className="rounded-xl bg-slate-50 p-3">
                            <p className="font-semibold">{item.sku} · {item.descripcion}</p>
                            <p>{item.bultos} bultos + {item.unidades} unidades · origen cancha {item.court}</p>
                            <p className="text-sm text-slate-600">{item.calibre || 'Calibre sin informar'}</p>
                        </div>)}
                    </div>
                    {!disabled && <div className="mt-4 grid gap-2 sm:grid-cols-2">
                        <button type="button" className="min-h-11 rounded-xl border bg-white px-3" onClick={() => { setSelected(pallet.id); setNotice(`Seleccionaste ${pallet.id}. Ahora elegí el pallet destino.`) }}>{isSelected ? 'Seleccionado para mover' : 'Mover este pallet'}</button>
                        <button type="button" className="min-h-11 rounded-xl bg-blue-700 px-3 text-white disabled:opacity-40" disabled={!selected || isSelected} onClick={() => merge(selected, pallet.id)}>Unir aquí</button>
                    </div>}
                </article>
            })}
        </div>
    </section>
}
