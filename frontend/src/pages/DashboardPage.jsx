import { useEffect, useState } from 'react'
import axiosClient from '../api/axiosClient'

function DashboardPage() {
    const [metrics, setMetrics] = useState(null)

    useEffect(() => {
        async function loadMetrics() {
            try {
                const response = await axiosClient.get('/dashboard/summary')
                setMetrics(response.data)
            } catch (err) {
                console.error(err)
            }
        }
        loadMetrics()
    }, [])

    return (
        <div className="min-h-screen bg-slate-50 p-6">
            <div className="mb-8 flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-semibold text-slate-900">Dashboard operativo</h1>
                    <p className="text-slate-600">KPIs de picking, pallets completos y carga de PDF en tiempo real.</p>
                </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
                {[
                    'pdfs_procesados',
                    'repartos_procesados',
                    'camiones_procesados',
                    'pallets_completos',
                    'bultos_pick',
                    'skus_no_encontrados',
                ].map((key) => (
                    <div key={key} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                        <p className="text-sm uppercase tracking-[0.24em] text-slate-400">{key.replace(/_/g, ' ')}</p>
                        <p className="mt-4 text-3xl font-semibold text-slate-900">{metrics?.[key] ?? '...'}</p>
                    </div>
                ))}
            </div>
        </div>
    )
}

export default DashboardPage
