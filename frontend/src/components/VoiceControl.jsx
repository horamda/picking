import { useEffect, useRef, useState } from 'react'
import { parseVoice } from '../voice/parseVoice'
import { startListening, voiceSupported } from '../voice/voiceEngine'
import { speak } from '../voice/speech'

const secondary = 'min-h-12 touch-manipulation rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-40'

// Botón de voz para la pantalla de control. Escucha solo cuando está activado
// y entrega cada frase ya interpretada a `onCommand`.
export default function VoiceControl({ prompt, onCommand }) {
    const [listening, setListening] = useState(false)
    const [heard, setHeard] = useState('')
    const [error, setError] = useState('')
    const stopRef = useRef(null)
    const commandRef = useRef(onCommand)
    commandRef.current = onCommand

    // Cada vez que cambia el producto, el sistema lee la instrucción en voz alta.
    useEffect(() => { if (listening && prompt) speak(prompt) }, [prompt, listening])

    useEffect(() => () => { stopRef.current?.() }, [])

    async function toggle() {
        if (listening) {
            await stopRef.current?.(); stopRef.current = null
            setListening(false); return
        }
        setError('')
        try {
            stopRef.current = await startListening({
                onText: text => { setHeard(text); commandRef.current(parseVoice(text), text) },
                onPartial: partial => setHeard(partial),
            })
            setListening(true)
        } catch (err) {
            setError(err.message || 'No se pudo activar la voz. Usá los botones.')
        }
    }

    if (!voiceSupported()) {
        return <p className="text-sm text-slate-500">Voz no disponible en este navegador. Usá los botones.</p>
    }

    return (
        <div className="rounded-xl border border-slate-200 p-3">
            <div className="flex flex-wrap items-center gap-3">
                <button type="button" className={secondary} onClick={toggle}>
                    {listening ? 'Parar voz' : 'Activar voz'}
                </button>
                <span className="text-sm text-slate-500" aria-live="polite">
                    {listening ? (heard ? `Escuché: “${heard}”` : 'Escuchando…') : 'Voz desactivada'}
                </span>
            </div>
            {error && <p className="mt-2 text-sm text-red-700">{error}</p>}
        </div>
    )
}
