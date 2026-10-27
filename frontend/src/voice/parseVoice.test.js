import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parseVoice, NUMBER_WORDS } from './parseVoice.js'

test('comandos básicos', () => {
  assert.deepEqual(parseVoice('Correcto'), { action: 'ok' })
  assert.deepEqual(parseVoice('faltante.'), { action: 'shortage' })
  assert.deepEqual(parseVoice('error corregido'), { action: 'corrected' })
  assert.deepEqual(parseVoice('repetir'), { action: 'repeat' })
  assert.deepEqual(parseVoice('siguiente'), { action: 'next' })
  assert.deepEqual(parseVoice('anterior'), { action: 'prev' })
})

test('cantidades con etiquetas', () => {
  assert.deepEqual(parseVoice('dos bultos tres unidades'), { action: 'quantities', bultos: 2, unidades: 3 })
  assert.deepEqual(parseVoice('una unidad'), { action: 'quantities', bultos: undefined, unidades: 1 })
})

test('cantidades sin etiquetas: primero bultos, segundo unidades', () => {
  assert.deepEqual(parseVoice('cuatro y seis'), { action: 'quantities', bultos: 4, unidades: 6 })
  assert.deepEqual(parseVoice('0 12'), { action: 'quantities', bultos: 0, unidades: 12 })
})

test('números en español', () => {
  assert.equal(NUMBER_WORDS.una, 1)
  assert.equal(NUMBER_WORDS.veintiuno, 21)
  assert.equal(NUMBER_WORDS.cincuenta, 50)
})

test('cantidades compuestas de 31 a 49', () => {
  for (const [tens, base] of [['treinta', 30], ['cuarenta', 40]]) {
    for (const [unit, value] of Object.entries(NUMBER_WORDS).filter(([, n]) => n >= 1 && n <= 9)) {
      assert.deepEqual(parseVoice(`${tens} y ${unit} bultos tres unidades`),
        { action: 'quantities', bultos: base + value, unidades: 3 })
    }
  }
  assert.deepEqual(parseVoice('treinta y dos cuarenta y nueve'),
    { action: 'quantities', bultos: 32, unidades: 49 })
  assert.deepEqual(parseVoice('cuarenta y una unidades'),
    { action: 'quantities', bultos: undefined, unidades: 41 })
  assert.deepEqual(parseVoice('treinta bultos y dos unidades'),
    { action: 'quantities', bultos: 30, unidades: 2 })
})

test('frases no reconocidas', () => {
  assert.deepEqual(parseVoice('hola que tal'), { action: 'unknown' })
  assert.deepEqual(parseVoice(''), { action: 'unknown' })
})
