import hashlib
from datetime import datetime, timedelta
from functools import wraps

from flask import g, jsonify, request
import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from models import User, Role
from utils.db import db

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        try:
            if check_password_hash(password_hash, password):
                return True
        except ValueError:
            pass
        return hashlib.sha256(password.encode('utf-8')).hexdigest() == password_hash

    @staticmethod
    def needs_password_rehash(password_hash: str) -> bool:
        return not (password_hash or '').startswith(('scrypt:', 'pbkdf2:'))

    @staticmethod
    def generate_token(user: User) -> str:
        expires_at = datetime.utcnow() + timedelta(minutes=Config.TOKEN_EXPIRATION_MINUTES)
        payload = {
            'sub': str(user.id),
            'username': user.username,
            'role': user.role.name,
            'exp': expires_at,
        }
        return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

    @staticmethod
    def decode_token(token: str) -> dict:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])

    @staticmethod
    def initialize_roles():
        for name in ['administrador', 'supervisor', 'operador', 'controlador', 'palletizador']:
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name, description=f'Rol {name}'))
        db.session.commit()


def current_user_payload(user: User) -> dict:
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.name,
    }


def get_bearer_token() -> str | None:
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '):
        return None
    token = header.split(' ', 1)[1].strip()
    return token or None


def auth_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token = get_bearer_token()
        if not token:
            return jsonify({'error': 'Token requerido'}), 401

        try:
            payload = AuthService.decode_token(token)
            user_id = int(payload.get('sub'))
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Sesion expirada'}), 401
        except (jwt.InvalidTokenError, TypeError, ValueError):
            return jsonify({'error': 'Token invalido'}), 401

        query = User.query.filter_by(id=user_id, active=True)
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            query = query.with_for_update()
        user = query.first()
        if not user:
            return jsonify({'error': 'Usuario inactivo o inexistente'}), 401

        if user.role.name not in ('administrador', 'supervisor') and request.blueprint not in ('auth', 'load_control'):
            return jsonify(error='Esta cuenta solo tiene acceso a su trabajo asignado.'), 403
        g.current_user = user
        g.jwt_payload = payload
        return view(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(view):
        @auth_required
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = g.current_user
            if roles and user.role.name not in roles:
                return jsonify({'error': 'Permisos insuficientes'}), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator
