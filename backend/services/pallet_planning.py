"""Read-only, deterministic pallet estimate. Never rewrites picking quantities."""
from fractions import Fraction


def cross_court_compatible(pallet, reference):
    if not pallet['items']:
        return True
    base = pallet['items'][0]
    base_family, family = base.get('stack_family'), reference.get('stack_family')
    if not base_family or not family:
        return False
    if reference.get('must_be_bottom') and family != base_family:
        return False
    allowed = set(base.get('allowed_above') or [])
    return family == base_family or '*' in allowed or family in allowed


def plan_for_capacity(rows, capacity, mix_courts=False, compact_load_ids=None):
    """Keep courts separate unless requested or needed to fit the truck."""
    if type(mix_courts) is not bool:
        raise ValueError('La mezcla entre canchas debe ser verdadero o falso.')
    rows = list(rows)
    separate = simulate_pallets(rows, capacity, False, compact_load_ids)
    required = not separate['fits_estimate']
    result = simulate_pallets(rows, capacity, True, compact_load_ids) if mix_courts or required else separate
    result.update(separate_pallets=separate['total_pallets'], automatic_mix=required,
                  saved_positions=separate['total_pallets'] - result['total_pallets'])
    return result


def simulate_pallets(rows, capacity, mix_courts=False, compact_load_ids=None):
    if type(capacity) is not int or capacity <= 0:
        raise ValueError('La capacidad debe ser una cantidad entera positiva de pallets físicos.')
    if type(mix_courts) is not bool:
        raise ValueError('La mezcla entre canchas debe ser verdadero o falso.')
    rows = list(rows)
    compact_load_ids = [] if compact_load_ids is None else compact_load_ids
    if not isinstance(compact_load_ids, list) or any(type(n) is not int for n in compact_load_ids):
        raise ValueError('Indicá los repartos de supermercado con identificadores válidos.')
    if not set(compact_load_ids) <= {r['load_id'] for r in rows}:
        raise ValueError('Un reparto de supermercado no pertenece a la carga seleccionada.')
    compact = set(compact_load_ids)
    full, mixed, tasks = [], [], []
    pieces = []
    full_count = 0
    for order, source in enumerate(rows, 1):
        row = dict(source)
        for key in ('bultos', 'unidades'):
            if type(row.get(key)) is not int or row[key] < 0:
                raise ValueError(f'Cantidad inválida para SKU {row.get("sku")}.')
        bpp, upb = row.get('bultos_por_pallet'), row.get('unidades_por_bulto')
        if type(bpp) is not int or bpp <= 0 or type(upb) is not int or upb <= 0:
            raise ValueError(f'Falta capacidad válida en el catálogo para SKU {row.get("sku")}.')
        count, remainder = divmod(row['bultos'], bpp)
        reference = {key: row.get(key) for key in ('load_id', 'reparto', 'court', 'sku', 'descripcion',
            'calibre', 'stack_family', 'stack_family_name', 'must_be_bottom', 'base_priority', 'allowed_above',
            'cases_per_layer', 'max_layers')}
        reference['order'] = order
        reference['assembly_mode'] = 'compact' if row['load_id'] in compact else 'normal'
        if count:
            full.append(dict(reference, id=f'F{len(full)+1:03}', pallets=count, bultos=count*bpp, bultos_por_pallet=bpp))
            full_count += count
        tasks.append(dict(reference, bultos=remainder, unidades=row['unidades']))
        # Place integer bultos first, then integer units. No fractional case is invented.
        for field, amount, size in [('bultos', remainder, Fraction(1, bpp)),
                                    ('unidades', row['unidades'], Fraction(1, bpp*upb))]:
            pieces.append((reference, field, amount, size))
    # Stable/heavy configured bases are allocated first. Picking tasks retain source order.
    pieces.sort(key=lambda p: (p[0]['load_id'], -p[0].get('base_priority', 0),
        -p[3] if p[0]['load_id'] in compact else 0, p[0]['order']))
    for reference, field, amount, size in pieces:
        order = reference['order']
        while amount:
            pallet = next((p for p in mixed
                if p['load_id'] == reference['load_id']
                and (p['court'] == reference['court'] or ((mix_courts or reference['load_id'] in compact) and cross_court_compatible(p, reference)))
                and 1-p['used'] >= size), None)
            if pallet is None:
                pallet = dict(id=f'M{len(mixed)+1:03}', load_id=reference['load_id'], reparto=reference['reparto'],
                    assembly_mode=reference['assembly_mode'], court=reference['court'], used=Fraction(0), items=[])
                mixed.append(pallet)
            quantity = min(amount, int((1-pallet['used']) // size))
            item = next((i for i in pallet['items'] if i['order'] == order), None)
            if item is None:
                item = dict(reference, bultos=0, unidades=0)
                pallet['items'].append(item)
            item[field] += quantity
            pallet['used'] += quantity*size
            amount -= quantity
    for pallet in mixed:
        pallet['occupancy'] = round(float(pallet.pop('used')), 6)
        pallet['courts'] = sorted({i['court'] for i in pallet['items']})
        pallet['shared'] = len(pallet['courts']) > 1
        pallet['layers'] = [dict(position=n+1, placement='base' if n == 0 else 'arriba', **item)
            for n, item in enumerate(pallet['items'])]
        del pallet['court']
    total = full_count + len(mixed)
    load_plans = []
    for load_id in dict.fromkeys(r['load_id'] for r in rows):
        own_full = [p for p in full if p['load_id'] == load_id]
        own_mixed = [p for p in mixed if p['load_id'] == load_id]
        load_plans.append(dict(load_id=load_id, reparto=next(r['reparto'] for r in rows if r['load_id']==load_id),
            assembly_mode='compact' if load_id in compact else 'normal', full_count=sum(p['pallets'] for p in own_full),
            mixed_count=len(own_mixed), total_pallets=sum(p['pallets'] for p in own_full)+len(own_mixed),
            pallet_ids=[p['id'] for p in own_full+own_mixed]))
    missing_rules = sorted({(r.get('calibre') or 'SIN CALIBRE') for r in rows
        if (r.get('bultos') or r.get('unidades')) and not r.get('stack_family')})
    return dict(capacity=capacity, mix_courts=mix_courts, full_pallets=full,
                separation_policy='reparto_v1', compact_load_ids=sorted(compact), load_plans=load_plans,
                picking_tasks=tasks, mixed_pallets=mixed, full_count=full_count,
                mixed_count=len(mixed), total_pallets=total, free_positions=max(0, capacity-total),
                excess_positions=max(0, total-capacity), fits_estimate=total <= capacity,
                missing_caliber_rules=missing_rules, status='simulation', method='caliber_first_fit_per_load',
                warning='Estimación por equivalencia de bultos y reglas de calibre. Requiere revisión física de altura, peso y estabilidad por el supervisor.')
