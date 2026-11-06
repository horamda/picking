"""Editable speech templates with safe, documented placeholders."""
from datetime import datetime
from string import Formatter

from utils.db import db


class VoiceTemplate(db.Model):
    __tablename__ = 'voice_templates'
    key = db.Column(db.String(80), primary_key=True)
    text = db.Column(db.String(1000), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


DEFINITIONS = {
    'picking_product': dict(name='Producto de picking', process='Picking',
        text='Producto {position} de {total}. Agarrá {quantity} de {product}.',
        variables=('position', 'total', 'quantity', 'product')),
    'pallet_product': dict(name='Pallets completos', process='Pallets completos',
        text='Producto {position} de {total}. Prepará {pallets} de {product}.',
        variables=('position', 'total', 'pallets', 'product')),
    'empty_product': dict(name='Producto sin cantidades', process='Picking',
        text='Producto {position} de {total}. {product} no tiene cantidades para preparar. Revisá la planilla con el supervisor.',
        variables=('position', 'total', 'product')),
    'last_product': dict(name='Último producto', process='Picking',
        text='Último producto registrado. Revisá el avance y decí finalizar picking.', variables=()),
    'shortage_quantities': dict(name='Carga de faltante', process='Faltantes',
        text='Decí los bultos y unidades físicos. Revisá y confirmá con el botón.', variables=()),
    'assistance_start': dict(name='Inicio de refuerzo', process='Picking',
        text='Refuerzo en cancha {court}. Tenés {total} productos asignados. Prepará solamente los productos que indica la aplicación.',
        variables=('court', 'total')),
    'new_tasks': dict(name='Nuevas tareas', process='Avisos',
        text='Tenés nuevas tareas habilitadas. Revisá tu próximo trabajo.', variables=()),
    'unknown_command': dict(name='Comando no reconocido', process='Avisos',
        text='No entendí. Decí correcto, faltante o repetir.', variables=()),
}

SETTING_DEFINITIONS = {
    'speak_freshness_picking': dict(name='Leer frescura en picking', default=True),
    'speak_freshness_full_pallets': dict(name='Leer frescura en pallets completos', default=True),
    'block_expired_products': dict(name='Bloquear productos con frescura vencida', default=True),
}

COMMAND_DEFINITIONS = {
    'ok': dict(name='Correcto', aliases=('correcto', 'ok', 'confirmo', 'bien')),
    'shortage': dict(name='Faltante', aliases=('faltante', 'falta')),
    'repeat': dict(name='Repetir', aliases=('repetir', 'repite')),
    'next': dict(name='Siguiente', aliases=('siguiente',)),
    'prev': dict(name='Anterior', aliases=('anterior',)),
    'continue': dict(name='Continuar tarea', aliases=('continuar', 'continuar tarea')),
    'start': dict(name='Iniciar cancha', aliases=('iniciar', 'iniciar cancha')),
    'finish': dict(name='Finalizar picking', aliases=('finalizar', 'finalizar picking')),
    'confirm': dict(name='Confirmar acción', aliases=('confirmar', 'si confirmar')),
    'cancel': dict(name='Cancelar acción', aliases=('cancelar', 'no cancelar')),
    'refresh': dict(name='Actualizar tareas', aliases=('actualizar', 'actualizar tareas')),
    'register': dict(name='Registrar faltante', aliases=('registrar faltante', 'guardar faltante')),
}
SPEECH_RATE_DEFAULT = 1.0
FRESHNESS_WARNING_DAYS_DEFAULT = 30


def command_catalog():
    keys = [f'command_{key}' for key in COMMAND_DEFINITIONS]
    overrides = {row.key: row for row in VoiceTemplate.query.filter(VoiceTemplate.key.in_(keys)).all()}
    return [dict(key=key, name=value['name'], aliases=(overrides[f'command_{key}'].text.split(',')
            if f'command_{key}' in overrides else list(value['aliases']))) for key, value in COMMAND_DEFINITIONS.items()]


def runtime_commands():
    return {item['key']: item['aliases'] for item in command_catalog()}


def speech_rate():
    row = db.session.get(VoiceTemplate, 'speech_rate')
    try:
        return max(0.6, min(1.6, float(row.text))) if row else SPEECH_RATE_DEFAULT
    except (TypeError, ValueError):
        return SPEECH_RATE_DEFAULT


def freshness_warning_days():
    row = db.session.get(VoiceTemplate, 'freshness_warning_days')
    try:
        return max(0, min(365, int(row.text))) if row else FRESHNESS_WARNING_DAYS_DEFAULT
    except (TypeError, ValueError):
        return FRESHNESS_WARNING_DAYS_DEFAULT


def validate_aliases(key, aliases):
    if key not in COMMAND_DEFINITIONS or not isinstance(aliases, list):
        raise ValueError('Comando inexistente.')
    cleaned = []
    for alias in aliases:
        value = ' '.join(str(alias).strip().lower().split())
        if not value or len(value) > 40 or not all(ch.isalnum() or ch in ' áéíóúüñ' for ch in value):
            raise ValueError('Cada palabra debe tener entre 1 y 40 caracteres y no usar símbolos.')
        if value not in cleaned:
            cleaned.append(value)
    if not cleaned or len(cleaned) > 8:
        raise ValueError('Indicá entre 1 y 8 palabras o frases.')
    used = {alias for item in command_catalog() if item['key'] != key for alias in item['aliases']}
    conflict = next((alias for alias in cleaned if alias in used), None)
    if conflict:
        raise ValueError(f'La palabra "{conflict}" ya pertenece a otro comando.')
    return cleaned


def settings_catalog():
    overrides = {row.key: row for row in VoiceTemplate.query.filter(VoiceTemplate.key.in_(SETTING_DEFINITIONS)).all()}
    return [dict(key=key, name=value['name'], enabled=overrides[key].enabled if key in overrides else value['default'])
            for key, value in SETTING_DEFINITIONS.items()]


def runtime_settings():
    return {item['key']: item['enabled'] for item in settings_catalog()}


def validate_text(key, text):
    definition = DEFINITIONS.get(key)
    if not definition:
        raise ValueError('Frase inexistente.')
    if not isinstance(text, str) or not text.strip() or len(text.strip()) > 1000:
        raise ValueError('La frase debe tener entre 1 y 1000 caracteres.')
    try:
        fields = {name for _, name, _, _ in Formatter().parse(text) if name}
    except ValueError as exc:
        raise ValueError('Las llaves de las variables no están balanceadas.') from exc
    allowed = set(definition['variables'])
    if not fields <= allowed:
        raise ValueError('Variables no permitidas: ' + ', '.join(sorted(fields - allowed)) + '.')
    missing = allowed - fields
    if missing:
        raise ValueError('Faltan variables obligatorias: ' + ', '.join(sorted(missing)) + '.')
    return text.strip()


def catalog():
    overrides = {row.key: row for row in VoiceTemplate.query.all()}
    return [dict(key=key, name=value['name'], process=value['process'], variables=list(value['variables']),
        default_text=value['text'], text=overrides[key].text if key in overrides else value['text'],
        enabled=overrides[key].enabled if key in overrides else True,
        customized=key in overrides, updated_at=overrides[key].updated_at.isoformat() if key in overrides else None)
        for key, value in DEFINITIONS.items()]


def runtime_templates():
    return {item['key']: item['text'] if item['enabled'] else None for item in catalog()}
