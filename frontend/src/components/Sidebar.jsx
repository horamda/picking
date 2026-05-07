import { NavLink } from 'react-router-dom'

const navItems = [
    { label: 'Dashboard', path: '/' },
    { label: 'Carga PDF', path: '/upload' },
    { label: 'Operacion', path: '/operacion' },
    { label: 'Historial', path: '/historial' },
    { label: 'Articulos', path: '/articulos' },
    { label: 'Exclusiones', path: '/exclusiones' },
]

function Sidebar() {
    return (
        <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white p-6 xl:block">
            <div className="mb-10">
                <h2 className="text-xl font-semibold text-slate-900">Picking Analytics</h2>
                <p className="mt-2 text-sm text-slate-500">Control logistico y analisis de pallets.</p>
            </div>
            <nav className="space-y-2">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) =>
                            `block rounded-2xl px-4 py-3 text-sm font-medium ${isActive ? 'bg-brand-500 text-white' : 'text-slate-700 hover:bg-slate-100'}`
                        }
                    >
                        {item.label}
                    </NavLink>
                ))}
            </nav>
        </aside>
    )
}

export default Sidebar
