import { NavLink, useNavigate } from 'react-router-dom'
import { clearAuthSession, getStoredUser } from '../utils/auth'
import { homeForRole } from '../utils/roleAccess'
import { NAVIGATION, navigationGroups } from '../utils/navigation'

const MenuIcon = () => <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-current opacity-50" aria-hidden="true" />

function Brand({ home, onClose }) {
    return <NavLink to={home} onClick={onClose} className="mb-6 block rounded-xl bg-[#0B0F17] p-2 focus:ring-2 focus:ring-[#FFB020]" aria-label="PickearYa · Volver al inicio">
        <img src="/brand/lockup-negro-1x.png" srcSet="/brand/lockup-negro-1x.png 1x, /brand/lockup-negro-3x.png 3x" width="340" height="100" alt="PickearYa" className="h-10 w-auto max-w-full object-contain" />
    </NavLink>
}

function SidebarContent({ onClose }) {
    const navigate = useNavigate()
    const user = getStoredUser()
    const groups = navigationGroups(user?.role)
    function logout() { clearAuthSession(); onClose?.(); navigate('/login', { replace: true }) }
    return <div className="flex min-h-full flex-col">
        <div className="flex items-start justify-between gap-2"><Brand home={homeForRole(user?.role)} onClose={onClose} />{onClose && <button type="button" onClick={onClose} className="rounded-xl p-2 text-white/70 hover:bg-white/10" aria-label="Cerrar menú">×</button>}</div>
        <nav className="flex-1 space-y-5" aria-label="Navegación principal">
            {groups.map(([title, keys]) => <section key={title}><h2 className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-white/60">{title}</h2><div className="space-y-1">{keys.map(key => NAVIGATION[key]).map(item => <NavLink key={item.path} to={item.path} end onClick={onClose} title={item.description} className={({ isActive }) => `group flex min-h-11 items-start gap-2.5 rounded-xl px-3 py-2.5 text-sm transition-colors ${isActive ? 'bg-[#FFB020] text-[#0B0F17]' : 'text-white/80 hover:bg-white/10 hover:text-white'}`}>{({ isActive }) => <><MenuIcon /><span className="min-w-0"><span className="block font-medium leading-4">{item.label}</span>{isActive && <span className="mt-0.5 block text-[11px] leading-4 opacity-80">{item.description}</span>}</span></>}</NavLink>)}</div></section>)}
        </nav>
        <div className="mt-6 border-t border-white/15 pt-4"><p className="truncate text-sm font-medium text-white">{user?.username || 'Usuario'}</p><p className="truncate text-xs capitalize text-white/50">{user?.role || 'sin rol'}</p><button type="button" onClick={logout} className="mt-3 w-full rounded-xl border border-white/20 px-3 py-2 text-sm font-medium text-white/80 hover:bg-white/10">Cerrar sesión</button></div>
    </div>
}

export default function Sidebar({ isOpen, onClose }) {
    return <><aside className="admin-sidebar hidden w-72 shrink-0 overflow-y-auto p-5 xl:block"><SidebarContent /></aside><aside aria-hidden={!isOpen} inert={!isOpen ? '' : undefined} className={`admin-sidebar fixed inset-y-0 left-0 z-30 w-72 overflow-y-auto p-5 transition-transform duration-200 xl:hidden ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}><SidebarContent onClose={onClose} /></aside></>
}
