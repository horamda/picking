import { useEffect, useRef, useState } from 'react'
import { parseVoice } from '../voice/parseVoice'
import { startListening, voiceSupported } from '../voice/voiceEngine'
import { speak, stopSpeaking } from '../voice/speech'
import { deviceTelemetry } from '../utils/deviceTelemetry'

const secondary = 'min-h-12 touch-manipulation rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-40'

// Botón de voz para la pantalla de control. Escucha solo cuando está activado
// y entrega cada frase ya interpretada a `onCommand`.
export default function VoiceControl({ prompt, onCommand, activationPrompt }) {
    const [listening, setListening] = useState(false)
    const [heard, setHeard] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState('')
    const activationRef = useRef(null)
    const stopRef = useRef(null)
    const commandRef = useRef(onCommand)
    const automaticallySpokenRef = useRef(new Set())
    commandRef.current = onCommand

    // Cada vez que cambia el producto, el sistema lee la instrucción en voz alta.
    useEffect(() => {
        if (!listening || !prompt || automaticallySpokenRef.current.has(prompt)) return
        automaticallySpokenRef.current.add(prompt)
        speak(prompt, setError)
    }, [prompt, listening])

    useEffect(() => () => { activationRef.current?.abort(); stopRef.current?.(); stopSpeaking() }, [])

    async function toggle() {
        if (loading) return
        if (listening) {
            stopSpeaking()
            await stopRef.current?.(); stopRef.current = null
            setListening(false); deviceTelemetry('voice_stopped'); return
        }
        setError('')
        setLoading(true)
        const controller = new AbortController()
        activationRef.current = controller
        const activationStarted = performance.now()
        deviceTelemetry('voice_activation_started')
        const activation = activationPrompt === undefined ? 'Activando voz. Permití el micrófono y esperá a que termine de cargar.' : activationPrompt
        if (activation) speak(activation, setError)
        try {
            const stop = await startListening({
                signal: controller.signal,
                onStatus: value => { if (!controller.signal.aborted) setStatus(value) },
                onText: text => { const parsed = parseVoice(text); setHeard(text); deviceTelemetry(parsed.action === 'unknown' ? 'recognition_rejected' : 'recognition_accepted'); commandRef.current(parsed, text) },
                onPartial: partial => setHeard(partial),
            })
            if (controller.signal.aborted) { await stop(); return }
            stopRef.current = stop
            setListening(true)
            deviceTelemetry('voice_ready', { duration_ms: Math.round(performance.now() - activationStarted) })
        } catch (err) {
            if (!controller.signal.aborted) deviceTelemetry('voice_activation_failed', {
                duration_ms: Math.round(performance.now() - activationStarted), error_code: err.name || 'VoiceError',
            })
            if (!controller.signal.aborted) setError(err.name === 'NotAllowedError'
                ? 'Micrófono bloqueado. Permití el micrófono en la configuración de este sitio y volvé a activar voz.'
                : err.message || 'No se pudo activar la voz. Usá los botones.')
        } finally {
            if (!controller.signal.aborted) setLoading(false)
        }
    }

    if (!voiceSupported()) {
        return <p role="alert" className="text-sm text-red-700">{!window.isSecureContext ? 'Para usar voz desde el celular, abrí la dirección HTTPS. La dirección HTTP de la PC no permite micrófono.' : 'Micrófono no disponible en este navegador. Abrí el sitio en Chrome y revisá los permisos.'}</p>
    }

    return (
        <div className="rounded-xl border border-slate-200 p-3">
            <div className="flex flex-wrap items-center gap-3">
                <button type="button" className={secondary} onClick={toggle} disabled={loading}>
                    {loading ? 'Preparando voz…' : listening ? 'Parar voz' : 'Activar voz'}
                </button>
                <button type="button" className={secondary} disabled={loading} onClick={() => { setError(''); speak(prompt, setError) }}>Escuchar producto</button>
                <span className="text-sm text-slate-500" aria-live="polite">
                    {loading ? status : listening ? (heard ? `Escuché: “${heard}”` : 'Escuchando…') : 'Voz desactivada'}
                </span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Comandos: correcto, faltante, anterior, siguiente y repetir.</p>
            {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
        </div>
    )
}
