"""The approved truck owns its loads; destinations never cross reparto boundaries."""
from test_load_control import ControlFlowTest, db, tearDownModule
from services.load_control import ControlTruck, ControlLoad
import unittest


class Fixture(ControlFlowTest):
    pass


for name in dir(ControlFlowTest):
    if name.startswith('test_'):
        setattr(Fixture, name, None)


class RepartoPlanningTest(Fixture):
    def test_compact_selection_is_signed_persisted_and_sent_to_workers(self):
        second, other_truck, _ = self.dispatch_sources()
        self.select_dispatch([self.source.id, second.id, other_truck.id])
        second_load = ControlLoad.query.filter_by(source_id=second.id).one()
        foreign_load = ControlLoad.query.filter_by(source_id=other_truck.id).one()
        path=f'/trucks/{self.truck_id}/planning'
        plan=self.call('post',path+'/simulate',data=dict(capacity=20,mix_courts=False,compact_load_ids=[second_load.id]))
        self.assertEqual(plan['compact_load_ids'],[second_load.id])
        self.assertEqual(plan['separation_policy'],'reparto_v1')
        self.assertEqual([p['total_pallets'] for p in plan['load_plans']],[1,3])
        self.assertTrue(all(len({i['load_id'] for i in p['items']})==1 for p in plan['mixed_pallets']))
        self.call('post',path+'/approve',data=dict(plan,compact_load_ids=[],physical_review=True),expected=409)
        self.call('post',path+'/simulate',data=dict(capacity=20,mix_courts=True,compact_load_ids=[foreign_load.id]),expected=400)
        self.call('post',path+'/approve',data=dict(plan,physical_review=True))
        saved=self.call('get',path)
        self.assertEqual(saved['plan']['compact_load_ids'],[second_load.id])
        self.assertEqual({l['id'] for l in saved['loads']},{self.load_id,second_load.id})
        detail=self.call('get',f'/loads/{second_load.id}','picker')
        self.assertEqual(detail['assembly_mode'],'compact')
        self.assertTrue(detail['separate_reparto'])
        check=self.call('post',f'/loads/{second_load.id}/courts/1/start/0','picker')
        self.assertTrue(all(p['assembly_mode']=='compact' and p['reparto']==second.reparto for p in check['products']))
        self.assertTrue(all(p['pallet_destinations'] for p in check['products']))
        full=self.call('post',f'/loads/{second_load.id}/courts/1/start/4','pallet')
        self.assertTrue(all(p['pallet_group'] and p['separate_reparto'] for p in full['products']))
        self.call('post',path+'/approve',data=dict(plan,physical_review=True),expected=409)

    def test_capacity_cannot_be_met_by_merging_repartos(self):
        second,_,_=self.dispatch_sources()
        self.select_dispatch([self.source.id,second.id])
        self.call('put','/settings',data=dict(branch='Central',truck='ABC123',capacity=3,mix_courts_default=True))
        path=f'/trucks/{self.truck_id}/planning'
        plan=self.call('post',path+'/simulate',data=dict(capacity=3,mix_courts=True))
        self.assertEqual(plan['total_pallets'],4)
        self.assertFalse(plan['fits_estimate'])
        self.call('post',path+'/approve',data=dict(plan,physical_review=True),expected=409)
        self.assertNotIn('planning',db.session.get(ControlTruck,self.truck_id).state)


def load_tests(loader, tests, pattern):
    return loader.loadTestsFromTestCase(RepartoPlanningTest)


if __name__ == '__main__':
    unittest.main()
