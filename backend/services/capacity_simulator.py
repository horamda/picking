"""Pure capacity scenarios. It never changes planning or operational state."""
import math


def simulate_capacity(data):
    try:
        operators = int(data.get('operators'))
        hours = float(data.get('hours'))
        productivity = float(data.get('productivity'))
        demand = float(data.get('demand'))
    except (TypeError, ValueError, OverflowError):
        raise ValueError('Completá operarios, horas, productividad y demanda con números válidos.')
    if isinstance(data.get('operators'), bool) or operators != float(data.get('operators')):
        raise ValueError('La cantidad de operarios debe ser un entero.')
    if not 0 <= operators <= 10000 or not 0 <= hours <= 24 or not 0 <= productivity <= 10000 or not 0 <= demand <= 1_000_000_000:
        raise ValueError('Los valores están fuera de los límites permitidos.')
    capacity = operators * hours * productivity
    coverage = capacity / demand * 100 if demand else None
    difference = capacity - demand
    per_operator = hours * productivity
    additional = max(0, math.ceil(demand / per_operator) - operators) if per_operator else None
    required_hours = demand / (operators * productivity) if operators and productivity else None
    return dict(version=1, hypothetical=True, unit='bultos', operators=operators,
        hours=round(hours, 2), productivity=round(productivity, 2), demand=round(demand, 2),
        capacity=round(capacity, 2), coverage_pct=round(coverage, 1) if coverage is not None else None,
        difference=round(difference, 2), additional_operators=additional,
        required_hours=round(required_hours, 2) if required_hours is not None else None,
        assumptions='Escenario informativo: no modifica cargas, asignaciones ni objetivos.')
