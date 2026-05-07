export function Badge({ variant = 'neutral', children }) {
    const variants = {
        neutral: 'bg-slate-100 text-slate-600',
        success: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
        warning: 'bg-amber-50 text-amber-700 border border-amber-200',
        danger: 'bg-red-50 text-red-700 border border-red-200',
        info: 'bg-brand-100 text-brand-700',
    }
    return (
        <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${variants[variant]}`}>
            {children}
        </span>
    )
}

export function EstadoBadge({ estado }) {
    if (!estado) return <Badge variant="neutral">—</Badge>
    const lower = String(estado).toLowerCase().replace(/_/g, ' ')
    if (lower === 'encontrado') return <Badge variant="success">encontrado</Badge>
    if (lower.includes('no encontrado')) return <Badge variant="warning">no encontrado</Badge>
    if (lower === 'excluido') return <Badge variant="neutral">excluido</Badge>
    return <Badge variant="neutral">{estado}</Badge>
}

export function ActiveBadge({ activo }) {
    return activo
        ? <Badge variant="success">activo</Badge>
        : <Badge variant="neutral">inactivo</Badge>
}
