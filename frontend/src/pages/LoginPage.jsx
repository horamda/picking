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
        <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
            <div className="w-full max-w-sm">
                <div className="mb-8 flex items-center justify-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-500">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
                        </svg>
                    </div>
                    <div>
                        <p className="text-base font-semibold leading-none text-white">Picking Analytics</p>
                        <p className="mt-0.5 text-xs text-slate-400">Control logistico</p>
                    </div>
                </div>

                <div className="rounded-3xl bg-white p-8 shadow-2xl ring-1 ring-white/10">
                    <h1 className="mb-6 text-xl font-semibold text-slate-900">Ingresar al sistema</h1>

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
