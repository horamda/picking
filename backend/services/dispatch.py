"""Read-only summaries and per-worker queue policy. State is stored on ControlTruck."""
from decimal import Decimal, InvalidOperation
import unicodedata

from services.load_control import selected_loads, court_state
from services.pallet_planning import simulate_pallets, plan_for_capacity


def totals(rows, catalog):
    bultos = sum(r['bultos'] for r in rows)
    units = sum(r.get('unidades', 0) for r in rows)
    hl, missing = Decimal(0), set()
    for row in rows:
        if not row['bultos'] and not row.get('unidades', 0):
            continue
        article = catalog.get(row['sku'])
        raw = (article.datos_origen or {}) if article else {}
        raw = {''.join(c for c in unicodedata.normalize('NFKD', k.strip().lower()) if not unicodedata.combining(c)): str(v).strip() for k, v in raw.items()}
        try:
            if raw.get('descripcion unidad de medida', '').upper() != 'HECTOLITROS':
                raise ValueError('Sin factor HL')
            factor = Decimal(raw['valor unidad de medida'].replace(',', '.'))
            upb = article.unidades_por_bulto
            if not factor.is_finite() or factor <= 0 or not upb or upb <= 0:
                raise ValueError('Factor inválido')
            hl += (Decimal(row['bultos']) + Decimal(row.get('unidades', 0)) / upb) * factor
        except (KeyError, ValueError, InvalidOperation):
            missing.add(row['sku'])
    return dict(bultos=bultos, unidades=units, hl=round(float(hl), 4) if not missing else None,
                hl_known=round(float(hl), 4), hl_missing=sorted(missing),
                courts=len({r['court'] for r in rows}), loads=len({r['load_id'] for r in rows}))


def selection_preview(rows, catalog, capacity=None, mix_courts=False):
    """Read-only packing preview; missing factors never become guessed quantities."""
    result = totals(rows, catalog)
    valid, missing = [], set()
    for row in rows:
        if not row['bultos'] and not row.get('unidades', 0):
            continue
        article = catalog.get(row['sku'])
        if not article or not article.activo or not article.unidades_por_bulto or article.unidades_por_bulto <= 0 or not article.bultos_por_pallet or article.bultos_por_pallet <= 0:
            missing.add(row['sku'])
            continue
        valid.append(dict(row, bultos_por_pallet=article.bultos_por_pallet, unidades_por_bulto=article.unidades_por_bulto))
    # Capacity affects the fit check, not packing. Never expose the placeholder as a real capacity.
    plan = plan_for_capacity(valid, capacity, mix_courts) if capacity and not missing else simulate_pallets(valid, capacity or 1, mix_courts)
    result.update(pallets=plan['total_pallets'] if not missing else None,
                  pallets_known=plan['total_pallets'], full_pallets_known=plan['full_count'],
                  picking_pallets_known=plan['mixed_count'], pallet_missing=sorted(missing),
                  capacity=capacity, mix_courts=plan['mix_courts'],
                  automatic_mix=plan.get('automatic_mix', False), separate_pallets=plan.get('separate_pallets'),
                  fits=None if missing or capacity is None else plan['fits_estimate'])
    descriptions = {row['sku']: row['descripcion'] for row in rows}
    result['missing'] = [dict(sku=sku, descripcion=descriptions[sku], hl=sku in result['hl_missing'],
                              pallets=sku in missing) for sku in sorted(missing | set(result['hl_missing']))]
    def equivalents(items):
        cases, pallets = Decimal(0), Decimal(0)
        cases_missing, pallets_missing = False, False
        for row in items:
            article = catalog.get(row['sku'])
            upb = article.unidades_por_bulto if article else None
            bpp = article.bultos_por_pallet if article else None
            amount = Decimal(row['bultos'])
            if row.get('unidades', 0):
                if not upb or upb <= 0:
                    cases_missing = pallets_missing = True
                    continue
                amount += Decimal(row['unidades']) / upb
            cases += amount
            if amount and (not bpp or bpp <= 0 or not article.activo):
                pallets_missing = True
            elif amount:
                pallets += amount / bpp
        return dict(bultos_equiv=float(cases) if not cases_missing else None,
                    pallets_equiv=float(pallets) if not pallets_missing else None)
    result.update(equivalents(rows))
    result['court_totals'] = []
    for court in sorted({row['court'] for row in rows}):
        items = [row for row in rows if row['court'] == court]
        result['court_totals'].append(dict(court=court, **totals(items, catalog), **equivalents(items)))
    result['assembly'] = [dict(id=f'F{index + 1:03}', count=item['pallets'],
        items=[dict(item, **equivalents([item]))]) for index, item in enumerate(plan['full_pallets'])]
    result['assembly'] += [dict(id=pallet['id'], count=1,
        items=[dict(item, **equivalents([item])) for item in pallet['items']]) for pallet in plan['mixed_pallets']]
    return result


def original_rows(truck):
    return [dict(p, load_id=load.id, reparto=load.reparto, court=c['numero'])
            for load in selected_loads(truck) for c in load.content['canchas'] for p in c['productos']]


def pending_for_worker(truck, courts, stage, products):
    """Done belongs to the assigned court; other courts and controls do not gate this user."""
    return any(c['numero'] in courts and (products(load, c, stage) if truck.state.get('planning') else c['productos'])
               and court_state(truck.state, load.id, c['numero'])['checks'].get(str(stage), {}).get('status') != 'done'
               for load in selected_loads(truck) for c in load.content['canchas'])


def worker_queue(trucks, courts, stage, products):
    ordered = sorted((t for t in trucks if t.state.get('dispatch', {}).get('load_ids') and not t.state.get('released_at')),
                     key=lambda t: (t.load_date, t.state['dispatch']['position'], t.branch, t.id))
    return [t for t in ordered if pending_for_worker(t, courts, stage, products)]


def truck_summary(truck, catalog, courts=None, stage=0, valid=True):
    summary = totals(original_rows(truck), catalog)
    plan = truck.state.get('planning') if valid else None
    summary.update(pallets=plan['total_pallets'] if plan else None,
                   full_pallets=plan['full_count'] if plan else None,
                   picking_pallets=plan['mixed_count'] if plan else None,
                   capacity=plan['capacity'] if plan else None)
    if courts is None:
        return summary
    tasks = (plan or {}).get('picking_tasks' if stage == 0 else 'full_pallets', [])
    own = [p for p in tasks if p['court'] in courts and (p['bultos'] or p.get('unidades', 0))]
    own_summary = totals(own, catalog)
    allocations = []
    for pallet in ((plan or {}).get('mixed_pallets', []) if stage == 0 else []):
        items = [i for i in pallet['items'] if i['court'] in courts]
        if items:
            allocations.append(dict(id=pallet['id'], shared=len({i['court'] for i in pallet['items']}) > 1, items=items))
    own_summary.update(stage=stage, pallets=len(allocations) if plan and stage == 0 else sum(p.get('pallets', 0) for p in own) if plan else None,
                       allocations=allocations,
                       full_pallets_info=sum(p['pallets'] for p in (plan or {}).get('full_pallets', []) if p['court'] in courts))
    own_summary['tasks'] = len({(p['load_id'], p['court']) for p in own})
    own_summary['finished_tasks'] = sum(
        court_state(truck.state, load_id, court)['checks'].get(str(stage), {}).get('status') == 'done'
        for load_id, court in {(p['load_id'], p['court']) for p in own})
    summary['mine'] = own_summary
    return summary
