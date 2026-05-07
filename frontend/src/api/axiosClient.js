import axios from 'axios'
import { clearAuthSession } from '../utils/auth'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const axiosClient = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json',
    },
})

axiosClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

axiosClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && window.location.pathname !== '/login') {
            clearAuthSession()
            window.location.assign('/login')
        }
        return Promise.reject(error)
    }
)

export default axiosClient
