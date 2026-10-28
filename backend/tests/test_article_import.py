"""CSV/voice regression tests on a disposable SQLite database only."""
import csv
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

TEMP = tempfile.TemporaryDirectory()
os.environ.update(DATABASE_URL='sqlite:///' + str(Path(TEMP.name) / 'articles.db'),
                  INIT_DB_ON_STARTUP='0', ALLOW_SQLITE_FOR_TESTS='1', JWT_SECRET='article-tests-secret-only-long-enough')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as application
from sqlalchemy.schema import CreateTable, DropTable
from models import Article, Role, User, LogEntry
from auth import AuthService
from utils.db import db
from services.csv_import import parse_article_csv, import_articles_from_csv
from routes.load_control import voice_products


def csv_bytes(*changes):
    template = {'Articulo': '001', 'Descripcion articulo': 'BRAHMA X12', 'Unidades por bulto': '12',
                'Bultos por pallet': '50', 'TIPO DE PRODUCTO': 'MERCADERIA', 'Activo': 'SI',
                'Usado en dispositivo movil': 'SI', 'Anulado': 'NO', 'Codigo de barras': '001234', 'Extra futuro': '  original  '}
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(template), delimiter=';')
    writer.writeheader()
    for change in changes or ({},):
        writer.writerow(dict(template, **change))
    return output.getvalue().encode('utf-8-sig')


class ArticleImportTest(unittest.TestCase):
    def test_automatic_voice_import_and_creation_preserve_existing(self):
        result = import_articles_from_csv(csv_bytes())
        self.assertEqual(result['voice_generated'], 1)
        article = Article.query.one()
        self.assertEqual(article.descripcion_voz, 'BRAHMA pack de 12')
        article.descripcion_voz = 'Mi nombre manual'
        db.session.commit()
        result = import_articles_from_csv(csv_bytes({'Descripcion articulo': 'BUD CAN X24 355CC'}))
        self.assertEqual(result['voice_generated'], 0)
        self.assertEqual(article.descripcion_voz, 'Mi nombre manual')
        article.descripcion_voz = None
        db.session.commit()
        result = import_articles_from_csv(csv_bytes({'Descripcion articulo': 'BUD CAN X24 355CC'}))
        self.assertEqual(result['voice_generated'], 1)
        self.assertEqual(article.descripcion_voz, 'Budweiser lata pack de 24 de 355 cc')
        response = self.client.post('/api/articles', json={'sku': 'nuevo', 'descripcion': 'BUD CAN'}, headers=self.tokens['administrador'])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Article.query.filter_by(sku='nuevo').one().descripcion_voz, 'Budweiser lata')

    def test_voice_suggestions_preview_apply_conflict_and_limits(self):
        headers = self.tokens['administrador']
        db.session.add_all([
            Article(sku='a', descripcion='BUD CAN', activo=True),
            Article(sku='b', descripcion='BUD', descripcion_voz='Manual', activo=True),
            Article(sku='c', descripcion='BUD', activo=False),
            Article(sku='d', descripcion='BUD ' * 60, activo=True),
        ])
        db.session.commit()
        self.assertEqual(self.client.get('/api/articles/voice-suggestions', headers=self.tokens['operador']).status_code, 403)
        response = self.client.get('/api/articles/voice-suggestions', headers=headers)
        self.assertEqual(response.headers['X-Voice-Skipped'], '1')
        self.assertIsNone(Article.query.filter_by(sku='a').one().descripcion_voz)
        def post(apply):
            return self.client.post('/api/articles/voice-csv', headers=headers,
                                    data={'file': (io.BytesIO(response.data), 'propuestas.csv'), 'apply': apply})
        self.assertEqual(post('0').json['changes'], [{'sku': 'a', 'before': '', 'after': 'Budweiser lata'}])
        self.assertIsNone(Article.query.filter_by(sku='a').one().descripcion_voz)
        self.assertEqual(post('1').status_code, 200)
        self.assertEqual(post('1').status_code, 409)
        self.assertEqual(Article.query.filter_by(sku='b').one().descripcion_voz, 'Manual')
        self.assertIsNone(Article.query.filter_by(sku='c').one().descripcion_voz)
        self.assertIsNone(Article.query.filter_by(sku='d').one().descripcion_voz)
        self.assertEqual(LogEntry.query.filter_by(action='editar_descripcion_voz').count(), 1)
        self.assertEqual(voice_products([{'sku': 'a', 'descripcion': 'BUD CAN'}])[0]['descripcion_voz'], 'Budweiser lata')
        self.assertEqual(self.client.get('/api/articles/voice-suggestions', headers=headers).status_code, 204)

    @classmethod
    def tearDownClass(cls):
        with application.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def setUp(self):
        self.ctx = application.app.app_context(); self.ctx.push()
        self.addCleanup(self.ctx.pop); self.addCleanup(db.session.remove)
        with db.engine.begin() as connection:
            for table in reversed(db.metadata.sorted_tables): connection.execute(DropTable(table, if_exists=True))
            for table in db.metadata.sorted_tables: connection.execute(CreateTable(table))
        self.client = application.app.test_client()
        self.tokens = {}
        for name in ('administrador', 'operador'):
            role = Role(name=name); db.session.add(role); db.session.flush()
            user = User(username=name, email=name+'@test.local', password_hash='unused', role=role, active=True)
            db.session.add(user); db.session.flush()
            self.tokens[name] = {'Authorization': 'Bearer '+AuthService.generate_token(user)}
        db.session.commit()

    def test_filters_and_preserves_raw_columns(self):
        raw = csv_bytes({}, {'Articulo': '002', 'Activo': 'NO'}, {'Articulo': '003', 'Anulado': 'SI'},
                        {'Articulo': '004', 'TIPO DE PRODUCTO': 'ENVASE'},
                        {'Articulo': '005', 'Usado en dispositivo movil': 'NO'},
                        {'Articulo': '006', 'Activo': ''},
                        {'Articulo': '007', 'TIPO DE PRODUCTO': ' Mercadería ', 'Activo': 'sí'})
        parsed = parse_article_csv(raw)
        self.assertEqual([a['sku'] for a in parsed['articles']], ['001', '007'])
        self.assertEqual(len(parsed['excluded']), 5)
        self.assertEqual(parsed['articles'][0]['datos_origen']['Codigo de barras'], '001234')
        self.assertEqual(parsed['articles'][0]['datos_origen']['Extra futuro'], '  original  ')

    def test_reimport_and_sync_preserve_ids_voice_and_history(self):
        self.assertTrue(import_articles_from_csv(csv_bytes())['applied'])
        article = Article.query.one(); article_id = article.id
        article.descripcion_voz = 'Brahma de un litro'
        db.session.add(Article(sku='absent', descripcion='Anterior', activo=True)); db.session.commit()
        self.assertTrue(import_articles_from_csv(csv_bytes({'Descripcion articulo': 'Nueva'}), 'replace')['applied'])
        article = db.session.get(Article, article_id)
        self.assertEqual(article.descripcion_voz, 'Brahma de un litro')
        self.assertEqual(article.descripcion, 'Nueva')
        self.assertFalse(Article.query.filter_by(sku='absent').one().activo)
        result = import_articles_from_csv(csv_bytes({'Anulado': 'SI', 'Unidades por bulto': 'invalido'}))
        self.assertTrue(result['applied']); self.assertEqual(result['inactive'], 1)
        self.assertEqual(Article.query.count(), 2)
        self.assertFalse(db.session.get(Article, article_id).activo)
        self.assertTrue(import_articles_from_csv(csv_bytes())['applied'])
        self.assertEqual(db.session.get(Article, article_id).descripcion_voz, 'Brahma de un litro')

    def test_invalid_or_duplicate_csv_changes_nothing(self):
        import_articles_from_csv(csv_bytes())
        for raw in (csv_bytes({}, {}), csv_bytes({'Unidades por bulto': 'bad'}), b'Articulo;Unidades por bulto;Bultos por pallet\n001;12;50\n'):
            for mode in ('merge', 'replace'):
                self.assertFalse(import_articles_from_csv(raw, mode)['applied'])
                self.assertEqual(Article.query.one().descripcion, 'BRAHMA X12')
                self.assertTrue(Article.query.one().activo)

    def test_voice_survives_absence_and_return_in_both_import_modes(self):
        import_articles_from_csv(csv_bytes())
        article = Article.query.one()
        original_id = article.id
        article.descripcion_voz = 'Nombre manual permanente'
        db.session.commit()
        for mode in ('merge', 'replace'):
            self.assertTrue(import_articles_from_csv(csv_bytes({'Articulo': '002'}), mode)['applied'])
            db.session.expire_all()
            self.assertEqual(db.session.get(Article, original_id).descripcion_voz, 'Nombre manual permanente')
            self.assertTrue(import_articles_from_csv(csv_bytes({'Descripcion articulo': 'Texto nuevo del proveedor'}), mode)['applied'])
            db.session.expire_all()
            article = db.session.get(Article, original_id)
            self.assertTrue(article.activo)
            self.assertEqual(article.descripcion_voz, 'Nombre manual permanente')

    def test_csv_cannot_write_voice_even_if_future_parser_exposes_it(self):
        import_articles_from_csv(csv_bytes())
        article = Article.query.one()
        article.descripcion_voz = 'Nombre manual permanente'
        db.session.commit()
        for mode in ('merge', 'replace'):
            parsed = parse_article_csv(csv_bytes({}, {'Articulo': '002'}))
            for payload in parsed['articles']:
                payload['descripcion_voz'] = 'No debe sobrescribir la voz'
            with patch('services.csv_import.parse_article_csv', return_value=parsed):
                self.assertTrue(import_articles_from_csv(b'unused', mode)['applied'])
            db.session.expire_all()
            self.assertEqual(Article.query.filter_by(sku='001').one().descripcion_voz, 'Nombre manual permanente')
            self.assertEqual(Article.query.filter_by(sku='002').one().descripcion_voz, 'BRAHMA pack de 12')

    def test_voice_api_permissions_conflict_and_product_fallback(self):
        import_articles_from_csv(csv_bytes())
        article = Article.query.one(); article_id = article.id
        path = f'/api/articles/{article_id}/voice'
        payload = {'descripcion_voz': 'Brahma de un litro', 'previous': article.descripcion_voz}
        self.assertEqual(self.client.put(path, json=payload, headers=self.tokens['operador']).status_code, 403)
        self.assertEqual(self.client.put(path, json=payload, headers=self.tokens['administrador']).status_code, 200)
        self.assertEqual(self.client.put(path, json=payload, headers=self.tokens['administrador']).status_code, 409)
        detail = self.client.get(f'/api/articles/{article_id}', headers=self.tokens['administrador']).json
        self.assertEqual(len(detail['datos_origen']), 10)
        self.assertEqual(LogEntry.query.filter_by(action='editar_descripcion_voz').count(), 1)
        products = voice_products([{'sku': '001', 'descripcion': 'PDF original'}, {'sku': 'missing', 'descripcion': 'Otra'}])
        self.assertEqual(products[0]['descripcion_voz'], payload['descripcion_voz'])
        self.assertEqual(products[0]['descripcion'], 'PDF original')
        self.assertEqual(products[1]['descripcion_voz'], 'Otra')
        response = self.client.put(path, json={'descripcion_voz': '', 'previous': payload['descripcion_voz']}, headers=self.tokens['administrador'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(voice_products([{'sku': '001', 'descripcion': 'PDF original'}])[0]['descripcion_voz'], 'PDF original')

    def test_import_endpoint_archives_full_file(self):
        raw = csv_bytes()
        response = self.client.post('/api/articles/import-csv', headers=self.tokens['administrador'],
                                    data={'file': (io.BytesIO(raw), 'articles.csv'), 'mode': 'merge'})
        self.assertEqual(response.status_code, 200, response.json)
        from models import UploadedFile
        self.assertEqual(db.session.get(UploadedFile, response.json['uploaded_file_id']).data, raw)

    def test_voice_csv_preview_apply_conflict_and_atomic_validation(self):
        import_articles_from_csv(csv_bytes({}, {'Articulo': '002'}))
        for article in Article.query.all(): article.descripcion_voz = None
        db.session.commit()
        headers = self.tokens['administrador']
        path = '/api/articles/voice-csv'
        self.assertEqual(self.client.get(path, headers=self.tokens['operador']).status_code, 403)
        response = self.client.get(path, headers=headers)
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(io.StringIO(response.data.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(rows[1][0], '001')
        rows[1][2] = 'Brahma de un litro'
        rows[2][2] = 'Agua sin gas'

        def post(rows, apply='0', auth=headers):
            stream = io.StringIO(newline='')
            csv.writer(stream, delimiter=';').writerows(rows)
            return self.client.post(path, headers=auth, data={
                'file': (io.BytesIO(stream.getvalue().encode('utf-8-sig')), 'voz.csv'), 'apply': apply})

        self.assertEqual(post(rows, '1', self.tokens['operador']).status_code, 403)
        preview = post(rows)
        self.assertEqual(preview.json['updated'], 2)
        self.assertIsNone(Article.query.filter_by(sku='001').one().descripcion_voz)
        self.assertEqual(post(rows + [rows[1]], '1').status_code, 422)
        rows[2][2] = 'x' * 256
        self.assertEqual(post(rows, '1').status_code, 422)
        self.assertIsNone(Article.query.filter_by(sku='001').one().descripcion_voz)
        rows[2][2] = 'Agua sin gas'
        self.assertEqual(post(rows, '1').json['updated'], 2)
        self.assertEqual(LogEntry.query.filter_by(action='editar_descripcion_voz').count(), 2)
        self.assertEqual(post(rows, '1').status_code, 409)
        rows = list(csv.reader(io.StringIO(self.client.get(path, headers=headers).data.decode('utf-8-sig')), delimiter=';'))
        rows[1][2] = ''  # Blank preserves; explicit SI clears.
        rows[2][3] = 'SI'
        self.assertEqual(post(rows, '1').json['updated'], 1)
        self.assertEqual(Article.query.filter_by(sku='001').one().descripcion_voz, 'Brahma de un litro')
        self.assertIsNone(Article.query.filter_by(sku='002').one().descripcion_voz)
        self.assertEqual(Article.query.filter_by(sku='001').one().descripcion, 'BRAHMA X12')

    def test_voice_csv_preserves_special_text_and_rejects_modified_codes(self):
        from services.voice_csv import export_voice_csv, parse_voice_csv
        article = Article(sku='0001', descripcion='=original', descripcion_voz='=voz; "especial"\nOtra línea')
        rows = list(csv.reader(io.StringIO(export_voice_csv([article]).decode('utf-8-sig')), delimiter=';'))
        self.assertTrue(rows[1][1].startswith("'="))
        self.assertEqual(parse_voice_csv(export_voice_csv([article]))[0]['value'], article.descripcion_voz)
        rows[1][0] = '1'
        output = io.StringIO(); csv.writer(output, delimiter=';').writerows(rows)
        with self.assertRaises(ValueError): parse_voice_csv(output.getvalue().encode())

    def test_voice_backup_includes_inactive_and_all_pages_without_changing_data(self):
        for n in range(205):
            db.session.add(Article(sku=f'{n:04}', descripcion='Original',
                                   descripcion_voz=f'Voz número {n}', activo=n % 2 == 0))
        db.session.add(Article(sku='no-voice', descripcion='Sin voz'))
        db.session.commit()
        path = '/api/articles/voice-backup'
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, headers=self.tokens['operador']).status_code, 403)
        response = self.client.get(path, headers=self.tokens['administrador'])
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertEqual(data['total'], 205)
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['items'][1], {'sku': '0001', 'descripcion_voz': 'Voz número 1'})
        self.assertEqual(len(data['items']), 205)
        self.assertEqual(Article.query.count(), 206)
        self.assertIn('no-store', response.headers['Cache-Control'])


if __name__ == '__main__': unittest.main()
