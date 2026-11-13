// Geometría de solo lectura para el simulador 3D: convierte el plan de pallets en cajas ubicadas.
// Las alturas usan la misma fórmula que el cálculo del servidor: (altura de referencia − tarima) / pisos por pallet.

const num = value => { if (value === '' || value == null) return null; const n = Number(value); return Number.isFinite(n) ? n : null }

export const caliberKey = item => `${String(item.business_unit || '').trim().toUpperCase()}|${String(item.calibre || '').trim().toUpperCase()}`
export const caliberLabel = item => `${String(item.calibre || '').trim() || 'Calibre sin informar'}`

// Un registro por pallet físico, en el orden de los repartos del plan.
export function expandPallets(plan) {
    const pallets = []
    for (const full of plan.full_pallets || []) {
        const count = Math.max(1, Number(full.pallets) || 1)
        const perPallet = Number(full.bultos_por_pallet) || Math.round(Number(full.bultos || 0) / count)
        for (let n = 0; n < count; n++) pallets.push({
            id: count > 1 ? `${full.id}·${n + 1}` : String(full.id), kind: 'full', loadId: full.load_id, reparto: full.reparto, court: full.court,
            items: [{ ...full, bultos: perPallet, unidades: 0 }], occupancy: 1,
            heightCm: num(full.height_cm), weightKg: num(full.weight_kg), heightLimitCm: num(full.height_limit_cm), weightLimitKg: num(full.weight_limit_kg),
            heightExceeded: Boolean(full.height_exceeded), weightExceeded: Boolean(full.weight_exceeded), weightComplete: full.weight_complete !== false,
        })
    }
    for (const mixed of plan.mixed_pallets || []) pallets.push({
        id: String(mixed.id), kind: 'picking', loadId: mixed.load_id, reparto: mixed.reparto, court: mixed.owner_court ?? mixed.courts?.[0],
        items: mixed.items || [], occupancy: Number(mixed.occupancy) || 0,
        heightCm: num(mixed.height_cm), weightKg: num(mixed.weight_kg), heightLimitCm: num(mixed.height_limit_cm), weightLimitKg: num(mixed.weight_limit_kg),
        heightExceeded: Boolean(mixed.height_exceeded), weightExceeded: Boolean(mixed.weight_exceeded), weightComplete: mixed.weight_complete !== false,
    })
    const order = (plan.load_plans || []).map(load => load.load_id)
    const rank = id => { const index = order.indexOf(id); return index < 0 ? order.length : index }
    return pallets.map((pallet, index) => ({ pallet, index })).sort((a, b) => rank(a.pallet.loadId) - rank(b.pallet.loadId) || a.index - b.index).map(entry => entry.pallet)
}

// Reparte n bultos en una grilla sobre la huella de la tarima. Si hay medidas reales del bulto y entran en la celda, se usan.
function floorLayout(perFloor, sizeX, sizeZ, dims) {
    const realLong = dims ? Math.max(dims.length, dims.width) : null, realShort = dims ? Math.min(dims.length, dims.width) : null
    const target = realLong && realShort ? realLong / realShort : 1.4
    let best = null
    for (let cols = 1; cols <= perFloor; cols++) {
        const rows = Math.ceil(perFloor / cols), cellX = sizeX / cols, cellZ = sizeZ / rows
        const ratio = Math.max(cellX, cellZ) / Math.min(cellX, cellZ)
        const score = (cols * rows - perFloor) * 0.6 + Math.abs(Math.log(ratio / target))
        if (!best || score < best.score) best = { cols, rows, cellX, cellZ, score }
    }
    const gap = 1.2
    let boxX = best.cellX - gap, boxZ = best.cellZ - gap, real = false
    if (realLong && realShort) {
        const [alongX, alongZ] = best.cellX >= best.cellZ ? [realLong, realShort] : [realShort, realLong]
        if (alongX <= best.cellX + 0.5 && alongZ <= best.cellZ + 0.5) { boxX = Math.min(alongX, best.cellX) - gap; boxZ = Math.min(alongZ, best.cellZ) - gap; real = true }
    }
    const slots = []
    for (let row = 0; row < best.rows; row++) for (let col = 0; col < best.cols; col++) {
        if (slots.length >= perFloor) break
        slots.push({ x: -sizeX / 2 + best.cellX * (col + 0.5), z: -sizeZ / 2 + best.cellZ * (row + 0.5), w: boxX, d: boxZ })
    }
    return { slots, real }
}

// Apila los artículos del pallet de abajo hacia arriba y devuelve las cajas en coordenadas locales (cm).
export function stackPallet(pallet, config, dimensions, sizeX, sizeZ) {
    const base = num(config.pallet_base_height_cm), reference = num(config.reference_pallet_height_cm)
    const exactHeights = base != null && reference != null && reference > base
    const baseCm = base ?? 15, usable = exactHeights ? reference - base : 150
    const share = Boolean(config.share_floor_remainders)
    const boxes = [], floors = [], missing = [], open = new Map()
    let top = baseCm, realFootprint = true
    for (const item of pallet.items) {
        const perCase = Number(item.unidades_por_bulto) || 0
        const amount = Number(item.bultos || 0) + (perCase ? Number(item.unidades || 0) / perCase : 0)
        let count = Math.ceil(amount - 1e-9)
        if (count <= 0) continue
        const perFloor = Number(item.bultos_por_piso) || 0, perPallet = Number(item.pisos_por_pallet) || 0
        if (!perFloor || !perPallet) { missing.push(String(item.sku)); continue }
        const key = `${perFloor}x${perPallet}`, floorHeight = usable / perPallet, color = caliberKey(item)
        const layout = floorLayout(perFloor, sizeX, sizeZ, dimensions.get(color))
        if (!layout.real) realFootprint = false
        let floor = share ? open.get(key) : null
        while (count > 0) {
            if (!floor || floor.used >= perFloor) {
                floor = { number: floors.length + 1, y: top, h: floorHeight, used: 0, perFloor, layout, parts: [] }
                floors.push(floor); top += floorHeight
                if (share) open.set(key, floor)
            }
            const take = Math.min(count, perFloor - floor.used)
            for (let n = 0; n < take; n++) { const slot = floor.layout.slots[floor.used + n]; boxes.push({ x: slot.x, z: slot.z, w: slot.w, d: slot.d, y: floor.y, h: floorHeight, color, floor: floor.number }) }
            floor.used += take; floor.parts.push({ item, count: take }); count -= take
        }
    }
    return { boxes, floors, baseCm, topCm: top, exactHeights, realFootprint, missing }
}
