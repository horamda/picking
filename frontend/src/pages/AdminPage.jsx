import { Link } from 'react-router-dom'
import { NAVIGATION, ADMIN_GROUPS } from '../utils/navigation'
import { NavIcon } from '../components/NavIcon'

const visibleGroups = ADMIN_GROUPS.filter(([title]) => title !== 'Inicio')
const groupDescriptions = {
    'Operación y supervisión': 'Trabajo diario del depósito y seguimiento en tiempo real.',
    'Personas y configuración': 'Maestros y parámetros que definen cómo trabaja el sistema.',
    'Carga de datos': 'Entrada de consolidados y catálogos externos.',
    'Reportes e historial': 'Consultas de información registrada; no modifican el trabajo actual.',
}
const action = 'inline-flex min-h-10 items-center rounded-lg px-4 text-sm font-medium'

export default function AdminPage() {
    return <div className="mx-auto max-w-6xl space-y-10 px-4 py-8 sm:px-8 sm:py-10">
        <header className="flex flex-wrap items-end justify-between gap-5">
            <div className="max-w-xl">
                <h1 className="text-[26px] font-semibold leading-8">Operación de picking por voz</h1>
                <p className="text-muted mt-2 text-[15px] leading-[22px]">Accedé a la operación, la configuración y los reportes del depósito.</p>
            </div>
            <div className="flex flex-wrap gap-2">
                <Link to="/supervision" className={`btn-primary ${action}`}>Seguimiento en vivo</Link>
                <Link to="/supervision/cargas" className={`btn-quiet ${action}`}>Planificar cargas</Link>
                <Link to="/importaciones" className={`btn-quiet ${action}`}>Importar datos</Link>
            </div>
        </header>
        {visibleGroups.map(([title, keys]) => <section key={title}>
            <div className="mb-3.5 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h2 className="text-[15px] font-semibold leading-[22px]">{title}</h2>
                <p className="text-muted text-[13px]">{groupDescriptions[title]}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {keys.map(key => <Link key={key} to={NAVIGATION[key].path} className="tile flex items-start gap-3 rounded-2xl p-4">
                    <span className="tile-icon flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"><NavIcon name={key} size={17} /></span>
                    <span className="min-w-0">
                        <span className="block text-sm font-medium">{NAVIGATION[key].label}</span>
                        <span className="text-muted mt-0.5 block text-[13px] leading-[19px]">{NAVIGATION[key].description}</span>
                    </span>
                </Link>)}
            </div>
        </section>)}
        <section className="tile flex flex-wrap items-center justify-between gap-4 rounded-2xl px-5 py-4">
            <div className="flex items-center gap-3.5">
                <img src="/brand/pickearya-icon.png" alt="" className="h-10 w-10 rounded-2xl" />
                <div>
                    <h2 className="text-sm font-medium">PickearYa para Android</h2>
                    <p className="text-muted mt-0.5 text-[13px]">Aplicación para pickeadores, pallets completos y controladores.</p>
                </div>
            </div>
            <a href="/downloads/del-palacio-picking-0.18.0.apk" className={`btn-quiet ${action} gap-2`}><NavIcon name="capacityReports" size={16} />Descargar APK</a>
        </section>
    </div>
}
