import { Navigate, useLocation } from 'react-router-dom'
import { clearAuthSession, getToken, getStoredUser, isTokenExpired } from '../utils/auth'
import { canVisit, homeForRole } from '../utils/roleAccess'

function ProtectedRoute({ children }) {
    const { pathname } = useLocation()
    const role = getStoredUser()?.role
    const token = getToken()
    if (!token || isTokenExpired(token) || !['operador', 'controlador', 'supervisor', 'administrador', 'palletizador'].includes(role)) {
        clearAuthSession()
        return <Navigate to="/login" replace />
    }
    if (!canVisit(role, pathname)) return <Navigate to={homeForRole(role)} replace />
    return children
}

export default ProtectedRoute
