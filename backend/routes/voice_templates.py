import json

from flask import Blueprint, g, jsonify, request

from auth import auth_required, roles_required
from models import LogEntry
from services.voice_templates import (VoiceTemplate, DEFINITIONS, SETTING_DEFINITIONS, COMMAND_DEFINITIONS, catalog,
                                      command_catalog, runtime_commands, runtime_settings, runtime_templates,
                                      freshness_warning_days, settings_catalog, speech_rate, validate_aliases, validate_text)
from utils.db import db


voice_templates_bp = Blueprint('voice_templates', __name__)


@voice_templates_bp.get('/runtime')
@auth_required
def runtime():
    return jsonify(templates=runtime_templates(), settings=runtime_settings(), commands=runtime_commands(),
        speech_rate=speech_rate(), freshness_warning_days=freshness_warning_days(), version=max(
        (row.updated_at.isoformat() for row in VoiceTemplate.query.all()), default='defaults'))


@voice_templates_bp.get('')
@roles_required('administrador')
def list_templates():
    return jsonify(templates=catalog(), settings=settings_catalog(), commands=command_catalog(),
        speech_rate=speech_rate(), freshness_warning_days=freshness_warning_days())


@voice_templates_bp.put('/commands/<key>')
@roles_required('administrador')
def update_command(key):
    data = request.get_json(silent=True) or {}
    try:
        aliases = validate_aliases(key, data.get('aliases'))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    row = db.session.get(VoiceTemplate, f'command_{key}')
    before = row.text if row else ','.join(COMMAND_DEFINITIONS[key]['aliases'])
    if not row:
        row = VoiceTemplate(key=f'command_{key}', enabled=True)
        db.session.add(row)
    row.text, row.updated_by = ','.join(aliases), g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='voice_command', action='editar_comando_voz',
        details=json.dumps(dict(key=key, before=before, after=row.text), ensure_ascii=False)))
    db.session.commit()
    return jsonify(next(item for item in command_catalog() if item['key'] == key))


@voice_templates_bp.put('/speech-rate')
@roles_required('administrador')
def update_speech_rate():
    try:
        value = float((request.get_json(silent=True) or {}).get('value'))
    except (TypeError, ValueError):
        return jsonify(error='Indicá una velocidad válida.'), 400
    if not 0.6 <= value <= 1.6:
        return jsonify(error='La velocidad debe estar entre 0,6 y 1,6.'), 400
    row = db.session.get(VoiceTemplate, 'speech_rate')
    before = speech_rate()
    if not row:
        row = VoiceTemplate(key='speech_rate', enabled=True)
        db.session.add(row)
    row.text, row.updated_by = f'{value:.2f}', g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='voice_setting', action='editar_velocidad_voz',
        details=json.dumps(dict(before=before, after=value))))
    db.session.commit()
    return jsonify(value=value)


@voice_templates_bp.put('/freshness-warning-days')
@roles_required('administrador')
def update_freshness_warning_days():
    try:
        value = int((request.get_json(silent=True) or {}).get('value'))
    except (TypeError, ValueError):
        return jsonify(error='Indicá una cantidad de días válida.'), 400
    if not 0 <= value <= 365:
        return jsonify(error='La anticipación debe estar entre 0 y 365 días.'), 400
    row = db.session.get(VoiceTemplate, 'freshness_warning_days')
    before = freshness_warning_days()
    if not row:
        row = VoiceTemplate(key='freshness_warning_days', enabled=True)
        db.session.add(row)
    row.text, row.updated_by = str(value), g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='freshness_setting', action='editar_aviso_frescura',
        details=json.dumps(dict(before=before, after=value))))
    db.session.commit()
    return jsonify(value=value)


@voice_templates_bp.put('/settings/<key>')
@roles_required('administrador')
def update_setting(key):
    if key not in SETTING_DEFINITIONS:
        return jsonify(error='Configuración inexistente.'), 404
    data = request.get_json(silent=True) or {}
    if type(data.get('enabled')) is not bool:
        return jsonify(error='Indicá si la opción está activa.'), 400
    row = db.session.get(VoiceTemplate, key)
    before = row.enabled if row else SETTING_DEFINITIONS[key]['default']
    if not row:
        row = VoiceTemplate(key=key, text=SETTING_DEFINITIONS[key]['name'])
        db.session.add(row)
    row.enabled, row.updated_by = data['enabled'], g.current_user.id
    db.session.add(LogEntry(user_id=g.current_user.id, entity='voice_setting', action='editar_configuracion_voz',
        details=json.dumps(dict(key=key, before=before, after=row.enabled))))
    db.session.commit()
    return jsonify(next(item for item in settings_catalog() if item['key'] == key))


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
