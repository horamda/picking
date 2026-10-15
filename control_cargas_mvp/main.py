import os, json, hmac, hashlib, secrets
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import jwt
from parser_chess import parse_pdf

DB=os.getenv('DATABASE_URL','sqlite:///./control_cargas.db').replace('postgres://','postgresql+psycopg://',1).replace('postgresql://','postgresql+psycopg://',1)
KEY=os.getenv('SECRET_KEY','DEV_ONLY_NOT_FOR_PRODUCTION')
engine=create_engine(DB,connect_args={'check_same_thread':False} if DB.startswith('sqlite') else {},pool_pre_ping=True)
app=FastAPI(title='Control de Cargas - Del Palacio',version='0.1.0')
app.mount('/static', StaticFiles(directory='static'), name='static')

def now():return datetime.now(timezone.utc).isoformat()
def hash_pass(password):
    salt=secrets.token_bytes(16);digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,250_000)
    return 'pbkdf2$'+salt.hex()+'$'+digest.hex()
def verify(password, stored):
    try:
        _,sh,dh=stored.split('$');return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(sh),250_000),bytes.fromhex(dh))
    except Exception:return False

def init():
    stmts=[
    'CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1)',
    'CREATE TABLE IF NOT EXISTS loads(id INTEGER PRIMARY KEY,branch TEXT NOT NULL,load_date TEXT NOT NULL,reparto TEXT NOT NULL,truck TEXT NOT NULL,driver TEXT,content TEXT NOT NULL,created_at TEXT NOT NULL, UNIQUE(branch,load_date,reparto))',
    'CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY,load_id INTEGER NOT NULL,court INTEGER NOT NULL,stage INTEGER NOT NULL,user_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT \'active\',started_at TEXT NOT NULL,finished_at TEXT, UNIQUE(load_id,court,stage))',
    'CREATE TABLE IF NOT EXISTS answers(id INTEGER PRIMARY KEY,check_id INTEGER NOT NULL,sku TEXT NOT NULL,result TEXT NOT NULL,physical_b INTEGER,physical_u INTEGER,note TEXT,created_at TEXT NOT NULL, UNIQUE(check_id,sku))',
    'CREATE TABLE IF NOT EXISTS shortages(id INTEGER PRIMARY KEY,load_id INTEGER NOT NULL,court INTEGER NOT NULL,sku TEXT NOT NULL,expected_b INTEGER NOT NULL,expected_u INTEGER NOT NULL,actual_b INTEGER NOT NULL,actual_u INTEGER NOT NULL,reported_by INTEGER NOT NULL,approved_by INTEGER,approved_at TEXT,adjusted_by INTEGER,adjusted_at TEXT,note TEXT,created_at TEXT NOT NULL, UNIQUE(load_id,court,sku))',
    'CREATE TABLE IF NOT EXISTS assets(id INTEGER PRIMARY KEY,branch TEXT NOT NULL,load_date TEXT NOT NULL,truck TEXT NOT NULL,details TEXT NOT NULL,user_id INTEGER NOT NULL,created_at TEXT NOT NULL, UNIQUE(branch,load_date,truck))',
    'CREATE TABLE IF NOT EXISTS departures(id INTEGER PRIMARY KEY,branch TEXT NOT NULL,load_date TEXT NOT NULL,truck TEXT NOT NULL,released_at TEXT NOT NULL, UNIQUE(branch,load_date,truck))',
    'CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL)']
    with engine.begin() as c:
        for statement in stmts:c.execute(text(statement))
        admin=os.getenv('ADMIN_USER','admin');password=os.getenv('ADMIN_PASSWORD','')
        if password and not c.execute(text('SELECT id FROM users WHERE username=:u'),{'u':admin}).first():
            c.execute(text('INSERT INTO users(username,password,name,role) VALUES (:u,:p,:n,:r)'),dict(u=admin,p=hash_pass(password),n='Administrador',r='admin'))
init()

@contextmanager
def session():
    with Session(engine) as s:
        yield s

def get_user(authorization:str|None=Header(None)):
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Iniciá sesión')
    try:payload=jwt.decode(authorization[7:],KEY,algorithms=['HS256'])
    except Exception:raise HTTPException(401,'Sesión inválida')
    with session() as s:
        u=s.execute(text('SELECT id,username,name,role,active FROM users WHERE id=:id'),{'id':int(payload['sub'])}).mappings().first()
        if not u or not u['active']:raise HTTPException(401,'Usuario inactivo')
        return dict(u)

def role(u,allowed):
    if u['role'] not in allowed:raise HTTPException(403,'No tenés permisos')

def audit(s,u,action,details):
    s.execute(text('INSERT INTO audit(actor,action,details,created_at) VALUES (:a,:b,:c,:d)'),dict(a=u['id'] if u else None,b=action,c=json.dumps(details,ensure_ascii=False),d=now()))

class Login(BaseModel):username:str; password:str
class UserCreate(BaseModel):username:str;password:str=Field(min_length=10);name:str;role:str='controller'
class Answer(BaseModel):result:str;physical_b:int|None=None;physical_u:int|None=None;note:str=''
class Shortage(BaseModel):actual_b:int=Field(ge=0);actual_u:int=Field(ge=0);note:str=''
class Assets(BaseModel):branch:str;load_date:str;truck:str;quantities:dict[str,int]
class Reason(BaseModel):reason:str=Field(min_length=3)

@app.get('/')
def home():return FileResponse('static/index.html')
@app.post('/api/login')
def login(body:Login):
    with session() as s:
        u=s.execute(text('SELECT * FROM users WHERE username=:u'),{'u':body.username.strip()}).mappings().first()
        if not u or not u['active'] or not verify(body.password,u['password']):raise HTTPException(401,'Usuario o contraseña incorrectos')
        token=jwt.encode({'sub':str(u['id']),'exp':datetime.now(timezone.utc)+timedelta(hours=24)},KEY,algorithm='HS256')
        return {'token':token,'user':dict(id=u['id'],username=u['username'],name=u['name'],role=u['role'])}
@app.get('/api/me')
def me(u=Depends(get_user)):return u
@app.get('/api/users')
def users(u=Depends(get_user)):
    role(u,['admin','supervisor'])
    with session() as s:return [dict(x) for x in s.execute(text('SELECT id,username,name,role,active FROM users ORDER BY name')).mappings()]
@app.post('/api/users')
def create_user(body:UserCreate,u=Depends(get_user)):
    role(u,['admin'])
    if body.role not in ['admin','supervisor','controller']:raise HTTPException(400,'Rol inválido')
    with session() as s:
        if s.execute(text('SELECT 1 FROM users WHERE username=:u'),{'u':body.username}).first():raise HTTPException(409,'Usuario ya existe')
        s.execute(text('INSERT INTO users(username,password,name,role) VALUES (:u,:p,:n,:r)'),dict(u=body.username,p=hash_pass(body.password),n=body.name,r=body.role));audit(s,u,'new_user',{'username':body.username});s.commit()
    return {'ok':True}
@app.post('/api/import')
async def import_pdfs(files:list[UploadFile]=File(...),u=Depends(get_user)):
    role(u,['admin','supervisor'])
    preview=[]
    for f in files:
        data=await f.read()
        if len(data)>12_000_000:raise HTTPException(400,f'{f.filename}: PDF demasiado grande')
        try:p=parse_pdf(data)
        except Exception as e:raise HTTPException(422,f'{f.filename}: {e}')
        if p['advertencias']:raise HTTPException(422,f"{f.filename}: no se importó porque hay líneas ambiguas: {p['advertencias'][:5]}")
        preview.append((f.filename,p))
    with session() as s:
        for name,p in preview:
            dup=s.execute(text('SELECT 1 FROM loads WHERE branch=:br AND load_date=:dt AND reparto=:rep'),dict(br=p['deposito'],dt=p['fecha'],rep=p['reparto'])).first()
            if dup:raise HTTPException(409,f'{name}: reparto {p["reparto"]} ya importado')
        for name,p in preview:
            s.execute(text('INSERT INTO loads(branch,load_date,reparto,truck,driver,content,created_at) VALUES (:br,:dt,:rep,:tr,:dr,:ct,:ts)'),dict(br=p['deposito'],dt=p['fecha'],rep=p['reparto'],tr=p['camion'],dr=p['chofer'],ct=json.dumps(p,ensure_ascii=False),ts=now()))
            audit(s,u,'import_pdf',{'filename':name,'reparto':p['reparto']})
        s.commit()
    return [{'archivo':n,'reparto':p['reparto'],'camion':p['camion'],'canchas':len(p['canchas']),'productos':sum(len(c['productos']) for c in p['canchas'])} for n,p in preview]

def product(p,court,sku):
    for c in p['canchas']:
        if c['numero']==court:
            for x in c['productos']:
                if x['sku']==sku:return x
    raise HTTPException(404,'Producto no encontrado')

def getload(s,load_id):
    r=s.execute(text('SELECT * FROM loads WHERE id=:id'),{'id':load_id}).mappings().first()
    if not r:raise HTTPException(404,'Planilla no encontrada')
    return dict(r),json.loads(r['content'])

def stage_completed(s,load_id,court,stage):
    return s.execute(text("SELECT 1 FROM checks WHERE load_id=:l AND court=:c AND stage=:s AND status='done'"),dict(l=load_id,c=court,s=stage)).first() is not None

def shortages_for(s,load_id,court):
    return [dict(x) for x in s.execute(text('SELECT * FROM shortages WHERE load_id=:l AND court=:c'),dict(l=load_id,c=court)).mappings()]

def court_status(s,load_id,court):
    checks=[dict(r) for r in s.execute(text('SELECT id,stage,user_id,status FROM checks WHERE load_id=:l AND court=:c'),dict(l=load_id,c=court)).mappings()]
    return {'checks':checks,'shortages':shortages_for(s,load_id,court),'done':stage_completed(s,load_id,court,1) and stage_completed(s,load_id,court,2)}

def truck_status(s,branch,date,truck):
    loads=[dict(r) for r in s.execute(text('SELECT id,content,reparto FROM loads WHERE branch=:b AND load_date=:d AND truck=:t'),dict(b=branch,d=date,t=truck)).mappings()]
    complete=bool(loads)
    ids=[]
    for l in loads:
        ids.append(l['id'])
        for c in json.loads(l['content'])['canchas']:
            complete=complete and court_status(s,l['id'],c['numero'])['done']
    sh=[]
    for id in ids:
        sh += [dict(r) for r in s.execute(text('SELECT * FROM shortages WHERE load_id=:l'),{'l':id}).mappings()]
    assets=s.execute(text('SELECT * FROM assets WHERE branch=:b AND load_date=:d AND truck=:t'),dict(b=branch,d=date,t=truck)).first()
    allowed=complete and bool(assets) and all(x['approved_by'] for x in sh)
    released=s.execute(text('SELECT released_at FROM departures WHERE branch=:b AND load_date=:d AND truck=:t'),dict(b=branch,d=date,t=truck)).first()
    return {'complete':complete,'assets':bool(assets),'shortages':sh,'allowed':allowed,'released_at':released[0] if released else None,'repartos':[l['reparto'] for l in loads]}

def release_if_ready(s,branch,date,truck):
    status=truck_status(s,branch,date,truck)
    if status['allowed'] and not status['released_at']:
        s.execute(text('INSERT INTO departures(branch,load_date,truck,released_at) VALUES (:b,:d,:t,:ts)'),dict(b=branch,d=date,t=truck,ts=now()))
        audit(s,None,'automatic_departure',{'branch':branch,'date':date,'truck':truck})
    return truck_status(s,branch,date,truck)

@app.get('/api/loads')
def loads(u=Depends(get_user)):
    with session() as s:
        rows=[dict(r) for r in s.execute(text('SELECT id,branch,load_date,reparto,truck,driver,content FROM loads ORDER BY id DESC')).mappings()]
        for r in rows:
            p=json.loads(r.pop('content'));r['canchas']=[{'numero':c['numero'],'cantidad':len(c['productos']),'status':court_status(s,r['id'],c['numero'])} for c in p['canchas']]
            r['truck_status']=truck_status(s,r['branch'],r['load_date'],r['truck'])
        return rows
@app.get('/api/loads/{load_id}')
def detail(load_id:int,u=Depends(get_user)):
    with session() as s:
        l,p=getload(s,load_id)
        for c in p['canchas']:c['status']=court_status(s,load_id,c['numero'])
        return {'id':load_id,**p,'truck_status':truck_status(s,l['branch'],l['load_date'],l['truck'])}
@app.post('/api/loads/{load_id}/court/{court}/start/{stage}')
def start(load_id:int,court:int,stage:int,u=Depends(get_user)):
    if stage not in (1,2):raise HTTPException(400,'Etapa inválida')
    with session() as s:
        l,p=getload(s,load_id)
        if court not in [c['numero'] for c in p['canchas']]:raise HTTPException(404,'Cancha inexistente')
        if stage==2:
            if not stage_completed(s,load_id,court,1):raise HTTPException(409,'Primero debe terminar el control 1')
            prev=s.execute(text('SELECT user_id FROM checks WHERE load_id=:l AND court=:c AND stage=1'),dict(l=load_id,c=court)).first()
            if prev[0]==u['id']:raise HTTPException(403,'El segundo control debe hacerlo otra persona')
        check=s.execute(text('SELECT * FROM checks WHERE load_id=:l AND court=:c AND stage=:s'),dict(l=load_id,c=court,s=stage)).mappings().first()
        if check:
            if check['status']=='done':raise HTTPException(409,'Control finalizado; solo supervisor puede reabrir')
            if check['user_id']!=u['id']:raise HTTPException(409,'El control está reservado por otro empleado')
            return {'check_id':check['id'],'resumed':True}
        s.execute(text('INSERT INTO checks(load_id,court,stage,user_id,status,started_at) VALUES (:l,:c,:st,:u,\'active\',:ts)'),dict(l=load_id,c=court,st=stage,u=u['id'],ts=now()))
        checkid=s.execute(text('SELECT id FROM checks WHERE load_id=:l AND court=:c AND stage=:st'),dict(l=load_id,c=court,st=stage)).scalar_one()
        audit(s,u,'start_check',{'load':load_id,'court':court,'stage':stage});s.commit()
        return {'check_id':checkid,'resumed':False}

def check_access(s,check_id,u):
    ch=s.execute(text('SELECT * FROM checks WHERE id=:id'),{'id':check_id}).mappings().first()
    if not ch:raise HTTPException(404,'Control no encontrado')
    if ch['user_id']!=u['id']:raise HTTPException(403,'No es tu control')
    if ch['status']!='active':raise HTTPException(409,'Control cerrado')
    return dict(ch)
@app.get('/api/checks/{check_id}')
def check_detail(check_id:int,u=Depends(get_user)):
    with session() as s:
        ch=s.execute(text('SELECT * FROM checks WHERE id=:id'),{'id':check_id}).mappings().first()
        if not ch or ch['user_id']!=u['id']:raise HTTPException(403,'Control no disponible')
        l,p=getload(s,ch['load_id'])
        c=next(x for x in p['canchas'] if x['numero']==ch['court'])
        ans={x['sku']:dict(x) for x in s.execute(text('SELECT * FROM answers WHERE check_id=:id'),{'id':check_id}).mappings()}
        return {'check':dict(ch),'court':{'numero':c['numero'],'productos':c['productos']},'answers':ans}
@app.post('/api/checks/{check_id}/answer/{sku}')
def answer(check_id:int,sku:str,body:Answer,u=Depends(get_user)):
    if body.result not in ['ok','corrected','shortage']:raise HTTPException(400,'Resultado inválido')
    with session() as s:
        ch=check_access(s,check_id,u);l,p=getload(s,ch['load_id']);prod=product(p,ch['court'],sku)
        if body.result=='shortage':
            if body.physical_b is None or body.physical_u is None or min(body.physical_b,body.physical_u)<0:raise HTTPException(400,'Ingresá cantidades físicas válidas')
            if body.physical_b>prod['bultos'] or body.physical_u>prod['unidades'] or (body.physical_b==prod['bultos'] and body.physical_u==prod['unidades']):raise HTTPException(400,'El faltante debe ser menor a Chess')
            prev=s.execute(text('SELECT * FROM shortages WHERE load_id=:l AND court=:c AND sku=:sku'),dict(l=ch['load_id'],c=ch['court'],sku=sku)).mappings().first()
            if ch['stage']==1:
                if prev:raise HTTPException(409,'Faltante ya registrado; avisá al supervisor')
                s.execute(text('INSERT INTO shortages(load_id,court,sku,expected_b,expected_u,actual_b,actual_u,reported_by,note,created_at) VALUES (:l,:c,:sku,:eb,:eu,:ab,:au,:uid,:note,:ts)'),dict(l=ch['load_id'],c=ch['court'],sku=sku,eb=prod['bultos'],eu=prod['unidades'],ab=body.physical_b,au=body.physical_u,uid=u['id'],note=body.note,ts=now()))
            else:
                if not prev or prev['actual_b']!=body.physical_b or prev['actual_u']!=body.physical_u:raise HTTPException(409,'El segundo control debe confirmar el faltante ya declarado o pedir revisión al supervisor')
        elif body.result=='corrected' and not body.note.strip():raise HTTPException(400,'Describí brevemente el error que se corrigió')
        if body.result=='ok' and ch['stage']==2:
            shortage=s.execute(text('SELECT 1 FROM shortages WHERE load_id=:l AND court=:c AND sku=:sku'),dict(l=ch['load_id'],c=ch['court'],sku=sku)).first()
            if shortage:raise HTTPException(409,'Este SKU tiene faltante: confirmá la cantidad reducida')
        old=s.execute(text('SELECT id FROM answers WHERE check_id=:ch AND sku=:sku'),dict(ch=check_id,sku=sku)).first()
        if old:
            s.execute(text('UPDATE answers SET result=:r,physical_b=:b,physical_u=:q,note=:n,created_at=:ts WHERE id=:id'),dict(r=body.result,b=body.physical_b,u=body.physical_u,q=body.physical_u,n=body.note,ts=now(),id=old[0]))
        else:s.execute(text('INSERT INTO answers(check_id,sku,result,physical_b,physical_u,note,created_at) VALUES (:ch,:sku,:r,:b,:u,:n,:ts)'),dict(ch=check_id,sku=sku,r=body.result,b=body.physical_b,u=body.physical_u,n=body.note,ts=now()))
        audit(s,u,'product_answer',{'check':check_id,'sku':sku,'result':body.result,'note':body.note});s.commit()
        return {'ok':True}
@app.post('/api/checks/{check_id}/finish')
def finish(check_id:int,u=Depends(get_user)):
    with session() as s:
        ch=check_access(s,check_id,u);l,p=getload(s,ch['load_id']);c=next(x for x in p['canchas'] if x['numero']==ch['court'])
        answered=set(r[0] for r in s.execute(text('SELECT sku FROM answers WHERE check_id=:ch'),{'ch':check_id}))
        missed=[x['sku'] for x in c['productos'] if x['sku'] not in answered]
        if missed:raise HTTPException(409,f'Quedan {len(missed)} productos pendientes')
        s.execute(text("UPDATE checks SET status='done',finished_at=:ts WHERE id=:id"),dict(ts=now(),id=check_id))
        audit(s,u,'finish_check',{'check':check_id});release_if_ready(s,l['branch'],l['load_date'],l['truck']);s.commit()
        return {'ok':True}
@app.post('/api/loads/{load_id}/court/{court}/reopen')
def reopen(load_id:int,court:int,body:Reason,u=Depends(get_user)):
    role(u,['admin','supervisor'])
    with session() as s:
        l,p=getload(s,load_id)
        if not any(c['numero']==court for c in p['canchas']):raise HTTPException(404,'Cancha inexistente')
        departed=s.execute(text('SELECT 1 FROM departures WHERE branch=:b AND load_date=:d AND truck=:t'),dict(b=l['branch'],d=l['load_date'],t=l['truck'])).first()
        if departed:raise HTTPException(409,'Camión liberado: no se permite reapertura retroactiva. Registrá incidencia operativa fuera del MVP')
        for ch in s.execute(text('SELECT id FROM checks WHERE load_id=:l AND court=:c'),dict(l=load_id,c=court)):
            s.execute(text('DELETE FROM answers WHERE check_id=:id'),{'id':ch[0]})
        s.execute(text('DELETE FROM checks WHERE load_id=:l AND court=:c'),dict(l=load_id,c=court))
        audit(s,u,'reopen_court',{'load':load_id,'court':court,'reason':body.reason});s.commit()
        return {'ok':True}
@app.post('/api/shortages/{shortage_id}/approve')
def approve(shortage_id:int,u=Depends(get_user)):
    role(u,['admin','supervisor'])
    with session() as s:
        sh=s.execute(text('SELECT * FROM shortages WHERE id=:id'),{'id':shortage_id}).mappings().first()
        if not sh:raise HTTPException(404,'Faltante no encontrado')
        if sh['approved_by']:return {'ok':True}
        l,p=getload(s,sh['load_id'])
        s.execute(text('UPDATE shortages SET approved_by=:u,approved_at=:ts WHERE id=:id'),dict(u=u['id'],ts=now(),id=shortage_id))
        audit(s,u,'approve_shortage',{'id':shortage_id,'load':l['reparto']});release_if_ready(s,l['branch'],l['load_date'],l['truck']);s.commit()
        return {'ok':True}
@app.post('/api/shortages/{shortage_id}/adjusted')
def adjusted(shortage_id:int,u=Depends(get_user)):
    role(u,['admin','supervisor'])
    with session() as s:
        sh=s.execute(text('SELECT * FROM shortages WHERE id=:id'),{'id':shortage_id}).mappings().first()
        if not sh or not sh['approved_by']:raise HTTPException(409,'Primero debe aprobar el supervisor')
        s.execute(text('UPDATE shortages SET adjusted_by=:u,adjusted_at=:ts WHERE id=:id'),dict(u=u['id'],ts=now(),id=shortage_id))
        audit(s,u,'chess_adjustment_confirmed',{'id':shortage_id});s.commit()
        return {'ok':True}
ASSET_NAMES=['Esqueletos litro X12','Botellas litro X12','Barriles 20 L','Barriles 30 L','Barriles 50 L','Pallets CHEP','Pallets BEES','Tuppers','Carros','Chapadurs']
@app.get('/api/asset-types')
def asset_types(u=Depends(get_user)):return ASSET_NAMES
@app.post('/api/assets')
def save_assets(body:Assets,u=Depends(get_user)):
    branch,date,truck=body.branch,body.load_date,body.truck
    if set(body.quantities)!=set(ASSET_NAMES) or any(type(x)!=int or x<0 for x in body.quantities.values()):raise HTTPException(400,'Completá todos los tipos de activo con cantidades válidas, incluso cero')
    with session() as s:
        loads=s.execute(text('SELECT 1 FROM loads WHERE branch=:b AND load_date=:d AND truck=:t'),dict(b=branch,d=date,t=truck)).first()
        if not loads:raise HTTPException(404,'Camión no encontrado')
        done=truck_status(s,branch,date,truck)
        if not done['complete']:raise HTTPException(409,'Primero terminá el doble control de todas las planillas')
        if s.execute(text('SELECT 1 FROM assets WHERE branch=:b AND load_date=:d AND truck=:t'),dict(b=branch,d=date,t=truck)).first():raise HTTPException(409,'Activos ya confirmados; edición no habilitada en este MVP')
        s.execute(text('INSERT INTO assets(branch,load_date,truck,details,user_id,created_at) VALUES (:b,:d,:t,:details,:uid,:ts)'),dict(b=branch,d=date,t=truck,details=json.dumps(body.quantities,ensure_ascii=False),uid=u['id'],ts=now()))
        audit(s,u,'record_assets',{'truck':truck,'date':date,'quantities':body.quantities});status=release_if_ready(s,branch,date,truck);s.commit()
        return status
@app.get('/api/shortages')
def list_shortages(u=Depends(get_user)):
    role(u,['admin','supervisor'])
    with session() as s:
        return [dict(r) for r in s.execute(text('SELECT sh.*,l.reparto,l.truck,l.branch FROM shortages sh JOIN loads l ON l.id=sh.load_id ORDER BY sh.id DESC')).mappings()]
@app.get('/api/health')
def health():return {'ok':True}
