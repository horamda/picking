// Tablas del panel: solo líneas horizontales, encabezado discreto y totales sin bloques de color.
const line = 'border-b border-slate-200 px-3'
export const tableClass = 'min-w-full border-collapse text-left text-sm'
export const headerRowClass = 'text-xs font-medium text-slate-500'
export const rowClass = 'hover:bg-slate-50'
export const selectedRowClass = 'bg-brand-50'
export const cellClass = `${line} py-2.5 text-slate-700`
export const strongCellClass = `${line} py-2.5 font-medium text-slate-900`
export const numberCellClass = `${line} py-2.5 text-right tabular-nums text-slate-700`
export const strongNumberCellClass = `${line} py-2.5 text-right tabular-nums font-medium text-slate-900`
export const headerCellClass = `${line} py-2`
export const headerNumberCellClass = `${headerCellClass} text-right`
export const totalHeaderCellClass = `${line} py-2 text-right text-slate-900`
export const totalCellClass = `${line} py-2.5 text-right tabular-nums font-semibold text-slate-900`
export const totalRowClass = 'bg-slate-50 font-semibold text-slate-900'
export const totalLabelCellClass = `${line} py-2.5 text-slate-900`
export const totalNumberCellClass = `${line} py-2.5 text-right tabular-nums text-slate-900`
export const totalRowValueCellClass = `${line} py-2.5 text-right tabular-nums font-semibold text-slate-900`
