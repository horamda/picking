import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axiosClient from '../api/axiosClient'

function LoginPage() {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const navigate = useNavigate()

    const handleSubmit = async (event) => {
        event.preventDefault()
        try {
            const response = await axiosClient.post('/auth/login', { username, password })
            localStorage.setItem('token', response.data.token)
            localStorage.setItem('role', response.data.user.role)
            navigate('/')
        } catch (err) {
            setError(err.response?.data?.error || 'Error de autenticación')
        }
    }

    return (
        <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4">
            <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-xl ring-1 ring-slate-200">
                <h1 className="mb-6 text-3xl font-semibold text-slate-900">Ingresar</h1>
                {error && <div className="mb-4 rounded-xl bg-red-100 px-4 py-3 text-red-800">{error}</div>}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <label className="block">
                        <span className="text-slate-700">Usuario</span>
                        <input value={username} onChange={(e) => setUsername(e.target.value)} className="mt-2 w-full rounded-2xl border border-slate-300 px-4 py-3" />
                    </label>
                    <label className="block">
                        <span className="text-slate-700">Contraseña</span>
                        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-2 w-full rounded-2xl border border-slate-300 px-4 py-3" />
                    </label>
                    <button type="submit" className="w-full rounded-2xl bg-brand-500 px-4 py-3 text-white transition hover:bg-brand-600">Ingresar</button>
                </form>
            </div>
        </div>
    )
}

export default LoginPage
