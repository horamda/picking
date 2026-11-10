"""Quality KPIs and shortage review stay explicit and auditable."""
import unittest

from test_load_control import ControlFlowTest, tearDownModule


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class DashboardQualityTest(Fixture):
    def report(self, query='', user='admin', expected=200):
        response = self.client.get('/api/dashboard/quality' + query,
            headers={'Authorization': 'Bearer ' + self.tokens[user]})
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response.json

    def test_empty_period_reports_unavailable_percentages(self):
        metrics = self.report('?desde=2026-10-15&hasta=2026-10-15')['metrics']
        self.assertIsNone(metrics['exactitud_picking_pct'])
        self.assertIsNone(metrics['diferencias_stock_pct'])
        self.assertIsNone(metrics['retrabajo_pct'])
        self.assertIsNone(metrics['exactitud_segundo_control_lineas_pct'])
        self.assertIsNone(metrics['exactitud_segundo_control_unidades_pct'])

    def test_picking_quality_separates_stock_from_attributable_errors(self):
        path = self.start(0, 'picker')
        self.answer(path, '1001', 'picker', 'shortage', physical_b=0, physical_u=0,
                    shortage_reason='stock')
        self.answer(path, '1002', 'picker', 'shortage', physical_b=0, physical_u=0,
                    shortage_reason='rotura')
        report = self.report('?sucursal=Central&camion=ABC123&reparto=0001')
        metrics = report['metrics']
        self.assertEqual(metrics['lineas_preparacion'], 2)
        self.assertEqual(metrics['errores_picking'], 1)
        self.assertEqual(metrics['diferencias_stock'], 1)
        self.assertEqual(metrics['exactitud_picking_pct'], 50)
        self.assertEqual(metrics['diferencias_stock_pct'], 50)
        self.assertEqual({row['origin'] for row in report['incidents']}, {'picking', 'stock'})
        self.assertEqual(sum(row['count'] for row in report['causes']), 2)

    def test_confirmed_shortage_does_not_penalize_second_control(self):
        self.complete(1, 'ana', shortage=True)
        self.complete(2, 'ben', shortage=True)
        metrics = self.report()['metrics']
        self.assertEqual(metrics['lineas_segundo_control'], 2)
        self.assertEqual(metrics['errores_segundo_control'], 0)
        self.assertEqual(metrics['exactitud_segundo_control_lineas_pct'], 100)
        self.assertIsNone(metrics['exactitud_segundo_control_unidades_pct'])

    def test_review_workflow_requires_reason_and_preserves_history(self):
        self.complete(1, 'ana', shortage=True)
        self.complete(2, 'ben', shortage=True)
        path = f'/loads/{self.load_id}/courts/1/shortages/1001'
        self.call('post', path + '/review', 'super', expected=400, data={'reason': 'x'})
        self.call('post', path + '/review', 'super', data={'reason': 'Verificar ubicacion'})
        self.call('post', path + '/recount', 'super', data={'reason': 'Segundo conteo requerido'})
        shortage = self.call('get', '/trucks')[0]['status']['shortages'][0]
        self.assertEqual(shortage['review_status'], 'recuento_solicitado')
        self.assertEqual([event['status'] for event in shortage['review_history']],
                         ['en_revision', 'recuento_solicitado'])
        incident = self.report()['incidents'][0]
        self.assertEqual(incident['status'], 'recuento_solicitado')
        self.assertEqual(len(incident['review_history']), 2)
        self.call('post', path + '/approve', 'super')
        self.call('post', path + '/reject', 'super', expected=409, data={'reason': 'No aplica'})

    def test_filters_validation_and_permissions(self):
        self.assertEqual(self.report('?sucursal=Otra')['metrics']['lineas_preparacion'], 0)
        self.assertEqual(self.report('?desde=bad', expected=400)['error'],
                         'desde debe tener formato AAAA-MM-DD.')
        self.assertEqual(self.report('?estado=otro', expected=400)['error'],
                         'Estado operativo inválido.')
        self.report(user='picker', expected=403)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(DashboardQualityTest)


if __name__ == '__main__':
    unittest.main()
