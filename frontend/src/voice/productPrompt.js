const fill = (template, values) => template.replace(/\{(\w+)\}/g, (_, key) => values[key] ?? `{${key}}`)

const freshnessPrompt = product => product.fecha_frescura
    ? ` Frescura exacta ${new Date(`${product.fecha_frescura}T00:00:00`).toLocaleDateString('es-AR')}.`
    : ' Frescura no informada.'

export function voicePrompt(p, index, total, stage, templates = {}) {
    const name = p.descripcion_voz || p.descripcion
    const intro = `Producto ${index + 1} de ${total}. `
    const freshness = freshnessPrompt(p)
    const destination = (p.pallet_destinations || []).map(d => `Pallet ${d.pallet_id}: ${[Number(d.bultos) > 0 && `${d.bultos} bultos`, Number(d.unidades) > 0 && `${d.unidades} unidades`].filter(Boolean).join(' y ')}. `).join('')
    if (stage === 4 && Number(p.pallets) > 0) {
        const pallets = Number(p.pallets) === 1 ? 'un pallet completo' : `${p.pallets} pallets completos`
        const fallback = `${intro}Prepará ${pallets} de ${name}. ${p.pallet_group ? `Grupo ${p.pallet_group}. ` : ''}`
        const prompt = Object.hasOwn(templates, 'pallet_product')
            ? (templates.pallet_product ? fill(templates.pallet_product, { position: index + 1, total, pallets, product: name }) : '')
            : fallback
        return prompt ? `${prompt}${freshness}` : ''
    }
    const quantities = []
    if (Number(p.bultos) > 0) quantities.push(Number(p.bultos) === 1 ? 'un bulto' : `${p.bultos} bultos`)
    if (Number(p.unidades) > 0) quantities.push(Number(p.unidades) === 1 ? 'una unidad' : `${p.unidades} unidades`)
    if (!quantities.length) return Object.hasOwn(templates, 'empty_product')
        ? (templates.empty_product ? fill(templates.empty_product, { position: index + 1, total, product: name }) : '')
        : `${intro}${name} no tiene cantidades para preparar. Revisá la planilla con el supervisor.`
    const picking = [0, 4].includes(stage)
    if (picking && Object.hasOwn(templates, 'picking_product')) return templates.picking_product
        ? `${fill(templates.picking_product, { position: index + 1, total, quantity: quantities.join(' y '), product: name })}${freshness} ${destination}`
        : ''
    return `${intro}${picking ? 'Agarrá' : 'Verificá'} ${quantities.join(' y ')} de ${name}.${freshness} ${destination}`
}
