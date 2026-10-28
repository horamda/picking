export default function FullPalletInfo({ items = [] }) {
    if (!items.length) return null
    return <aside className="my-3 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-950" aria-label="Información de pallets completos">
        <p className="font-semibold">Pallets completos · Información</p>
        <ul className="my-2 space-y-1">{items.map(item => <li key={item.sku}>{item.pallets} pallets · {item.descripcion} ({item.bultos} bultos)</li>)}</ul>
        <p className="text-xs">Se registran por separado del picking de bultos y unidades sueltas.</p>
    </aside>
}
