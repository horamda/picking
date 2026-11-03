import json

from flask import Blueprint, g, jsonify, request

from auth import auth_required, roles_required
from models import LogEntry
from services.voice_templates import VoiceTemplate, DEFINITIONS, catalog, runtime_templates, validate_text
from utils.db import db


voice_templates_bp = Blueprint('voice_templates', __name__)


@voice_templates_bp.get('/runtime')
@auth_required
def runtime():
    return jsonify(templates=runtime_templates(), version=max(
        (row.updated_at.isoformat() for row in VoiceTemplate.query.all()), default='defaults'))


@voice_templates_bp.get('')
@roles_required('administrador')
def list_templates():
    return jsonify(catalog())


@voice_templates_bp.put('/<key>')
@roles_required('administrador')
def update_template(key):
    if key not in DEFINITIONS:
        return jsonify(error='Frase inexistente.'), 404
    data = request.get_json(silent=True) or {}
    try:
        text = validate_text(key, data.get('text'))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    if type(data.get('enabled')) is not bool:
        return jsonify(error='Indicá si la frase está activa.'), 400
    row = db.session.get(VoiceTemplate, key)
    before = dict(text=row.text, enabled=row.enabled) if row else None
    if not row:
        row = VoiceTemplate(key=key)
        db.session.add(row)
    row.text, row.enabled, row.updated_by = text, data['enabled'], g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='voice_template', action='editar_frase_voz',
        details=json.dumps(dict(key=key, before=before, after=dict(text=text, enabled=row.enabled)))))
    db.session.commit()
    return jsonify(next(item for item in catalog() if item['key'] == key))


@voice_templates_bp.delete('/<key>')
@roles_required('administrador')
def reset_template(key):
    if key not in DEFINITIONS:
        return jsonify(error='Frase inexistente.'), 404
    row = db.session.get(VoiceTemplate, key)
    if row:
        db.session.delete(row)
        db.session.add(LogEntry(user_id=g.current_user.id, entity='voice_template', action='restaurar_frase_voz',
            details=json.dumps(dict(key=key, previous_text=row.text, previous_enabled=row.enabled))))
        db.session.commit()
    return jsonify(next(item for item in catalog() if item['key'] == key))
