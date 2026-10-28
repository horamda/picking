const number = value => value == null ? 'Pendiente' : Number(value).toLocaleString('es-AR', { maximumFractionDigits: 4 })
export default function TruckWorkSummary({ summary: s, waiting = false }) {
    if (!s) return null
    const mine = s.mine
    return <section className="my-3 space-y-3 rounded-xl border border-blue-200 bg-blue-50 p-4">
        <h3 className="font-semibold">Resumen de este camión</h3>
        <p className="text-sm">{s.loads} repartos · {s.courts} canchas · {number(s.bultos)} bultos + {number(s.unidades)} unidades · {number(s.hl)} HL</p>
        {!!s.hl_missing?.length && <p className="text-sm text-amber-800">HL incompletos: faltan factores de {s.hl_missing.length} artículos.</p>}
        <p className="font-semibold">{number(s.pallets)} pallets físicos previstos / capacidad {number(s.capacity)}</p>
        <p className="text-sm">{number(s.full_pallets)} completos + {number(s.picking_pallets)} de picking. Armado sujeto al plan aprobado.</p>
        {waiting && <p role="status" className="font-semibold text-amber-800">Esperando la aprobación del supervisor para comenzar este camión.</p>}
        {mine && !waiting && <>
            <h4 className="font-semibold">Tu trabajo en este camión</h4>
            <p className="text-sm">{mine.courts} canchas · {mine.loads} repartos · {number(mine.bultos)} bultos + {number(mine.unidades)} unidades · {number(mine.hl)} HL</p>
            <p className="text-sm">{mine.finished_tasks}/{mine.tasks} tareas terminadas · {number(mine.pallets)} pallets en tu armado.</p>
            <p className="text-sm">Pallets completos de tus canchas: {mine.full_pallets_info} (se registran en el proceso de pallets completos).</p>
            {!!mine.allocations?.length && <details><summary className="min-h-12 cursor-pointer py-3 font-medium">Cómo distribuir el picking en pallets</summary>
                <p className="mb-3 text-sm">Conservá estos identificadores entre repartos. Los pallets compartidos cuentan una sola vez en el total del camión.</p>
                {mine.allocations.map(p => <div key={p.id} className="my-2 rounded-lg bg-white p-3"><b>Pallet {p.id}{p.shared ? ' · Compartido con otras canchas' : ''}</b><ul className="mt-2 space-y-1 text-sm">{p.items.map((i, n) => <li key={n}>Reparto {i.reparto} · Cancha {i.court} · {i.descripcion}: {i.bultos} bultos + {i.unidades} unidades</li>)}</ul></div>)}
            </details>}
        </>}
    </section>
}
