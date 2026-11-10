import api from '../api/axiosClient'

// Best effort only: diagnostics must never delay or block voice/picking.
export function deviceTelemetry(event, details = {}) {
    const payload = { event, platform: 'web', client_version: String(import.meta.env.VITE_APP_VERSION || '') }
    if (Number.isInteger(details.duration_ms)) payload.duration_ms = details.duration_ms
    if (details.error_code) payload.error_code = String(details.error_code).replace(/[^A-Za-z0-9_.-]/g, '_').slice(0, 80)
    api.post('/load-control/device-events', payload, { timeout: 3000 }).catch(() => {})
}
