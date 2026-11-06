export const NAVIGATION = {
    adminHome: { path: '/administracion', label: 'Inicio administrativo', description: 'Accesos y estado general de la configuración del sistema.' },
    supervision: { path: '/supervision', label: 'Seguimiento en vivo', description: 'Ver el avance actual de operarios, canchas y camiones.' },
    planning: { path: '/supervision/cargas', label: 'Planificar cargas', description: 'Seleccionar repartos, simular pallets y aprobar el trabajo.' },
    shortages: { path: '/supervision/faltantes', label: 'Faltantes y autorizaciones', description: 'Revisar diferencias y autorizar salidas con faltantes.' },
    resources: { path: '/supervision/equipo', label: 'Asignar recursos', description: 'Planificar canchas semanales y refuerzos del día.' },
    monitor: { path: '/monitor', label: 'Pantalla del depósito', description: 'Tablero de avance para mostrar en una pantalla grande.' },
    timing: { path: '/tiempos', label: 'Tiempos y actividad', description: 'Auditar tiempos, tareas, errores y responsables.' },
    people: { path: '/equipo', label: 'Personal y canchas', description: 'Crear personas, asignar roles y canchas fijas.' },
    trucks: { path: '/configuracion', label: 'Camiones y capacidad', description: 'Configurar posiciones físicas y criterios del depósito.' },
    imports: { path: '/importaciones', label: 'Importaciones', description: 'Subir consolidados PDF, artículos y datos logísticos.' },
    articles: { path: '/articulos', label: 'Artículos y voz', description: 'Mantener el catálogo y las descripciones de lectura.' },
    voice: { path: '/frases-voz', label: 'Frases y comandos de voz', description: 'Configurar lo que dice y entiende la aplicación.' },
    pallets: { path: '/reglas-pallets', label: 'Reglas del mezclador', description: 'Definir calibres, bases y compatibilidad de pallets.' },
    exclusions: { path: '/exclusiones', label: 'Exclusiones', description: 'Administrar productos o reglas excluidas del proceso.' },
    previousLoads: { path: '/administracion/cargas-anteriores', label: 'Cargas anteriores', description: 'Consultar estados y anular armados históricos incompletos.' },
    reports: { path: '/operacion', label: 'Reportes operativos', description: 'Consultar picking por cancha, reparto, pallets y controles.' },
    dashboard: { path: '/', label: 'Dashboard histórico', description: 'Analizar indicadores acumulados y evolución de la operación.' },
    history: { path: '/historial', label: 'Historial de archivos', description: 'Consultar PDFs importados y sus procesos anteriores.' },
}

export const ADMIN_GROUPS = [
    ['Inicio', ['adminHome']],
    ['Operación y supervisión', ['supervision', 'planning', 'shortages', 'resources', 'monitor', 'timing']],
    ['Personas y configuración', ['people', 'trucks', 'articles', 'voice', 'pallets', 'exclusions']],
    ['Carga de datos', ['imports']],
    ['Reportes e historial', ['reports', 'dashboard', 'previousLoads', 'history']],
]

export const SUPERVISOR_GROUPS = [
    ['Inicio', ['supervision']],
    ['Operación', ['planning', 'shortages', 'resources', 'monitor', 'timing']],
    ['Datos de consulta', ['articles', 'imports']],
    ['Reportes e historial', ['reports', 'dashboard', 'history']],
]

export const navigationGroups = role => role === 'administrador' ? ADMIN_GROUPS : SUPERVISOR_GROUPS
