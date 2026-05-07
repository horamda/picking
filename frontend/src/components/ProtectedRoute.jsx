import { Navigate } from 'react-router-dom'
import { clearAuthSession, getToken, isTokenExpired } from '../utils/auth'

function ProtectedRoute({ children }) {
    const token = getToken()
    if (!token || isTokenExpired(token)) {
        clearAuthSession()
        return <Navigate to="/login" replace />
    }
    return children
}

export default ProtectedRoute
