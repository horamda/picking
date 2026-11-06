import { NavLink, useNavigate } from 'react-router-dom'
import { clearAuthSession, getStoredUser } from '../utils/auth'
import { homeForRole } from '../utils/roleAccess'
import { NAVIGATION, navigationGroups } from '../utils/navigation'

const MenuIcon = () => <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-current opacity-50" aria-hidden="true" />

function Brand({ home, onClose }) {
    return <NavLink to={home} onClick={onClose} className="mb-6 flex items-center gap-2.5 rounded-xl focus:ring-2 focus:ring-brand-500" aria-label="Volver al inicio">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500 text-white"><svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0h8.25m3 0h1.125M3 14.25h11.25V6.5H3v7.75zm11.25-6.5h3l3.375 5.25v1.25H14.25v-6.5z" /></svg></div>
        <div><p className="text-sm font-semibold leading-none text-slate-900">Picking Analytics</p><p className="mt-1 text-xs text-slate-500">Inicio · Control logístico</p></div>
    </NavLink>
}

function SidebarContent({ onClose }) {
    const navigate = useNavigate()
    const user = getStoredUser()
    const groups = navigationGroups(user?.role)
    function logout() { clearAuthSession(); onClose?.(); navigate('/login', { replace: true }) }
    return <div className="flex min-h-full flex-col">
        <div className="flex items-start justify-between"><Brand home={homeForRole(user?.role)} onClose={onClose} />{onClose && <button type="button" onClick={onClose} className="rounded-xl p-2 text-slate-400 hover:bg-slate-100" aria-label="Cerrar menú">×</button>}</div>
        <nav className="flex-1 space-y-5" aria-label="Navegación principal">
            {groups.map(([title, keys]) => <section key={title}><h2 className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{title}</h2><div className="space-y-1">{keys.map(key => NAVIGATION[key]).map(item => <NavLink key={item.path} to={item.path} end onClick={onClose} title={item.description} className={({ isActive }) => `group flex min-h-10 items-start gap-2.5 rounded-xl px-3 py-2 text-sm transition-colors ${isActive ? 'bg-brand-500 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}>{({ isActive }) => <><MenuIcon /><span className="min-w-0"><span className="block font-medium leading-4">{item.label}</span>{isActive && <span className="mt-0.5 block text-[11px] leading-4 opacity-80">{item.description}</span>}</span></>}</NavLink>)}</div></section>)}
        </nav>
        <div className="mt-6 border-t border-slate-100 pt-4"><p className="truncate text-sm font-medium text-slate-800">{user?.username || 'Usuario'}</p><p className="truncate text-xs capitalize text-slate-400">{user?.role || 'sin rol'}</p><button type="button" onClick={logout} className="mt-3 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50">Cerrar sesión</button></div>
    </div>
}

export default function Sidebar({ isOpen, onClose }) {
    return <><aside className="hidden w-72 shrink-0 overflow-y-auto border-r border-slate-200 bg-white p-5 xl:block"><SidebarContent /></aside><aside aria-hidden={!isOpen} inert={!isOpen ? '' : undefined} className={`fixed inset-y-0 left-0 z-30 w-72 overflow-y-auto border-r border-slate-200 bg-white p-5 transition-transform duration-200 xl:hidden ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}><SidebarContent onClose={onClose} /></aside></>
}
