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
    return (
        <div className="min-h-screen bg-slate-50 text-slate-900">
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route
                    path="/*"
                    element={
                        <ProtectedRoute>
                            <div className="flex min-h-screen">
                                <Sidebar />
                                <main className="flex-1 bg-slate-50 px-4 py-6 xl:px-10">
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
                        </ProtectedRoute>
                    }
                />
            </Routes>
        </div>
    )
}

export default App
