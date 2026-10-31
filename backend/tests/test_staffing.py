"""Weekly planning uses isolated fixtures, never Railway."""
from test_load_control import ControlFlowTest, db, tearDownModule
from models import User
from services.staffing import activate_due_week, StaffingWeek
from services.warehouse import assigned_courts
from services.load_control import ControlTruck, ControlTimer
from datetime import date
from unittest.mock import patch
import unittest


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class StaffingTest(Fixture):
    def setUp(self):
        super().setUp()
        self.addCleanup(patch.stopall)
        patch.dict('os.environ', {'STAFFING_ENABLED': '1'}).start()
        patch('routes.staffing.local_day', return_value=date(2026, 10, 30)).start()

    def test_future_publication_activation_and_idempotence(self):
        path = '/staffing/weeks/2026-11-02'
        plan = self.call('get', path)
        picker = User.query.filter_by(username='picker').one().id
        plan['draft'][str(picker)] = [2, 3]
        saved = self.call('put', path, data=dict(version=0, assignments=plan['draft']))
        self.call('post', path+'/publish', data=dict(version=saved['version']))
        self.assertEqual(assigned_courts(picker), [1])
        self.assertFalse(activate_due_week(date(2026, 10, 30)))
        self.assertTrue(activate_due_week(date(2026, 11, 2)))
        self.assertEqual(assigned_courts(picker), [2, 3])
        self.assertFalse(activate_due_week(date(2026, 11, 2)))
        self.assertEqual(StaffingWeek.query.count(), 1)
        self.call('put', path, data=dict(version=self.call('get',path)['version'], assignments=plan['draft']), expected=409)

    def test_rotation_preserves_answers_and_archives_time(self):
        check = self.call('post', f'/loads/{self.load_id}/courts/1/start/0', 'picker')
        self.call('post', f'/loads/{self.load_id}/courts/1/checks/0/{check["id"]}/answer', 'picker', data=dict(sku='1001',result='ok'))
        path = '/staffing/weeks/2026-11-02'
        plan = self.call('get',path)
        picker = User.query.filter_by(username='picker').one().id
        plan['draft'][str(picker)] = [2]
        saved = self.call('put',path,data=dict(version=0,assignments=plan['draft']))
        self.call('post',path+'/publish',data=dict(version=saved['version']))
        activate_due_week(date(2026,11,2))
        state = db.session.get(ControlTruck,self.truck_id).state
        current = state['courts'][f'{self.load_id}:1']['checks']['0']
        self.assertIsNone(current['user_id'])
        self.assertIn('1001',current['answers'])
        self.assertEqual(state['archived_checks'][-1]['user_id'],picker)
        self.assertEqual(ControlTimer.query.filter_by(user_id=picker).count(),0)

    def test_roles_invalid_dates_and_stale_versions(self):
        path='/staffing/weeks/2026-11-02'
        self.call('get',path,'picker',expected=403)
        self.call('get','/staffing/weeks/2026-11-03',expected=400)
        plan=self.call('get',path)
        self.call('put',path,data=dict(version=0,assignments=plan['draft']))
        self.call('put',path,data=dict(version=0,assignments=plan['draft']),expected=409)
        self.call('post',path+'/publish',data=dict(version=0),expected=409)
        self.call('put',path,data=dict(version=1,assignments={}),expected=409)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(StaffingTest)


if __name__ == '__main__':
    unittest.main()
