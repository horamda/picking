export const isManager = role => ['administrador', 'supervisor'].includes(role)
export const homeForRole = role => ({ operador: '/picking', palletizador: '/pallets', controlador: '/controles', administrador: '/administracion', supervisor: '/supervision' }[role] || '/login')
export const stagesForRole = role => role === 'operador' ? [0] : role === 'palletizador' ? [4] : role === 'controlador' ? [1, 2] : isManager(role) ? [0, 1, 2, 4] : []
export function canVisit(role, path) {
  if (['operador', 'controlador', 'palletizador'].includes(role)) return path === homeForRole(role)
  if (role === 'administrador') return true
  if (role === 'supervisor') return !['/administracion', '/configuracion', '/exclusiones'].includes(path)
  return false
}
