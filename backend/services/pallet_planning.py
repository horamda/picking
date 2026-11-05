"""Read-only, deterministic pallet estimate. Never rewrites picking quantities."""
from fractions import Fraction
from collections import Counter


def prefers_complete_floors(reference):
    unit = str(reference.get('business_unit') or '').upper()
    caliber = str(reference.get('calibre') or '').upper()
    return 'CERVEZA' in unit and any(size in caliber for size in ('975', '1000'))


def pallet_compatible(pallet, reference, mix_courts, compact):
    if not pallet['items']:
        return True
    same_item = any(item.get('order') == reference.get('order') for item in pallet['items'])
    if same_item:
        return True
    base = pallet['items'][0]
    # Retornables de litro se arman desde la base por pisos. Un resto de piso
    # queda concentrado y no se utiliza como apoyo para otro artÃ­culo.
    if prefers_complete_floors(reference):
        return False
    if prefers_complete_floors(base) and not base.get('floor_complete'):
        return False
    if pallet['court'] == reference['court']:
        return True
    return (mix_courts or reference['load_id'] in compact) and cross_court_compatible(pallet, reference)


def cross_court_compatible(pallet, reference):
    if not pallet['items']:
        return True
    if any(item.get('order') == reference.get('order') for item in pallet['items']):
        return True
    base = pallet['items'][0]
    if (base.get('stacking_rule_pending') or not base.get('can_be_base') or not base.get('stable')
            or not base.get('floor_complete')):
        return False
    if reference.get('stacking_rule_pending') or reference.get('size_rank', 0) > base.get('size_rank', 0):
        return False
    # The approved rule is physical: stable complete base, then equal or smaller calibers.
    if base.get('business_unit') and reference.get('business_unit'):
        return True
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
        reference = {key: row.get(key) for key in ('load_id', 'reparto', 'court', 'sku', 'product_key',
            'fecha_frescura', 'descripcion',
            'calibre', 'stack_family', 'stack_family_name', 'must_be_bottom', 'base_priority', 'allowed_above',
            'cases_per_layer', 'max_layers', 'business_unit', 'can_be_base', 'stable',
            'allow_incomplete_floor', 'size_rank', 'bultos_por_piso', 'stacking_rule_pending',
            'bultos_por_pallet', 'unidades_por_bulto')}
        floor = reference.get('bultos_por_piso')
        reference['floor_complete'] = bool(reference.get('allow_incomplete_floor') or (floor and remainder >= floor
            and (not prefers_complete_floors(reference) or remainder % floor == 0)))
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
    pieces.sort(key=lambda p: (p[0]['load_id'], -p[0].get('size_rank', 0), -p[0].get('base_priority', 0),
        -p[3] if p[0]['load_id'] in compact else 0, p[0]['order']))
    for reference, field, amount, size in pieces:
        order = reference['order']
        while amount:
            pallet = next((p for p in mixed
                if p['load_id'] == reference['load_id']
                and pallet_compatible(p, reference, mix_courts, compact)
                and 1-p['used'] >= size), None)
            if pallet is None:
                pallet = dict(id=f'M{len(mixed)+1:03}', load_id=reference['load_id'], reparto=reference['reparto'],
                    assembly_mode=reference['assembly_mode'], court=reference['court'], used=Fraction(0), items=[])
                mixed.append(pallet)
            quantity = min(amount, int((1-pallet['used']) // size))
            floor = reference.get('bultos_por_piso')
            if field == 'bultos' and prefers_complete_floors(reference) and floor and amount >= floor:
                quantity = quantity - quantity % floor
                if not quantity:
                    pallet = dict(id=f'M{len(mixed)+1:03}', load_id=reference['load_id'], reparto=reference['reparto'],
                        assembly_mode=reference['assembly_mode'], court=reference['court'], used=Fraction(0), items=[])
                    mixed.append(pallet)
                    quantity = min(amount, int(Fraction(1, 1) // size))
                    quantity -= quantity % floor
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
        pallet['owner_court'] = pallet['court']
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
    missing_rules = sorted({f"{r.get('business_unit') or 'SIN UNIDAD'} / {r.get('calibre') or 'SIN CALIBRE'}"
        for r in rows if (r.get('bultos') or r.get('unidades')) and r.get('stacking_rule_pending')})
    return dict(capacity=capacity, mix_courts=mix_courts, full_pallets=full,
                separation_policy='reparto_v1', compact_load_ids=sorted(compact), load_plans=load_plans,
                picking_tasks=tasks, mixed_pallets=mixed, full_count=full_count,
                mixed_count=len(mixed), total_pallets=total, free_positions=max(0, capacity-total),
                excess_positions=max(0, total-capacity), fits_estimate=total <= capacity,
                missing_caliber_rules=missing_rules, status='simulation', method='caliber_first_fit_per_load',
                warning='Estimación por equivalencia de bultos y reglas de calibre. Requiere revisión física de altura, peso y estabilidad por el supervisor.')


def apply_manual_pallets(plan, submitted, merge_allowed_load_ids=None):
    """Validate a supervisor regrouping and assign each result to its destination court."""
    if not isinstance(submitted, list) or not submitted:
        raise ValueError('El armado manual no contiene pallets de picking.')

    def signature(item):
        return (item.get('load_id'), item.get('order'), item.get('court'),
                item.get('product_key') or str(item.get('sku')),
                item.get('bultos'), item.get('unidades'))

    allowed = set(merge_allowed_load_ids or [])
    originals = [item for pallet in plan['mixed_pallets'] for item in pallet['items']]
    available = {}
    for pallet in plan['mixed_pallets']:
        for item in pallet['items']:
            available.setdefault(signature(item), []).append((item, pallet['id']))
    expected = Counter(signature(item) for item in originals)
    received, mixed, seen_ids = Counter(), [], set()

    for index, raw in enumerate(submitted, 1):
        if not isinstance(raw, dict) or not isinstance(raw.get('items'), list) or not raw['items']:
            raise ValueError('Cada pallet debe contener al menos un artículo.')
        pallet_id = str(raw.get('id') or f'M{index:03}')
        if pallet_id in seen_ids:
            raise ValueError('Hay identificadores de pallet repetidos.')
        seen_ids.add(pallet_id)
        clean_items, source_pallet_ids = [], set()
        for candidate in raw['items']:
            key = signature(candidate)
            received[key] += 1
            pool = available.get(key, [])
            if received[key] > len(pool):
                raise ValueError('El armado manual modifica, duplica o agrega cantidades de productos.')
            original, source_pallet_id = pool[received[key] - 1]
            clean_items.append(dict(original))
            source_pallet_ids.add(source_pallet_id)
        if len({item['load_id'] for item in clean_items}) != 1:
            raise ValueError('No se pueden mezclar repartos dentro de un mismo pallet.')
        if len(source_pallet_ids) > 1 and clean_items[0]['load_id'] not in allowed:
            raise ValueError(f'El reparto {clean_items[0]["reparto"]} no permite unir pallets.')
        owner = raw.get('owner_court')
        if type(owner) is not int or owner not in {item['court'] for item in clean_items}:
            raise ValueError('La cancha responsable debe pertenecer al pallet de destino.')
        clean_items.sort(key=lambda item: (-item.get('size_rank', 0), -item.get('base_priority', 0), item['order']))
        used = sum(Fraction(item['bultos'], item['bultos_por_pallet']) +
                   Fraction(item['unidades'], item['bultos_por_pallet'] * item['unidades_por_bulto'])
                   for item in clean_items)
        if used > 1:
            raise ValueError(f'El pallet {pallet_id} supera el 100% de capacidad.')
        for item in clean_items:
            item['assigned_court'] = owner
            item['pallet_id'] = pallet_id
        mixed.append(dict(id=pallet_id, load_id=clean_items[0]['load_id'], reparto=clean_items[0]['reparto'],
                          assembly_mode=clean_items[0]['assembly_mode'], owner_court=owner,
                          occupancy=round(float(used), 6), courts=sorted({i['court'] for i in clean_items}),
                          shared=len({i['court'] for i in clean_items}) > 1, items=clean_items,
                          layers=[dict(position=n + 1, placement='base' if n == 0 else 'arriba', **item)
                                  for n, item in enumerate(clean_items)]))
    if received != expected:
        raise ValueError('El armado manual deja productos afuera o altera sus cantidades.')

    tasks = {}
    for pallet in mixed:
        for item in pallet['items']:
            key = (item['load_id'], item['assigned_court'], item.get('product_key') or item['sku'])
            task = tasks.setdefault(key, dict(item, court=item['assigned_court'], source_courts=[],
                                              bultos=0, unidades=0, pallet_ids=[]))
            task['bultos'] += item['bultos']
            task['unidades'] += item['unidades']
            if item['court'] not in task['source_courts']:
                task['source_courts'].append(item['court'])
            if pallet['id'] not in task['pallet_ids']:
                task['pallet_ids'].append(pallet['id'])

    original_mixed_count = plan['mixed_count']
    plan['mixed_pallets'] = mixed
    plan['picking_tasks'] = sorted(tasks.values(), key=lambda item: (item['load_id'], item['order'], item['sku']))
    plan['mixed_count'] = len(mixed)
    plan['total_pallets'] = plan['full_count'] + len(mixed)
    plan['free_positions'] = max(0, plan['capacity'] - plan['total_pallets'])
    plan['excess_positions'] = max(0, plan['total_pallets'] - plan['capacity'])
    plan['fits_estimate'] = plan['total_pallets'] <= plan['capacity']
    for load_plan in plan['load_plans']:
        own = [p for p in mixed if p['load_id'] == load_plan['load_id']]
        load_plan['mixed_count'] = len(own)
        load_plan['total_pallets'] = load_plan['full_count'] + len(own)
        load_plan['pallet_ids'] = ([p['id'] for p in plan['full_pallets'] if p['load_id'] == load_plan['load_id']] +
                                   [p['id'] for p in own])
    plan['manual_edition'] = True
    plan['merge_allowed_load_ids'] = sorted(allowed)
    plan['manual_saved_positions'] = original_mixed_count - len(mixed)
    return plan
