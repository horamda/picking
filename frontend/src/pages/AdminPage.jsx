import { Link } from 'react-router-dom'
import { NAVIGATION, ADMIN_GROUPS } from '../utils/navigation'

const visibleGroups = ADMIN_GROUPS.filter(([title]) => title !== 'Inicio')
const groupDescriptions = {
    'Operación y supervisión': 'Trabajo diario del depósito y seguimiento en tiempo real.',
    'Personas y configuración': 'Maestros y parámetros que definen cómo trabaja el sistema.',
    'Carga de datos': 'Entrada de consolidados y catálogos externos.',
    'Reportes e historial': 'Consultas de información registrada; no modifican el trabajo actual.',
}

export default function AdminPage() {
    return <div className="mx-auto max-w-7xl space-y-7 p-4 sm:p-8">
        <header className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0B3D91] via-[#0B3478] to-[#071A3B] p-5 text-white shadow-xl sm:p-7"><div className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-[#FFB020]/15 blur-3xl" /><div className="relative grid items-center gap-6 lg:grid-cols-[1fr_320px]"><div><p className="text-sm font-semibold text-[#FFD27A]">Panel administrativo · PickearYa</p><h1 className="mt-1 text-3xl font-bold">Operación de picking por voz</h1><p className="mt-2 max-w-3xl text-white/80">Elegí una tarea. Operación diaria, configuración y reportes permanecen separados para trabajar con claridad.</p><div className="mt-5 flex flex-wrap gap-3"><Link to="/supervision" className="min-h-12 rounded-xl bg-[#FFB020] px-5 py-3 font-semibold text-[#0B0F17]">Abrir supervisión en vivo</Link><Link to="/supervision/cargas" className="min-h-12 rounded-xl border border-white/30 bg-white/10 px-5 py-3 font-semibold text-white">Planificar cargas</Link><Link to="/monitor" className="min-h-12 rounded-xl border border-white/30 bg-white/10 px-5 py-3 font-semibold text-white">Pantalla del depósito</Link></div></div><div className="hidden justify-end lg:flex"><img src="/brand/lockup-negro-1x.png" srcSet="/brand/lockup-negro-1x.png 1x, /brand/lockup-negro-3x.png 3x" width="340" height="100" alt="PickearYa" className="w-full max-w-xs rounded-2xl bg-[#0B0F17] p-4 shadow-lg" /></div></div></header>
        {visibleGroups.map(([title, keys]) => <section key={title}><div className="mb-3"><h2 className="text-lg font-bold">{title}</h2><p className="text-sm text-slate-500">{groupDescriptions[title]}</p></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{keys.map(key => NAVIGATION[key]).map(item => <Link key={item.path} to={item.path} className="group rounded-2xl border bg-white p-4 transition hover:border-brand-500 hover:shadow-sm focus:ring-2 focus:ring-brand-500"><div className="flex items-center justify-between gap-3"><h3 className="font-semibold group-hover:text-brand-600">{item.label}</h3><span aria-hidden="true" className="text-slate-400">→</span></div><p className="mt-2 text-sm leading-5 text-slate-600">{item.description}</p></Link>)}</div></section>)}
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-brand-100 bg-brand-50 p-4"><div className="flex items-center gap-3"><img src="/brand/pickearya-icon.png" alt="" className="h-14 w-14 rounded-2xl" /><div><h2 className="font-semibold">PickearYa para Android</h2><p className="text-sm text-slate-600">Interfaz móvil para pickeadores, pallets completos y controladores.</p></div></div><a href="/downloads/del-palacio-picking-0.18.0.apk" className="min-h-12 rounded-xl bg-brand-700 px-4 py-3 font-semibold text-white">Descargar APK</a></section>
    </div>
}
