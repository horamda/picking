import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.pallet_planning import simulate_pallets, plan_for_capacity, apply_manual_pallets


def row(b=244, u=0, court=1, bpp=50, upb=12, sku='BRAHMA', family='general', priority=0, bottom=False, allowed=None, calibre='GENERAL', rank=1000, floor=10, can_base=True, stable=True, pending=False, business_unit='TEST', weight=None):
    return dict(load_id=1, reparto='R1', court=court, sku=sku, descripcion=sku,
                bultos=b, unidades=u, bultos_por_pallet=bpp, unidades_por_bulto=upb,
                calibre=calibre, stack_family=family, stack_family_name=family,
                base_priority=priority, must_be_bottom=bottom, allowed_above=['*'] if allowed is None else allowed,
                business_unit=business_unit, can_be_base=can_base, stable=stable, allow_incomplete_floor=False,
                size_rank=rank, bultos_por_piso=floor,
                pisos_por_pallet=(bpp // floor if isinstance(bpp, int) and bpp > 0 and floor else None),
                peso_por_bulto=weight,
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

    def test_loose_units_use_a_dedicated_pallet_owned_by_largest_unit_source(self):
        rows = [row(10, 6, court=1, sku='LATA-A', calibre='473 CC LATAS'),
                row(10, 20, court=2, sku='LATA-B', calibre='710 CC LATAS')]
        result = simulate_pallets(rows, 5, False)
        unit_pallets = [p for p in result['mixed_pallets'] if p.get('loose_units')]
        self.assertEqual(len(unit_pallets), 1)
        pallet = unit_pallets[0]
        self.assertEqual(pallet['id'], 'U001')
        self.assertTrue(all(p['id'].startswith('M') for p in result['mixed_pallets'] if not p.get('loose_units')))
        self.assertEqual(pallet['owner_court'], 2)
        self.assertEqual(pallet['courts'], [1, 2])
        self.assertEqual(sum(item['unidades'] for item in pallet['items']), 26)
        self.assertTrue(all(item['bultos'] == 0 for item in pallet['items']))
        self.assertTrue(all(item['unidades'] == 0 for p in result['mixed_pallets'] if not p.get('loose_units') for item in p['items']))

    def test_975_and_1000_cc_units_remain_with_their_product(self):
        rows = [row(10, 6, court=1, sku='LITRO', calibre='1000 CC VIDRIO'),
                row(10, 8, court=2, sku='RET-975', calibre='975 CC VIDRIO')]
        result = simulate_pallets(rows, 4, False)
        self.assertFalse(any(p.get('loose_units') for p in result['mixed_pallets']))
        for sku in ('LITRO', 'RET-975'):
            item = next(item for pallet in result['mixed_pallets'] for item in pallet['items'] if item['sku'] == sku)
            self.assertGreater(item['bultos'], 0)
            self.assertGreater(item['unidades'], 0)

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
        pallet = plan_for_capacity([liter, other], 1)['mixed_pallets'][0]
        self.assertEqual([i['sku'] for i in pallet['items']], ['RET', 'LATA'])

    def test_equal_liter_formats_share_a_pallet(self):
        rows = [row(20, sku='RET-A', calibre='1000 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ'),
                row(20, sku='RET-B', calibre='1000 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ')]
        roomy = plan_for_capacity(rows, 3)
        self.assertFalse(roomy['automatic_mix'])
        self.assertEqual(roomy['mixed_count'], 2)
        plan = plan_for_capacity(rows, 1)
        self.assertTrue(plan['automatic_mix'])
        self.assertEqual(plan['mixed_count'], 1)
        self.assertEqual([(item['sku'], item['bultos']) for item in plan['mixed_pallets'][0]['items']],
                         [('RET-A', 20), ('RET-B', 20)])

    def test_975_and_1000_returnables_share_identical_geometry(self):
        rows = [row(20, sku='RET-1000', calibre='1000 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ'),
                row(20, sku='RET-975', calibre='975 CC VIDRIO', floor=10,
                    bottom=True, priority=100, business_unit='CERVEZAS CMQ')]
        roomy = plan_for_capacity(rows, 3)
        self.assertEqual(roomy['mixed_count'], 2)
        plan = plan_for_capacity(rows, 1)
        self.assertTrue(plan['automatic_mix'])
        self.assertEqual(plan['mixed_count'], 1)
        self.assertEqual({item['sku'] for item in plan['mixed_pallets'][0]['items']}, {'RET-1000', 'RET-975'})

    def test_same_court_is_completed_before_cross_court_mixing(self):
        rows = [row(30, court=1, sku='A'), row(10, court=2, sku='C'), row(20, court=1, sku='B')]
        plan = simulate_pallets(rows, 2, True)
        first = plan['mixed_pallets'][0]
        self.assertEqual(first['occupancy'], 1)
        self.assertEqual(first['courts'], [1])
        self.assertEqual({item['sku'] for item in first['items']}, {'A', 'B'})

    def test_largest_stable_complete_floor_has_priority_over_size_rank(self):
        rows = [row(10, sku='RANGO-ALTO', rank=5000, floor=10),
                row(30, sku='MAS-BULTOS', rank=100, floor=10)]
        pallet = simulate_pallets(rows, 1)['mixed_pallets'][0]
        self.assertEqual([item['sku'] for item in pallet['items']], ['MAS-BULTOS', 'RANGO-ALTO'])
        rows[1]['stable'] = False
        pallet = simulate_pallets(rows, 1)['mixed_pallets'][0]
        self.assertEqual(pallet['items'][0]['sku'], 'RANGO-ALTO')

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

    def test_supervisor_can_split_item_quantities_between_pallets(self):
        plan = simulate_pallets([row(20, court=1, sku='COLA'), row(10, court=2, sku='AGUA')], 2, False)
        first, second = plan['mixed_pallets']
        cola = first['items'][0]
        submitted = [dict(first, items=[dict(cola, bultos=8, unidades=0)], owner_court=1),
                     dict(second, items=second['items'] + [dict(cola, bultos=12, unidades=0)], owner_court=2)]
        edited = apply_manual_pallets(plan, submitted, [1])
        cola_parts = [item['bultos'] for pallet in edited['mixed_pallets'] for item in pallet['items'] if item['sku'] == 'COLA']
        self.assertEqual(sorted(cola_parts), [8, 12])
        self.assertEqual(sum(cola_parts), 20)
        self.assertEqual(edited['mixed_pallets'][1]['owner_court'], 2)

    def test_manual_split_rejects_lost_or_duplicated_quantities(self):
        plan = simulate_pallets([row(20)], 2, False)
        original = plan['mixed_pallets'][0]
        item = original['items'][0]
        with self.assertRaisesRegex(ValueError, 'afuera|cantidades'):
            apply_manual_pallets(plan, [dict(original, items=[dict(item, bultos=19)], owner_court=1)], [1])
        with self.assertRaisesRegex(ValueError, 'duplica|cantidades'):
            apply_manual_pallets(plan, [dict(original, items=[dict(item, bultos=21)], owner_court=1)], [1])


class PhysicalLimitsTest(unittest.TestCase):
    def config(self, **changes):
        value = dict(pallet_base_height_cm=10, reference_pallet_height_cm=110,
            max_pallet_height_cm=110, empty_pallet_weight_kg=20, max_pallet_weight_kg=None,
            max_payload_kg=None, safety_margin_pct=0, height_excess_mode='block',
            pallet_weight_excess_mode='block', truck_weight_excess_mode='block',
            share_floor_remainders=False, weight_tiebreaker=False)
        value.update(changes)
        return value

    def test_incomplete_floor_uses_a_whole_layer(self):
        pallet = simulate_pallets([row(11, weight=10)], 2, configuration=self.config())['mixed_pallets'][0]
        self.assertEqual(pallet['height_cm'], 50)

    def test_equal_remainders_share_a_layer_only_when_enabled(self):
        rows = [row(5, sku='A', weight=1), row(5, sku='B', weight=1)]
        separate = simulate_pallets(rows, 2, configuration=self.config(max_pallet_height_cm=40))
        shared = simulate_pallets(rows, 2, configuration=self.config(max_pallet_height_cm=40, share_floor_remainders=True))
        self.assertEqual(separate['mixed_count'], 2)
        self.assertEqual(shared['mixed_count'], 1)
        self.assertEqual(shared['mixed_pallets'][0]['height_cm'], 30)
        different = [row(5, sku='A', weight=1), row(4, sku='B', floor=8, bpp=48, weight=1)]
        self.assertEqual(simulate_pallets(different, 2, configuration=self.config(max_pallet_height_cm=40, share_floor_remainders=True))['mixed_count'], 2)

    def test_lower_height_limit_reduces_mixed_pallet_layers(self):
        plan = simulate_pallets([row(40, weight=1)], 3, configuration=self.config(max_pallet_height_cm=70))
        self.assertEqual(plan['mixed_count'], 2)
        self.assertTrue(all(p['height_cm'] <= 70 for p in plan['mixed_pallets']))

    def test_weight_limit_and_margin_split_a_pallet(self):
        no_margin = simulate_pallets([row(40, weight=10)], 2,
            configuration=self.config(max_pallet_weight_kg=420, height_excess_mode='inform'))
        margin = simulate_pallets([row(40, weight=10)], 3,
            configuration=self.config(max_pallet_weight_kg=420, safety_margin_pct=10, height_excess_mode='inform'))
        self.assertEqual(no_margin['mixed_count'], 1)
        self.assertEqual(margin['mixed_count'], 2)

    def test_inform_mode_reports_without_splitting_or_blocking(self):
        plan = simulate_pallets([row(40, weight=10)], 1,
            configuration=self.config(max_pallet_weight_kg=200, pallet_weight_excess_mode='inform', height_excess_mode='inform'))
        self.assertEqual(plan['mixed_count'], 1)
        self.assertTrue(plan['mixed_pallets'][0]['weight_exceeded'])
        self.assertTrue(plan['fits_estimate'])

    def test_full_pallet_is_flagged_but_never_split(self):
        inform = simulate_pallets([row(50, weight=20)], 1,
            configuration=self.config(max_pallet_weight_kg=500, pallet_weight_excess_mode='inform'))
        self.assertEqual(inform['full_count'], 1)
        self.assertTrue(inform['full_pallets'][0]['weight_exceeded'])
        blocked = simulate_pallets([row(50, weight=20)], 1,
            configuration=self.config(max_pallet_weight_kg=500, pallet_weight_excess_mode='block'))
        self.assertEqual(blocked['full_count'], 1)
        self.assertFalse(blocked['fits_estimate'])

    def test_weight_is_only_a_tiebreaker(self):
        rows = [row(10, sku='LIVIANO', weight=1, rank=500, priority=10),
                row(10, sku='PESADO', weight=10, rank=500, priority=10)]
        plan = simulate_pallets(rows, 1, configuration=self.config(weight_tiebreaker=True, height_excess_mode='inform'))
        self.assertEqual([item['sku'] for item in plan['mixed_pallets'][0]['items']], ['PESADO', 'LIVIANO'])

    def test_truck_can_fit_positions_but_exceed_payload_and_tare_is_counted(self):
        plan = simulate_pallets([row(100, weight=10)], 2,
            configuration=self.config(max_payload_kg=1000, height_excess_mode='inform'))
        self.assertEqual(plan['total_pallets'], 2)
        self.assertEqual(plan['truck_weight_known_kg'], 1040)
        self.assertEqual(plan['truck_weight_excess_kg'], 40)
        self.assertFalse(plan['fits_estimate'])

    def test_missing_weight_is_explicit_and_does_not_break_plan(self):
        plan = simulate_pallets([row(10, sku='SIN-PESO')], 1, configuration=self.config())
        self.assertEqual(plan['missing_weights'], ['SIN-PESO'])
        self.assertFalse(plan['weight_complete'])
        self.assertIsNone(plan['truck_weight_kg'])

    def test_empty_configuration_keeps_original_pallet_counts(self):
        rows = [row(25, court=1), row(25, court=2, sku='B')]
        self.assertEqual(simulate_pallets(rows, 4, True)['total_pallets'], simulate_pallets(rows, 4, True, configuration={})['total_pallets'])

    def test_manual_plan_rejects_height_and_weight(self):
        height_plan = simulate_pallets([row(20, weight=1)], 2,
            configuration=self.config(max_pallet_height_cm=110, height_excess_mode='inform'))
        height_plan['configuration'].update(max_pallet_height_cm=20, height_excess_mode='block')
        with self.assertRaisesRegex(ValueError, 'altura'):
            apply_manual_pallets(height_plan, height_plan['mixed_pallets'], [1])
        weight_plan = simulate_pallets([row(20, weight=10)], 2,
            configuration=self.config(max_pallet_weight_kg=500, pallet_weight_excess_mode='inform'))
        weight_plan['configuration'].update(max_pallet_weight_kg=100, pallet_weight_excess_mode='block')
        with self.assertRaisesRegex(ValueError, 'peso'):
            apply_manual_pallets(weight_plan, weight_plan['mixed_pallets'], [1])


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
