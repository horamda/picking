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
    user = User(username=username, email=email,
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
        raise UserCreationError('El usuario o email ya existe.', 409) from None
    return user
