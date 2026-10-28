import test from 'node:test'
import assert from 'node:assert/strict'
import { groupControlTrucks } from './controlTrucks.js'

const truck = { id: 1, truck: 'ABC123', load_date: '2026-10-15', branch: 'Central',
    loads: [{ id: 1, source_id: 10, reparto: '1', canchas: [{ status: { done: true } }] }],
    status: { released_at: null, allowed: false } }
const source = { id: 11, reparto: '2', camion_control: 'ABC123',
    camion: '12 - (ABC123) Transporte', fecha: '2026-10-15T00:00:00', deposito: ' Central ' }

test('one truck includes both controlled and unstarted PDF loads', () => {
    const result = groupControlTrucks([truck], [source])
    assert.equal(result.length, 1)
    assert.equal(result[0].total, 2)
    assert.equal(result[0].completed, 1)
    assert.equal(result[0].pending[0].id, 11)
    assert.equal(result[0].released, false)
})

test('different dates and depots remain separate dispatch groups', () => {
    const result = groupControlTrucks([truck], [source,
        { ...source, id: 12, fecha: '2026-10-16T00:00:00' },
        { ...source, id: 13, deposito: 'Otro' }])
    assert.equal(result.length, 3)
    assert.equal(result.reduce((sum, group) => sum + group.total, 0), 4)
})

test('a historical release cannot hide newly pending loads', () => {
    const released = { ...truck, status: { released_at: '2026-10-15T15:00:00Z', allowed: true } }
    assert.equal(groupControlTrucks([released], [])[0].released, true)
    assert.equal(groupControlTrucks([released], [source])[0].released, false)
})

test('dispatch selection excludes unselected PDF loads from operative totals', () => {
    const selected = { ...truck, dispatch: { load_ids: [1], position: 1 } }
    const result = groupControlTrucks([selected], [source])[0]
    assert.equal(result.total, 1)
    assert.deepEqual(result.pending, [])
})
