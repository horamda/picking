"""Run only against the disposable local PostgreSQL container, never Railway.

docker run --detach --name picking-concurrency-test -p 127.0.0.1:55433:5432 \
  -e POSTGRES_PASSWORD=picking-local-test-only -e POSTGRES_DB=picking_test postgres:16-alpine
python backend/tests/test_warehouse_concurrency.py
"""
import os
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path

os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:picking-local-test-only@127.0.0.1:55433/picking_test'
os.environ['INIT_DB_ON_STARTUP'] = '0'
os.environ['JWT_SECRET'] = 'isolated-concurrency-test-secret-only'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as application
from sqlalchemy.schema import CreateTable, DropTable
from models import Role, User, Article
from services.load_control import ControlTruck, ControlLoad, ControlTimer
from services.warehouse import UserCourt, DepotSettings, TruckCapacity
from auth import AuthService
from utils.db import db


class ConcurrentWarehouseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with application.app.app_context():
            assert db.engine.url.host == '127.0.0.1' and db.engine.url.port == 55433
            # DDL is confined to this disposable database; no application startup DDL.
            with db.engine.begin() as connection:
                for table in reversed(db.metadata.sorted_tables):
                    connection.execute(DropTable(table, if_exists=True))
                for table in db.metadata.sorted_tables:
                    connection.execute(CreateTable(table))
            roles = {n: Role(name=n) for n in ('administrador', 'operador')}
            db.session.add_all(roles.values())
            db.session.flush()
            cls.tokens = {}
            for name in ('admin', 'one', 'two', *[f'worker{n}' for n in range(3,11)]):
                user = User(username=name, email=name+'@test.local', password_hash='unused', active=True,
                            role=roles['administrador' if name == 'admin' else 'operador'])
                db.session.add(user); db.session.flush()
                cls.tokens[name] = AuthService.generate_token(user)
                if name != 'admin':
                    db.session.add_all([UserCourt(user_id=user.id, court_number=n) for n in range(1,11)])
            db.session.add(Article(sku='A', descripcion='Brahma', bultos_por_pallet=50, unidades_por_bulto=12, activo=True))
            db.session.add(DepotSettings(branch='Test', mix_courts_default=False)); db.session.flush()
            db.session.add(TruckCapacity(branch='Test', truck='TEST', pallet_capacity=100))
            truck = ControlTruck(branch='Test', load_date='2026-10-27', truck='TEST', state={'courts': {}})
            db.session.add(truck); db.session.flush()
            load = ControlLoad(branch='Test', load_date='2026-10-27', reparto='TEST', truck_id=truck.id,
                content=dict(reparto='TEST', camion='TEST', deposito='Test', fecha='2026-10-27',
                    canchas=[dict(numero=n, productos=[dict(sku='A', descripcion='Brahma', bultos=244, unidades=0)]) for n in range(1,11)]))
            db.session.add(load); db.session.commit()
            cls.truck_id, cls.load_id = truck.id, load.id

    def request(self, user, path, data=None, method='POST'):
        with application.app.test_client() as client:
            response = client.open('/api/load-control'+path, method=method, json=data,
                headers={'Authorization':'Bearer '+self.tokens[user]})
            return response.status_code, response.json

    def pair(self, calls):
        barrier = Barrier(2)
        def run(call):
            barrier.wait(timeout=10)
            return self.request(*call)
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, calls))

    def test_simultaneous_reservations_answers_and_monitor(self):
        endpoint = f'/trucks/{self.truck_id}/planning'
        status, plan = self.request('admin', endpoint+'/simulate', dict(capacity=100, mix_courts=False))
        self.assertEqual(status, 200, plan)
        self.assertEqual(self.request('admin', endpoint+'/approve', dict(plan, physical_review=True))[0], 200)
        start1 = f'/loads/{self.load_id}/courts/1/start/0'
        results = self.pair([('one',start1), ('two',start1)])
        self.assertEqual(sorted(r[0] for r in results), [200,409])
        winner = 'one' if results[0][0] == 200 else 'two'
        other = 'two' if winner == 'one' else 'one'
        check1 = next(r[1] for r in results if r[0] == 200)
        code, check2 = self.request(other, f'/loads/{self.load_id}/courts/2/start/0')
        self.assertEqual(code,200,check2)
        paths = [f'/loads/{self.load_id}/courts/{n}/checks/0/{check["id"]}/answer' for n,check in [(1,check1),(2,check2)]]
        elapsed = []
        for _ in range(10):
            begin=time.monotonic()
            responses=self.pair([(winner,paths[0],dict(sku='A',result='ok')), (other,paths[1],dict(sku='A',result='ok'))])
            elapsed.append(time.monotonic()-begin)
            self.assertEqual([r[0] for r in responses],[200,200],responses)
        with application.app.app_context():
            truck=db.session.get(ControlTruck,self.truck_id)
            for n in (1,2):
                self.assertEqual(truck.state['courts'][f'{self.load_id}:{n}']['checks']['0']['answers']['A']['physical_b'],44)
            self.assertEqual(ControlTimer.query.count(),2)
        code, monitor=self.request('admin','/monitor?date=2026-10-27',method='GET')
        self.assertEqual(code,200)
        running=[p for p in monitor['processes'] if p['status']=='running']
        self.assertEqual(len(running),2)
        self.assertTrue(all(p['answered']==1 for p in running))
        self.assertEqual(self.request(winner,'/monitor',method='GET')[0],403)
        for n in range(3,11):
            code, check = self.request(f'worker{n}',f'/loads/{self.load_id}/courts/{n}/start/0')
            self.assertEqual(code,200,check)
            paths.append(f'/loads/{self.load_id}/courts/{n}/checks/0/{check["id"]}/answer')
        workers=[winner,other]+[f'worker{n}' for n in range(3,11)]
        barrier=Barrier(10)
        def confirm(pair):
            worker,path=pair
            barrier.wait(timeout=10)
            return self.request(worker,path,dict(sku='A',result='ok'))
        begin=time.monotonic()
        with ThreadPoolExecutor(max_workers=10) as pool:
            responses=list(pool.map(confirm,zip(workers,paths)))
        batch_time=time.monotonic()-begin
        self.assertTrue(all(code==200 for code,_ in responses),responses)
        code,monitor=self.request('admin','/monitor?date=2026-10-27',method='GET')
        self.assertEqual(len([p for p in monitor['processes'] if p['status']=='running' and p['answered']==1]),10)
        print(f'10 concurrent operators, all confirmations preserved; local batch: {batch_time:.3f}s; slowest pair: {max(elapsed):.3f}s')

    @classmethod
    def tearDownClass(cls):
        with application.app.app_context():
            db.session.remove()
            db.engine.dispose()



if __name__ == '__main__':
    unittest.main()
