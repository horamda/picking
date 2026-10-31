import { useEffect, useState } from 'react'
import api from '../api/axiosClient'

const field = 'min-h-12 w-full rounded-xl border border-slate-300 bg-white p-3'
const button = 'min-h-12 rounded-xl border px-4 py-3 disabled:opacity-50'
function monday(offset = 0) {
    const d = new Date()
    d.setDate(d.getDate() - (d.getDay() + 6) % 7 + offset)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function WeeklyStaffing({ users }) {
    const [week, setWeek] = useState(() => monday(7))
    const [plan, setPlan] = useState(null), [draft, setDraft] = useState({})
    const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
    const workers = users.filter(u => u.active && ['operador', 'palletizador', 'controlador'].includes(u.role))
    const read = p => { setPlan(p); setDraft(Object.fromEntries(Object.entries(p.draft).map(([k, v]) => [k, v.join(', ')]))) }
    useEffect(() => {
        const controller = new AbortController()
        setPlan(null); setError(''); setMessage('')
        api.get(`/load-control/staffing/weeks/${week}`, { signal: controller.signal }).then(r => {
            if (!controller.signal.aborted) read(r.data)
        }).catch(e => { if (!controller.signal.aborted) setError(e.response?.data?.error || 'No se pudo cargar la semana.') })
        return () => controller.abort()
    }, [week])
    async function action(fn) {
        if (busy) return
        setBusy(true); setError(''); setMessage('')
        try { await fn() } catch (e) { setError(e.response?.data?.error || e.message || 'No se pudo guardar.') }
        finally { setBusy(false) }
    }
    async function save(publish) {
        const assignments = Object.fromEntries(workers.map(u => {
            const text = (draft[u.id] || '').trim()
            const values = text ? text.split(',').map(s => Number(s.trim())) : []
            if (values.some(n => !Number.isInteger(n) || n < 1)) throw new Error('Ingresá números de cancha positivos separados por coma.')
            return [u.id, values]
        }))
        let r = await api.put(`/load-control/staffing/weeks/${week}`, { version: plan.version, assignments })
        read(r.data)
        if (publish) {
            r = await api.post(`/load-control/staffing/weeks/${week}/publish`, { version: r.data.version })
            read(r.data)
        }
        setMessage(publish ? 'Semana publicada. Entra en vigencia en su fecha; no cambia las canchas de hoy por adelantado.' : 'Borrador guardado. Todavía no se aplica.')
    }
    return <section className="space-y-4 rounded-2xl border bg-white p-5">
        <h2 className="text-xl font-bold">Planificación semanal</h2>
        <p className="text-sm text-slate-600">Prepará las canchas de cada persona y publicá la semana. Sin un nuevo plan publicado se conservan las asignaciones actuales.</p>
        <label className="block">Lunes de la semana<input type="date" className={field} value={week} disabled={busy} onChange={e => e.target.value && setWeek(e.target.value)} /></label>
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-red-800">{error}</p>}
        {message && <p role="status" className="rounded-xl bg-emerald-50 p-3 text-emerald-800">{message}</p>}
        {plan && <>
            <p className="font-semibold">{plan.activated_at ? 'Semana activa' : plan.published ? 'Publicada · los cambios del borrador requieren volver a publicar' : 'Borrador sin publicar'}</p>
            <fieldset disabled={busy || !!plan.activated_at} className="space-y-4">
                <button className={button} onClick={() => action(async () => {
                    const d = new Date(`${week}T12:00:00`); d.setDate(d.getDate() - 7)
                    const previous = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
                    const r = await api.get(`/load-control/staffing/weeks/${previous}`)
                    if (!r.data.published) throw new Error('La semana anterior no tiene un plan publicado.')
                    setDraft(Object.fromEntries(workers.map(u => [u.id, (r.data.published[u.id] || []).join(', ')])))
                    setMessage('Semana anterior copiada al formulario. Guardá o publicá para confirmar.')
                })}>Copiar semana anterior</button>
                <div className="grid gap-3 sm:grid-cols-2">{workers.map(u => <label key={u.id}>{u.username} · {u.role}<input className={field} value={draft[u.id] || ''} placeholder="1, 2, 3" onChange={e => setDraft({ ...draft, [u.id]: e.target.value })} /></label>)}</div>
                <p className="text-sm text-slate-500">Dejá vacío para no asignar canchas a esa persona.</p>
                <div className="flex flex-wrap gap-3"><button className={button} onClick={() => action(() => save(false))}>Guardar borrador</button><button className={`${button} bg-brand-500 text-white`} onClick={() => action(() => save(true))}>Guardar y publicar</button></div>
            </fieldset>
        </>}
    </section>
}
