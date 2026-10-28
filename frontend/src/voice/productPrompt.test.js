import { test } from 'node:test'
import assert from 'node:assert/strict'
import { voicePrompt } from './productPrompt.js'

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
