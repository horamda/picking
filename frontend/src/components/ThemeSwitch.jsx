import { useState } from 'react'

export function applyStoredTheme() {
    const theme = localStorage.getItem('picking-theme') || 'light'
    document.documentElement.dataset.theme = theme
    return theme
}

export default function ThemeSwitch() {
    const [theme, setTheme] = useState(applyStoredTheme)
    return <div className="flex justify-end border-b bg-white px-4 py-2"><label className="flex items-center gap-2 text-sm">Apariencia<select aria-label="Apariencia" className="min-h-10 rounded-lg border bg-white px-3" value={theme} onChange={e => {
        localStorage.setItem('picking-theme', e.target.value)
        document.documentElement.dataset.theme = e.target.value
        setTheme(e.target.value)
    }}><option value="light">Modo claro</option><option value="dark">Modo oscuro</option></select></label></div>
}
