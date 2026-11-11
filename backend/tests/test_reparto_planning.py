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
    def physical_settings(self, **changes):
        data = dict(branch='Central', truck='ABC123', capacity=20, mix_courts_default=False,
            pallet_base_height_cm=10, reference_pallet_height_cm=110, max_pallet_height_cm=100,
            empty_pallet_weight_kg=20, max_pallet_weight_kg=800, safety_margin_pct=5,
            height_excess_mode='inform', pallet_weight_excess_mode='inform', truck_weight_excess_mode='inform',
            share_floor_remainders=False, weight_tiebreaker=False, max_payload_kg=10000, max_height_cm=None)
        data.update(changes)
        return data

    def test_truck_height_overrides_depot_and_configuration_is_audited(self):
        from models import LogEntry
        self.call('put','/settings',data=self.physical_settings(max_height_cm=80))
        plan=self.call('post',f'/trucks/{self.truck_id}/planning/simulate',data=dict(capacity=20,mix_courts=False))
        self.assertEqual(plan['configuration']['max_pallet_height_cm'],80)
        self.assertTrue(plan['configuration']['truck_height_override'])
        log=LogEntry.query.filter_by(action='configurar_capacidad').order_by(LogEntry.id.desc()).first()
        self.assertIn('previous',log.details);self.assertIn('current',log.details)

    def test_logistics_weight_accepts_spacing_case_and_decimal_comma(self):
        from models import Article
        from routes.load_control import planning_rows
        article=Article.query.filter_by(sku='1001').one();article.datos_logisticos={' P e S o ':'20,17'};db.session.commit()
        truck=db.session.get(ControlTruck,self.truck_id)
        weights={item['sku']:item['peso_por_bulto'] for item in planning_rows(truck)}
        self.assertEqual(weights['1001'],'20.17')

    def test_invalid_physical_settings_are_rejected(self):
        self.call('put','/settings',data=self.physical_settings(safety_margin_pct=51),expected=400)
        self.call('put','/settings',data=self.physical_settings(pallet_base_height_cm=20,max_pallet_height_cm=10),expected=400)
        self.call('put','/settings',data=self.physical_settings(height_excess_mode='ignore'),expected=400)

    def test_legacy_capacity_update_preserves_physical_configuration(self):
        self.call('put','/settings',data=self.physical_settings(max_payload_kg=9000))
        self.call('put','/settings',data=dict(branch='Central',truck='ABC123',capacity=20,mix_courts_default=True))
        settings=self.call('get','/settings')
        depot=next(item for item in settings['depots'] if item['branch']=='Central')
        truck=next(item for item in settings['trucks'] if item['branch']=='Central' and item['truck']=='ABC123')
        self.assertEqual(depot['pallet_base_height_cm'],10)
        self.assertEqual(truck['max_payload_kg'],9000)

    def test_configuration_invalidates_unstarted_plan_but_not_started_work(self):
        from routes.load_control import approved
        truck=db.session.get(ControlTruck,self.truck_id)
        self.assertTrue(approved(truck))
        self.call('put','/settings',data=self.physical_settings())
        db.session.refresh(truck);self.assertFalse(approved(truck))
        plan=self.call('post',f'/trucks/{self.truck_id}/planning/simulate',data=dict(capacity=20,mix_courts=False))
        self.call('post',f'/trucks/{self.truck_id}/planning/approve',data=dict(plan,physical_review=True))
        check=self.call('post',f'/loads/{self.load_id}/courts/1/start/0','picker')
        self.assertIsNotNone(check['id'])
        self.call('put','/settings',data=self.physical_settings(safety_margin_pct=10))
        db.session.refresh(truck);self.assertTrue(approved(truck))

    def test_capacity_accepts_unique_pdf_depot_code_alias(self):
        from services.warehouse import DepotSettings, TruckCapacity, truck_capacity
        truck=db.session.get(ControlTruck,self.truck_id)
        truck.branch='001 - CASA CENTRAL'
        db.session.add(DepotSettings(branch='1',mix_courts_default=False));db.session.flush()
        db.session.add(TruckCapacity(branch='1',truck=truck.truck,pallet_capacity=9));db.session.commit()
        path=f'/trucks/{self.truck_id}/planning'
        self.assertEqual(self.call('get',path)['configured_capacity'],9)
        plan=self.call('post',path+'/simulate',data=dict(capacity=9,mix_courts=False))
        self.call('post',path+'/approve',data=dict(plan,physical_review=True))
        self.assertIsNone(truck_capacity('002 - OTHER',truck.truck))

    def test_configuration_resolves_pdf_depot_and_exact_capacity_wins(self):
        from services.warehouse import TruckCapacity
        truck=db.session.get(ControlTruck,self.truck_id)
        truck.branch='001 - CASA CENTRAL';db.session.commit()
        self.call('put','/settings',data=dict(branch='1',truck=truck.truck,capacity=9,mix_courts_default=False))
        self.assertEqual(db.session.get(TruckCapacity,('001 - CASA CENTRAL',truck.truck)).pallet_capacity,9)
        self.assertEqual(self.call('get',f'/trucks/{self.truck_id}/planning')['configured_capacity'],9)

    def test_compact_selection_is_signed_persisted_and_sent_to_workers(self):
        second, other_truck, _ = self.dispatch_sources()
        self.select_dispatch([self.source.id, second.id])
        second_load = ControlLoad.query.filter_by(source_id=second.id).one()
        from models import User
        from services.warehouse import UserCourt
        for username in ('picker','pallet'):
            db.session.add(UserCourt(user_id=User.query.filter_by(username=username).one().id,court_number=2))
        db.session.commit()
        path=f'/trucks/{self.truck_id}/planning'
        plan=self.call('post',path+'/simulate',data=dict(capacity=20,mix_courts=False,compact_load_ids=[second_load.id]))
        self.assertEqual(plan['compact_load_ids'],[second_load.id])
        self.assertEqual(plan['separation_policy'],'reparto_v1')
        self.assertEqual([p['total_pallets'] for p in plan['load_plans']],[1,3])
        self.assertTrue(all(len({i['load_id'] for i in p['items']})==1 for p in plan['mixed_pallets']))
        self.call('post',path+'/approve',data=dict(plan,compact_load_ids=[],physical_review=True),expected=409)
        self.call('post',path+'/simulate',data=dict(capacity=20,mix_courts=True,compact_load_ids=[999999]),expected=400)
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
        self.assertTrue(all(destination.get('placement') in ('base', 'arriba')
                            for product in check['products'] for destination in product['pallet_destinations']))
        self.assertTrue(all(type(destination.get('shared')) is bool
                            for product in check['products'] for destination in product['pallet_destinations']))
        from routes.load_control import load_picking_complete, task_products
        self.assertFalse(load_picking_complete(second_load))
        self.assertEqual(task_products(second_load,second_load.content['canchas'][0],4),[])
        self.call('post',f'/loads/{second_load.id}/courts/1/checks/0/{check["id"]}/finish','picker')
        second_check=self.call('post',f'/loads/{second_load.id}/courts/2/start/0','picker')
        self.call('post',f'/loads/{second_load.id}/courts/2/checks/0/{second_check["id"]}/finish','picker')
        db.session.refresh(second_load)
        db.session.refresh(second_load.truck)
        self.assertTrue(load_picking_complete(second_load))
        full=task_products(second_load,second_load.content['canchas'][0],4)
        self.assertTrue(all(p['pallet_group'] and p['separate_reparto'] for p in full))
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
