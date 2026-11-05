import { test } from 'node:test'
import assert from 'node:assert/strict'
import { voicePrompt } from './productPrompt.js'

test('no repite reparto ni comandos en cada producto', () => {
    for (const stage of [0,4]) {
        const prompt=voicePrompt({descripcion:'Agua',bultos:2,pallets:1,reparto:'60701',separate_reparto:true,assembly_mode:'compact'},0,1,stage)
        assert.doesNotMatch(prompt,/Reparto 60701|Supermercado|No mezclar|decí correcto|decí faltante/i)
    }
})

test('omite cantidades cero, vacías o ausentes y usa singular', () => {
    for (const empty of [0, null, undefined, '']) {
        const units = voicePrompt({ descripcion: 'Agua', bultos: empty, unidades: 4 }, 0, 3, 0)
        assert.match(units, /Agarrá 4 unidades de Agua/)
        assert.doesNotMatch(units, /bultos/)
        const cases = voicePrompt({ descripcion: 'Agua', bultos: 2, unidades: empty }, 0, 3, 0)
        assert.match(cases, /Agarrá 2 bultos de Agua/)
        assert.doesNotMatch(cases, /unidades/)
    }
    assert.match(voicePrompt({ descripcion: 'Agua', bultos: 1, unidades: 1 }, 0, 3, 0), /un bulto y una unidad/)
})
test('sin cantidades pide revisión y conserva instrucciones por proceso', () => {
    const empty = voicePrompt({ descripcion: 'Agua', bultos: 0, unidades: 0 }, 0, 3, 0)
    assert.match(empty, /supervisor/)
    assert.doesNotMatch(empty, /Agarrá|decí correcto/)
    assert.match(voicePrompt({ descripcion: 'Agua', pallets: 1 }, 0, 3, 4), /un pallet completo/)
    assert.match(voicePrompt({ descripcion: 'Original', descripcion_voz: 'Nombre hablado', unidades: 1 }, 0, 3, 1), /Verificá una unidad de Nombre hablado/)
})

test('aplica la plantilla administrativa con sus variables', () => {
    const spoken = voicePrompt({ descripcion_voz: 'Brahma litro', bultos: 2, unidades: 4 }, 2, 12, 0,
        { picking_product: 'Buscá {quantity} de {product}. Vas {position} de {total}.' })
    assert.match(spoken, /Buscá 2 bultos y 4 unidades de Brahma litro\. Vas 3 de 12\./)
    assert.equal(voicePrompt({ descripcion: 'Agua', bultos: 2 }, 0, 1, 0, { picking_product: null }), '')
})

test('lee la frescura exacta sin mezclarla con la descripción editable', () => {
    const prompt = voicePrompt({ descripcion: 'Brahma', descripcion_voz: 'Brahma litro', bultos: 2, fecha_frescura: '2027-06-03' }, 0, 1, 0)
    assert.match(prompt, /Brahma litro/)
    assert.match(prompt, /Frescura exacta 3\/6\/2027/)
})
