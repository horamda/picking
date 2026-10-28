import { test } from 'node:test'
import assert from 'node:assert/strict'
import { canVisit, homeForRole, stagesForRole } from './roleAccess.js'

test('operador y controlador entran solo a su pantalla, incluso por URL directa', () => {
  for (const [role, home, stages] of [['operador', '/picking', [0]], ['controlador', '/controles', [1, 2]], ['palletizador', '/pallets', [4]]]) {
    assert.equal(homeForRole(role), home)
    assert.deepEqual(stagesForRole(role), stages)
    for (const path of ['/', '/operacion', '/upload', '/importaciones', '/administracion', '/supervision', '/supervision/cargas', '/supervision/faltantes', '/supervision/equipo', '/monitor', '/tiempos', '/historial', '/articulos', '/exclusiones', '/control-cargas', '/picking', '/controles', '/pallets']) {
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
  assert.equal(homeForRole('administrador'), '/administracion')
  assert.equal(homeForRole('supervisor'), '/supervision')
  assert.equal(canVisit('supervisor', '/administracion'), false)
  assert.equal(canVisit('supervisor', '/configuracion'), false)
  assert.equal(canVisit('supervisor', '/supervision/cargas'), true)
  assert.deepEqual(stagesForRole('desconocido'), [])
})
