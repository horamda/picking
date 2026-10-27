from flask import Blueprint, g, jsonify, request

from auth import AuthService, auth_required, current_user_payload, roles_required
from models import User
from services.users import create_user, UserCreationError
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

    g.current_user = user
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
    try:
        user = create_user(request.get_json(silent=True), g.current_user)
    except UserCreationError as exc:
        return jsonify({'error': str(exc)}), exc.status
    return jsonify({'message': 'Usuario creado', 'user': current_user_payload(user)}), 201
