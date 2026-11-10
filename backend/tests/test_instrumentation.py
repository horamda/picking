"""Additive measurement and incident regression on the disposable API fixture."""
import json
import os
import unittest
from copy import deepcopy
from unittest.mock import patch

from test_load_control import ControlFlowTest, db, tearDownModule
from models import Article, LogEntry
from services.load_control import ControlTruck, answer_measurement


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class InstrumentationTest(Fixture):
    def setUp(self):
        super().setUp()
        self.flag = patch.dict(os.environ, KPI_INSTRUMENTATION_ENABLED='1')
        self.flag.start()
        self.addCleanup(self.flag.stop)

    def test_legacy_client_records_actual_and_expected_without_new_request_fields(self):
        path = self.start(0, 'picker')
        saved = self.answer(path, '1001', 'picker', 'shortage', physical_b=2, physical_u=0)
        answer = saved['answers']['1001']
        self.assertEqual(answer['physical_b'], 2)
        self.assertEqual(answer['measurement']['expected_b'], 5)
        self.assertEqual(answer['measurement']['expected_u'], 0)
        self.assertEqual(answer['measurement']['units_per_case'], 12)
        self.assertEqual(answer['measurement']['confirmation_source'], 'unknown')
        self.assertEqual(answer['measurement']['process_id'], saved['id'])
        self.assertEqual(answer['shortage_reason'], 'no_localizado')
        event = LogEntry.query.filter_by(action='respuesta_control').one()
        details = json.loads(event.details)
        self.assertEqual(details['process_id'], saved['id'])
        self.assertEqual(details['measurement'], answer['measurement'])
        self.assertEqual(details['load_id'], self.load_id)

    def test_stock_is_not_an_operator_error_and_preserves_detector(self):
        path = self.start(0, 'picker')
        saved = self.answer(path, '1001', 'picker', 'shortage', physical_b=0,
                            physical_u=0, shortage_reason='stock')
        incident = saved['answers']['1001']['incident']
        self.assertEqual(incident['origin'], 'stock')
        self.assertEqual(incident['error_count'], 0)
        self.assertIsNone(incident['responsible_user_id'])
        self.assertEqual(incident['detected_username'], 'picker')
        report = self.call('get', '/performance')
        self.assertEqual(report['incidents'][0]['incident'], incident)

    def test_replay_keeps_original_factor_and_one_business_event(self):
        path = self.start(0, 'picker')
        payload = dict(sku='1001', result='ok', request_id='11111111-1111-4111-8111-111111111111')
        first = self.call('post', path+'/answer', 'picker', data=payload)
        article = Article.query.filter_by(sku='1001').one()
        article.unidades_por_bulto = 24
        db.session.commit()
        replay = self.call('post', path+'/answer', 'picker', data=payload)
        self.assertEqual(first['answers'], replay['answers'])
        self.assertEqual(LogEntry.query.filter_by(action='respuesta_control').count(), 1)
        self.call('post', path+'/answer', 'picker', expected=409, data=dict(payload, result='shortage'))
        self.assertEqual(LogEntry.query.filter_by(action='respuesta_control').count(), 1)

    def test_capture_can_be_disabled_without_removing_previous_answers(self):
        path = self.start(0, 'picker')
        first = self.answer(path, '1001', 'picker')['answers']['1001']
        with patch.dict(os.environ, KPI_INSTRUMENTATION_ENABLED='0'):
            saved = self.answer(path, '1002', 'picker')
        self.assertNotIn('measurement', saved['answers']['1002'])
        self.assertEqual(saved['answers']['1001'], first)

    def test_snapshot_factor_is_preferred_and_missing_catalog_is_unknown(self):
        check = {'id': 'example'}
        measured = answer_measurement(dict(sku='1001', bultos=2, unidades=3, unidades_por_bulto=6), check)['measurement']
        self.assertEqual(measured['units_per_case'], 6)
        self.assertEqual(measured['units_per_case_source'], 'task_snapshot')
        measured = answer_measurement(dict(sku='MISSING', bultos=2, unidades=3), check)['measurement']
        self.assertIsNone(measured['units_per_case'])
        self.assertIsNone(measured['units_per_case_source'])

    def test_invalid_reason_and_wrong_user_do_not_create_measurements(self):
        path = self.start(0, 'picker')
        self.answer(path, '1001', 'picker', 'shortage', expected=400,
                    physical_b=0, physical_u=0, shortage_reason='invented')
        self.answer(path, '1001', 'ana', expected=403)
        self.assertEqual(LogEntry.query.filter_by(action='respuesta_control').count(), 0)

    def test_pallet_measurement_replay_and_freshness_incidents_are_distinct(self):
        path = self.start(0, 'picker')
        self.call('post', path+'/finish', 'picker')
        truck = db.session.get(ControlTruck, self.truck_id)
        state = deepcopy(truck.state)
        pallet = state['planning']['mixed_pallets'][0]
        original = pallet['items'][0]
        pallet['items'] = [dict(original, product_key=original['sku']+'|'+day, fecha_frescura=day)
                           for day in ('2027-01-01', '2027-02-01')]
        truck.state = state
        db.session.commit()
        check = self.call('post', f'/loads/{self.load_id}/pallets/{pallet["id"]}/start/1', 'ana')
        endpoint = f'/loads/{self.load_id}/pallets/{pallet["id"]}/checks/1/{check["id"]}/answer'
        for index, product in enumerate(check['products']):
            payload = dict(sku=product['sku'], product_key=product['product_key'],
                result='shortage', physical_b=0, physical_u=0, error_type='stock',
                request_id=f'11111111-1111-4111-8111-{index:012d}')
            first = self.call('post', endpoint, 'ana', data=payload)
            replay = self.call('post', endpoint, 'ana', data=payload)
            self.assertEqual(first['answers'], replay['answers'])
            self.assertEqual(first['answers'][product['product_key']]['measurement']['expected_b'], product['bultos'])
        db.session.expire_all()
        incidents = db.session.get(ControlTruck, self.truck_id).state['incidents']
        self.assertEqual(len(incidents), 2)
        self.assertEqual(len({row['product_key'] for row in incidents.values()}), 2)
        events = LogEntry.query.filter_by(action='respuesta_control_pallet').all()
        self.assertEqual(len(events), 2)
        self.assertTrue(all(json.loads(event.details)['process_id'] == check['id'] for event in events))

        # Previously deployed code keyed a freshness incident by SKU only.
        # A later correction must update that incident, not count it twice.
        truck = db.session.get(ControlTruck, self.truck_id)
        state = deepcopy(truck.state)
        product = check['products'][0]
        canonical = f'{check["id"]}:{pallet["id"]}:{product["product_key"]}'
        legacy = f'{check["id"]}:{pallet["id"]}:{product["sku"]}'
        state['incidents'][legacy] = state['incidents'].pop(canonical)
        truck.state = state
        db.session.commit()
        self.call('post', endpoint, 'ana', data=dict(sku=product['sku'], product_key=product['product_key'],
            result='shortage', physical_b=0, physical_u=0, error_type='stock', note='Revisado'))
        db.session.expire_all()
        incidents = db.session.get(ControlTruck, self.truck_id).state['incidents']
        self.assertEqual(len(incidents), 2)
        self.assertEqual(incidents[legacy]['note'], 'Revisado')


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(InstrumentationTest)


if __name__ == '__main__':
    unittest.main()
