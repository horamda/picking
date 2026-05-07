import hashlib
from datetime import datetime, timedelta
import jwt
from config import Config
from models import User, Role
from utils.db import db

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return AuthService.hash_password(password) == password_hash

    @staticmethod
    def generate_token(user: User) -> str:
        payload = {
            'sub': user.id,
            'username': user.username,
            'role': user.role.name,
            'exp': datetime.utcnow() + timedelta(minutes=Config.TOKEN_EXPIRATION_MINUTES)
        }
        return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

    @staticmethod
    def decode_token(token: str) -> dict:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])

    @staticmethod
    def initialize_roles():
        for name in ['administrador', 'supervisor', 'operador']:
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name, description=f'Rol {name}'))
        db.session.commit()
