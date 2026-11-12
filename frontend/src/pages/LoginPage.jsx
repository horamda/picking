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
        <div className="login-page flex min-h-screen items-center justify-center px-4">
            <div className="w-full max-w-sm">
                <div className="mb-6 flex items-center justify-center gap-2.5">
                    <img src="/brand/pickearya-icon.png" width="36" height="36" alt="" className="h-9 w-9 rounded-lg" />
                    <span className="text-xl font-semibold tracking-tight">PickearYa</span>
                </div>

                <div className="login-card rounded-2xl border p-7">
                    <h1 className="text-xl font-semibold">Ingresar</h1>
                    <p className="text-muted mb-6 mt-1 text-sm">Picking por voz</p>

                    {error && (
                        <div role="alert" className="note note--danger mb-4 flex items-center gap-2">
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
                                className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            />
                        </label>
                        <label className="block">
                            <span className="text-sm font-medium text-slate-700">Contraseña</span>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                autoComplete="current-password"
                                className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                            />
                        </label>
                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-primary min-h-10 w-full rounded-lg px-4 text-sm font-medium disabled:opacity-60"
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
