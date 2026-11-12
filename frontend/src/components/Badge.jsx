export function Badge({ variant = 'neutral', children }) {
    return <span className={`badge badge--${variant}`}>{children}</span>
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
