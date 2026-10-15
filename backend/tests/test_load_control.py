"""Flujo de control sobre una base temporal; nunca usa la base local."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO
from pdf_fixture import planilla_pdf
from pathlib import Path
from datetime import datetime, timedelta, timezone

TEMP = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(TEMP.name) / 'control.db')
os.environ['INIT_DB_ON_STARTUP'] = '0'
os.environ['ALLOW_SQLITE_FOR_TESTS'] = '1'
os.environ['ADMIN_PASSWORD'] = 'TestPassword123!'
os.environ['JWT_SECRET'] = 'test-control-only-long-enough-secret'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as application
from models import User, Role, Consolidado, ConsolidadoDetalle, ProcessingBatch, Article, UploadedFile
from auth import AuthService
from services.load_control import ControlTruck, ControlTimer, ASSET_NAMES
from utils.db import db
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError


class ControlFlowTest(unittest.TestCase):
    def setUp(self):
        self.ctx = application.app.app_context()
        self.ctx.push()
        self.addCleanup(self.ctx.pop)
        self.addCleanup(db.session.remove)
        db.drop_all()
        application.initialize_database()
        for name, role in [('ana', 'operador'), ('ben', 'controlador'), ('super', 'supervisor')]:
            db.session.add(User(username=name, email=name+'@test.local', active=True,
                password_hash=AuthService.hash_password('TestPassword123!'),
                role=Role.query.filter_by(name=role).one()))
        batch = ProcessingBatch(nombre='Test', estado='completo')
        db.session.add(batch); db.session.flush()
        self.batch_id = batch.id
        self.source = Consolidado(batch_id=self.batch_id, filename='test.pdf', reparto='0001', camion='12 - (ABC123) Transporte', deposito='Central', fecha_reparto=datetime(2026,10,15), chofer='Chofer')
        db.session.add(self.source)
        db.session.flush()
        for sku, b in [('1001', 2), ('1001', 3), ('1002', 4)]:
            db.session.add(ConsolidadoDetalle(consolidado_id=self.source.id, sku=sku, descripcion='Producto '+sku,
                bultos=b, unidades=0, cancha='001 - CANCHA 1', almacen='Bebidas'))
        db.session.commit()
        self.client = application.app.test_client()
        self.tokens = {}
        for name in ['admin', 'ana', 'ben', 'super']:
            self.tokens[name] = self.client.post('/api/auth/login', json={'username':name,'password':'TestPassword123!'}).json['token']
        self.load_id = self.call('post', '/sources/'+str(self.source.id), 'ana', expected=201)['id']
        self.truck_id = self.call('get', '/trucks')[0]['id']

    def tearDown(self):
        db.session.remove()


    def call(self, method, path, user='admin', expected=200, data=None):
        kwargs = {'headers':{'Authorization':'Bearer '+self.tokens[user]}}
        if data is not None:
            kwargs['json'] = data
        response = getattr(self.client, method)('/api/load-control'+path, **kwargs)
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response.json

    def start(self, stage, user):
        check = self.call('post', f'/loads/{self.load_id}/courts/1/start/{stage}', user)
        return f'/loads/{self.load_id}/courts/1/checks/{stage}/{check["id"]}'

    def answer(self, path, sku, user, result='ok', expected=200, **extra):
        return self.call('post', path+'/answer', user, expected, dict(sku=sku, result=result, **extra))

    def complete(self, stage, user, shortage=False):
        path = self.start(stage, user)
        if shortage:
            self.answer(path, '1001', user, 'shortage', physical_b=3, physical_u=0,
                responsible_user_id=User.query.filter_by(username='ana').one().id, origin='picking', note='Faltan dos bultos')
        else:
            self.answer(path, '1001', user)
        self.answer(path, '1002', user)
        self.call('post', path+'/finish', user)
        return path

    def upload_pdf(self, data, filename='synthetic.pdf', user='ana'):
        return self.client.post('/api/uploads/pdf',
            headers={'Authorization': 'Bearer ' + self.tokens[user]},
            data={'files': (BytesIO(data), filename)}, content_type='multipart/form-data')

    def test_real_pdf_import_download_duplicate_and_control(self):
        db.session.add(Article(sku='1001', descripcion='Prueba', unidades_por_bulto=6, bultos_por_pallet=10))
        db.session.commit()
        pdf = planilla_pdf()
        response = self.upload_pdf(pdf)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['errors'], [])
        self.assertEqual(len(response.json['processed']), 1)
        self.assertEqual(response.json['processed'][0]['excluded'], 1)
        source = Consolidado.query.filter_by(reparto='TEST-9001').one()
        detail = ConsolidadoDetalle.query.filter_by(consolidado_id=source.id, sku='1001').one()
        self.assertEqual((detail.bultos, detail.unidades), (14, 3))
        self.assertEqual((detail.pallets_completos, detail.bultos_pickear, detail.unidades_sueltas), (1, 4, 3))
        self.assertEqual(detail.bultos_equivalentes, 14.5)
        self.assertEqual(source.fecha_reparto.date(), datetime(2026, 10, 15).date())
        unknown = ConsolidadoDetalle.query.filter_by(consolidado_id=source.id, sku='9999').one()
        self.assertEqual(unknown.sku_estado, 'no encontrado')
        file_id = response.json['processed'][0]['uploaded_file_id']
        downloaded = self.client.get(f'/api/uploads/files/{file_id}/download',
            headers={'Authorization': 'Bearer ' + self.tokens['ana']})
        self.assertEqual(downloaded.data, pdf)
        before = Consolidado.query.count()
        duplicate = self.upload_pdf(pdf)
        self.assertEqual(duplicate.json['processed'], [])
        self.assertEqual(len(duplicate.json['errors']), 1)
        self.assertEqual(Consolidado.query.count(), before)
        controlled = self.call('post', '/sources/'+str(source.id), 'ana', expected=201)
        self.assertTrue(controlled['id'])

    def test_pdf_multiple_repartos_and_continuation_pages(self):
        response = self.upload_pdf(planilla_pdf(('TEST-9100', 'TEST-9101'), repeat_page=True))
        self.assertEqual(response.json['errors'], [])
        self.assertEqual(len(response.json['processed']), 2)
        for reparto in ['TEST-9100', 'TEST-9101']:
            source = Consolidado.query.filter_by(reparto=reparto).one()
            row = ConsolidadoDetalle.query.filter_by(consolidado_id=source.id, sku='1001').one()
            self.assertEqual((row.bultos, row.unidades), (28, 6))

    def test_pdf_rejections_do_not_create_consolidados(self):
        before = Consolidado.query.count()
        self.assertEqual(self.upload_pdf(planilla_pdf(), user='ben').status_code, 403)
        for data, name in [(b'not a pdf', 'bad.pdf'), (b'not a pdf', 'bad.txt'), (planilla_pdf(()), 'empty.pdf')]:
            response = self.upload_pdf(data, name)
            self.assertEqual(response.json['processed'], [])
            self.assertEqual(len(response.json['errors']), 1)
        self.assertEqual(Consolidado.query.count(), before)

    def test_pdf_failed_second_reparto_is_not_reported_as_saved(self):
        from routes.uploads import compute_consolidation_metrics
        def fail_second(row, article):
            if Consolidado.query.filter_by(reparto='TEST-9201').first():
                raise ValueError('Synthetic processing failure')
            return compute_consolidation_metrics(row, article)
        with patch('routes.uploads.compute_consolidation_metrics', side_effect=fail_second):
            response = self.upload_pdf(planilla_pdf(('TEST-9200', 'TEST-9201')))
        self.assertEqual(len(response.json['errors']), 1)
        self.assertEqual(Consolidado.query.filter(Consolidado.reparto.in_(['TEST-9200', 'TEST-9201'])).count(), 0)
        self.assertEqual(response.json['processed'], [])

    def test_shared_railway_startup_only_inspects_schema(self):
        with patch.object(application.Config, 'APP_MODE', 'prueba'), \
             patch.object(application.Config, 'SQLALCHEMY_DATABASE_URI', 'postgresql+psycopg://test'), \
             patch.object(db, 'create_all') as create, \
             patch.object(application, 'ensure_runtime_schema') as alter, \
             patch.object(AuthService, 'initialize_roles') as roles, \
             patch.object(application, 'seed_admin_user') as seed:
            for mode in ['prueba', 'produccion']:
                with patch.object(application.Config, 'APP_MODE', mode):
                    application.initialize_database()
            for mutation in [create, alter, roles, seed]:
                mutation.assert_not_called()

    def test_user_creation_routes_share_policy_and_preserve_contracts(self):
        headers = {'Authorization': 'Bearer ' + self.tokens['admin']}
        for index, endpoint in enumerate(['/api/auth/register', '/api/load-control/users']):
            payload = dict(username='created'+str(index), email='CREATED'+str(index)+'@test.local',
                           password='Password123!', role='controlador')
            denied = self.client.post(endpoint, json=payload,
                headers={'Authorization': 'Bearer ' + self.tokens['super']})
            self.assertEqual(denied.status_code, 403)
            for invalid in [dict(payload, password='short'), dict(payload, email='invalid'),
                            dict(payload, role='unknown'), dict(payload, role=[]), []]:
                response = self.client.post(endpoint, json=invalid, headers=headers)
                self.assertEqual(response.status_code, 400, response.json)
            response = self.client.post(endpoint, json=payload, headers=headers)
            self.assertEqual(response.status_code, 201, response.json)
            user = response.json['user'] if endpoint.endswith('register') else response.json
            self.assertEqual(user['username'], payload['username'])
            self.assertEqual(user['role'], 'controlador')
            self.assertNotIn('password_hash', user)
            duplicate = self.client.post('/api/auth/register', json=payload, headers=headers)
            self.assertEqual(duplicate.status_code, 409)
            login = self.client.post('/api/auth/login', json=dict(username=payload['username'], password=payload['password']))
            self.assertEqual(login.status_code, 200)
            self.assertEqual(User.query.filter_by(username=payload['username']).one().email, payload['email'].lower())

    def test_existing_read_endpoints_preserve_source_data(self):
        headers = {'Authorization': 'Bearer ' + self.tokens['ana']}
        before = (Consolidado.query.count(), ConsolidadoDetalle.query.count())
        for endpoint in ['/api/auth/me', '/api/operations/trucks', '/api/operations/picking',
                         '/api/operations/pallets', '/api/operations/picking-by-cancha',
                         '/api/operations/by-court', '/api/history/search',
                         '/api/history/'+str(self.source.id), '/api/dashboard/summary',
                         '/api/dashboard/charts']:
            response = self.client.get(endpoint, headers=headers)
            self.assertEqual(response.status_code, 200, (endpoint, response.get_data(as_text=True)))
        self.assertEqual(before, (Consolidado.query.count(), ConsolidadoDetalle.query.count()))
        self.assertEqual(self.client.post('/api/auth/login', json=dict(username='ana', password='wrong')).status_code, 401)

    def test_shared_data_and_permissions(self):
        detail = self.call('get', f'/loads/{self.load_id}')
        self.assertEqual(len(detail['canchas'][0]['productos']), 2)
        self.assertEqual(detail['canchas'][0]['productos'][0]['bultos'], 5)
        self.assertEqual(detail['camion'], 'ABC123')
        self.assertEqual(self.call('get', '/sources'), [])
        self.call('post', '/sources/'+str(self.source.id), expected=409)
        self.call('get', '/performance', 'ana', expected=403)
        self.call('post', '/users', 'ana', expected=403, data={})
        self.assertEqual(self.client.get('/api/load-control/trucks').status_code, 401)
        self.call('post', '/users', expected=201, data=dict(username='nuevo', email='nuevo@test.local', password='Password123!',role='controlador'))
        self.assertEqual(self.client.post('/api/auth/login',json=dict(username='nuevo', password='Password123!')).status_code,200)

    def test_two_people_shortage_assets_and_manual_adjustment(self):
        picking = self.start(0, 'ana')
        self.call('post', f'/loads/{self.load_id}/courts/1/start/1', 'ben', expected=409)
        self.call('post', picking+'/finish', 'ana')
        self.complete(1, 'ana', shortage=True)
        self.call('post', f'/loads/{self.load_id}/courts/1/start/2', 'ana', expected=403)
        second = self.start(2, 'ben')
        self.answer(second, '1001', 'ben', expected=409)
        self.answer(second, '1001', 'ben', 'corrected', expected=409, note='Corregido',
            responsible_user_id=User.query.filter_by(username='ana').one().id, origin='picking')
        self.answer(second, '1001', 'ben', 'shortage', physical_b=3, physical_u=0)
        self.answer(second, '1002', 'ben')
        self.call('post', second+'/finish', 'ben')
        self.call('post', f'/trucks/{self.truck_id}/assets/start', 'ben')
        self.call('post', f'/trucks/{self.truck_id}/assets', 'ben', data={'quantities':{name:0 for name in ASSET_NAMES}})
        truck = self.call('get', '/trucks')[0]
        self.assertFalse(truck['status']['released_at'])
        self.call('post', f'/loads/{self.load_id}/courts/1/shortages/1001/approve', 'ana', expected=403)
        self.call('post', f'/loads/{self.load_id}/courts/1/shortages/1001/approve', 'super')
        truck = self.call('get', '/trucks')[0]
        self.assertTrue(truck['status']['released_at'])
        self.assertFalse(truck['status']['shortages'][0].get('adjusted_at'))
        self.call('post', f'/loads/{self.load_id}/courts/1/reopen', 'super', 409, {'reason':'Revisar'})
        self.call('post', f'/loads/{self.load_id}/courts/1/shortages/1001/adjusted', 'super')
        report = self.call('get', '/performance')
        self.assertEqual(len(report['processes']), 4)
        self.assertEqual(len(report['incidents']), 1)  # confirmation is not a second error
        self.assertEqual(report['incidents'][0]['incident']['responsible_username'], 'ana')
        self.assertEqual(ControlTimer.query.count(), 0)

    def test_reservations_pause_time_and_reopen_preserve_history(self):
        path = self.start(1, 'ana')
        self.call('post', f'/loads/{self.load_id}/courts/1/start/1', 'ben', expected=409)
        self.call('post', path+'/finish', 'ana', expected=409)
        # Simulate elapsed time without sleeping.
        from copy import deepcopy
        truck = db.session.get(ControlTruck, self.truck_id)
        state = deepcopy(truck.state)
        state['courts'][f'{self.load_id}:1']['checks']['1']['timer_started_at'] = (datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat()
        truck.state = state
        db.session.commit()
        paused = self.call('post', path+'/pause', 'ana')
        self.assertGreaterEqual(paused['active_seconds'], 29)
        self.assertIsNone(paused['timer_started_at'])
        self.answer(path, '1001', 'ana', expected=409)
        self.start(1, 'ana')
        self.answer(path, '1001', 'ana', 'corrected', note='Producto equivocado',
            responsible_user_id=User.query.filter_by(username='ben').one().id, origin='picking')
        # Correcting the current answer must not erase an already reported incident.
        self.answer(path, '1001', 'ana')
        self.call('post', f'/loads/{self.load_id}/courts/1/reopen', 'super', data={'reason':'Verificar diferencia'})
        self.call('post', path+'/finish', 'ana', expected=409)
        report = self.call('get', '/performance')
        self.assertEqual(report['processes'][0]['status'], 'reopened')
        self.assertGreaterEqual(report['processes'][0]['elapsed_seconds'], 29)
        self.assertEqual(len(report['incidents']), 1)
        self.assertEqual(ControlTimer.query.count(), 0)
        self.start(1, 'ben')

    def test_validation_and_pending_planillas_block_release(self):
        path = self.start(1, 'ana')
        self.answer(path, '1001', 'ana', 'corrected', expected=400, note='Sin responsable')
        self.answer(path, '1001', 'ana', 'shortage', expected=400, physical_b=-1, physical_u=0,
            responsible_user_id=User.query.filter_by(username='ana').one().id, origin='picking')
        self.call('post', f'/trucks/{self.truck_id}/assets', 'ana', expected=400, data={'quantities':{'Carros':0}})
        self.answer(path, '1001', 'ana')
        self.answer(path, '1002', 'ana')
        self.call('post', path+'/finish', 'ana')
        self.complete(2, 'ben')
        pending = Consolidado(batch_id=self.batch_id, filename='test2.pdf', reparto='0002', camion='ABC123', deposito='Central', fecha_reparto=datetime(2026,10,15))
        db.session.add(pending); db.session.commit()
        self.call('post', f'/trucks/{self.truck_id}/assets/start', 'ben', expected=409)
        truck = self.call('get', '/trucks')[0]
        self.assertEqual(truck['status']['pending_sources'], [pending.id])
        self.assertFalse(truck['status']['complete'])

    def test_truck_with_two_loads_releases_only_after_both_are_controlled(self):
        second = Consolidado(batch_id=self.batch_id, filename='second.pdf', reparto='0002',
            camion='ABC123', deposito='Central', fecha_reparto=datetime(2026,10,15))
        db.session.add(second); db.session.flush()
        for sku in ['1001', '1002']:
            db.session.add(ConsolidadoDetalle(consolidado_id=second.id, sku=sku,
                descripcion='Producto', bultos=1, unidades=0, cancha='1'))
        db.session.commit()
        sources = self.call('get', '/sources')
        self.assertEqual(sources[0]['camion_control'], 'ABC123')
        self.complete(1, 'ana'); self.complete(2, 'ben')
        self.call('post', f'/trucks/{self.truck_id}/assets/start', 'ben', expected=409)
        first_id = self.load_id
        self.load_id = self.call('post', '/sources/'+str(second.id), 'ana', expected=201)['id']
        trucks = self.call('get', '/trucks')
        self.assertEqual(len(trucks), 1)
        self.assertEqual(len(trucks[0]['loads']), 2)
        self.assertTrue(self.call('get', '/loads/'+str(first_id))['canchas'][0]['status']['done'])
        self.assertFalse(self.call('get', '/loads/'+str(self.load_id))['canchas'][0]['status']['done'])
        self.complete(1, 'ana')
        self.call('post', f'/trucks/{self.truck_id}/assets/start', 'ben', expected=409)
        self.complete(2, 'ben')
        truck = self.call('get', '/trucks')[0]
        self.assertTrue(truck['status']['complete'])
        self.assertFalse(truck['status']['released_at'])
        self.call('post', f'/trucks/{self.truck_id}/assets/start', 'ben')
        self.call('post', f'/trucks/{self.truck_id}/assets', 'ben', data={'quantities': {name: 0 for name in ASSET_NAMES}})
        self.assertTrue(self.call('get', '/trucks')[0]['status']['released_at'])

    def test_reopen_invalidates_assets_and_preserves_incidents(self):
        self.complete(1, 'ana', shortage=True)
        self.complete(2, 'ben', shortage=True)
        self.call('post', f'/trucks/{self.truck_id}/assets/start', 'ben')
        self.call('post', f'/trucks/{self.truck_id}/assets', 'ben', data={'quantities':{name:0 for name in ASSET_NAMES}})
        self.call('post', f'/loads/{self.load_id}/courts/1/reopen', 'super', data={'reason':'Revisar mercaderia'})
        state = self.call('get', '/trucks')[0]['status']
        self.assertIsNone(state['assets'])
        self.assertFalse(state['complete'])
        self.assertEqual(state['shortages'], [])
        report = self.call('get', '/performance')
        self.assertEqual(len(report['processes']), 3)
        self.assertTrue(all(p['status'] == 'reopened' for p in report['processes']))
        self.assertEqual(len(report['incidents']), 1)
        self.assertEqual(ControlTimer.query.count(), 0)

    def test_database_configuration_requires_explicit_railway_connection(self):
        from config import get_database_url
        from unittest.mock import patch
        for value, allow in [('', '0'), ('sqlite:///picking.db', '0'), ('postgresql://test:test@postgres.railway.internal/railway', '0')]:
            with patch.dict(os.environ, {'DATABASE_URL':value, 'ALLOW_SQLITE_FOR_TESTS':allow}):
                with self.assertRaises(RuntimeError): get_database_url()
        with patch.dict(os.environ, {'DATABASE_URL':'postgresql://test:test@public.proxy.rlwy.net:1234/railway', 'ALLOW_SQLITE_FOR_TESTS':'0'}):
            self.assertTrue(get_database_url().startswith('postgresql+psycopg://'))

    def test_optimistic_concurrency(self):
        with Session(db.engine) as first, Session(db.engine) as second:
            a = first.get(ControlTruck, self.truck_id)
            b = second.get(ControlTruck, self.truck_id)
            a.state = dict(a.state, change='first')
            first.commit()
            b.state = dict(b.state, change='second')
            with self.assertRaises(StaleDataError):
                second.commit()

    def test_only_one_running_process_per_user(self):
        self.start(1, 'ana')
        other = Consolidado(batch_id=self.batch_id, filename='test3.pdf', reparto='0003', camion='OTHER', deposito='Central', fecha_reparto=datetime(2026,10,15))
        db.session.add(other); db.session.flush()
        db.session.add(ConsolidadoDetalle(consolidado_id=other.id,sku='2001',descripcion='Otro',bultos=1,unidades=0,cancha='1'))
        db.session.commit()
        lid = self.call('post','/sources/'+str(other.id),'ana',201)['id']
        self.call('post',f'/loads/{lid}/courts/1/start/1','ana',expected=409)


def tearDownModule():
    with application.app.app_context():
        db.session.remove()
        db.engine.dispose()
    TEMP.cleanup()


if __name__ == '__main__':
    unittest.main()
