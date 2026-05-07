def compute_consolidation_metrics(item: dict, article=None) -> dict:
    bultos = int(item.get('bultos', 0) or 0)
    unidades = int(item.get('unidades', 0) or 0)

    if not article:
        return {
            'unidades_equivalentes': unidades,
            'bultos_equivalentes': float(bultos),
            'bultos_totales': float(bultos),
            'pallets_completos': 0,
            'bultos_pickear': bultos,
            'unidades_sueltas': unidades,
            'prioridad': 'alta' if bultos or unidades else 'normal'
        }

    unidades_por_bulto = max(int(article.unidades_por_bulto), 1)
    bultos_por_pallet = int(article.bultos_por_pallet)

    # Convertir todo a unidades para evitar errores de punto flotante
    total_unidades = bultos * unidades_por_bulto + unidades
    # bultos_equivalentes es float solo para visualización (puede tener fracción)
    bultos_equivalentes = total_unidades / unidades_por_bulto

    if bultos_por_pallet <= 0:
        bultos_pickear = total_unidades // unidades_por_bulto
        unidades_sueltas = total_unidades % unidades_por_bulto
        return {
            'unidades_equivalentes': total_unidades,
            'bultos_equivalentes': bultos_equivalentes,
            'bultos_totales': bultos_equivalentes,
            'pallets_completos': 0,
            'bultos_pickear': bultos_pickear,
            'unidades_sueltas': unidades_sueltas,
            'prioridad': 'alta' if total_unidades > 0 else 'normal'
        }

    unidades_por_pallet = bultos_por_pallet * unidades_por_bulto
    pallets_completos = total_unidades // unidades_por_pallet
    unidades_restantes = total_unidades % unidades_por_pallet
    bultos_pickear = unidades_restantes // unidades_por_bulto
    unidades_sueltas = unidades_restantes % unidades_por_bulto

    prioridad = 'alta' if pallets_completos == 0 and (bultos_pickear > 0 or unidades_sueltas > 0) else 'normal'
    return {
        'unidades_equivalentes': total_unidades,
        'bultos_equivalentes': bultos_equivalentes,
        'bultos_totales': bultos_equivalentes,
        'pallets_completos': pallets_completos,
        'bultos_pickear': bultos_pickear,
        'unidades_sueltas': unidades_sueltas,
        'prioridad': prioridad
    }
