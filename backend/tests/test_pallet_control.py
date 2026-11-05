import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.pallet_control import physical_pallets, claim_assignment


class PalletControlTest(unittest.TestCase):
    def truck(self):
        load = SimpleNamespace(id=7, reparto='68045')
        plan = {'mixed_pallets': [dict(id='M001', load_id=7, owner_court=5, occupancy=.8,
                    items=[dict(sku='A', descripcion='A', bultos=4, unidades=2, court=2)])],
                'full_pallets': [dict(id='F001', load_id=7, reparto='68045', court=1, sku='B',
                    descripcion='B', pallets=2, bultos=100, bultos_por_pallet=50)]}
        return SimpleNamespace(state={'planning': plan}, loads=[load])

    def test_expands_every_physical_pallet(self):
        pallets = physical_pallets(self.truck())
        self.assertEqual([p['id'] for p in pallets], ['M001', 'F001-01', 'F001-02'])
        self.assertEqual([p['owner_court'] for p in pallets], [5, 1, 1])
        self.assertEqual([p['items'][0]['bultos'] for p in pallets], [4, 50, 50])

    def test_assignments_are_crossed_and_exclusive(self):
        state = {}
        angel, piojo = SimpleNamespace(id=1, username='angel'), SimpleNamespace(id=2, username='piojo')
        claim_assignment(state, 1, angel)
        with self.assertRaises(PermissionError): claim_assignment(state, 2, angel)
        claim_assignment(state, 2, piojo)
        with self.assertRaises(ValueError): claim_assignment(state, 1, piojo)


if __name__ == '__main__': unittest.main()
