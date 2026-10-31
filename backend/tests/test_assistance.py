from test_load_control import ControlFlowTest, db, tearDownModule
from models import User, Role
from auth import AuthService
from services.load_control import ControlTruck
from services.assistance import pause_expired
from services.push import available_tasks
from datetime import date
from unittest.mock import patch
import unittest


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class AssistanceTest(Fixture):
    def setUp(self):
        super().setUp()
        self.addCleanup(patch.stopall)
        patch.dict('os.environ', {'STAFFING_ENABLED': '1'}).start()
        helper = User(username='helper',email='helper@test.local',active=True,
            password_hash=AuthService.hash_password('TestPassword123!'),role=Role.query.filter_by(name='operador').one())
        db.session.add(helper); db.session.commit()
        self.helper_id = helper.id
        self.tokens['helper'] = AuthService.generate_token(helper)
        self.start_path = f'/loads/{self.load_id}/courts/1/start/0'
        self.assignment_path = f'/loads/{self.load_id}/courts/1/assistance/0'

    def assign(self, skus, expected=201):
        version = db.session.get(ControlTruck,self.truck_id).version
        return self.call('post',self.assignment_path,data=dict(version=version,user_id=self.helper_id,skus=skus),expected=expected)

    def check_path(self, check):
        return f'/loads/{self.load_id}/courts/1/checks/0/{check["id"]}'

    def test_exclusive_products_permissions_totals_and_control_gate(self):
        primary=self.call('post',self.start_path,'picker')
        self.assign(['1002'],expected=409)
        self.call('post',self.check_path(primary)+'/pause','picker')
        self.assign(['1002'])
        primary=self.call('post',self.start_path,'picker')
        helper=self.call('post',self.start_path,'helper')
        self.assertEqual([p['sku'] for p in primary['products']],['1001'])
        self.assertEqual([p['sku'] for p in helper['products']],['1002'])
        self.call('post',self.check_path(primary)+'/answer','picker',data=dict(sku='1002',result='ok'),expected=404)
        self.call('post',self.check_path(helper)+'/answer','helper',data=dict(sku='1001',result='ok'),expected=404)
        detail=self.call('get',f'/loads/{self.load_id}','helper')
        self.assertTrue(detail['canchas'][0]['assistance'])
        self.assertEqual(detail['truck_summary']['mine']['bultos'],4)
        self.call('post',self.check_path(primary)+'/finish','picker')
        self.call('post',f'/loads/{self.load_id}/courts/1/start/1','ana',expected=409)
        self.call('post',self.check_path(helper)+'/finish','helper',expected=409)
        self.call('post',self.check_path(helper)+'/answer','helper',data=dict(sku='1002',result='ok'))
        self.call('post',self.check_path(helper)+'/finish','helper')
        self.call('post',f'/loads/{self.load_id}/courts/1/start/1','ana')
        self.assertEqual(self.call('get','/my-courts','helper')['courts'],[])
        report=self.call('get','/performance')
        self.assertTrue(any(p.get('assistance') and p['user_id']==self.helper_id for p in report['processes']))

    def test_return_requires_pause_and_physical_review_preserves_answers(self):
        self.assign(['1001','1002'])
        helper=self.call('post',self.start_path,'helper')
        self.call('post',self.check_path(helper)+'/answer','helper',data=dict(sku='1001',result='ok'))
        path=f'/loads/{self.load_id}/courts/1/assistance/{helper["id"]}/return'
        self.call('post',path,data=dict(physical_review=True),expected=409)
        self.call('post',self.check_path(helper)+'/pause','helper')
        self.call('post',path,expected=400)
        self.call('post',path,data=dict(physical_review=True))
        primary=self.call('post',self.start_path,'picker')
        self.assertEqual([p['sku'] for p in primary['products']],['1002'])
        state=db.session.get(ControlTruck,self.truck_id).state
        self.assertIn('1001',state['courts'][f'{self.load_id}:1']['helpers'][0]['answers'])

    def test_expiration_pauses_without_redistributing_unconfirmed_work(self):
        self.assign(['1002'])
        helper=self.call('post',self.start_path,'helper')
        with patch('services.assistance.local_day',return_value=date(2099,1,1)):
            pause_expired()
            self.call('post',self.check_path(helper)+'/answer','helper',data=dict(sku='1002',result='ok'),expected=403)
            self.call('post',self.start_path,'helper',expected=403)
            self.call('get',f'/loads/{self.load_id}','helper',expected=403)
        primary=self.call('post',self.start_path,'picker')
        self.assertEqual([p['sku'] for p in primary['products']],['1001'])

    def test_assignment_auth_and_stale_version(self):
        self.call('post',self.assignment_path,'picker',data={},expected=403)
        self.call('post',self.assignment_path,data=dict(version=-1,user_id=self.helper_id,skus=['1002']),expected=409)
        self.assign(['missing'],expected=409)
        self.assign(['1002'])
        self.assign(['1001'],expected=409)
        plan=self.call('post',f'/trucks/{self.truck_id}/planning/simulate',data=dict(capacity=20,mix_courts=False))
        self.call('post',f'/trucks/{self.truck_id}/planning/approve',data=dict(plan,physical_review=True),expected=409)
        tasks=available_tasks(User.query.filter_by(username='helper').one(),ControlTruck.query.all())
        self.assertEqual(tasks,[f'{self.load_id}:1:0'])


def load_tests(loader,tests,pattern):
    return loader.loadTestsFromTestCase(AssistanceTest)


if __name__ == '__main__':
    unittest.main()
