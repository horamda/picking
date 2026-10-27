export function processState(check) {
  if (!check) return 'not_started'
  if (check.status === 'done') return 'done'
  if (check.status === 'active') return check.timer_started_at ? 'running' : 'paused'
  return 'not_started'
}

export function matchesProcess(court, stages, filter) {
  return filter === 'all' || stages.some(stage =>
    processState(court.status.checks.find(check => check.stage === stage)) === filter)
}

export function filterProcessGroups(groups, stages, filter) {
  if (filter === 'all') return groups
  return groups.map(group => {
    const loads = group.loads.map(load => ({ ...load,
      canchas: load.canchas.filter(court => matchesProcess(court, stages, filter)),
    })).filter(load => load.canchas.length)
    const pending = filter === 'not_started' ? group.pending : []
    return { ...group, loads, pending, total: loads.length + pending.length,
      completed: loads.filter(load => load.canchas.every(court => court.status.done)).length }
  }).filter(group => group.total)
}
