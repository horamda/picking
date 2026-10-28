import { test } from 'node:test'
import assert from 'node:assert/strict'
import { voiceBackupCsv, voiceBackupJson } from './voiceBackup.js'

test('respaldo JSON conserva códigos, acentos y textos exactamente', () => {
    const data = { version: 1, items: [{ sku: '0001', descripcion_voz: 'Agua "sin gas"; un litro\nRetornable' }, { sku: '2', descripcion_voz: '=texto literal' }] }
    assert.deepEqual(JSON.parse(voiceBackupJson(data)), data)
})

test('tabla CSV incluye BOM, escapa comillas y evita interpretar fórmulas', () => {
    const items = [{ sku: '0001', descripcion_voz: 'Agua "sin gas"; limón' }, { sku: '2', descripcion_voz: '=1+1' }]
    assert.equal(voiceBackupCsv(items), '\uFEFF"Codigo";"Descripcion para voz"\r\n"0001";"Agua ""sin gas""; limón"\r\n"2";"\'=1+1"\r\n')
    assert.equal(items[1].descripcion_voz, '=1+1')
})
