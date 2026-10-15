"""Smoke test end-to-end against temporary SQLite database. Run: python tests/smoke_test.py"""
import os,sys,tempfile
from pathlib import Path
TMP=tempfile.TemporaryDirectory();os.environ['DATABASE_URL']='sqlite:///'+str(Path(TMP.name)/'test.db');os.environ['SECRET_KEY']='smoke_test_only_super_long_secret_string_2026';os.environ['ADMIN_PASSWORD']='SmokeTestPassword42!';sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from main import app
c=TestClient(app)
def call(method,path,token=None,**kw):
    r=c.request(method,'/api'+path,headers={'Authorization':'Bearer '+token} if token else None,**kw)
    if r.status_code>=400:raise RuntimeError(f'{method} {path}: {r.status_code} {r.text}')
    return r.json()
def login(name,password):return call('POST','/login',json={'username':name,'password':password})['token']
a=login('admin','SmokeTestPassword42!')
for username in ['ana','ben']:
    call('POST','/users',a,json={'username':username,'name':username,'password':'ControllerPassword20!','role':'controller'})
tokens=[login('ana','ControllerPassword20!'),login('ben','ControllerPassword20!')]
pdf=Path('/mnt/data/20261009142924planilladecarga.pdf').read_bytes()
r=call('POST','/import',a,files=[('files',('sample.pdf',pdf,'application/pdf'))]);assert r[0]['productos']==68
load=call('GET','/loads',a)[0];lid=load['id'];detail=call('GET',f'/loads/{lid}',a)
assert sum(p['bultos'] for ct in detail['canchas'] for p in ct['productos'])==471
assert sum(p['unidades'] for ct in detail['canchas'] for p in ct['productos'])==106
for ct in detail['canchas']:
 for stage,who in [(1,tokens[0]),(2,tokens[1])]:
    check=call('POST',f'/loads/{lid}/court/{ct["numero"]}/start/{stage}',who)['check_id']
    for p in ct['productos']:
       body={'result':'ok'}
       if ct['numero']==5 and p['sku']=='47489':body={'result':'shortage','physical_b':2,'physical_u':0,'note':'Faltan físicamente 2 bultos'}
       call('POST',f'/checks/{check}/answer/{p["sku"]}',who,json=body)
    call('POST',f'/checks/{check}/finish',who)
status=call('GET','/loads',a)[0]['truck_status'];assert status['complete'] and not status['allowed']
short=call('GET','/shortages',a);assert len(short)==1
call('POST',f'/shortages/{short[0]["id"]}/approve',a)
assets=call('GET','/asset-types',a)
status=call('POST','/assets',tokens[0],json={'branch':load['branch'],'load_date':load['load_date'],'truck':load['truck'],'quantities':{n:0 for n in assets}})
assert status['allowed'] and status['released_at']
assert status['shortages'][0]['adjusted_at'] is None
call('POST',f'/shortages/{short[0]["id"]}/adjusted',a)
print('PASS: PDF 471 bultos/106 unidades, 6 canchas, 2 controladores, faltante, autorizacion, activos, liberacion, ajuste Chess pendiente y confirmacion')
TMP.cleanup()
