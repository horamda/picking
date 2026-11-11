import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { getStoredUser } from '../utils/auth'
import { homeForRole } from '../utils/roleAccess'
import { NAVIGATION, navigationGroups } from '../utils/navigation'

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
    const location = useLocation()
    const navigate = useNavigate()
    const user = getStoredUser()
    const groups = user ? navigationGroups(user.role) : []
    const currentEntry = Object.values(NAVIGATION).find(item => item.path === location.pathname)
    const currentGroup = groups.find(([, keys]) => keys.some(key => NAVIGATION[key]?.path === location.pathname))?.[0]
    const home = homeForRole(user?.role)
    useEffect(() => { document.title = `${currentEntry?.label || 'PickearYa'} · PickearYa` }, [currentEntry?.label])

    return <div className="app-toolbar sticky top-0 z-40 flex min-h-12 items-center justify-between gap-3 border-b px-4 py-1.5">
        <div className="min-w-0">
            {user ? <div className="flex min-w-0 items-center gap-2 text-sm">
                <Link to={home} className="shrink-0 font-semibold text-brand-600 hover:underline">PickearYa</Link>
                <span className="text-slate-400" aria-hidden="true">/</span>
                {currentGroup && <><span className="hidden text-slate-500 md:inline">{currentGroup}</span><span className="hidden text-slate-400 md:inline" aria-hidden="true">/</span></>}
                <span className="truncate font-medium">{currentEntry?.label || 'Panel operativo'}</span>
            </div> : <span className="text-sm font-semibold">PickearYa</span>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
            {user && <label className="hidden items-center gap-2 text-sm font-medium lg:flex"><span className="text-slate-500">Ir a</span><select aria-label="Ir a otra página" className="min-h-9 max-w-64 rounded-lg border px-3" value={currentEntry?.path || ''} onChange={event => event.target.value && navigate(event.target.value)}><option value="" disabled>Seleccionar página</option>{groups.map(([title, keys]) => <optgroup key={title} label={title}>{keys.map(key => NAVIGATION[key]).map(item => <option key={item.path} value={item.path}>{item.label}</option>)}</optgroup>)}</select></label>}
            <label className="flex items-center gap-2 text-sm font-medium"><span className="hidden sm:inline">Apariencia</span><select aria-label="Apariencia" className="min-h-9 rounded-lg border px-3" value={theme} onChange={event => {
                const nextTheme = event.target.value === 'light' ? 'light' : 'dark'
                try { localStorage.setItem('picking-theme', nextTheme) } catch (_) { /* El selector funciona durante la sesión. */ }
                document.documentElement.dataset.theme = nextTheme
                setTheme(nextTheme)
            }}><option value="light">Modo claro</option><option value="dark">Modo oscuro</option></select></label>
        </div>
    </div>
}
