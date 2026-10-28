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
        for name, role in [('ana', 'controlador'), ('ben', 'controlador'), ('picker', 'operador'), ('pallet', 'palletizador'), ('super', 'supervisor')]:
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
        for name in ['admin', 'ana', 'ben', 'picker', 'pallet', 'super']:
            self.tokens[name] = self.client.post('/api/auth/login', json={'username':name,'password':'TestPassword123!'}).json['token']
        self.load_id = self.call('post', '/sources/'+str(self.source.id), 'admin', expected=201)['id']
        self.truck_id = self.call('get', '/trucks')[0]['id']
        from services.warehouse import UserCourt
        for name in ['ana', 'ben', 'picker', 'pallet']:
            db.session.add(UserCourt(user_id=User.query.filter_by(username=name).one().id, court_number=1))
        for sku in ['1001', '1002']:
            db.session.add(Article(sku=sku, descripcion=sku, bultos_por_pallet=100, unidades_por_bulto=12))
        db.session.commit()
        self.approve_current()

    def approve_current(self):
        self.call('put', '/settings', data=dict(branch='Central', truck='ABC123', capacity=20, mix_courts_default=False))
        plan = self.call('post', f'/trucks/{self.truck_id}/planning/simulate', data=dict(capacity=20, mix_courts=False))
        self.call('post', f'/trucks/{self.truck_id}/planning/approve', data=dict(plan, physical_review=True))

    def tearDown(self):
        db.session.remove()

    def test_live_monitor_includes_approvals_assets_and_safe_activity(self):
        from models import LogEntry
        actor = User.query.filter_by(username='admin').one()
        db.session.add(LogEntry(user_id=actor.id, action='aprobar_planificacion', entity='control_truck',
                               timestamp=datetime(2026, 10, 16, 1, 0), details='{"private":"not sent"}'))
        db.session.commit()
        data = self.call('get', '/monitor?date=2026-10-15', 'super')
        self.assertEqual(data['trucks'][0]['planning'], 'approved')
        self.assertEqual(data['trucks'][0]['assets_status'], 'pending')
        self.assertFalse(data['trucks'][0]['released'])
        self.assertTrue(any(e['action'] == 'aprobar_planificacion' for e in data['events']))
        self.assertTrue(all('details' not in e for e in data['events']))
        self.call('get', '/monitor?date=2026-10-15', 'picker', expected=403)
        self.call('get', '/monitor?date=2026-10-15', 'ana', expected=403)


    def call(self, method, path, user='admin', expected=200, data=None):
        kwargs = {'headers':{'Authorization':'Bearer '+self.tokens[user]}}
        if data is not None:
            kwargs['json'] = data
        response = getattr(self.client, method)('/api/load-control'+path, **kwargs)
        self.assertEqual(response.status_code, expected, response.get_data(as_text=True))
        return response.json

    def start(self, stage, user):
        if stage == 1:
            # Preparation is now a prerequisite for controls; exercise its real API.
            load = self.call('get', f'/loads/{self.load_id}')
            existing = load['canchas'][0]['status']['checks']
            if not any(c['stage'] == 0 for c in existing):
                prep = self.call('post', f'/loads/{self.load_id}/courts/1/start/0', 'admin')
                self.call('post', f'/loads/{self.load_id}/courts/1/checks/0/{prep['id']}/finish', 'admin')
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

    def upload_pdf(self, data, filename='synthetic.pdf', user='admin'):
        return self.client.post('/api/uploads/pdf',
            headers={'Authorization': 'Bearer ' + self.tokens[user]},
            data={'files': (BytesIO(data), filename)}, content_type='multipart/form-data')

    def test_real_pdf_import_download_duplicate_and_control(self):
        Article.query.filter_by(sku='1001').update(dict(unidades_por_bulto=6, bultos_por_pallet=10))
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
            headers={'Authorization': 'Bearer ' + self.tokens['admin']})
        self.assertEqual(downloaded.data, pdf)
        before = Consolidado.query.count()
        duplicate = self.upload_pdf(pdf)
        self.assertEqual(duplicate.json['processed'], [])
        self.assertEqual(len(duplicate.json['errors']), 1)
        self.assertEqual(Consolidado.query.count(), before)
        controlled = self.call('post', '/sources/'+str(source.id), 'admin', expected=201)
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
        headers = {'Authorization': 'Bearer ' + self.tokens['admin']}
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

    def test_pallet_simulation_is_manager_only_and_does_not_change_state(self):
        from copy import deepcopy
        for sku in ['1001', '1002']:
            Article.query.filter_by(sku=sku).update(dict(bultos_por_pallet=5, unidades_por_bulto=12))
        db.session.commit()
        before = deepcopy(db.session.get(ControlTruck, self.truck_id).state)
        endpoint = f'/trucks/{self.truck_id}/planning/simulate'
        payload = dict(capacity=2, mix_courts=False)
        self.call('post', endpoint, 'ana', expected=403, data=payload)
        self.call('post', endpoint, 'ben', expected=403, data=payload)
        result = self.call('post', endpoint, 'super', data=payload)
        self.assertEqual(result['full_count'], 1)
        self.assertEqual(result['mixed_count'], 1)
        self.assertTrue(result['fits_estimate'])
        self.assertEqual(db.session.get(ControlTruck, self.truck_id).state, before)
        self.call('post', endpoint, 'super', expected=400, data=dict(capacity=0))
        Article.query.filter_by(sku='1002').delete(); db.session.commit()
        self.call('post', endpoint, 'super', expected=400, data=payload)

    def test_picking_answers_are_saved_and_corrected_is_rejected(self):
        path = self.start(0, 'picker')
        responsible_id = User.query.filter_by(username='picker').one().id
        self.answer(path, '1001', 'picker')
        self.answer(path, '1002', 'picker', 'shortage', physical_b=3, physical_u=0,
            responsible_user_id=responsible_id, origin='picking', note='Falta un bulto')
        before = self.call('get', f'/trucks/{self.truck_id}/audit')
        rejected = self.answer(path, '1001', 'picker', 'corrected', expected=400,
            responsible_user_id=responsible_id, origin='picking', note='Corregido')
        self.assertIn('En picking', rejected['error'])
        self.assertEqual(self.call('get', f'/trucks/{self.truck_id}/audit'), before)
        db.session.expire_all()
        state = db.session.get(ControlTruck, self.truck_id).state
        court = state['courts'][f'{self.load_id}:1']
        answers = court['checks']['0']['answers']
        self.assertEqual(answers['1001']['result'], 'ok')
        self.assertEqual((answers['1001']['physical_b'], answers['1001']['physical_u']), (5, 0))
        self.assertEqual(answers['1002']['result'], 'shortage')
        self.assertEqual((answers['1002']['physical_b'], answers['1002']['physical_u']), (3, 0))
        self.assertEqual(court['preparation_shortages']['0']['1002']['actual_b'], 3)
        incident = answers['1002']['incident']
        self.assertEqual(incident['responsible_user_id'], responsible_id)
        self.assertEqual(incident['detected_by'], responsible_id)
        self.assertEqual(incident['origin'], 'picking')
        audit = [row['details'] for row in before if row['action'] == 'respuesta_control']
        self.assertEqual({row['result'] for row in audit}, {'ok', 'shortage'})
        self.assertTrue(all(row['stage'] == 0 for row in audit))
        report = self.call('get', '/performance')
        self.assertEqual(len(report['incidents']), 1)
        self.assertEqual(report['incidents'][0]['stage'], 0)

    def test_picking_can_finish_with_unanswered_products(self):
        path = self.start(0, 'picker')
        self.answer(path, '1001', 'picker')
        self.call('post', path+'/finish', 'picker')
        db.session.expire_all()
        check = db.session.get(ControlTruck, self.truck_id).state['courts'][f'{self.load_id}:1']['checks']['0']
        self.assertEqual(check['status'], 'done')
        self.assertNotIn('1002', check['answers'])

    def test_two_people_shortage_assets_and_manual_adjustment(self):
        picking = self.start(0, 'picker')
        self.call('post', f'/loads/{self.load_id}/courts/1/start/1', 'ben', expected=409)
        self.call('post', picking+'/finish', 'picker')
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
        self.call('post', f'/loads/{self.load_id}/courts/1/start/1', 'ana', expected=409)
        first_id = self.load_id
        second_id = self.call('post', '/sources/'+str(second.id), 'admin', expected=201)['id']
        self.approve_current()
        self.complete(1, 'ana'); self.complete(2, 'ben')
        self.call('post', f'/trucks/{self.truck_id}/assets/start', 'ben', expected=409)
        self.load_id = second_id
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
        self.assertEqual(len(report['processes']), 4)
        self.assertTrue(all(p['status'] == ('done' if p['stage'] == 0 else 'reopened') for p in report['processes']))
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
        lid = self.call('post','/sources/'+str(other.id),'admin',201)['id']
        self.call('post',f'/loads/{lid}/courts/1/start/1','ana',expected=409)

    def test_assignments_enforced_for_lists_direct_urls_and_revocation(self):
        picker = User.query.filter_by(username='picker').one()
        self.assertEqual(self.call('get', '/my-courts', 'picker')['courts'], [1])
        self.call('post', f'/loads/{self.load_id}/courts/1/start/1', 'picker', expected=403)
        self.call('post', '/sources/'+str(self.source.id), 'picker', expected=403)
        response = self.client.get('/api/operations/picking', headers={'Authorization':'Bearer '+self.tokens['picker']})
        self.assertEqual(response.status_code, 403)
        path = self.start(0, 'picker')
        self.answer(path, '1001', 'picker')
        self.call('put', f'/users/{picker.id}/courts', 'super', data={'courts': []})
        self.assertEqual(self.call('get', '/trucks', 'picker'), [])
        self.call('get', f'/loads/{self.load_id}', 'picker', expected=403)
        self.answer(path, '1002', 'picker', expected=403)
        self.assertIsNone(db.session.get(ControlTimer, picker.id))
        self.call('put', f'/users/{picker.id}/courts', 'super', data={'courts': [1, 2, 1]})
        self.assertEqual(self.call('get', '/my-courts', 'picker')['courts'], [1, 2])
        resumed = self.call('post', f'/loads/{self.load_id}/courts/1/start/0', 'picker')
        self.assertIn('1001', resumed['answers'])

    def test_approval_and_full_pallet_split_preserve_original_controls(self):
        from services.load_control import ControlLoad
        load = db.session.get(ControlLoad, self.load_id)
        from copy import deepcopy
        content = deepcopy(load.content)
        content['canchas'][0]['productos'][0]['bultos'] = 244
        load.content = content
        Article.query.filter_by(sku='1001').update(dict(bultos_por_pallet=50))
        db.session.commit()
        self.assertEqual(self.call('get', '/trucks', 'picker'), [])
        self.call('post', f'/loads/{self.load_id}/courts/1/start/0', 'picker', expected=409)
        self.approve_current()
        picking = self.call('get', f'/loads/{self.load_id}', 'picker')['canchas'][0]['productos']
        pallets = self.call('get', f'/loads/{self.load_id}', 'pallet')['canchas'][0]['productos']
        self.assertEqual(picking[0]['bultos'], 44)
        self.assertEqual((pallets[0]['pallets'], pallets[0]['bultos']), (4, 200))
        self.assertEqual(self.call('get', f'/loads/{self.load_id}', 'ana')['canchas'][0]['productos'][0]['bultos'], 244)
        path = self.start(4, 'pallet')
        self.answer(path, '1001', 'pallet')
        self.call('post', path+'/finish', 'pallet')
        self.call('post', f'/loads/{self.load_id}/courts/1/start/0', 'pallet', expected=403)

    def test_stale_overcapacity_and_unreviewed_plans_cannot_be_approved(self):
        endpoint = f'/trucks/{self.truck_id}/planning'
        plan = self.call('post', endpoint+'/simulate', data={'capacity': 20, 'mix_courts': False})
        self.call('post', endpoint+'/approve', expected=400, data=plan)
        self.call('post', endpoint+'/approve', expected=409, data=dict(plan, physical_review=True, version=0))
        Article.query.filter_by(sku='1001').update(dict(bultos_por_pallet=1))
        db.session.commit()
        self.call('post', endpoint+'/approve', expected=409, data=dict(plan, physical_review=True))
        self.call('put', '/settings', data=dict(branch='Central', truck='ABC123', capacity=1, mix_courts_default=False))
        over = self.call('post', endpoint+'/simulate', data={'capacity': 1, 'mix_courts': False})
        self.call('post', endpoint+'/approve', expected=409, data=dict(over, physical_review=True))
        self.call('put', '/settings', 'super', expected=403, data={})

    def test_create_operator_with_multiple_courts_is_atomic(self):
        data = dict(username='multi', email='multi@test.local', password='TestPassword123!', role='operador', courts=[1,2])
        result = self.call('post', '/users', expected=201, data=data)
        from services.warehouse import assigned_courts
        self.assertEqual(assigned_courts(result['id']), [1,2])
        self.call('post', '/users', expected=400, data=dict(data, username='invalid', email='invalid@test.local', courts=[0]))
        self.assertIsNone(User.query.filter_by(username='invalid').first())

    def test_control_waits_for_preparation_and_legacy_can_continue(self):
        self.call('post', f'/loads/{self.load_id}/courts/1/start/1', 'ana', expected=409)
        path = self.start(1, 'ana')
        # Existing pre-planning processes remain operable after rollout.
        from copy import deepcopy
        truck = db.session.get(ControlTruck, self.truck_id)
        state = deepcopy(truck.state)
        state.pop('planning')
        truck.state = state
        db.session.commit()
        self.answer(path, '1001', 'ana')
        self.assertEqual(len(self.call('get', '/trucks', 'ana')), 1)

    def test_picker_sees_full_pallets_as_information_without_double_counting(self):
        for article in Article.query.all():
            article.bultos_por_pallet = 2
        db.session.commit()
        self.approve_current()
        load = self.call('get', f'/loads/{self.load_id}', 'picker')
        court = load['canchas'][0]
        self.assertEqual(court['full_pallet_count'], 4)
        self.assertEqual(len(court['full_pallets_info']), 2)
        self.assertEqual(len(court['productos']), 1)
        product = court['productos'][0]
        self.assertEqual((product['sku'], product['bultos'], product['full_pallets_count'], product['full_pallets_bultos']), ('1001', 1, 2, 4))
        started = self.call('post', f'/loads/{self.load_id}/courts/1/start/0', 'picker')
        self.assertEqual(started['products'][0]['bultos'], 1)
        self.assertEqual(started['products'][0]['full_pallets_count'], 2)
        self.assertEqual(started['products'][0]['pallets'], 0)

    def test_full_pallet_only_court_remains_visible_to_picker_without_startable_work(self):
        for article in Article.query.all():
            article.bultos_por_pallet = 1
        db.session.commit()
        self.approve_current()
        load = self.call('get', f'/loads/{self.load_id}', 'picker')
        self.assertEqual(load['canchas'][0]['productos'], [])
        self.assertEqual(load['canchas'][0]['full_pallet_count'], 9)
        trucks = self.call('get', '/trucks', 'picker')
        self.assertEqual(trucks[0]['loads'][0]['canchas'][0]['full_pallet_count'], 9)
        self.call('post', f'/loads/{self.load_id}/courts/1/start/0', 'picker', expected=409)

    def test_timing_audit_and_monitor_permissions(self):
        from services.load_control import timing
        end = datetime.now(timezone.utc)
        result = timing(dict(started_at=(end-timedelta(seconds=20)).isoformat(), finished_at=end.isoformat(), active_seconds=5, timer_started_at=None))
        self.assertEqual(result, dict(active_seconds=5, wall_seconds=20, paused_seconds=15))
        endpoint = f'/trucks/{self.truck_id}/planning'
        self.call('post', endpoint+'/start', 'super')
        self.approve_current()
        plan = db.session.get(ControlTruck, self.truck_id).state['planning']
        self.assertGreaterEqual(plan['review_seconds'], 0)
        self.assertGreaterEqual(plan['waiting_seconds'], 0)
        self.call('get', '/monitor?date=2026-10-15', 'picker', expected=403)
        monitor = self.call('get', '/monitor?date=2026-10-15', 'super')
        self.assertTrue(monitor['processes'])
        local_day = datetime.now(timezone(timedelta(hours=-3))).date().isoformat()
        events = self.call('get', '/activity?date='+local_day, 'super')['events']
        self.assertTrue(any(e['details'].get('server_ms') is not None for e in events))
        self.assertNotIn('TestPassword123!', str(events))
        self.assertNotIn(self.tokens['admin'], str(events))


def tearDownModule():
    with application.app.app_context():
        db.session.remove()
        db.engine.dispose()
    TEMP.cleanup()


if __name__ == '__main__':
    unittest.main()
