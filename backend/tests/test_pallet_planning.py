import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.pallet_planning import simulate_pallets, plan_for_capacity, apply_manual_pallets


def row(b=244, u=0, court=1, bpp=50, upb=12, sku='BRAHMA', family='general', priority=0, bottom=False, allowed=None, calibre='GENERAL', rank=1000, floor=10, can_base=True, stable=True, pending=False, business_unit='TEST'):
    return dict(load_id=1, reparto='R1', court=court, sku=sku, descripcion=sku,
                bultos=b, unidades=u, bultos_por_pallet=bpp, unidades_por_bulto=upb,
                calibre=calibre, stack_family=family, stack_family_name=family,
                base_priority=priority, must_be_bottom=bottom, allowed_above=['*'] if allowed is None else allowed,
                business_unit=business_unit, can_be_base=can_base, stable=stable, allow_incomplete_floor=False,
                size_rank=rank, bultos_por_piso=floor,
                pisos_por_pallet=(bpp // floor if isinstance(bpp, int) and bpp > 0 and floor else None),
                stacking_rule_pending=pending)


class PlanningTest(unittest.TestCase):
    def test_different_repartos_never_share_a_pallet_even_to_fit(self):
        rows=[row(25),dict(row(25),load_id=2,reparto='R2')]
        for mix in (False,True):
            result=plan_for_capacity(rows,1,mix)
            self.assertEqual(result['total_pallets'],2)
            self.assertFalse(result['fits_estimate'])
            self.assertTrue(all(len({i['load_id'] for i in p['items']})==1 for p in result['mixed_pallets']))

    def test_supermarket_compacts_only_its_own_courts(self):
        rows=[row(25,court=1),row(25,court=2),dict(row(25,court=1),load_id=2,reparto='R2'),dict(row(25,court=2),load_id=2,reparto='R2')]
        result=plan_for_capacity(rows,8,False,[2])
        self.assertEqual(result['total_pallets'],3)
        self.assertEqual([p['total_pallets'] for p in result['load_plans']],[2,1])
        self.assertFalse(result['mix_courts'])
        self.assertEqual([p['order'] for p in result['picking_tasks']],[1,2,3,4])
        self.assertEqual(sum(i['bultos'] for p in result['mixed_pallets'] for i in p['items']),100)
        self.assertEqual(len({p['id'] for p in result['mixed_pallets']}),3)
        with self.assertRaises(ValueError):plan_for_capacity(rows,8,False,[999])

    def test_capacity_drives_combination_without_changing_work(self):
        rows = [row(25, court=i, sku=str(i)) for i in range(1, 10)]
        plan = plan_for_capacity(rows, 8)
        self.assertEqual((plan['separate_pallets'], plan['total_pallets']), (9, 5))
        self.assertTrue(plan['automatic_mix'])
        self.assertTrue(plan['fits_estimate'])
        self.assertEqual(sum(i['bultos'] for p in plan['mixed_pallets'] for i in p['items']), 225)
        self.assertEqual([i['court'] for i in plan['picking_tasks']], list(range(1, 10)))
        separate = plan_for_capacity(rows[:7], 8)
        self.assertFalse(separate['automatic_mix'])
        self.assertFalse(separate['mix_courts'])
        self.assertEqual(separate['total_pallets'], 7)
        too_large = plan_for_capacity(rows, 4)
        self.assertFalse(too_large['fits_estimate'])
        self.assertEqual(too_large['excess_positions'], 1)

    def test_full_pallets_and_remainder(self):
        result = simulate_pallets([row()], 5)
        self.assertEqual(result['full_count'], 4)
        self.assertEqual(result['picking_tasks'][0]['bultos'], 44)
        self.assertEqual(result['total_pallets'], 5)
        self.assertTrue(result['fits_estimate'])
        self.assertEqual(simulate_pallets([row()], 4)['excess_positions'], 1)

    def test_mix_courts_switch(self):
        rows = [row(25, court=1), row(30, court=2, bpp=60, sku='AGUA')]
        self.assertEqual(simulate_pallets(rows, 1, False)['mixed_count'], 2)
        mixed = simulate_pallets(rows, 1, True)['mixed_pallets']
        self.assertEqual(len(mixed), 1)
        self.assertEqual(mixed[0]['courts'], [1, 2])
        self.assertEqual(mixed[0]['occupancy'], 1)

    def test_units_and_quantities_are_conserved(self):
        rows = [row(244, 17), row(49, 11, bpp=60, upb=6, sku='AGUA')]
        result = simulate_pallets(rows, 10, True)
        for original in rows:
            full = sum(p['bultos'] for p in result['full_pallets'] if p['sku'] == original['sku'])
            pieces = [i for p in result['mixed_pallets'] for i in p['items'] if i['sku'] == original['sku']]
            self.assertEqual(full + sum(i['bultos'] for i in pieces), original['bultos'])
            self.assertEqual(sum(i['unidades'] for i in pieces), original['unidades'])
        self.assertTrue(all(p['occupancy'] <= 1 for p in result['mixed_pallets']))
        self.assertEqual([p['sku'] for p in result['picking_tasks']], ['BRAHMA', 'AGUA'])

    def test_exact_full_pallet_does_not_create_empty_mixed_pallet(self):
        self.assertEqual(simulate_pallets([row(100)], 2)['mixed_count'], 0)

    def test_invalid_catalog_capacity_and_flags_fail(self):
        for invalid in [None, 0, -1, True, 2.5]:
            with self.assertRaises(ValueError): simulate_pallets([row()], invalid)
        for invalid in [None, 0, -1]:
            with self.assertRaises(ValueError): simulate_pallets([row(bpp=invalid)], 5)
        with self.assertRaises(ValueError): simulate_pallets([row()], 5, 'false')

    def test_liter_caliber_is_base_and_accepts_other_courts_above(self):
        rows = [row(25, court=2, sku='LATA', family='lata', allowed=[], calibre='473 CC LATAS'),
                row(25, court=1, sku='LITRO', family='litro', priority=100, bottom=True, allowed=['*'], calibre='1000 CC VIDRIO')]
        result = simulate_pallets(rows, 1, True)
        self.assertEqual(result['total_pallets'], 1)
        pallet = result['mixed_pallets'][0]
        self.assertTrue(pallet['shared'])
        self.assertEqual([i['sku'] for i in pallet['layers']], ['LITRO', 'LATA'])
        self.assertEqual([i['placement'] for i in pallet['layers']], ['base', 'arriba'])

    def test_unknown_caliber_never_crosses_courts(self):
        rows = [row(25, court=1, family=None, calibre='SIN REGLA', pending=True), row(25, court=2, sku='OTRO', family='general')]
        result = simulate_pallets(rows, 1, True)
        self.assertEqual(result['total_pallets'], 2)
        self.assertEqual(result['missing_caliber_rules'], ['TEST / SIN REGLA'])

    def test_larger_caliber_never_stacks_on_smaller(self):
        rows = [row(25, court=1, sku='CHICO', rank=473), row(25, court=2, sku='GRANDE', rank=1000)]
        pallet = simulate_pallets(rows, 1, True)['mixed_pallets'][0]
        self.assertEqual([item['sku'] for item in pallet['layers']], ['GRANDE', 'CHICO'])

    def test_incomplete_floor_cannot_support_another_product(self):
        rows = [row(5, court=1, sku='BASE', rank=1000, floor=10), row(25, court=2, sku='ARRIBA', rank=473)]
        self.assertEqual(simulate_pallets(rows, 2, True)['total_pallets'], 2)

    def test_returnable_beer_keeps_complete_floors_and_isolates_remainder(self):
        liter = row(44, sku='RET', calibre='1000 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ')
        other = row(6, sku='LATA', calibre='473 CC LATAS', rank=473)
        plan = simulate_pallets([liter, other], 3)
        self.assertEqual(plan['mixed_count'], 2)
        returnable = next(p for p in plan['mixed_pallets'] if any(i['sku'] == 'RET' for i in p['items']))
        self.assertEqual([(i['sku'], i['bultos']) for i in returnable['items']], [('RET', 44)])

    def test_complete_returnable_floor_can_carry_another_article(self):
        liter = row(40, sku='RET', calibre='975 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ')
        other = row(10, sku='LATA', calibre='473 CC LATAS', rank=473)
        pallet = simulate_pallets([liter, other], 2)['mixed_pallets'][0]
        self.assertEqual([i['sku'] for i in pallet['items']], ['RET', 'LATA'])

    def test_equal_liter_formats_share_a_pallet(self):
        rows = [row(20, sku='RET-A', calibre='1000 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ'),
                row(20, sku='RET-B', calibre='1000 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ')]
        plan = simulate_pallets(rows, 2)
        self.assertEqual(plan['mixed_count'], 1)
        self.assertEqual([(item['sku'], item['bultos']) for item in plan['mixed_pallets'][0]['items']],
                         [('RET-A', 20), ('RET-B', 20)])

    def test_different_liter_geometry_stays_separate(self):
        rows = [row(20, sku='RET-A', calibre='1000 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ'),
                row(20, sku='RET-B', calibre='1000 CC VIDRIO', floor=8,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ')]
        self.assertEqual(simulate_pallets(rows, 2)['mixed_count'], 2)

    def test_supervisor_can_merge_pallets_without_losing_products(self):
        plan = simulate_pallets([row(10, court=1), row(10, court=2, sku='AGUA')], 2, False)
        first, second = plan['mixed_pallets']
        submitted = [dict(first, items=first['items'] + second['items'], owner_court=1)]
        edited = apply_manual_pallets(plan, submitted, [1])
        self.assertEqual((edited['mixed_count'], edited['total_pallets']), (1, 1))
        self.assertEqual(sum(item['bultos'] for item in edited['mixed_pallets'][0]['items']), 20)
        self.assertEqual({task['court'] for task in edited['picking_tasks']}, {1})
        self.assertEqual(edited['picking_tasks'][1]['source_courts'], [2])

    def test_manual_merge_rejects_overfill_and_cross_reparto(self):
        plan = simulate_pallets([row(30), dict(row(10, court=2, sku='AGUA'), load_id=2, reparto='R2')], 3, False)
        first, second = plan['mixed_pallets']
        with self.assertRaisesRegex(ValueError, 'repartos'):
            apply_manual_pallets(plan, [dict(first, items=first['items'] + second['items'], owner_court=1)], [1])
        plan = simulate_pallets([row(30), row(30, court=2, sku='AGUA')], 3, False)
        first, second = plan['mixed_pallets']
        with self.assertRaisesRegex(ValueError, '100%'):
            apply_manual_pallets(plan, [dict(first, items=first['items'] + second['items'], owner_court=1)], [1])

    def test_manual_merge_requires_reparto_permission(self):
        plan = simulate_pallets([row(10), row(10, court=2, sku='AGUA')], 2, False)
        first, second = plan['mixed_pallets']
        with self.assertRaisesRegex(ValueError, 'no permite'):
            apply_manual_pallets(plan, [dict(first, items=first['items'] + second['items'], owner_court=1)], [])


if __name__ == '__main__': unittest.main()


class SameCourtWithoutRulesTest(unittest.TestCase):
    def test_skus_without_stacking_rule_share_pallet_in_same_court(self):
        rows = [row(5, sku=f'S{i}', calibre=f'C{i}', pending=True, can_base=False, stable=False) for i in range(40)]
        result = simulate_pallets(rows, 9)
        self.assertEqual(result['total_pallets'], 4)
        self.assertTrue(result['fits_estimate'])

    def test_cross_court_mixing_still_requires_rules(self):
        rows = [row(5, court=c, sku=f'S{c}', pending=True) for c in (1, 2)]
        self.assertEqual(simulate_pallets(rows, 9, True)['total_pallets'], 2)
