// Íconos de línea del menú, indexados por la clave de NAVIGATION.
const PATHS = {
    adminHome: 'M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z',
    supervision: 'M3 12h4l3-8 4 16 3-8h4',
    planning: 'M9 4h6v3H9zM7 5H5v16h14V5h-2M9 12h6M9 16h4',
    shortages: 'M12 4 2.5 20h19zM12 10v4M12 17v.5',
    resources: 'M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM20 20v-1.5a3.5 3.5 0 0 0-2.5-3.3M15.5 4.2a3.5 3.5 0 0 1 0 6.6',
    monitor: 'M3 5h18v11H3zM8 20h8M12 16v4',
    timing: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2',
    people: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM5 20a7 7 0 0 1 14 0',
    trucks: 'M2 6h11v10H2zM13 9h4l4 4v3h-8zM6.5 19a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3zM17.5 19a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z',
    imports: 'M12 16V4M7 9l5-5 5 5M4 20h16',
    articles: 'M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8',
    voice: 'M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3zM6 11v1a6 6 0 0 0 12 0v-1M12 18v3',
    pallets: 'M12 3 3 8l9 5 9-5zM3 12l9 5 9-5M3 16l9 5 9-5',
    exclusions: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM5.6 5.6l12.8 12.8',
    previousLoads: 'M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 8v4l3 2',
    reports: 'M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-6',
    capacityReports: 'M12 4v12M7 11l5 5 5-5M4 20h16',
    dashboard: 'M3 17l6-6 4 4 8-8M15 7h6v6',
    history: 'M6 3h8l4 4v14H6zM14 3v4h4',
    close: 'M6 6l12 12M18 6 6 18',
    arrow: 'M5 12h14M13 6l6 6-6 6',
}

export function NavIcon({ name, size = 18 }) {
    return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
        <path d={PATHS[name] || 'M12 12h.01'} />
    </svg>
}
