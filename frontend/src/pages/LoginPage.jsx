import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axiosClient from '../api/axiosClient'
import { saveAuthSession } from '../utils/auth'
import { homeForRole } from '../utils/roleAccess'

function LoginPage() {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const handleSubmit = async (event) => {
        event.preventDefault()
        setLoading(true)
        setError('')
        try {
            const response = await axiosClient.post('/auth/login', { username, password })
            saveAuthSession(response.data)
            navigate(homeForRole(response.data.user.role), { replace: true })
        } catch (err) {
            setError(err.response?.data?.error || 'Usuario o contraseña incorrectos')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gradient-to-br from-[#071A3B] via-[#0B3D91] to-[#0B0F17] px-4">
            <div className="pointer-events-none absolute -left-24 top-20 h-72 w-72 rounded-full bg-[#FFB020]/10 blur-3xl" />
            <div className="pointer-events-none absolute -right-24 bottom-20 h-80 w-80 rounded-full bg-brand-400/20 blur-3xl" />
            <div className="w-full max-w-sm">
                <div className="relative mb-6 flex justify-center">
                    <img src="/brand/lockup-negro-1x.png" srcSet="/brand/lockup-negro-1x.png 1x, /brand/lockup-negro-3x.png 3x" width="340" height="100" alt="PickearYa" className="h-20 w-auto rounded-2xl bg-[#0B0F17] px-4 py-2 shadow-xl" />
                </div>

                <div className="relative rounded-3xl bg-white p-8 shadow-2xl ring-1 ring-white/20">
                    <p className="text-xs font-bold uppercase tracking-[.2em] text-[#0B3D91]">Picking por voz</p>
                    <h1 className="mb-6 mt-1 text-2xl font-semibold text-slate-900">Ingresar a PickearYa</h1>

                    {error && (
                        <div className="mb-4 flex items-center gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                            </svg>
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <label className="block">
                            <span className="text-sm font-medium text-slate-700">Usuario</span>
                            <input
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                autoComplete="username"
                                className="mt-1.5 w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                            />
                        </label>
                        <label className="block">
                            <span className="text-sm font-medium text-slate-700">Contraseña</span>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                autoComplete="current-password"
                                className="mt-1.5 w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                            />
                        </label>
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full rounded-2xl bg-brand-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-600 disabled:opacity-60"
                        >
                            {loading ? 'Ingresando...' : 'Ingresar'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}

export default LoginPage
