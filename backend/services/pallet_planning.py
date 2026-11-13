"""Read-only, deterministic pallet estimate. Never rewrites picking quantities."""
from fractions import Fraction
from decimal import Decimal, InvalidOperation
import re


MODES = {'inform', 'block'}


def fraction(value, label):
    if value in (None, ''):
        return None
    try:
        result = Fraction(Decimal(str(value).replace(',', '.')))
    except (InvalidOperation, ValueError, ZeroDivisionError) as exc:
        raise ValueError(f'{label} debe ser un número válido.') from exc
    if result <= 0:
        raise ValueError(f'{label} debe ser positivo.')
    return result


def validate_configuration(configuration=None):
    source = dict(configuration or {})
    result = {}
    numeric = {
        'pallet_base_height_cm': 'La altura de la tarima',
        'reference_pallet_height_cm': 'La altura de referencia',
        'max_pallet_height_cm': 'La altura máxima',
        'empty_pallet_weight_kg': 'El peso de la tarima',
        'max_pallet_weight_kg': 'El peso máximo por pallet',
        'max_payload_kg': 'La carga útil del camión',
    }
    for key, label in numeric.items():
        result[key] = fraction(source.get(key), label)
    margin = source.get('safety_margin_pct')
    if margin in (None, ''):
        result['safety_margin_pct'] = Fraction(0)
    else:
        try:
            result['safety_margin_pct'] = Fraction(Decimal(str(margin).replace(',', '.')))
        except (InvalidOperation, ValueError, ZeroDivisionError) as exc:
            raise ValueError('El margen de seguridad debe ser un número entre 0 y 50.') from exc
        if not 0 <= result['safety_margin_pct'] <= 50:
            raise ValueError('El margen de seguridad debe estar entre 0 y 50%.')
    base, reference, maximum = (result['pallet_base_height_cm'], result['reference_pallet_height_cm'],
                                result['max_pallet_height_cm'])
    if reference is not None and base is not None and reference <= base:
        raise ValueError('La altura de referencia debe ser mayor que la altura de la tarima.')
    if maximum is not None and base is not None and maximum <= base:
        raise ValueError('La altura máxima debe ser mayor que la altura de la tarima.')
    for key in ('height_excess_mode', 'pallet_weight_excess_mode', 'truck_weight_excess_mode'):
        value = source.get(key, 'inform')
        if value not in MODES:
            raise ValueError('Los modos de exceso deben ser informar o bloquear.')
        result[key] = value
    for key in ('share_floor_remainders', 'weight_tiebreaker'):
        value = source.get(key, False)
        if type(value) is not bool:
            raise ValueError('Las opciones de planificación deben ser verdadero o falso.')
        result[key] = value
    result['truck_height_override'] = bool(source.get('truck_height_override', False))
    return result


def effective_limit(value, configuration):
    return value * (100 - configuration['safety_margin_pct']) / 100 if value is not None else None


def json_number(value, digits=3):
    return None if value is None else round(float(value), digits)


def item_case_amount(item):
    return Fraction(item.get('bultos', 0)) + Fraction(item.get('unidades', 0), item['unidades_por_bulto'])


def pallet_metrics(items, configuration):
    base_height = configuration['pallet_base_height_cm']
    reference_height = configuration['reference_pallet_height_cm']
    empty_weight = configuration['empty_pallet_weight_kg'] or Fraction(0)
    weight, missing_weights = empty_weight, set()
    height, missing_dimensions = base_height, set()
    height_groups = {}
    for item in items:
        amount = item_case_amount(item)
        if not amount:
            continue
        raw_weight = item.get('peso_por_bulto')
        try:
            case_weight_value = fraction(raw_weight, 'El peso por bulto') if raw_weight not in (None, '') else None
        except ValueError:
            case_weight_value = None
        if case_weight_value is None:
            missing_weights.add(str(item.get('sku')))
        else:
            weight += amount * case_weight_value
        per_floor, floors = item.get('bultos_por_piso'), item.get('pisos_por_pallet')
        if base_height is None or reference_height is None:
            if not per_floor or not floors:
                missing_dimensions.add(str(item.get('sku')))
            height = None
            continue
        if not per_floor or not floors or reference_height <= base_height:
            missing_dimensions.add(str(item.get('sku')))
            height = None
            continue
        floor_height = (reference_height - base_height) / floors
        if configuration['share_floor_remainders']:
            key = (item.get('business_unit'), item.get('bultos_por_pallet'), per_floor, floors)
            current = height_groups.setdefault(key, dict(amount=Fraction(0), floor_height=floor_height,
                                                          per_floor=per_floor))
            current['amount'] += amount
        else:
            key = (item.get('order'), item.get('sku'))
            height_groups[key] = dict(amount=amount, floor_height=floor_height, per_floor=per_floor)
    if height is not None:
        for key, group in height_groups.items():
            per_floor = group['per_floor']
            occupied = group['amount'] / per_floor
            layers = (occupied.numerator + occupied.denominator - 1) // occupied.denominator
            height += layers * group['floor_height']
    height_limit = effective_limit(configuration['max_pallet_height_cm'], configuration)
    weight_limit = effective_limit(configuration['max_pallet_weight_kg'], configuration)
    return dict(
        height_cm=json_number(height, 2), weight_kg=json_number(weight, 3),
        height_fraction=height, weight_fraction=weight,
        height_limit_cm=json_number(height_limit, 2), weight_limit_kg=json_number(weight_limit, 3),
        height_excess_cm=json_number(max(Fraction(0), height - height_limit), 2) if height is not None and height_limit is not None else 0,
        weight_excess_kg=json_number(max(Fraction(0), weight - weight_limit), 3) if weight_limit is not None and not missing_weights else 0,
        height_exceeded=bool(height is not None and height_limit is not None and height > height_limit),
        weight_exceeded=bool(weight_limit is not None and not missing_weights and weight > weight_limit),
        missing_weights=sorted(missing_weights), missing_dimensions=sorted(missing_dimensions),
        weight_complete=not missing_weights, height_complete=height is not None and not missing_dimensions,
    )


def public_metrics(metrics):
    return {key: value for key, value in metrics.items() if key not in ('height_fraction', 'weight_fraction')}


def assembly_priority(item, bultos=None, unidades=None):
    """Put the largest stable complete-floor base first, then retain configured criteria."""
    cases = int(item.get('bultos', 0) if bultos is None else bultos)
    units = int(item.get('unidades', 0) if unidades is None else unidades)
    floor = item.get('bultos_por_piso')
    full_floors = cases // floor if isinstance(floor, int) and floor > 0 else 0
    eligible = bool(item.get('can_be_base') and item.get('stable') and not item.get('stacking_rule_pending')
                    and full_floors > 0)
    equivalent = Fraction(cases)
    upb = item.get('unidades_por_bulto')
    if isinstance(upb, int) and upb > 0:
        equivalent += Fraction(units, upb)
    return (0 if eligible else 1,
            -equivalent if eligible else 0,
            -full_floors if eligible else 0,
            -int(item.get('size_rank') or 0),
            -int(item.get('base_priority') or 0),
            -equivalent if not eligible else 0)


def prefers_complete_floors(reference):
    unit = str(reference.get('business_unit') or '').upper()
    caliber = str(reference.get('calibre') or '').upper()
    return 'CERVEZA' in unit and any(size in caliber for size in ('975', '1000'))


def separates_loose_units(reference):
    """Loose units, except 975/1000 cc calibers, travel on dedicated picking pallets."""
    sizes = set(re.findall(r'\d+', str(reference.get('calibre') or '')))
    return bool(reference.get('unidades')) and not sizes.intersection({'975', '1000'})


def loose_unit_pallet_compatible(pallet, reference):
    """All eligible loose units of a load share their dedicated pallet while limits allow it."""
    return not pallet['items'] or pallet['load_id'] == reference['load_id']


def floor_remainder_compatible(pallet, reference):
    if not pallet['items'] or any(item.get('order') == reference.get('order') for item in pallet['items']):
        return True
    return same_physical_format(pallet['items'][0], reference)


def same_physical_format(left, right):
    """Articles with identical layer geometry can share the same pallet base."""
    fields = ('business_unit', 'bultos_por_piso', 'pisos_por_pallet', 'bultos_por_pallet')
    same_geometry = all(left.get(field) == right.get(field) for field in fields)
    same_caliber = str(left.get('calibre') or '').strip().upper() == str(right.get('calibre') or '').strip().upper()
    return same_geometry and (same_caliber or (prefers_complete_floors(left) and prefers_complete_floors(right)))


def pallet_compatible(pallet, reference, mix_courts, compact):
    if not pallet['items']:
        return True
    same_item = any(item.get('order') == reference.get('order') for item in pallet['items'])
    if same_item:
        return True
    base = pallet['items'][0]
    # Compact/supermarket loads are assembled by forklift. Inside the same load,
    # occupancy is the physical limit and courts do not split an otherwise valid pallet.
    # Unknown rules remain isolated because their compatibility cannot be proven.
    if reference['load_id'] in compact:
        return not reference.get('stacking_rule_pending') and not any(
            item.get('stacking_rule_pending') for item in pallet['items'])
    compacting = mix_courts or reference['load_id'] in compact
    # Retornables de litro se arman desde la base por pisos. Un resto de piso
    # queda concentrado y no se utiliza como apoyo para otro artículo.
    if prefers_complete_floors(reference):
        if not prefers_complete_floors(base) or not same_physical_format(base, reference):
            return False
        if not compacting:
            return False
        if pallet['court'] == reference['court']:
            return True
        return cross_court_compatible(pallet, reference)
    if prefers_complete_floors(base) and not base.get('floor_complete'):
        return False
    if prefers_complete_floors(base) and not compacting:
        return False
    if pallet['court'] == reference['court']:
        return True
    return compacting and cross_court_compatible(pallet, reference)


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


def plan_for_capacity(rows, capacity, mix_courts=False, compact_load_ids=None, configuration=None):
    """Keep courts separate unless requested or needed to fit the truck."""
    if type(mix_courts) is not bool:
        raise ValueError('La mezcla entre canchas debe ser verdadero o falso.')
    rows = list(rows)
    separate = simulate_pallets(rows, capacity, False, compact_load_ids, configuration, False)
    required = not separate['fits_estimate']
    if required:
        alternatives = []
        for strategy, complete_floors, best_fit, shared_layers in (
                ('mezcla_por_cancha', False, False, False), ('mezcla_mejor_ajuste', False, True, False),
                ('pisos_por_cancha', True, False, False), ('pisos_mejor_ajuste', True, True, False),
                ('capas_compartidas', False, True, True), ('pisos_y_capas_compartidas', True, True, True)):
            candidate_configuration = dict(configuration or {})
            if shared_layers:
                candidate_configuration['share_floor_remainders'] = True
            proposal = simulate_pallets(rows, capacity, True, compact_load_ids, candidate_configuration,
                                        complete_floors, best_fit)
            proposal['optimization_strategy'] = strategy
            alternatives.append(proposal)
        def quality(plan):
            floor_breaks = 0
            for pallet in plan['mixed_pallets']:
                complete = any(item.get('bultos_por_piso') and item['bultos'] >= item['bultos_por_piso']
                               and item['bultos'] % item['bultos_por_piso'] == 0 for item in pallet['items'])
                remainder = any(item.get('bultos_por_piso') and item['bultos'] % item['bultos_por_piso']
                                for item in pallet['items'])
                floor_breaks += int(complete and remainder)
            low_occupancy = sum(pallet['occupancy'] < .5 for pallet in plan['mixed_pallets'])
            wasted = round(sum(1 - pallet['occupancy'] for pallet in plan['mixed_pallets']), 6)
            shared = sum(pallet['shared'] for pallet in plan['mixed_pallets'])
            blocked = sum(bool(value) for value in plan['blocking_excesses'].values())
            return (not plan['fits_estimate'], plan['total_pallets'], blocked, floor_breaks,
                    low_occupancy, shared, wasted)
        result = min(alternatives, key=quality)
        result['optimization_alternatives'] = [dict(strategy=plan['optimization_strategy'],
            total_pallets=plan['total_pallets'], fits=plan['fits_estimate'], score=list(quality(plan)))
            for plan in alternatives]
    else:
        result = simulate_pallets(rows, capacity, True, compact_load_ids, configuration, False) if mix_courts else separate
    result.update(separate_pallets=separate['total_pallets'], automatic_mix=required,
                  saved_positions=separate['total_pallets'] - result['total_pallets'])
    return result


def simulate_pallets(rows, capacity, mix_courts=False, compact_load_ids=None, configuration=None,
                     optimize_complete_floors=False, prefer_best_fit=False):
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
    config = validate_configuration(configuration)
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
            'bultos_por_pallet', 'pisos_por_pallet', 'unidades_por_bulto', 'peso_por_bulto')}
        floor = reference.get('bultos_por_piso')
        reference['floor_complete'] = bool(reference.get('allow_incomplete_floor') or (floor and remainder >= floor
            and (not prefers_complete_floors(reference) or remainder % floor == 0)))
        reference['order'] = order
        reference['assembly_mode'] = 'compact' if row['load_id'] in compact else 'normal'
        if count:
            full.append(dict(reference, id=f'F{len(full)+1:03}', pallets=count, bultos=count*bpp, bultos_por_pallet=bpp))
            full_count += count
        tasks.append(dict(reference, bultos=remainder, unidades=row['unidades']))
        # Stable base products contribute complete floors first. Their remainder is kept
        # out of those pallets so it cannot break an already completed floor.
        floor_ready = bool(optimize_complete_floors and reference.get('can_be_base') and reference.get('stable')
                           and not reference.get('stacking_rule_pending') and isinstance(floor, int) and floor > 0)
        complete_floor_cases = remainder - remainder % floor if floor_ready else 0
        if complete_floor_cases:
            pieces.append((dict(reference, floor_complete=True), 'bultos', complete_floor_cases,
                           Fraction(1, bpp), False, True, False))
        if remainder - complete_floor_cases:
            pieces.append((reference, 'bultos', remainder - complete_floor_cases,
                           Fraction(1, bpp), False, False, floor_ready))
        pieces.append((reference, 'unidades', row['unidades'], Fraction(1, bpp*upb),
                       separates_loose_units(row), False, False))
    floor_pieces = [piece for piece in pieces if piece[5]]
    floor_mix_orders = set()
    for left in floor_pieces:
        for right in floor_pieces:
            if left[0]['order'] == right[0]['order'] or left[0]['load_id'] != right[0]['load_id']:
                continue
            fake = dict(load_id=left[0]['load_id'], court=left[0]['court'], items=[left[0]])
            if pallet_compatible(fake, right[0], True, compact):
                floor_mix_orders.update((left[0]['order'], right[0]['order']))
    # Without a compatible partner there is no benefit in isolating the remainder.
    # Excluded 975/1000 cc units stay with their product's complete-floor pallet.
    pieces = [(reference, field, amount, size, loose_units,
               (floor_build and reference['order'] in floor_mix_orders)
               or (field == 'unidades' and not loose_units and reference['order'] in floor_mix_orders),
               floor_remainder and reference['order'] in floor_mix_orders)
              for reference, field, amount, size, loose_units, floor_build, floor_remainder in pieces]
    # A stable configured base with a complete floor and more cases is allocated first.
    def piece_weight(piece):
        try:
            return fraction(piece[0].get('peso_por_bulto'), 'Peso') or Fraction(0)
        except ValueError:
            return Fraction(0)
    pieces.sort(key=lambda p: (p[0]['load_id'], p[4], 0 if p[5] else 1,
        *assembly_priority(p[0], p[2] if p[1] == 'bultos' else 0,
                                                                     p[2] if p[1] == 'unidades' else 0),
        -piece_weight(p) if config['weight_tiebreaker'] else 0,
        -p[3] if p[0]['load_id'] in compact else 0,
        p[0]['court'] if mix_courts or p[0]['load_id'] in compact else p[0]['order'], p[0]['order']))
    def quantity_allowed(pallet, reference, field, quantity):
        items = [dict(item) for item in pallet['items']]
        item = next((candidate for candidate in items if candidate['order'] == reference['order']), None)
        if item is None:
            item = dict(reference, bultos=0, unidades=0)
            items.append(item)
        item[field] += quantity
        metrics = pallet_metrics(items, config)
        if (pallet.get('assembly_mode') != 'compact' and config['height_excess_mode'] == 'block'
                and metrics['height_exceeded']):
            return False
        if config['pallet_weight_excess_mode'] == 'block' and metrics['weight_exceeded']:
            return False
        return True

    def maximum_quantity(pallet, reference, field, amount, size):
        upper = min(amount, int((1-pallet['used']) // size))
        low, high = 0, upper
        while low < high:
            middle = (low + high + 1) // 2
            if quantity_allowed(pallet, reference, field, middle):
                low = middle
            else:
                high = middle - 1
        return low

    def next_mixed_id(loose_units):
        prefix = 'U' if loose_units else 'M'
        sequence = sum(1 for pallet in mixed if str(pallet['id']).startswith(prefix)) + 1
        return f'{prefix}{sequence:03}'

    for reference, field, amount, size, loose_units, floor_build, floor_remainder in pieces:
        order = reference['order']
        while amount:
            candidates = [(p, maximum_quantity(p, reference, field, amount, size)) for p in mixed
                if p['load_id'] == reference['load_id']
                and p.get('loose_units', False) == loose_units
                and p.get('floor_build', False) == floor_build
                and p.get('floor_remainder', False) == floor_remainder
                and (loose_unit_pallet_compatible(p, reference) if loose_units
                     else floor_remainder_compatible(p, reference) if floor_remainder
                     else pallet_compatible(p, reference, True if floor_build else mix_courts, compact))
                and 1-p['used'] >= size]
            if floor_build and field == 'bultos':
                floor = reference['bultos_por_piso']
                candidates = [(p, quantity - quantity % floor) for p, quantity in candidates]
            candidates = [(p, quantity) for p, quantity in candidates if quantity > 0]
            selected = max(candidates, key=(lambda pair: (pair[0]['used'], pair[1],
                                                           pair[0]['court'] == reference['court']))
                           if prefer_best_fit else
                           (lambda pair: (pair[0]['court'] == reference['court'], pair[0]['used'], pair[1])),
                           default=None)
            pallet, allowed_quantity = selected if selected else (None, 0)
            if pallet is None:
                pallet = dict(id=next_mixed_id(loose_units), load_id=reference['load_id'], reparto=reference['reparto'],
                    assembly_mode=reference['assembly_mode'], court=reference['court'], loose_units=loose_units,
                    floor_build=floor_build, floor_remainder=floor_remainder, used=Fraction(0), items=[])
                mixed.append(pallet)
                allowed_quantity = maximum_quantity(pallet, reference, field, amount, size)
            # A single indivisible case/unit that exceeds a blocking limit is retained and flagged;
            # otherwise the loop could neither conserve quantities nor produce a reviewable plan.
            quantity = allowed_quantity or min(amount, 1)
            floor = reference.get('bultos_por_piso')
            if floor_build and field == 'bultos':
                quantity = quantity - quantity % floor
                if not quantity:
                    pallet = dict(id=next_mixed_id(loose_units), load_id=reference['load_id'], reparto=reference['reparto'],
                        assembly_mode=reference['assembly_mode'], court=reference['court'], loose_units=loose_units,
                        floor_build=True, floor_remainder=False, used=Fraction(0), items=[])
                    mixed.append(pallet)
                    quantity = min(amount, maximum_quantity(pallet, reference, field, amount, size)
                                   or int(Fraction(1, 1) // size))
                    quantity -= quantity % floor
                    if not quantity:
                        quantity = min(amount, floor)
            item = next((i for i in pallet['items'] if i['order'] == order), None)
            if item is None:
                item = dict(reference, bultos=0, unidades=0, floor_build=floor_build,
                            floor_remainder=floor_remainder)
                pallet['items'].append(item)
            item[field] += quantity
            pallet['used'] += quantity*size
            amount -= quantity

    # Greedy placement can leave two compact pallets separated by internal floor/remainder
    # categories even when their final combined occupancy is valid. Compact loads use a
    # last consolidation pass because the forklift assembles them by total occupancy.
    changed = True
    while changed:
        changed = False
        for left_index, left in enumerate(mixed):
            if left['load_id'] not in compact or left.get('loose_units'):
                continue
            for right_index in range(left_index + 1, len(mixed)):
                right = mixed[right_index]
                if right['load_id'] != left['load_id'] or right.get('loose_units'):
                    continue
                if left['used'] + right['used'] > 1:
                    continue
                combined = [dict(item) for item in left['items']]
                for candidate in right['items']:
                    item = next((current for current in combined
                                 if current['order'] == candidate['order']), None)
                    if item:
                        item['bultos'] += candidate['bultos']
                        item['unidades'] += candidate['unidades']
                    else:
                        combined.append(dict(candidate))
                if any(item.get('stacking_rule_pending') for item in combined):
                    continue
                metrics = pallet_metrics(combined, config)
                if config['pallet_weight_excess_mode'] == 'block' and metrics['weight_exceeded']:
                    continue
                combined.sort(key=lambda item: (*assembly_priority(item), item['order']))
                for item in combined:
                    item['floor_build'] = False
                    item['floor_remainder'] = False
                left['items'] = combined
                left['used'] += right['used']
                left['court'] = combined[0]['court']
                left['floor_build'] = False
                left['floor_remainder'] = False
                mixed.pop(right_index)
                changed = True
                break
            if changed:
                break
    for pallet in mixed:
        pallet['occupancy'] = round(float(pallet.pop('used')), 6)
        pallet['courts'] = sorted({i['court'] for i in pallet['items']})
        pallet['shared'] = len(pallet['courts']) > 1
        pallet['owner_court'] = (max(pallet['items'], key=lambda item: (item['unidades'], -item['order']))['court']
                                  if pallet.get('loose_units') else pallet['court'])
        pallet['layers'] = [dict(position=n+1, placement='base' if n == 0 else 'arriba', **item)
            for n, item in enumerate(pallet['items'])]
        metrics = public_metrics(pallet_metrics(pallet['items'], config))
        if pallet.get('assembly_mode') == 'compact' and pallet['occupancy'] <= 1:
            metrics.update(height_cm=None, height_complete=False, height_exceeded=False,
                           height_excess_cm=0, missing_dimensions=[], height_check='occupancy')
        pallet.update(metrics)
        del pallet['court']
    for pallet in full:
        one = dict(pallet, bultos=pallet['bultos_por_pallet'], unidades=0)
        metrics = public_metrics(pallet_metrics([one], config))
        if pallet.get('assembly_mode') == 'compact':
            metrics.update(height_cm=None, height_complete=False, height_exceeded=False,
                           height_excess_cm=0, missing_dimensions=[], height_check='occupancy')
        pallet.update(metrics)
    position_pallets = [pallet for pallet in mixed if not pallet.get('loose_units')]
    unit_pallet_count = len(mixed) - len(position_pallets)
    total = full_count + len(position_pallets)
    load_plans = []
    for load_id in dict.fromkeys(r['load_id'] for r in rows):
        own_full = [p for p in full if p['load_id'] == load_id]
        own_mixed = [p for p in mixed if p['load_id'] == load_id]
        own_positions = [p for p in own_mixed if not p.get('loose_units')]
        own_units = len(own_mixed) - len(own_positions)
        load_plans.append(dict(load_id=load_id, reparto=next(r['reparto'] for r in rows if r['load_id']==load_id),
            assembly_mode='compact' if load_id in compact else 'normal', full_count=sum(p['pallets'] for p in own_full),
            mixed_count=len(own_positions), unit_pallet_count=own_units,
            total_pallets=sum(p['pallets'] for p in own_full)+len(own_positions),
            pallet_ids=[p['id'] for p in own_full+own_mixed]))
    missing_rules = sorted({f"{r.get('business_unit') or 'SIN UNIDAD'} / {r.get('calibre') or 'SIN CALIBRE'}"
        for r in rows if (r.get('bultos') or r.get('unidades')) and r.get('stacking_rule_pending')})
    all_pallets = [(p, p['pallets']) for p in full] + [(p, 1) for p in mixed]
    missing_weights = sorted({sku for pallet, _ in all_pallets for sku in pallet['missing_weights']})
    missing_dimensions = sorted({sku for pallet, _ in all_pallets for sku in pallet['missing_dimensions']})
    known_weight = sum(Fraction(str(pallet['weight_kg'])) * count for pallet, count in all_pallets)
    weight_complete = not missing_weights
    truck_limit = effective_limit(config['max_payload_kg'], config)
    truck_excess = max(Fraction(0), known_weight - truck_limit) if truck_limit is not None else Fraction(0)
    truck_exceeded = bool(truck_limit is not None and known_weight > truck_limit)
    height_blocked = config['height_excess_mode'] == 'block' and any(p['height_exceeded'] for p, _ in all_pallets)
    pallet_weight_blocked = config['pallet_weight_excess_mode'] == 'block' and any(p['weight_exceeded'] for p, _ in all_pallets)
    truck_weight_blocked = config['truck_weight_excess_mode'] == 'block' and truck_exceeded
    fits = total <= capacity and not height_blocked and not pallet_weight_blocked and not truck_weight_blocked
    config_result = {key: (json_number(value, 3) if isinstance(value, Fraction) else value) for key, value in config.items()}
    return dict(capacity=capacity, mix_courts=mix_courts, full_pallets=full,
                separation_policy='reparto_v1', compact_load_ids=sorted(compact), load_plans=load_plans,
                picking_tasks=tasks, mixed_pallets=mixed, full_count=full_count,
                mixed_count=len(position_pallets), unit_pallet_count=unit_pallet_count,
                total_pallets=total, free_positions=max(0, capacity-total),
                excess_positions=max(0, total-capacity), fits_estimate=fits,
                configuration=config_result, missing_weights=missing_weights,
                missing_dimensions=missing_dimensions, weight_complete=weight_complete,
                truck_weight_kg=json_number(known_weight, 3) if weight_complete else None,
                truck_weight_known_kg=json_number(known_weight, 3),
                truck_weight_limit_kg=json_number(truck_limit, 3),
                truck_weight_excess_kg=json_number(truck_excess, 3), truck_weight_exceeded=truck_exceeded,
                blocking_excesses=dict(height=height_blocked, pallet_weight=pallet_weight_blocked,
                                       truck_weight=truck_weight_blocked),
                missing_caliber_rules=missing_rules, status='simulation', method='caliber_floor_height_weight_first_fit_per_load',
                warning='Plan calculado por equivalencia, pisos, altura, peso y reglas de calibre con los datos disponibles. La estabilidad y los datos faltantes requieren revisión física del supervisor.')


def apply_manual_pallets(plan, submitted, merge_allowed_load_ids=None):
    """Validate a supervisor regrouping and assign each result to its destination court."""
    if not isinstance(submitted, list) or not submitted:
        raise ValueError('El armado manual no contiene pallets de picking.')

    def identity(item):
        return (item.get('load_id'), item.get('order'), item.get('court'),
                item.get('product_key') or str(item.get('sku')), bool(item.get('floor_build')),
                bool(item.get('floor_remainder')))

    allowed = set(merge_allowed_load_ids or [])
    config = validate_configuration(plan.get('configuration'))
    originals = [item for pallet in plan['mixed_pallets'] for item in pallet['items']]
    available, expected = {}, {}
    for pallet in plan['mixed_pallets']:
        for item in pallet['items']:
            key = identity(item)
            entry = available.setdefault(key, dict(template=item, source_pallet_ids=set()))
            entry['source_pallet_ids'].add(pallet['id'])
            totals = expected.setdefault(key, dict(bultos=0, unidades=0))
            totals['bultos'] += item['bultos']
            totals['unidades'] += item['unidades']
    received, mixed, seen_ids = {}, [], set()

    for index, raw in enumerate(submitted, 1):
        if not isinstance(raw, dict) or not isinstance(raw.get('items'), list) or not raw['items']:
            raise ValueError('Cada pallet debe contener al menos un artículo.')
        pallet_id = str(raw.get('id') or f'M{index:03}')
        if pallet_id in seen_ids:
            raise ValueError('Hay identificadores de pallet repetidos.')
        seen_ids.add(pallet_id)
        clean_items, source_pallet_ids = [], set()
        for candidate in raw['items']:
            key = identity(candidate)
            source = available.get(key)
            bultos, unidades = candidate.get('bultos'), candidate.get('unidades')
            if source is None or type(bultos) is not int or type(unidades) is not int or bultos < 0 or unidades < 0 or not (bultos or unidades):
                raise ValueError('El armado manual modifica, duplica o agrega cantidades de productos.')
            totals = received.setdefault(key, dict(bultos=0, unidades=0))
            totals['bultos'] += bultos
            totals['unidades'] += unidades
            if totals['bultos'] > expected[key]['bultos'] or totals['unidades'] > expected[key]['unidades']:
                raise ValueError('El armado manual modifica, duplica o agrega cantidades de productos.')
            clean_items.append(dict(source['template'], bultos=bultos, unidades=unidades))
            source_pallet_ids.update(source['source_pallet_ids'])
        if len({item['load_id'] for item in clean_items}) != 1:
            raise ValueError('No se pueden mezclar repartos dentro de un mismo pallet.')
        if len(source_pallet_ids) > 1 and clean_items[0]['load_id'] not in allowed:
            raise ValueError(f'El reparto {clean_items[0]["reparto"]} no permite unir pallets.')
        loose_units = any(item['unidades'] and separates_loose_units(item) for item in clean_items)
        if loose_units and any(item['bultos'] or not item['unidades'] or not separates_loose_units(item)
                               for item in clean_items):
            raise ValueError('Las unidades sueltas deben permanecer en un pallet exclusivo, excepto 975 y 1000 cc.')
        floor_modes = {bool(item.get('floor_build')) for item in clean_items}
        if len(floor_modes) > 1:
            raise ValueError('Los restos no pueden mezclarse con pallets reservados para pisos completos.')
        floor_build = floor_modes == {True}
        if floor_build and any(item['bultos'] % item['bultos_por_piso'] for item in clean_items):
            raise ValueError('Cada producto debe conservar pisos completos en este pallet.')
        remainder_modes = {bool(item.get('floor_remainder')) for item in clean_items}
        if len(remainder_modes) > 1:
            raise ValueError('Los restos deben permanecer en sus pallets compatibles.')
        floor_remainder = remainder_modes == {True}
        if floor_remainder and any(not same_physical_format(clean_items[0], item) for item in clean_items[1:]):
            raise ValueError('Solo se pueden agrupar restos con la misma geometría de piso.')
        owner = (max(clean_items, key=lambda item: (item['unidades'], -item['order']))['court']
                 if loose_units else raw.get('owner_court'))
        if type(owner) is not int or owner not in {item['court'] for item in clean_items}:
            raise ValueError('La cancha responsable debe pertenecer al pallet de destino.')
        clean_items.sort(key=lambda item: (*assembly_priority(item), item['order']))
        used = sum(Fraction(item['bultos'], item['bultos_por_pallet']) +
                   Fraction(item['unidades'], item['bultos_por_pallet'] * item['unidades_por_bulto'])
                   for item in clean_items)
        if used > 1:
            raise ValueError(f'El pallet {pallet_id} supera el 100% de capacidad.')
        metrics = pallet_metrics(clean_items, config)
        if (clean_items[0]['assembly_mode'] != 'compact' and config['height_excess_mode'] == 'block'
                and metrics['height_exceeded']):
            raise ValueError(f'El pallet {pallet_id} supera la altura máxima permitida.')
        if config['pallet_weight_excess_mode'] == 'block' and metrics['weight_exceeded']:
            raise ValueError(f'El pallet {pallet_id} supera el peso máximo permitido.')
        public = public_metrics(metrics)
        if clean_items[0]['assembly_mode'] == 'compact' and used <= 1:
            public.update(height_cm=None, height_complete=False, height_exceeded=False,
                          height_excess_cm=0, missing_dimensions=[], height_check='occupancy')
        for item in clean_items:
            item['assigned_court'] = owner
            item['pallet_id'] = pallet_id
        mixed.append(dict(id=pallet_id, load_id=clean_items[0]['load_id'], reparto=clean_items[0]['reparto'],
                          assembly_mode=clean_items[0]['assembly_mode'], owner_court=owner,
                          loose_units=loose_units, floor_build=floor_build, floor_remainder=floor_remainder,
                          occupancy=round(float(used), 6), courts=sorted({i['court'] for i in clean_items}),
                          shared=len({i['court'] for i in clean_items}) > 1, items=clean_items,
                          layers=[dict(position=n + 1, placement='base' if n == 0 else 'arriba', **item)
                                  for n, item in enumerate(clean_items)], **public))
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
    position_pallets = [pallet for pallet in mixed if not pallet.get('loose_units')]
    plan['mixed_count'] = len(position_pallets)
    plan['unit_pallet_count'] = len(mixed) - len(position_pallets)
    plan['total_pallets'] = plan['full_count'] + len(position_pallets)
    plan['free_positions'] = max(0, plan['capacity'] - plan['total_pallets'])
    plan['excess_positions'] = max(0, plan['total_pallets'] - plan['capacity'])
    all_pallets = [(p, p['pallets']) for p in plan['full_pallets']] + [(p, 1) for p in mixed]
    plan['missing_weights'] = sorted({sku for pallet, _ in all_pallets for sku in pallet.get('missing_weights', [])})
    plan['missing_dimensions'] = sorted({sku for pallet, _ in all_pallets for sku in pallet.get('missing_dimensions', [])})
    known_weight = sum(Fraction(str(pallet.get('weight_kg') or 0)) * count for pallet, count in all_pallets)
    truck_limit = effective_limit(config['max_payload_kg'], config)
    truck_excess = max(Fraction(0), known_weight - truck_limit) if truck_limit is not None else Fraction(0)
    plan.update(weight_complete=not plan['missing_weights'],
                truck_weight_kg=json_number(known_weight, 3) if not plan['missing_weights'] else None,
                truck_weight_known_kg=json_number(known_weight, 3), truck_weight_limit_kg=json_number(truck_limit, 3),
                truck_weight_excess_kg=json_number(truck_excess, 3),
                truck_weight_exceeded=bool(truck_limit is not None and known_weight > truck_limit))
    height_blocked = config['height_excess_mode'] == 'block' and any(p.get('height_exceeded') for p, _ in all_pallets)
    pallet_weight_blocked = config['pallet_weight_excess_mode'] == 'block' and any(p.get('weight_exceeded') for p, _ in all_pallets)
    truck_weight_blocked = config['truck_weight_excess_mode'] == 'block' and plan['truck_weight_exceeded']
    plan['blocking_excesses'] = dict(height=height_blocked, pallet_weight=pallet_weight_blocked,
                                     truck_weight=truck_weight_blocked)
    plan['fits_estimate'] = (plan['total_pallets'] <= plan['capacity'] and not height_blocked
                             and not pallet_weight_blocked and not truck_weight_blocked)
    for load_plan in plan['load_plans']:
        own = [p for p in mixed if p['load_id'] == load_plan['load_id']]
        own_positions = [p for p in own if not p.get('loose_units')]
        load_plan['mixed_count'] = len(own_positions)
        load_plan['unit_pallet_count'] = len(own) - len(own_positions)
        load_plan['total_pallets'] = load_plan['full_count'] + len(own_positions)
        load_plan['pallet_ids'] = ([p['id'] for p in plan['full_pallets'] if p['load_id'] == load_plan['load_id']] +
                                   [p['id'] for p in own])
    plan['manual_edition'] = True
    plan['merge_allowed_load_ids'] = sorted(allowed)
    plan['manual_saved_positions'] = original_mixed_count - len(position_pallets)
    return plan
