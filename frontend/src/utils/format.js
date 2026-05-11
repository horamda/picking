export function formatNumber(value, options = {}) {
    return Number(value || 0).toLocaleString('es-AR', {
        maximumFractionDigits: 2,
        ...options,
    })
}

export function formatDate(value) {
    if (!value) return '-'
    // Bare date strings (YYYY-MM-DD) are parsed as UTC; append T00:00:00 to treat as local time.
    const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00` : value
    const date = new Date(normalized)
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
