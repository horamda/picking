export function getToken() {
    return localStorage.getItem('token')
}

export function getStoredUser() {
    const raw = localStorage.getItem('user')
    if (!raw) return null
    try {
        return JSON.parse(raw)
    } catch {
        return null
    }
}

export function saveAuthSession({ token, user }) {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    localStorage.setItem('role', user.role)
}

export function clearAuthSession() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('role')
}

export function isTokenExpired(token) {
    if (!token) return true
    try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
        const padded = base64.padEnd(base64.length + ((4 - base64.length % 4) % 4), '=')
        const payload = JSON.parse(atob(padded))
        if (!payload.exp) return false
        return payload.exp * 1000 <= Date.now()
    } catch {
        return true
    }
}
