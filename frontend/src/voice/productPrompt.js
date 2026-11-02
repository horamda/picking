export function voicePrompt(p, index, total, stage) {
    const name = p.descripcion_voz || p.descripcion
    const separation = p.separate_reparto ? `Reparto ${p.reparto}. ${p.assembly_mode === 'compact' ? 'Supermercado. Armado compacto. ' : ''}No mezclar con otros repartos. ` : ''
    const intro = `${separation}Producto ${index + 1} de ${total}. `
    const destination = (p.pallet_destinations || []).map(d => `Pallet ${d.pallet_id}: ${[Number(d.bultos) > 0 && `${d.bultos} bultos`, Number(d.unidades) > 0 && `${d.unidades} unidades`].filter(Boolean).join(' y ')}. `).join('')
    if (stage === 4 && Number(p.pallets) > 0) {
        return `${intro}Prepará ${Number(p.pallets) === 1 ? 'un pallet completo' : `${p.pallets} pallets completos`} de ${name}. ${p.pallet_group ? `Grupo ${p.pallet_group}. ` : ''}Cuando termines, decí correcto.`
    }
    const quantities = []
    if (Number(p.bultos) > 0) quantities.push(Number(p.bultos) === 1 ? 'un bulto' : `${p.bultos} bultos`)
    if (Number(p.unidades) > 0) quantities.push(Number(p.unidades) === 1 ? 'una unidad' : `${p.unidades} unidades`)
    if (!quantities.length) return `${intro}${name} no tiene cantidades para preparar. Revisá la planilla con el supervisor.`
    const picking = [0, 4].includes(stage)
    return `${intro}${picking ? 'Agarrá' : 'Verificá'} ${quantities.join(' y ')} de ${name}. ${destination}${picking ? 'Cuando termines, decí correcto. Si falta mercadería, decí faltante.' : 'Decí correcto, error corregido o faltante.'}`
}
