"""Single user creation policy shared by the existing API and compatibility routes."""
from sqlalchemy.exc import IntegrityError

from auth import AuthService
from models import LogEntry, Role, User
from utils.db import db
from services.warehouse import UserCourt, validate_courts


class UserCreationError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def create_user(data, actor, default_role='operador'):
    if not isinstance(data, dict):
        raise UserCreationError('Se requiere un objeto JSON.')
    username = str(data.get('username') or '').strip()
    email = str(data.get('email') or '').strip().lower()
    password = data.get('password')
    if not username or len(username) > 128 or not email or len(email) > 255 or '@' not in email:
        raise UserCreationError('Ingresá un usuario y un email válidos.')
    if not isinstance(password, str) or len(password) < 10:
        raise UserCreationError('La contraseña debe tener al menos 10 caracteres.')
    role_name = data.get('role', default_role)
    if not isinstance(role_name, str):
        raise UserCreationError('Rol inválido.')
    if role_name not in ('administrador', 'supervisor', 'operador', 'controlador', 'palletizador'):
        raise UserCreationError('Rol inválido.')
    try:
        courts = validate_courts(data.get('courts', []))
    except ValueError as exc:
        raise UserCreationError(str(exc))
    role = Role.query.filter_by(name=role_name).first()
    if not role and role_name == 'palletizador':
        role = Role(name=role_name, description='Armador de pallets completos')
        db.session.add(role)
    if not role:
        raise UserCreationError('Rol inválido.')
    if User.query.filter((User.username == username) | (User.email == email)).first():
        raise UserCreationError('El usuario o email ya existe.', 409)
    profile = validate_profile(data)
    user = User(**profile, username=username, email=email,
                password_hash=AuthService.hash_password(password), role=role, active=True)
    try:
        db.session.add(user)
        db.session.flush()
        for number in courts:
            db.session.add(UserCourt(user_id=user.id, court_number=number))
        db.session.add(LogEntry(user_id=actor.id, action='crear_usuario_control',
                                entity='users', details=username))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise UserCreationError('El usuario, email o legajo ya existe.', 409) from None
    return user


def validate_profile(data):
    result = {}
    for key, limit in [('first_name', 100), ('last_name', 100), ('employee_number', 50)]:
        value = data.get(key, '')
        if not isinstance(value, str) or len(value.strip()) > limit:
            raise UserCreationError('Nombre, apellido o legajo inválido.')
        result[key] = value.strip() or None
    return result


def active_work(user_id):
    from services.load_control import ControlTruck
    found = []
    for truck in ControlTruck.query.order_by(ControlTruck.id).all():
        state = truck.state or {}
        entries = [('activos', state.get('asset_check', {}))]
        for court, value in state.get('courts', {}).items():
            entries.extend((court, check) for check in value.get('checks', {}).values())
            entries.extend((court, check) for check in value.get('helpers', []))
        for location, check in entries:
            if check.get('user_id') == user_id and check.get('status') == 'active':
                found.append(f'camión {truck.id}, cancha/proceso {location}')
    return found


def update_user(user_id, data, actor):
    import json
    from services.push import PushDevice
    if not isinstance(data, dict) or not data:
        raise UserCreationError('Indicá los cambios de la persona.')
    allowed = {'username', 'email', 'role', 'active', 'password', 'first_name', 'last_name', 'employee_number'}
    if set(data) - allowed:
        raise UserCreationError('Hay campos no permitidos.')
    user = User.query.filter_by(id=user_id).with_for_update().first()
    if not user:
        raise UserCreationError('Persona inexistente.', 404)
    before = dict(username=user.username, email=user.email, role=user.role.name, active=user.active,
                  first_name=user.first_name, last_name=user.last_name, employee_number=user.employee_number)
    values = dict(before)
    for field, limit in [('username', 128), ('email', 255)]:
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
                raise UserCreationError('Usuario o email inválido.')
            values[field] = value.strip().lower() if field == 'email' else value.strip()
    if '@' not in values['email']:
        raise UserCreationError('Email inválido.')
    if 'active' in data:
        if type(data['active']) is not bool:
            raise UserCreationError('Estado inválido.')
        values['active'] = data['active']
    role_name = data.get('role', values['role'])
    if not isinstance(role_name, str) or role_name not in ('administrador','supervisor','operador','controlador','palletizador'):
        raise UserCreationError('Rol inválido.')
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        raise UserCreationError('Rol no configurado.')
    values['role'] = role_name
    profile = validate_profile({k: data.get(k, values[k] or '') for k in ('first_name','last_name','employee_number')})
    values.update(profile)
    access_change = values['role'] != before['role'] or values['active'] != before['active']
    if actor.id == user.id and (not values['active'] or values['role'] != 'administrador'):
        raise UserCreationError('No podés desactivar tu propia cuenta ni quitarte el rol administrador.', 409)
    if access_change:
        work = active_work(user.id)
        if work:
            raise UserCreationError('Primero finalizá o reasigná el trabajo activo (también el pausado): ' + '; '.join(work[:5]), 409)
    password = data.get('password')
    if 'password' in data and (not isinstance(password, str) or len(password) < 10 or len(password) > 256):
        raise UserCreationError('La contraseña debe tener entre 10 y 256 caracteres.')
    duplicate = User.query.filter(User.id != user.id).filter((User.username == values['username']) | (User.email == values['email'])).first()
    if duplicate:
        raise UserCreationError('El usuario o email ya existe.', 409)
    if profile['employee_number'] and User.query.filter(User.id != user.id, User.employee_number == profile['employee_number']).first():
        raise UserCreationError('El legajo ya existe.', 409)
    for key, value in values.items():
        if key != 'role':
            setattr(user, key, value)
    user.role = role
    if password:
        user.password_hash = AuthService.hash_password(password)
    if access_change or password:
        user.session_version += 1
        PushDevice.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    changed = {key: {'antes': before[key], 'después': value} for key, value in values.items() if before[key] != value}
    if password:
        changed['password_reset'] = True
    if changed:
        db.session.add(LogEntry(user_id=actor.id, action='editar_personal', entity='users', entity_id=user.id,
                                details=json.dumps(changed, ensure_ascii=False)))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise UserCreationError('El usuario, email o legajo ya existe.', 409) from None
    return user
