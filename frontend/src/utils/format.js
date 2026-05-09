export function formatNumber(value, options = {}) {
    return Number(value || 0).toLocaleString('es-AR', {
        maximumFractionDigits: 2,
        ...options,
    })
}

export function formatDate(value) {
    if (!value) return '-'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return '-'
    return new Intl.DateTimeFormat('es-AR').format(date)
}

export function todayInputValue() {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
}
