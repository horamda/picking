// Motor de voz en el dispositivo (Vosk en WebAssembly). El audio no sale del equipo.
// El modelo en español se sirve desde el propio sitio (ver README: "Modelo de voz").
import { VOICE_VOCABULARY } from './parseVoice.js'

const MODEL_URL = import.meta.env.VITE_VOICE_MODEL_URL || '/voice/model.tar.gz'

let modelPromise = null

export function voiceSupported() {
  return typeof window !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia) && typeof AudioContext !== 'undefined'
}

export function loadVoiceModel() {
  if (!modelPromise) {
    modelPromise = import('vosk-browser').then(({ createModel }) => createModel(MODEL_URL, -1)).catch(err => {
      modelPromise = null // permite reintentar
      throw new Error(`No se pudo cargar el modelo de voz (${err?.message || 'sin detalle'}).`)
    })
  }
  return modelPromise
}

// Escucha continua restringida al vocabulario de la pantalla (números, comandos y unidades).
// Devuelve una función para detener la escucha.
export async function startListening({ onText, onPartial }) {
  const model = await loadVoiceModel()
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  })
  const context = new AudioContext()
  const grammar = JSON.stringify([...VOICE_VOCABULARY, '[unk]'])
  const recognizer = new model.KaldiRecognizer(context.sampleRate, grammar)

  recognizer.on('result', message => {
    const text = message?.result?.text
    if (text) onText(text)
  })
  recognizer.on('partialresult', message => {
    const partial = message?.result?.partial
    if (partial && onPartial) onPartial(partial)
  })

  const source = context.createMediaStreamSource(stream)
  // ScriptProcessor está deprecado pero es el que soporta vosk-browser@0.0.8 sin worklet propio.
  const processor = context.createScriptProcessor(4096, 1, 1)
  processor.onaudioprocess = event => {
    recognizer.acceptWaveformFloat(event.inputBuffer.getChannelData(0), context.sampleRate)
  }
  // Conectado a una ganancia en cero: algunos navegadores no disparan el proceso sin salida,
  // pero no queremos que el micrófono suene por el parlante.
  const silence = context.createGain()
  silence.gain.value = 0
  source.connect(processor)
  processor.connect(silence)
  silence.connect(context.destination)

  return async function stop() {
    processor.disconnect()
    silence.disconnect()
    source.disconnect()
    stream.getTracks().forEach(track => track.stop())
    recognizer.remove()
    await context.close()
  }
}
