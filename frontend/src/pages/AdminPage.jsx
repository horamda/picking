import { Link } from 'react-router-dom'

const areas = [
    ['/equipo', 'Usuarios y canchas', 'Alta de personas, roles y asignación de una o varias canchas.'],
    ['/configuracion', 'Camiones y capacidad', 'Posiciones físicas de pallets y configuración del depósito.'],
    ['/articulos', 'Artículos y voz', 'Maestro activo, datos originales y descripción para voz.'],
    ['/importaciones', 'Importaciones', 'Consolidados PDF y maestro de artículos CSV.'],
    ['/', 'Dashboard', 'Reportes anteriores de la operación.'],
    ['/historial', 'Historial', 'Consulta de archivos y procesos anteriores.'],
    ['/tiempos', 'Tiempos y auditoría', 'Actividad por persona, cancha y proceso.'],
    ['/exclusiones', 'Exclusiones', 'Mantenimiento de las exclusiones del sistema.'],
]

export default function AdminPage() {
    return <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-8">
        <header><p className="text-sm text-brand-600">Del Palacio · Administración</p><h1 className="mt-1 text-2xl font-bold">Panel administrativo</h1><p className="mt-2 text-slate-600">Configuración, usuarios, catálogos e importaciones.</p></header>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{areas.map(([to, title, text]) => <Link key={to} to={to} className="rounded-2xl border bg-white p-5 hover:border-brand-500 focus:ring-2 focus:ring-brand-500"><h2 className="text-lg font-semibold">{title}</h2><p className="mt-2 text-sm text-slate-600">{text}</p></Link>)}</div>
        <section className="rounded-2xl border bg-slate-100 p-5"><h2 className="font-semibold">Operación del depósito</h2><p className="mt-2 text-sm text-slate-600">El supervisor coordina y aprueba las cargas. Controladores y operarios ingresan con sus propios usuarios a su interfaz de trabajo.</p><div className="mt-4 flex flex-wrap gap-3"><Link to="/supervision" className="min-h-12 rounded-xl bg-brand-500 px-4 py-3 text-white">Abrir supervisión</Link><Link to="/monitor" className="min-h-12 rounded-xl border bg-white px-4 py-3">Pantalla en vivo</Link><a href="/downloads/del-palacio-picking-0.14.1.apk" className="min-h-12 rounded-xl border bg-white px-4 py-3">Descargar app Android</a></div></section>
    </div>
}
