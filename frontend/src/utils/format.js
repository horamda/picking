export function formatNumber(value, options = {}) {
    return Number(value || 0).toLocaleString('es-AR', {
        maximumFractionDigits: 2,
        ...options,
    })
}
