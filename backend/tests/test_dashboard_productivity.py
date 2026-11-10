"""Productivity separates preparation modalities, pauses and stock causes."""
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from test_load_control import ControlFlowTest, db, tearDownModule
from services.load_control import ControlTruck


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class DashboardProductivityTest(Fixture):
    def report(self, query='', user='admin', expected=200):
        response = self.client.get('/api/dashboard/productivity'+query,
            headers={'Authorization': 'Bearer '+self.tokens[user]})
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response.json

    def stabilize(self, path, active_seconds=3600, wall_seconds=5400):
        check_id = path.rsplit('/', 1)[-1]
        truck = db.session.get(ControlTruck, self.truck_id)
        state = deepcopy(truck.state)
        check = state['courts'][f'{self.load_id}:1']['checks']['0']
        self.assertEqual(check['id'], check_id)
        check.update(active_seconds=active_seconds, timer_started_at=None,
            started_at=(datetime.now(timezone.utc)-timedelta(seconds=wall_seconds)).isoformat())
        truck.state = state
        db.session.commit()

    def test_operator_productivity_uses_active_time_and_reports_pause(self):
        path = self.start(0, 'picker')
        self.answer(path, '1001', 'picker')
        self.answer(path, '1002', 'picker')
        self.stabilize(path)
        report = self.report('?desde=2026-10-15&hasta=2026-10-15')
        row = next(item for item in report['rows'] if item['username'] == 'picker')
        self.assertEqual(row['bultos'], 9)
        self.assertEqual(row['lineas'], 2)
        self.assertEqual(row['tiempo_efectivo_segundos'], 3600)
        self.assertGreaterEqual(row['tiempo_pausa_segundos'], 1799)
        self.assertEqual(row['productividad_bultos_hora'], 9)
        self.assertEqual(row['cobertura_pct'], 100)
        self.assertEqual(row['modalidades']['picking']['productividad_bultos_hora'], 9)
        self.assertEqual(report['evolution'][0]['productividad_bultos_hora'], 9)

    def test_stock_is_excluded_but_picking_error_is_attributed(self):
        path = self.start(0, 'picker')
        self.answer(path, '1001', 'picker', 'shortage', physical_b=0, physical_u=0, shortage_reason='stock')
        report = self.report('?operario='+str(self.client.get('/api/auth/me', headers={
            'Authorization':'Bearer '+self.tokens['picker']}).json['user']['id']))
        picker = report['rows'][0]
        self.assertEqual(picker['diferencias_atribuidas'], 0)

        self.answer(path, '1002', 'picker', 'shortage', physical_b=0, physical_u=0,
                    shortage_reason='rotura')
        report = self.report()
        picker = next(item for item in report['rows'] if item['username'] == 'picker')
        self.assertEqual(picker['diferencias_atribuidas'], 1)

    def test_pallet_mode_is_separate_and_controls_are_excluded(self):
        truck = db.session.get(ControlTruck, self.truck_id)
        state = deepcopy(truck.state)
        court = state['courts'].setdefault(f'{self.load_id}:1', {'checks': {}, 'shortages': {}})
        pallet_user = self.client.get('/api/auth/me', headers={
            'Authorization':'Bearer '+self.tokens['pallet']}).json['user']
        court['checks']['4'] = dict(id='pallet-prep', stage=4, user_id=pallet_user['id'], username='pallet',
            status='done', started_at=(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(), active_seconds=3600, timer_started_at=None,
            answers={'1001': dict(sku='1001', physical_b=10, physical_u=0,
                measurement=dict(units_per_case=12))})
        court['checks']['1'] = dict(id='control', stage=1, user_id=pallet_user['id'], username='pallet',
            status='done', started_at=(datetime.now(timezone.utc)-timedelta(hours=3)).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(), active_seconds=3600, timer_started_at=None,
            answers={'1001': dict(sku='1001', physical_b=999, physical_u=0,
                measurement=dict(units_per_case=12))})
        truck.state = state
        db.session.commit()
        report = self.report()
        row = next(item for item in report['rows'] if item['username'] == 'pallet')
        self.assertEqual(row['bultos'], 10)
        self.assertEqual(row['lineas'], 1)
        self.assertEqual(row['productividad_bultos_hora'], 10)
        self.assertNotIn('picking', row['modalidades'])
        self.assertEqual(row['modalidades']['pallets_completos']['bultos'], 10)

    def test_filters_permissions_and_no_work(self):
        self.assertEqual(self.report()['rows'], [])
        self.assertEqual(self.report('?desde=bad', expected=400)['error'], 'desde debe tener formato AAAA-MM-DD.')
        self.report(user='picker', expected=403)

    def test_legacy_naive_running_timestamp_does_not_break_report(self):
        truck = db.session.get(ControlTruck, self.truck_id)
        state = deepcopy(truck.state)
        picker = self.client.get('/api/auth/me', headers={
            'Authorization':'Bearer '+self.tokens['picker']}).json['user']
        court = state.setdefault('courts', {}).setdefault(f'{self.load_id}:1', {'checks': {}, 'shortages': {}})
        court['checks']['0'] = dict(id='legacy', stage=0,
            user_id=picker['id'], username='picker', status='active',
            started_at='2026-10-15T10:00:00', timer_started_at='2026-10-15T10:00:00',
            active_seconds=0, answers={'1001': dict(physical_b=5, physical_u=0,
                measurement=dict(units_per_case=12))})
        truck.state = state
        db.session.commit()
        row = self.report()['rows'][0]
        self.assertEqual(row['bultos'], 5)
        self.assertIsNone(row['productividad_bultos_hora'])


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(DashboardProductivityTest)


if __name__ == '__main__':
    unittest.main()
