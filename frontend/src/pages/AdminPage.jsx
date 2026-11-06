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
        <header className="rounded-3xl border border-brand-100 bg-brand-50 p-5 sm:p-7"><p className="text-sm font-semibold text-brand-600">Del Palacio · Administración</p><h1 className="mt-1 text-3xl font-bold">Inicio del sistema</h1><p className="mt-2 max-w-3xl text-slate-600">Elegí una tarea. La operación diaria, la configuración y los reportes están separados para que siempre sepas dónde trabajar.</p><div className="mt-5 flex flex-wrap gap-3"><Link to="/supervision" className="min-h-12 rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white">Abrir supervisión en vivo</Link><Link to="/supervision/cargas" className="min-h-12 rounded-xl border bg-white px-5 py-3 font-semibold">Planificar cargas</Link><Link to="/monitor" className="min-h-12 rounded-xl border bg-white px-5 py-3 font-semibold">Pantalla del depósito</Link></div></header>
        {visibleGroups.map(([title, keys]) => <section key={title}><div className="mb-3"><h2 className="text-lg font-bold">{title}</h2><p className="text-sm text-slate-500">{groupDescriptions[title]}</p></div><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{keys.map(key => NAVIGATION[key]).map(item => <Link key={item.path} to={item.path} className="group rounded-2xl border bg-white p-4 transition hover:border-brand-500 hover:shadow-sm focus:ring-2 focus:ring-brand-500"><div className="flex items-center justify-between gap-3"><h3 className="font-semibold group-hover:text-brand-600">{item.label}</h3><span aria-hidden="true" className="text-slate-400">→</span></div><p className="mt-2 text-sm leading-5 text-slate-600">{item.description}</p></Link>)}</div></section>)}
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-slate-100 p-4"><div><h2 className="font-semibold">Aplicación Android</h2><p className="text-sm text-slate-600">Interfaz móvil para pickeadores, pallets completos y controladores.</p></div><a href="/downloads/del-palacio-picking-0.18.0.apk" className="min-h-12 rounded-xl border bg-white px-4 py-3 font-semibold">Descargar APK</a></section>
    </div>
}
