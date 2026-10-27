import { test } from 'node:test'
import assert from 'node:assert/strict'
import { canVisit, homeForRole, stagesForRole } from './roleAccess.js'

test('operador y controlador entran solo a su pantalla, incluso por URL directa', () => {
  for (const [role, home, stages] of [['operador', '/picking', [0]], ['controlador', '/controles', [1, 2]]]) {
    assert.equal(homeForRole(role), home)
    assert.deepEqual(stagesForRole(role), stages)
    for (const path of ['/', '/operacion', '/upload', '/historial', '/articulos', '/exclusiones', '/control-cargas', '/picking', '/controles']) {
      assert.equal(canVisit(role, path), path === home, `${role}: ${path}`)
    }
  }
})

test('supervisión y administración conservan acceso; rol desconocido no tiene acceso', () => {
  for (const role of ['supervisor', 'administrador']) {
    for (const path of ['/', '/historial', '/operacion', '/operacion?tab=picking', '/operacion?tab=canchas', '/operacion?tab=pallets']) {
      assert.equal(canVisit(role, path), true, `${role}: ${path}`)
    }
    assert.deepEqual(stagesForRole(role), [0, 1, 2, 4])
  }
  assert.equal(canVisit(undefined, '/picking'), false)
  assert.deepEqual(stagesForRole('desconocido'), [])
})
