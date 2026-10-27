import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.pallet_planning import simulate_pallets


def row(b=244, u=0, court=1, bpp=50, upb=12, sku='BRAHMA'):
    return dict(load_id=1, reparto='R1', court=court, sku=sku, descripcion=sku,
                bultos=b, unidades=u, bultos_por_pallet=bpp, unidades_por_bulto=upb)


class PlanningTest(unittest.TestCase):
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


if __name__ == '__main__': unittest.main()
