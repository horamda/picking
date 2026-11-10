import { useState } from 'react'

export function applyStoredTheme() {
    let theme = 'dark'
    try {
        const stored = localStorage.getItem('picking-theme')
        if (stored === 'light' || stored === 'dark') theme = stored
    } catch (_) {
        // El tema predeterminado sigue disponible si el navegador bloquea storage.
    }
    document.documentElement.dataset.theme = theme
    return theme
}

export default function ThemeSwitch() {
    const [theme, setTheme] = useState(applyStoredTheme)
    return <div className="app-toolbar flex justify-end border-b px-4 py-2"><label className="flex items-center gap-2 text-sm font-medium">Apariencia<select aria-label="Apariencia" className="min-h-11 rounded-lg border px-3" value={theme} onChange={e => {
        const nextTheme = e.target.value === 'light' ? 'light' : 'dark'
        try { localStorage.setItem('picking-theme', nextTheme) } catch (_) { /* El selector funciona durante la sesión. */ }
        document.documentElement.dataset.theme = nextTheme
        setTheme(nextTheme)
    }}><option value="light">Modo claro</option><option value="dark">Modo oscuro</option></select></label></div>
}
