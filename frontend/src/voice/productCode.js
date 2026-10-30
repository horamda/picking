export function productCode(text) {
    const names = ['cero','uno','dos','tres','cuatro','cinco','seis','siete','ocho','nueve']
    const tokens = String(text || '').trim().toLowerCase().split(/\s+/)
    const parts = tokens.map(t => /^\d+$/.test(t) ? t : names.includes(t) ? String(names.indexOf(t)) : null)
    return parts.some(p => p == null) ? '' : parts.join('')
}
