from flask import Blueprint, g, jsonify, request

from auth import AuthService, auth_required, current_user_payload, roles_required
from models import Role, User
from utils.db import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    username = str(data.get('username', '')).strip()
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Usuario y contrasena son requeridos'}), 400

    user = User.query.filter_by(username=username, active=True).first()
    if not user or not AuthService.verify_password(password, user.password_hash):
        return jsonify({'error': 'Credenciales invalidas'}), 401

    if AuthService.needs_password_rehash(user.password_hash):
        user.password_hash = AuthService.hash_password(password)
        db.session.commit()

    token = AuthService.generate_token(user)
    return jsonify({
        'token': token,
        'user': current_user_payload(user),
    })


@auth_bp.route('/me', methods=['GET'])
@auth_required
def me():
    return jsonify({'user': current_user_payload(g.current_user)})


@auth_bp.route('/register', methods=['POST'])
@roles_required('administrador')
def register():
    data = request.json or {}
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = data.get('password')
    role_name = data.get('role', 'operador')

    if not username or not email or not password:
        return jsonify({'error': 'username, email y password son requeridos'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'El usuario ya existe'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'El email ya existe'}), 409

    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({'error': 'Rol invalido'}), 400

    user = User(
        username=username,
        email=email,
        password_hash=AuthService.hash_password(password),
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Usuario creado', 'user': current_user_payload(user)}), 201
