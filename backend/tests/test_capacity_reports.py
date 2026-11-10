"""Capacity scenarios stay hypothetical and CSV exports match dashboard projections."""
import unittest

from test_load_control import ControlFlowTest, db, tearDownModule
from services.capacity_simulator import simulate_capacity
from services.load_control import ControlTruck


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class CapacityReportsTest(Fixture):
    def post_simulator(self, payload, user='admin', expected=200):
        response = self.client.post('/api/dashboard/capacity-simulator', json=payload,
            headers={'Authorization': 'Bearer ' + self.tokens[user]})
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response.json

    def export(self, report, query='?desde=2026-10-15&hasta=2026-10-15', user='admin', expected=200):
        response = self.client.get(f'/api/dashboard/export/{report}.csv{query}',
            headers={'Authorization': 'Bearer ' + self.tokens[user]})
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response

    def test_capacity_formula_and_zero_denominators(self):
        result = self.post_simulator({'operators': 5, 'hours': 8, 'productivity': 40, 'demand': 1500})
        self.assertTrue(result['hypothetical'])
        self.assertEqual(result['capacity'], 1600)
        self.assertEqual(result['coverage_pct'], 106.7)
        self.assertEqual(result['difference'], 100)
        self.assertEqual(result['additional_operators'], 0)
        self.assertEqual(result['required_hours'], 7.5)
        zero = simulate_capacity({'operators': 0, 'hours': 0, 'productivity': 0, 'demand': 10})
        self.assertIsNone(zero['additional_operators'])
        self.assertIsNone(zero['required_hours'])
        no_demand = simulate_capacity({'operators': 2, 'hours': 8, 'productivity': 10, 'demand': 0})
        self.assertIsNone(no_demand['coverage_pct'])

    def test_simulator_validation_and_permissions(self):
        self.post_simulator({'operators': 1.5, 'hours': 8, 'productivity': 10, 'demand': 10}, expected=400)
        self.post_simulator({'operators': 2, 'hours': 25, 'productivity': 10, 'demand': 10}, expected=400)
        self.post_simulator({'operators': 2, 'hours': 8, 'productivity': 10, 'demand': 10}, user='picker', expected=403)

    def test_operations_export_reconciles_row_count_and_neutralizes_formulas(self):
        truck = db.session.get(ControlTruck, self.truck_id)
        truck.truck = '=CMD()'
        db.session.commit()
        response = self.export('operations')
        text = response.get_data(as_text=True)
        dashboard = self.client.get('/api/dashboard/operations?desde=2026-10-15&hasta=2026-10-15',
            headers={'Authorization': 'Bearer ' + self.tokens['admin']}).json
        self.assertEqual(int(response.headers['X-Report-Rows']), len(dashboard['rows']))
        self.assertTrue(text.startswith('\ufeff'))
        self.assertIn("'=CMD()", text)
        self.assertIn('attachment;', response.headers['Content-Disposition'])

    def test_all_exports_and_range_limits(self):
        for report in ('operations', 'productivity', 'quality'):
            self.assertEqual(self.export(report).mimetype, 'text/csv')
        self.export('operations', query='', expected=400)
        self.export('operations', '?desde=2025-01-01&hasta=2026-10-15', expected=400)
        self.export('unknown', expected=404)
        self.export('operations', user='picker', expected=403)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(CapacityReportsTest)


if __name__ == '__main__':
    unittest.main()
