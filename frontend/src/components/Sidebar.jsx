import { NavLink, useNavigate } from 'react-router-dom'
import { clearAuthSession, getStoredUser } from '../utils/auth'
import { isManager, homeForRole } from '../utils/roleAccess'

const navItems = [
    {
        label: 'Dashboard',
        path: '/',
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
            </svg>
        ),
    },
    {
        label: 'Carga PDF',
        path: '/upload',
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
        ),
    },
    {
        label: 'Camiones y controles',
        path: '/operacion',
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
            </svg>
        ),
    },
    {
        label: 'Historial',
        path: '/historial',
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        ),
    },
    {
        label: 'Articulos',
        path: '/articulos',
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
            </svg>
        ),
    },
    {
        label: 'Exclusiones',
        path: '/exclusiones',
        icon: (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
        ),
    },
]

function Brand() {
    return (
        <div className="mb-8">
            <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-500">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" />
                    </svg>
                </div>
                <div>
                    <p className="text-sm font-semibold leading-none text-slate-900">Picking Analytics</p>
                    <p className="mt-0.5 text-xs text-slate-400">Control logistico</p>
                </div>
            </div>
        </div>
    )
}

function SidebarContent({ onClose }) {
    const navigate = useNavigate()
    const user = getStoredUser()
    const manager = isManager(user?.role)
    const groups = manager ? [['Depósito', [homeForRole(user?.role), '/equipo', '/operacion', '/upload']], ['Reportes', ['/', '/historial']], ...(user?.role === 'administrador' ? [['Administración', ['/configuracion', '/articulos', '/exclusiones']]] : [])] : [['Mi trabajo', [homeForRole(user?.role)]]]
    const items = [...navItems, ...[['/picking', 'Picking'], ['/pallets', 'Pallets completos'], ['/controles', 'Controles y activos'], ['/supervision', 'Supervisión'], ['/administracion', 'Administración'], ['/equipo', 'Equipo y canchas'], ['/configuracion', 'Camiones y capacidad']].map(([path, label]) => ({ ...navItems.find(i => i.path === '/operacion'), path, label }))]


    const handleLogout = () => {
        clearAuthSession()
        if (onClose) onClose()
        navigate('/login', { replace: true })
    }

    return (
        <>
            <div className="flex items-start justify-between">
                <Brand />
                {onClose && (
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-xl p-1.5 text-slate-400 hover:bg-slate-100"
                        aria-label="Cerrar menu"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                )}
            </div>
            <nav className="space-y-5" aria-label="Navegacion principal">
                {groups.map(([title, paths]) => <section key={title}>
                    <h2 className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</h2>
                    <div className="space-y-1">{paths.map(path => items.find(item => item.path === path)).map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        onClick={onClose}
                        className={({ isActive }) =>
                            `flex items-center gap-3 min-h-12 rounded-2xl px-3 py-2.5 text-sm font-medium transition-colors ${
                                isActive
                                    ? 'bg-brand-500 text-white'
                                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                            }`
                        }
                    >
                        {item.icon}
                        {item.label}
                    </NavLink>
                ))}</div></section>)}
            </nav>
            <div className="mt-8 border-t border-slate-100 pt-4">
                <div className="mb-3">
                    <p className="truncate text-sm font-medium text-slate-800">{user?.username || 'Usuario'}</p>
                    <p className="truncate text-xs text-slate-400">{user?.role || localStorage.getItem('role') || 'sin rol'}</p>
                </div>
                <button
                    type="button"
                    onClick={handleLogout}
                    className="flex w-full items-center justify-center rounded-2xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
                >
                    Cerrar sesion
                </button>
            </div>
        </>
    )
}

function Sidebar({ isOpen, onClose }) {
    return (
        <>
            <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white p-5 xl:block">
                <SidebarContent />
            </aside>
            <aside
                aria-hidden={!isOpen}
                inert={!isOpen ? '' : undefined}
                className={`fixed inset-y-0 left-0 z-30 w-64 overflow-y-auto border-r border-slate-200 bg-white p-5 transition-transform duration-200 xl:hidden ${
                    isOpen ? 'translate-x-0' : '-translate-x-full'
                }`}
            >
                <SidebarContent onClose={onClose} />
            </aside>
        </>
    )
}

export default Sidebar
