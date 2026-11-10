"""Operational dashboard uses real control state without inventing unavailable data."""
import unittest

from test_load_control import ControlFlowTest, tearDownModule


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class DashboardOperationsTest(Fixture):
    def dashboard(self, query='', user='admin', expected=200):
        response = self.client.get('/api/dashboard/operations'+query,
            headers={'Authorization': 'Bearer '+self.tokens[user]})
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response.json

    def test_pending_load_and_unavailable_metrics_are_explicit(self):
        report = self.dashboard('?desde=2026-10-15&hasta=2026-10-15')
        metrics = report['metrics']
        self.assertEqual(metrics['planillas_programadas'], 1)
        self.assertEqual(metrics['planillas_pendientes'], 1)
        self.assertEqual(metrics['planillas_en_preparacion'], 0)
        self.assertIsNone(metrics['bultos_confirmados'])
        self.assertIsNone(metrics['bultos_pendientes'])
        self.assertIsNone(metrics['operarios_disponibles'])
        self.assertIsNone(metrics['cargas_demoradas'])
        self.assertIn('factor histórico', report['coverage']['bultos_pendientes'])
        self.assertEqual(report['rows'][0]['estado'], 'pendiente')

    def test_live_answer_reports_confirmed_cases_coverage_and_operator_filter(self):
        path = self.start(0, 'picker')
        self.answer(path, '1001', 'picker')
        report = self.dashboard('?desde=2026-10-15&hasta=2026-10-15')
        metrics = report['metrics']
        self.assertEqual(metrics['planillas_en_preparacion'], 1)
        self.assertEqual(metrics['operarios_en_proceso'], 1)
        self.assertEqual(metrics['bultos_confirmados'], 5)
        self.assertEqual(report['coverage']['respuestas_medibles_pct'], 100)
        if metrics['productividad_bultos_hora'] is not None:
            self.assertGreater(metrics['productividad_bultos_hora'], 0)
        picker = next(row for row in report['options']['operarios'] if row['username'] == 'picker')
        filtered = self.dashboard(f'?desde=2026-10-15&operario={picker["id"]}')
        self.assertEqual(filtered['metrics']['planillas_programadas'], 1)
        empty = self.dashboard('?desde=2026-10-15&operario=999999')
        self.assertEqual(empty['metrics']['planillas_programadas'], 0)

    def test_stock_difference_alert_and_filters_use_selected_loads(self):
        path = self.start(0, 'picker')
        self.answer(path, '1001', 'picker', 'shortage', physical_b=0, physical_u=0,
                    shortage_reason='stock')
        report = self.dashboard('?sucursal=Central&camion=ABC123&reparto=0001&estado=en_preparacion')
        self.assertEqual(report['metrics']['diferencias_detectadas'], 1)
        self.assertEqual(report['metrics']['alertas_operativas'], 1)
        self.assertEqual(report['alert_breakdown']['diferencias_preparacion'], 1)
        self.assertEqual(report['rows'][0]['reparto'], '0001')
        self.assertEqual(self.dashboard('?sucursal=Otra')['metrics']['planillas_programadas'], 0)
        self.assertEqual(self.dashboard('?estado=desconocido', expected=400)['error'], 'Estado operativo inválido.')

    def test_invalid_dates_and_permissions_are_rejected(self):
        self.assertEqual(self.dashboard('?desde=15-10-2026', expected=400)['error'],
                         'desde debe tener formato AAAA-MM-DD.')
        self.assertEqual(self.dashboard('?desde=2026-10-16&hasta=2026-10-15', expected=400)['error'],
                         'La fecha desde no puede ser posterior a la fecha hasta.')
        self.dashboard(user='picker', expected=403)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(DashboardOperationsTest)


if __name__ == '__main__':
    unittest.main()
