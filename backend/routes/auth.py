from flask import Blueprint, request, jsonify
from models import User, Role
from utils.db import db
from auth import AuthService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña son requeridos'}), 400

    user = User.query.filter_by(username=username, active=True).first()
    if not user or not AuthService.verify_password(password, user.password_hash):
        return jsonify({'error': 'Credenciales inválidas'}), 401

    token = AuthService.generate_token(user)
    return jsonify({'token': token, 'user': {'id': user.id, 'username': user.username, 'role': user.role.name}})

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role_name = data.get('role', 'operador')
    if not username or not email or not password:
        return jsonify({'error': 'username, email y password son requeridos'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'El usuario ya existe'}), 409

    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({'error': 'Rol inválido'}), 400

    user = User(username=username, email=email, password_hash=AuthService.hash_password(password), role=role)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Usuario creado', 'user': {'id': user.id, 'username': user.username}}), 201
