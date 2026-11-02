"""Account lifecycle preserves warehouse ownership and revokes prior sessions."""
import unittest
from test_load_control import ControlFlowTest, User, db, tearDownModule
from models import LogEntry
from services.load_control import ControlTruck

class Fixture(ControlFlowTest):
    pass
for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)

class PersonnelTest(Fixture):
    def uid(self, name='picker'):
        return User.query.filter_by(username=name).one().id

    def test_profile_unique_legajo_and_permissions(self):
        path=f'/users/{self.uid()}'
        self.call('put',path,'super',data={'first_name':'Pedro'},expected=403)
        person=self.call('put',path,data=dict(first_name='Pedro',last_name='Pérez',employee_number='001'))
        self.assertEqual(person['first_name'],'Pedro')
        self.call('put',f'/users/{self.uid("ana")}',data={'employee_number':'001'},expected=409)
        self.call('put',path,data={'email':'bad'},expected=400)
        self.call('put',path,data={'active':'false'},expected=400)
        self.call('put',path,data={'role':'root'},expected=400)
        self.assertEqual(User.query.get(self.uid()).first_name,'Pedro')

    def test_password_reset_revokes_session_and_keeps_audit_clean(self):
        self.call('put',f'/users/{self.uid()}',data={'password':'NewPassword123!'})
        self.call('get',f'/loads/{self.load_id}','picker',expected=401)
        response=self.client.post('/api/auth/login',json=dict(username='picker',password='NewPassword123!'))
        self.assertEqual(response.status_code,200)
        self.assertNotIn('NewPassword123!',LogEntry.query.filter_by(action='editar_personal').one().details)

    def test_deactivation_reactivation_and_self_protection(self):
        path=f'/users/{self.uid()}'
        self.call('put',path,data={'active':False})
        self.call('get',f'/loads/{self.load_id}','picker',expected=401)
        self.call('put',path,data={'active':True})
        self.call('get',f'/loads/{self.load_id}','picker',expected=401)
        self.call('put',f'/users/{self.uid("admin")}',data={'active':False},expected=409)
        self.call('put',f'/users/{self.uid("admin")}',data={'role':'operador'},expected=409)
        self.assertTrue(User.query.get(self.uid('admin')).active)

    def test_active_work_prevents_deactivation_or_role_change_and_keeps_history(self):
        check=self.call('post',f'/loads/{self.load_id}/courts/1/start/0','picker')
        path=f'/users/{self.uid()}'
        self.call('put',path,data={'active':False},expected=409)
        self.call('put',path,data={'role':'controlador'},expected=409)
        self.call('put',path,data={'username':'pedro'})
        truck=db.session.get(ControlTruck,self.truck_id)
        self.assertEqual(truck.state['courts'][f'{self.load_id}:1']['checks']['0']['username'],'picker')
        self.assertEqual(truck.state['courts'][f'{self.load_id}:1']['checks']['0']['id'],check['id'])

    def test_helper_and_assets_are_also_blockers(self):
        user_id=self.uid()
        for value in [dict(asset_check=dict(user_id=user_id,status='active')), dict(courts={'1:1':dict(helpers=[dict(user_id=user_id,status='active')])})]:
            truck=db.session.get(ControlTruck,self.truck_id)
            truck.state=value;db.session.commit()
            self.call('put',f'/users/{user_id}',data={'active':False},expected=409)

    def test_create_personnel_and_change_role_revokes_token(self):
        person=self.call('post','/users',data=dict(username='new',email='new@test.local',password='Password123!',role='operador',first_name='Roque',employee_number='77'),expected=201)
        self.assertEqual(person['employee_number'],'77')
        self.call('put',f'/users/{self.uid()}',data={'role':'controlador'})
        self.call('get',f'/loads/{self.load_id}','picker',expected=401)

def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(PersonnelTest)
if __name__ == '__main__':
    unittest.main()
