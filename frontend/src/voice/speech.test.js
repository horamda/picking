import { test } from 'node:test'
import assert from 'node:assert/strict'
import { speak, isSpeaking, stopSpeaking } from './speech.js'

test('lectura selecciona voz española y bloquea escucha mientras habla', () => {
  let utterance, cancelled = 0, resumed = 0
  globalThis.window = { speechSynthesis: {
    speaking: false, pending: false,
    cancel() { cancelled++ }, resume() { resumed++ },
    getVoices: () => [{ lang: 'en-US' }, { lang: 'es-AR' }],
    speak(value) { utterance = value },
  } }
  globalThis.SpeechSynthesisUtterance = class { constructor(text) { this.text = text } }
  try {
    let error
    speak('Agarrá dos bultos', message => { error = message })
    assert.equal(utterance.text, 'Agarrá dos bultos')
    assert.equal(utterance.voice.lang, 'es-AR')
    assert.equal(resumed, 1)
    assert.equal(isSpeaking(), true)
    utterance.onerror({ error: 'not-allowed' })
    assert.match(error, /not-allowed/)
    error = undefined
    utterance.onerror({ error: 'interrupted' })
    assert.equal(error, undefined)
    stopSpeaking()
    assert.equal(cancelled, 2)
  } finally { delete globalThis.window; delete globalThis.SpeechSynthesisUtterance }
})

test('informa cuando no hay síntesis disponible', () => {
  let error
  speak('Producto', message => { error = message })
  assert.match(error, /no tiene lectura/)
})
