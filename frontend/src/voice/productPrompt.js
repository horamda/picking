export function voicePrompt(p, index, total, stage) {
    const name = p.descripcion_voz || p.descripcion
    const intro = `Producto ${index + 1} de ${total}. `
    if (stage === 4 && Number(p.pallets) > 0) {
        return `${intro}Prepará ${Number(p.pallets) === 1 ? 'un pallet completo' : `${p.pallets} pallets completos`} de ${name}. Cuando termines, decí correcto.`
    }
    const quantities = []
    if (Number(p.bultos) > 0) quantities.push(Number(p.bultos) === 1 ? 'un bulto' : `${p.bultos} bultos`)
    if (Number(p.unidades) > 0) quantities.push(Number(p.unidades) === 1 ? 'una unidad' : `${p.unidades} unidades`)
    if (!quantities.length) return `${intro}${name} no tiene cantidades para preparar. Revisá la planilla con el supervisor.`
    const picking = [0, 4].includes(stage)
    return `${intro}${picking ? 'Agarrá' : 'Verificá'} ${quantities.join(' y ')} de ${name}. ${picking ? 'Cuando termines, decí correcto. Si falta mercadería, decí faltante.' : 'Decí correcto, error corregido o faltante.'}`
}
