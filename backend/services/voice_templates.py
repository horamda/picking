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
    'control_product': dict(name='Producto de control', process='Control',
        text='Producto {position} de {total}. Verificá {quantity} de {product}.',
        variables=('position', 'total', 'quantity', 'product')),
    'freshness_exact': dict(name='Frescura informada', process='Producto',
        text='Frescura exacta {date}.', variables=('date',)),
    'freshness_missing': dict(name='Frescura no informada', process='Producto',
        text='Frescura no informada.', variables=()),
    'pallet_group': dict(name='Grupo de pallets completos', process='Destino',
        text='Grupo de pallets completos {group}. Reparto {reparto}.', variables=('group', 'reparto')),
    'placement_base': dict(name='Ubicación en la base', process='Destino',
        text='Ubicá como base.', variables=()),
    'placement_top': dict(name='Ubicación sobre la base', process='Destino',
        text='Ubicá arriba de la base.', variables=()),
    'pallet_destination': dict(name='Destino en pallet', process='Destino',
        text='Pallet {pallet}: colocá {quantity}.', variables=('pallet', 'quantity')),
    'pallet_shared': dict(name='Pallet compartido', process='Destino',
        text='Compartido con otras canchas.', variables=()),
    'destination_missing': dict(name='Destino de pallet no disponible', process='Destino',
        text='Destino de pallet no disponible. Actualizá la tarea; si continúa, consultá al supervisor.', variables=()),
    'voice_activation': dict(name='Activación de voz', process='Avisos',
        text='Activando voz. Permití el micrófono y esperá a que termine de cargar.', variables=()),
    'operation_failed_retry': dict(name='Error recuperable de voz', process='Errores',
        text='No pude completar la operación. Revisá la pantalla y repetí el comando.', variables=()),
    'operation_failed_review': dict(name='Error de voz para revisar', process='Errores',
        text='No pude completar la operación. Revisá la pantalla y el estado del producto antes de activar la voz nuevamente.', variables=()),
    'queue_finished_empty': dict(name='Cancha finalizada sin tareas', process='Fin de tarea',
        text='Cancha finalizada. No tenés más camiones habilitados pendientes.', variables=()),
    'queue_finished_next': dict(name='Cancha finalizada con siguiente camión', process='Fin de tarea',
        text='Cancha finalizada. Tu camión actual es {truck}. {summary} Elegí el reparto y la cancha para continuar.',
        variables=('truck', 'summary')),
    'voice_loads_ready': dict(name='Voz activa con tarea disponible', process='Navegación por voz',
        text='Voz activa. Decí iniciar o continuar para abrir tu próxima tarea, o actualizar tareas.', variables=()),
    'voice_loads_empty': dict(name='Voz activa sin tareas', process='Navegación por voz',
        text='Voz activa. No hay tareas disponibles. Podés decir actualizar tareas.', variables=()),
    'voice_courts_ready': dict(name='Cancha disponible', process='Navegación por voz',
        text='Decí iniciar cancha para comenzar.', variables=()),
    'voice_courts_empty': dict(name='Sin canchas disponibles', process='Navegación por voz',
        text='No hay canchas disponibles en este reparto.', variables=()),
    'finish_confirmation': dict(name='Confirmación de finalización', process='Fin de tarea',
        text='¿Confirmás finalizar esta cancha? Decí confirmar o cancelar.', variables=()),
    'finish_cancelled': dict(name='Finalización cancelada', process='Fin de tarea',
        text='Finalización cancelada. Continuá con el picking.', variables=()),
    'finish_guidance': dict(name='Ayuda para confirmar finalización', process='Fin de tarea',
        text='Decí confirmar para finalizar o cancelar para continuar.', variables=()),
    'loads_no_task': dict(name='Intento de iniciar sin tarea', process='Comando no válido',
        text='Todavía no hay una tarea habilitada. Decí actualizar tareas.', variables=()),
    'loads_commands': dict(name='Ayuda de comandos en tareas', process='Comando no válido',
        text='Decí iniciar, continuar o actualizar tareas.', variables=()),
    'courts_commands': dict(name='Ayuda de comandos en canchas', process='Comando no válido',
        text='Decí iniciar cancha o cancelar.', variables=()),
    'shortage_commands': dict(name='Ayuda de comandos en faltantes', process='Comando no válido',
        text='Decí cantidades o registrar faltante.', variables=()),
    'summary_unavailable': dict(name='Resumen de camión no disponible', process='Resumen del camión',
        text='El resumen del camión no está disponible.', variables=()),
    'summary_pending': dict(name='Resumen con plan pendiente', process='Resumen del camión',
        text='Plan de armado pendiente. Consultá al supervisor para conocer tus pallets y cantidades asignadas.', variables=()),
    'summary_total': dict(name='Resumen general del camión', process='Resumen del camión',
        text='Carga total del camión: {loads} repartos, {courts} canchas. {pallets} pallets físicos previstos.',
        variables=('loads', 'courts', 'pallets')),
    'summary_separation': dict(name='Separación de repartos', process='Resumen del camión',
        text='Cada reparto se arma por separado. No mezcles repartos en un pallet.', variables=()),
    'summary_mine': dict(name='Trabajo asignado en el camión', process='Resumen del camión',
        text='Tu trabajo: {loads} repartos y {courts} canchas. {bultos} bultos y {unidades} unidades. Participa en {pallets} pallets.',
        variables=('loads', 'courts', 'bultos', 'unidades', 'pallets')),
    'summary_hl': dict(name='Hectolitros asignados', process='Resumen del camión',
        text='{hl} hectolitros.', variables=('hl',)),
    'summary_full_pallets': dict(name='Pallets completos separados', process='Resumen del camión',
        text='{pallets} pallets completos se preparan por separado.', variables=('pallets',)),
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
