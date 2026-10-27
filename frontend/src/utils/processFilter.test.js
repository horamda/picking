import { test } from 'node:test'
import assert from 'node:assert/strict'
import { processState, matchesProcess, filterProcessGroups } from './processFilter.js'

test('distingue sin iniciar, en curso, pausa y finalizado', () => {
  assert.equal(processState(), 'not_started')
  assert.equal(processState({ status: 'active', timer_started_at: '2026-10-24' }), 'running')
  assert.equal(processState({ status: 'active', timer_started_at: null }), 'paused')
  assert.equal(processState({ status: 'done' }), 'done')
})

test('filtra por etapa del rol y conserva solo cargas y canchas coincidentes', () => {
  const running = { numero: 1, status: { checks: [{ stage: 0, status: 'active', timer_started_at: 'now' }] } }
  const waiting = { numero: 2, status: { checks: [] } }
  assert.equal(matchesProcess(running, [0], 'running'), true)
  assert.equal(matchesProcess(running, [1, 2], 'running'), false)
  const groups = [{ loads: [{ canchas: [running, waiting] }], pending: [{ id: 2 }], total: 2 }]
  const result = filterProcessGroups(groups, [0], 'running')
  assert.deepEqual(result[0].loads[0].canchas, [running])
  assert.deepEqual(result[0].pending, [])
  assert.equal(filterProcessGroups(groups, [0], 'paused').length, 0)
  assert.equal(filterProcessGroups(groups, [0], 'not_started')[0].pending.length, 1)
  assert.equal(groups[0].loads[0].canchas.length, 2)
})
