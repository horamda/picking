// Motor de voz en el dispositivo (Vosk en WebAssembly). El audio no sale del equipo.
// El modelo en español se sirve desde el propio sitio (ver README: "Modelo de voz").
import { VOICE_VOCABULARY } from './parseVoice.js'
import { isSpeaking } from './speech.js'

const MODEL_URL = import.meta.env.VITE_VOICE_MODEL_URL || '/voice/model.tar.gz'

let modelPromise = null

export function voiceSupported() {
  return typeof window !== 'undefined' && Boolean(navigator.mediaDevices?.getUserMedia) && typeof AudioContext !== 'undefined'
}

export function loadVoiceModel() {
  if (!modelPromise) {
    modelPromise = import('vosk-browser').then(({ Model }) => new Promise((resolve, reject) => {
      const model = new Model(new URL(MODEL_URL, window.location.href).href, 0)
      const timer = setTimeout(() => fail(new Error('La carga superó dos minutos. Revisá la conexión y reintentá.')), 120000)
      let settled = false
      function fail(error) {
        if (settled) return
        settled = true
        clearTimeout(timer)
        model.terminate()
        reject(error)
      }
      model.on('error', message => fail(new Error(message?.error || 'Error del modelo de voz')))
      model.on('load', message => {
        if (settled) return
        if (!message.result) { fail(new Error('No se pudo abrir el modelo.')); return }
        settled = true
        clearTimeout(timer)
        resolve(model)
      })
    })).catch(err => {
      modelPromise = null // permite reintentar
      throw new Error(`No se pudo cargar el modelo de voz (${err?.message || 'sin detalle'}).`)
    })
  }
  return modelPromise
}

// Escucha continua restringida al vocabulario de la pantalla (números, comandos y unidades).
// Devuelve una función para detener la escucha.
export async function startListening({ onText, onPartial, onStatus = () => {}, signal }) {
  // Crear/reanudar desde el toque, antes de esperar la descarga del modelo.
  const context = new AudioContext()
  let stream, recognizer, source, processor, silence
  let stopped = false
  const onAbort = () => { void stop() }
  signal?.addEventListener('abort', onAbort, { once: true })
  async function stop() {
    if (stopped) return
    stopped = true
    signal?.removeEventListener('abort', onAbort)
    if (processor) processor.onaudioprocess = null
    processor?.disconnect()
    silence?.disconnect()
    source?.disconnect()
    stream?.getTracks().forEach(track => track.stop())
    recognizer?.remove()
    if (context.state !== 'closed') await context.close()
  }
  const checkCancelled = () => { if (signal?.aborted) throw new DOMException('Activación cancelada', 'AbortError') }
  try {
  await context.resume()
  checkCancelled()
  onStatus('Permití el uso del micrófono…')
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  })
  checkCancelled()
  onStatus('Cargando modelo de voz (40 MB). La primera vez puede demorar…')
  const model = await loadVoiceModel()
  checkCancelled()
  const grammar = JSON.stringify([...VOICE_VOCABULARY, '[unk]'])
  recognizer = new model.KaldiRecognizer(context.sampleRate, grammar)

  recognizer.on('result', message => {
    const text = message?.result?.text
    if (text && !stopped && !isSpeaking()) onText(text)
  })
  recognizer.on('partialresult', message => {
    const partial = message?.result?.partial
    if (partial && onPartial && !stopped && !isSpeaking()) onPartial(partial)
  })

  source = context.createMediaStreamSource(stream)
  // ScriptProcessor está deprecado pero es el que soporta vosk-browser@0.0.8 sin worklet propio.
  processor = context.createScriptProcessor(4096, 1, 1)
  processor.onaudioprocess = event => {
    const audio = event.inputBuffer.getChannelData(0)
    // Enviar silencio durante la lectura evita reconocer nuestros propios comandos.
    recognizer.acceptWaveformFloat(isSpeaking() ? new Float32Array(audio.length) : audio, context.sampleRate)
  }
  // Conectado a una ganancia en cero: algunos navegadores no disparan el proceso sin salida,
  // pero no queremos que el micrófono suene por el parlante.
  silence = context.createGain()
  silence.gain.value = 0
  source.connect(processor)
  processor.connect(silence)
  silence.connect(context.destination)

  return stop
  } catch (error) {
    stream?.getTracks().forEach(track => track.stop())
    await stop()
    throw error
  }
}
