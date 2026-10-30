import test from 'node:test'
import assert from 'node:assert/strict'
import { productCode } from './productCode.js'
test('full code preserves zeros and rejects commands and partial number words', () => {
    assert.equal(productCode('cero cuatro cero cinco uno dos'), '040512')
    assert.equal(productCode('40512'), '40512')
    assert.equal(productCode('correcto 40512'), '')
    assert.equal(productCode('cuarenta mil'), '')
    assert.equal(productCode(''), '')
})
