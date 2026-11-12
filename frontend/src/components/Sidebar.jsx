import { NavLink, useNavigate } from 'react-router-dom'
import { clearAuthSession, getStoredUser } from '../utils/auth'
import { homeForRole } from '../utils/roleAccess'
import { NAVIGATION, navigationGroups } from '../utils/navigation'
import { NavIcon } from './NavIcon'

function Brand({ home, onClose }) {
    return <NavLink to={home} onClick={onClose} className="flex min-h-10 items-center gap-2.5 rounded-lg px-2" aria-label="PickearYa · Volver al inicio">
        <img src="/brand/pickearya-icon.png" width="28" height="28" alt="" className="h-7 w-7 rounded-md" />
        <span className="text-[15px] font-semibold tracking-tight">PickearYa</span>
    </NavLink>
}

function SidebarContent({ onClose }) {
    const navigate = useNavigate()
    const user = getStoredUser()
    const groups = navigationGroups(user?.role)
    function logout() { clearAuthSession(); onClose?.(); navigate('/login', { replace: true }) }
    return <div className="flex min-h-full flex-col gap-5">
        <div className="flex items-center justify-between gap-2">
            <Brand home={homeForRole(user?.role)} onClose={onClose} />
            {onClose && <button type="button" onClick={onClose} className="nav-item flex h-10 w-10 items-center justify-center rounded-lg" aria-label="Cerrar menú"><NavIcon name="close" /></button>}
        </div>
        <nav className="flex-1 space-y-[18px]" aria-label="Navegación principal">
            {groups.map(([title, keys]) => <section key={title}>
                <h2 className="nav-group-title mb-1 px-2.5 text-xs font-medium">{title}</h2>
                <div className="space-y-0.5">
                    {keys.map(key => <NavLink key={key} to={NAVIGATION[key].path} end onClick={onClose} title={NAVIGATION[key].description} className="nav-item flex min-h-10 items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm leading-5 transition-colors">
                        <NavIcon name={key} />
                        <span className="min-w-0">{NAVIGATION[key].label}</span>
                    </NavLink>)}
                </div>
            </section>)}
        </nav>
        <div className="nav-footer flex items-center justify-between gap-2 border-t px-2 pt-3.5">
            <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user?.username || 'Usuario'}</p>
                <p className="nav-group-title truncate text-[13px] capitalize">{user?.role || 'sin rol'}</p>
            </div>
            <button type="button" onClick={logout} className="btn-quiet shrink-0 rounded-lg px-3 text-[13px]">Cerrar sesión</button>
        </div>
    </div>
}

export default function Sidebar({ isOpen, onClose }) {
    return <>
        <aside className="admin-sidebar sticky top-12 hidden h-[calc(100vh-3rem)] w-64 shrink-0 overflow-y-auto px-3 py-5 xl:block"><SidebarContent /></aside>
        <aside aria-hidden={!isOpen} inert={!isOpen ? '' : undefined} className={`admin-sidebar fixed bottom-0 left-0 top-12 z-30 w-72 max-w-[85vw] overflow-y-auto px-3 py-5 transition-transform duration-200 xl:hidden ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}><SidebarContent onClose={onClose} /></aside>
    </>
}
