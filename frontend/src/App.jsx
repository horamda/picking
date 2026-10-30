import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { getStoredUser, clearAuthSession } from './utils/auth'
import AdminPage from './pages/AdminPage'
import TimingPage from './pages/TimingPage'
import DepotMonitorPage from './pages/DepotMonitorPage'
import WarehousePage from './pages/WarehousePage'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ImportsPage from './pages/ImportsPage'
import ArticlesPage from './pages/ArticlesPage'
import HistoryPage from './pages/HistoryPage'
import OperationsPage from './pages/OperationsPage'
import LoadControlPage from './pages/LoadControlPage'
import ExclusionsPage from './pages/ExclusionsPage'
import axiosClient from './api/axiosClient'
import ProtectedRoute from './components/ProtectedRoute'
import Sidebar from './components/Sidebar'
import ThemeSwitch from './components/ThemeSwitch'

function App() {
    const monitor = useLocation().pathname === "/monitor"
    const navigate = useNavigate()
    const user = getStoredUser()
    const worker = ['operador', 'palletizador', 'controlador'].includes(user?.role)
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [runtime, setRuntime] = useState(null)
    useEffect(() => { axiosClient.get('/runtime-config').then(r => setRuntime(r.data)).catch(() => {}) }, [])

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900">
            <ThemeSwitch />
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route
                    path="/*"
                    element={
                        <ProtectedRoute>
                            <div className="flex min-h-screen">
                                {!monitor && !worker && <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />}
                                {sidebarOpen && !worker && (
                                    <div
                                        className="fixed inset-0 z-20 bg-black/40 xl:hidden"
                                        onClick={() => setSidebarOpen(false)}
                                    />
                                )}
                                <div className="flex min-h-screen min-w-0 flex-1 flex-col">
                                    {worker && <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-white px-4 py-2"><div><p className="font-semibold">Del Palacio · {user.role === 'controlador' ? 'Control de cargas' : user.role === 'palletizador' ? 'Pallets completos' : 'Mi picking'}</p><p className="text-sm text-slate-500">{user.username}</p></div><button className="min-h-12 rounded-xl border px-4" onClick={() => { clearAuthSession(); navigate('/login', { replace: true }) }}>Cerrar sesión</button></header>}
                                    <header className={`${monitor || worker ? "hidden" : "flex"} items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 xl:hidden`}>
                                        <button
                                            type="button"
                                            onClick={() => setSidebarOpen(true)}
                                            className="rounded-xl p-2 text-slate-600 hover:bg-slate-100"
                                            aria-label="Abrir menu"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                                            </svg>
                                        </button>
                                        <span className="text-base font-semibold text-slate-900">Picking Analytics</span>
                                    </header>
                                    <main className="min-w-0 flex-1">
                                        {runtime?.mode === 'prueba' && runtime.shared_database && <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">Modo prueba: conectado a la base de Railway. Los cambios se guardan en los datos compartidos.</div>}
                                        <Routes>
                                            <Route path="/" element={<DashboardPage />} />
                                            <Route path="/tiempos" element={<TimingPage />} />
                                            <Route path="/monitor" element={<DepotMonitorPage />} />
                                            <Route path="/supervision" element={<WarehousePage />} />
                                            <Route path="/administracion" element={<AdminPage />} />
                                            <Route path="/supervision/cargas" element={<LoadControlPage key="supervision-cargas" supervisorOnly />} />
                                            <Route path="/supervision/faltantes" element={<LoadControlPage key="supervision-faltantes" supervisorOnly initialView="shortages" />} />
                                            <Route path="/supervision/equipo" element={<WarehousePage section="team" supervision />} />
                                            <Route path="/equipo" element={<WarehousePage section="team" />} />
                                            <Route path="/configuracion" element={<WarehousePage section="settings" />} />
                                            <Route path="/pallets" element={<LoadControlPage key="pallets" palletsOnly />} />
                                            <Route path="/importaciones" element={<ImportsPage />} />
                                            <Route path="/upload" element={<Navigate to="/importaciones?tipo=pdf" replace />} />
                                            <Route path="/operacion" element={<OperationsPage />} />
                                            <Route path="/picking" element={<LoadControlPage key="picking" pickingOnly />} />
                                            <Route path="/controles" element={<LoadControlPage key="controles" controlsOnly />} />
                                            <Route path="/control-cargas" element={<Navigate to="/operacion?tab=control" replace />} />
                                            <Route path="/historial" element={<HistoryPage />} />
                                            <Route path="/articulos" element={<ArticlesPage />} />
                                            <Route path="/exclusiones" element={<ExclusionsPage />} />
                                            <Route path="*" element={<Navigate to="/" replace />} />
                                        </Routes>
                                    </main>
                                </div>
                            </div>
                        </ProtectedRoute>
                    }
                />
            </Routes>
        </div>
    )
}

export default App
