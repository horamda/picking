// Lectura en voz alta de la instrucción al operador (síntesis del sistema, en español).
// Vive aparte del motor de reconocimiento para no cargar Vosk en todas las pantallas.
export function speak(text) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'es-AR'
  utterance.rate = 1
  window.speechSynthesis.speak(utterance)
}
