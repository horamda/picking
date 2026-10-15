// The API supplies the canonical truck identifier used by the control service.
export function groupControlTrucks(trucks, sources) {
    const groups = new Map()
    const key = (truck, date, branch) => JSON.stringify([truck, date, branch])
    for (const truck of trucks) {
        groups.set(key(truck.truck, truck.load_date, truck.branch), { ...truck, pending: [] })
    }
    for (const source of sources) {
        const truck = source.camion_control || source.camion || ''
        const date = source.fecha?.slice(0, 10) || ''
        const branch = source.deposito?.trim() || ''
        // Incomplete metadata must not merge unrelated unidentified trucks.
        const groupKey = truck && date && branch ? key(truck, date, branch) : `source:${source.id}`
        if (!groups.has(groupKey)) groups.set(groupKey, {
            id: null, truck, load_date: date, branch, loads: [], pending: [],
            status: { shortages: [], assets: null, released_at: null, complete: false },
        })
        groups.get(groupKey).pending.push(source)
    }
    return [...groups.entries()].map(([key, group]) => {
        group.loads = [...group.loads].sort((a, b) => (a.source_id || a.id) - (b.source_id || b.id))
        group.pending.sort((a, b) => a.id - b.id)
        const completed = group.loads.filter(load => load.canchas.length > 0 && load.canchas.every(c => c.status.done)).length
        const total = group.loads.length + group.pending.length
        const released = Boolean(group.status.released_at && group.status.allowed && !group.pending.length)
        return { ...group, key, total, completed, released }
    }).sort((a, b) => b.load_date.localeCompare(a.load_date) || a.truck.localeCompare(b.truck))
}
