"""Read-only, deterministic pallet estimate. Never rewrites picking quantities."""
from fractions import Fraction


def simulate_pallets(rows, capacity, mix_courts=False):
    if type(capacity) is not int or capacity <= 0:
        raise ValueError('La capacidad debe ser una cantidad entera positiva de pallets físicos.')
    if type(mix_courts) is not bool:
        raise ValueError('La mezcla entre canchas debe ser verdadero o falso.')
    full, mixed, tasks = [], [], []
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
        reference = {key: row[key] for key in ('load_id', 'reparto', 'court', 'sku', 'descripcion')}
        reference['order'] = order
        if count:
            full.append(dict(reference, pallets=count, bultos=count*bpp, bultos_por_pallet=bpp))
            full_count += count
        tasks.append(dict(reference, bultos=remainder, unidades=row['unidades']))
        # Place integer bultos first, then integer units. No fractional case is invented.
        for field, amount, size in [('bultos', remainder, Fraction(1, bpp)),
                                    ('unidades', row['unidades'], Fraction(1, bpp*upb))]:
            while amount:
                pallet = next((p for p in mixed
                    if (mix_courts or p['court'] == row['court']) and 1-p['used'] >= size), None)
                if pallet is None:
                    pallet = dict(id=f'M{len(mixed)+1:03}', court=row['court'], used=Fraction(0), items=[])
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
        del pallet['court']
    total = full_count + len(mixed)
    return dict(capacity=capacity, mix_courts=mix_courts, full_pallets=full,
                picking_tasks=tasks, mixed_pallets=mixed, full_count=full_count,
                mixed_count=len(mixed), total_pallets=total, free_positions=max(0, capacity-total),
                excess_positions=max(0, total-capacity), fits_estimate=total <= capacity,
                status='simulation', method='first_fit_original_order',
                warning='Estimación por equivalencia de bultos. No verifica altura, peso, estabilidad ni compatibilidad de apilado. Requiere revisión física del supervisor.')
