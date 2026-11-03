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
        text='Último producto registrado. Revisá el avance y tocá finalizar picking.', variables=()),
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
