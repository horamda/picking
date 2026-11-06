// Lectura en voz alta de la instrucción al operador (síntesis del sistema, en español).
// Vive aparte del motor de reconocimiento para no cargar Vosk en todas las pantallas.
let quietUntil = 0
let configuredRate = 1
export function setSpeechRate(value) {
  configuredRate = Math.max(0.6, Math.min(1.6, Number(value) || 1))
}
export function isSpeaking() {
  return typeof window !== 'undefined' && Boolean(window.speechSynthesis?.speaking || window.speechSynthesis?.pending || Date.now() < quietUntil)
}

export function stopSpeaking() {
  if (typeof window !== 'undefined') window.speechSynthesis?.cancel()
  quietUntil = Date.now() + 400
}

export function speak(text, onError) {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    onError?.('Este navegador no tiene lectura en voz alta disponible.')
    return
  }
  stopSpeaking()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'es-AR'
  const voices = window.speechSynthesis.getVoices()
  utterance.voice = voices.find(v => v.lang === 'es-AR') || voices.find(v => v.lang.startsWith('es')) || null
  utterance.rate = configuredRate
  utterance.onend = () => { quietUntil = Date.now() + 400 }
  utterance.onerror = event => {
    quietUntil = Date.now() + 400
    if (!['canceled', 'interrupted'].includes(event.error)) onError?.(`No se pudo leer la instrucción: ${event.error}. Revisá el volumen multimedia y la voz en español del teléfono.`)
  }
  window.speechSynthesis.resume()
  window.speechSynthesis.speak(utterance)
}
