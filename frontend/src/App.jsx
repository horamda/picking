import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import UploadPage from './pages/UploadPage'
import ArticlesPage from './pages/ArticlesPage'
import HistoryPage from './pages/HistoryPage'
import OperationsPage from './pages/OperationsPage'
import ExclusionsPage from './pages/ExclusionsPage'
import ProtectedRoute from './components/ProtectedRoute'
import Sidebar from './components/Sidebar'

function App() {
    const [sidebarOpen, setSidebarOpen] = useState(false)

    return (
        <div className="min-h-screen bg-slate-50 text-slate-900">
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route
                    path="/*"
                    element={
                        <ProtectedRoute>
                            <div className="flex min-h-screen">
                                <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
                                {sidebarOpen && (
                                    <div
                                        className="fixed inset-0 z-20 bg-black/40 xl:hidden"
                                        onClick={() => setSidebarOpen(false)}
                                    />
                                )}
                                <div className="flex min-h-screen flex-1 flex-col">
                                    <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 xl:hidden">
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
                                    <main className="flex-1">
                                        <Routes>
                                            <Route path="/" element={<DashboardPage />} />
                                            <Route path="/upload" element={<UploadPage />} />
                                            <Route path="/operacion" element={<OperationsPage />} />
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
