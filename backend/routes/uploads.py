import os
import tempfile
from io import BytesIO

from flask import Blueprint, request, jsonify, send_file, g
from sqlalchemy import func
from werkzeug.utils import secure_filename
from auth import auth_required, roles_required
from models import ProcessingBatch, Consolidado, ConsolidadoDetalle, ProcessingError, Article, ExcludedArticle, UploadedFile
from utils.db import db
from services.pdf_parser import parse_pdf_file
from services.processing import compute_consolidation_metrics
from services.pdf_articles import enable_pdf_articles
from services.file_storage import create_uploaded_file_record, mark_uploaded_file, uploaded_file_to_dict

uploads_bp = Blueprint('uploads', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalize_reparto(value) -> str:
    return str(value or '').strip()


def duplicate_reparto_message(reparto: str, existing=None) -> str:
    if not existing:
        return f'Reparto {reparto} duplicado en esta carga. No se proceso nuevamente.'
    processed_at = existing.processed_at.strftime('%d/%m/%Y %H:%M') if existing.processed_at else 'fecha desconocida'
    return (
        f'Reparto {reparto} ya fue procesado el {processed_at} '
        f'en el archivo {existing.filename}. No se permite cargarlo nuevamente.'
    )


def validate_repartos(consolidado_items: list[dict], seen_repartos: set[str]) -> list[str]:
    repartos = []
    local_seen = set()
    for consolidado_data in consolidado_items:
        reparto = normalize_reparto(consolidado_data.get('reparto'))
        if not reparto:
            raise ValueError('No se pudo leer el Nro de reparto del PDF. No se proceso para evitar duplicados.')
        if reparto in local_seen or reparto in seen_repartos:
            raise ValueError(duplicate_reparto_message(reparto))
        existing = Consolidado.query.filter(func.trim(Consolidado.reparto) == reparto).first()
        if existing:
            raise ValueError(duplicate_reparto_message(reparto, existing))
        consolidado_data['reparto'] = reparto
        local_seen.add(reparto)
        repartos.append(reparto)
    return repartos


def parse_pdf_bytes(file_bytes: bytes, filename: str) -> dict:
    temp_path = None
    suffix = os.path.splitext(filename)[1] or '.pdf'
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name
        return parse_pdf_file(temp_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@uploads_bp.route('/pdf', methods=['POST'])
@roles_required('administrador', 'supervisor')
def upload_pdfs():
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No se recibieron archivos'}), 400

    batch = ProcessingBatch(nombre='Carga de PDFs', estado='procesando')
    db.session.add(batch)
    db.session.commit()

    saved = []
    errors = []
    seen_repartos = set()
    excluded_skus = {
        item.sku for item in ExcludedArticle.query.filter_by(activo=True).all()
    }
    for file in files:
        if not file:
            continue

        original_filename = file.filename or 'archivo.pdf'
        filename = secure_filename(original_filename) or 'archivo.pdf'
        file_bytes = file.read()
        uploaded_file = create_uploaded_file_record(
            file_bytes=file_bytes,
            filename=filename,
            original_filename=original_filename,
            category='pdf_consolidado',
            content_type=file.mimetype,
            batch_id=batch.id,
        )
        db.session.add(uploaded_file)
        db.session.commit()
        uploaded_file_id = uploaded_file.id

        if not allowed_file(filename):
            message = 'Extension no permitida. Solo se aceptan archivos PDF'
            mark_uploaded_file(uploaded_file, 'rechazado', message)
            db.session.add(ProcessingError(uploaded_file_id=uploaded_file.id, filename=filename, error_message=message))
            db.session.commit()
            errors.append({'filename': filename, 'uploaded_file_id': uploaded_file.id, 'error': message})
            continue

        try:
            file_saved = []
            mark_uploaded_file(uploaded_file, 'procesando')
            db.session.commit()

            parsed = parse_pdf_bytes(file_bytes, filename)
            consolidado_items = parsed.get('consolidados') or [parsed]
            if not consolidado_items:
                raise ValueError('No se encontraron items de carga en el PDF')
            validated_repartos = validate_repartos(consolidado_items, seen_repartos)

            for consolidado_data in consolidado_items:
                from services.load_control import ControlTruck, truck_name
                delivery = consolidado_data.get('fecha_reparto')
                if delivery:
                    date_value = delivery.date().isoformat() if hasattr(delivery, 'date') else str(delivery)[:10]
                    existing = ControlTruck.query.filter_by(branch=str(consolidado_data.get('deposito') or '').strip(),
                        truck=truck_name(consolidado_data.get('camion')), load_date=date_value).with_for_update().first()
                    if existing and any(c.get('checks') for c in existing.state.get('courts', {}).values()):
                        raise ValueError('El camion ya tiene trabajo iniciado. No se pueden agregar repartos al armado en curso.')
                consolidado = Consolidado(
                    batch_id=batch.id,
                    uploaded_file_id=uploaded_file.id,
                    filename=filename,
                    reparto=consolidado_data.get('reparto'),
                    camion=consolidado_data.get('camion'),
                    chofer=consolidado_data.get('chofer'),
                    deposito=consolidado_data.get('deposito'),
                    cancha=consolidado_data.get('cancha'),
                    almacen=consolidado_data.get('almacen'),
                    fecha_reparto=consolidado_data.get('fecha_reparto')
                )
                db.session.add(consolidado)
                db.session.flush()
                enabled = enable_pdf_articles(
                    [row['sku'] for row in consolidado_data.get('items', []) if row['sku'] not in excluded_skus],
                    g.current_user.id, consolidado.id)
                skipped = 0
                for row in consolidado_data.get('items', []):
                    if row['sku'] in excluded_skus:
                        skipped += 1
                        continue
                    article = Article.query.filter_by(sku=row['sku']).first()
                    row_metrics = compute_consolidation_metrics(row, article)
                    detalle = ConsolidadoDetalle(
                        consolidado_id=consolidado.id,
                        sku=row['sku'],
                        descripcion=row.get('descripcion'),
                        bultos=row.get('bultos', 0),
                        unidades=row.get('unidades', 0),
                        unidades_equivalentes=row_metrics['unidades_equivalentes'],
                        bultos_equivalentes=row_metrics['bultos_equivalentes'],
                        pallets_completos=row_metrics['pallets_completos'],
                        bultos_pickear=row_metrics['bultos_pickear'],
                        unidades_sueltas=row_metrics['unidades_sueltas'],
                        almacen=row.get('almacen') or consolidado.almacen,
                        cancha=row.get('cancha') or consolidado.cancha,
                        prioridad=row_metrics['prioridad'],
                        sku_estado='encontrado' if article else 'no encontrado'
                    )
                    db.session.add(detalle)
                file_saved.append({
                    'filename': filename,
                    'uploaded_file_id': uploaded_file.id,
                    'reparto': consolidado.reparto,
                    'camion': consolidado.camion,
                    'chofer': consolidado.chofer,
                    'deposito': consolidado.deposito,
                    'fecha_reparto': consolidado.fecha_reparto.isoformat() if consolidado.fecha_reparto else None,
                    'items': len(consolidado_data.get('items', [])) - skipped,
                    'excluded': skipped,
                    'enabled_articles': enabled,
                })
            mark_uploaded_file(uploaded_file, 'procesado')
            db.session.commit()
            saved.extend(file_saved)
            seen_repartos.update(validated_repartos)
        except Exception as exc:
            db.session.rollback()
            uploaded_file = db.session.get(UploadedFile, uploaded_file_id)
            mark_uploaded_file(uploaded_file, 'error', str(exc))
            db.session.add(ProcessingError(uploaded_file_id=uploaded_file.id, filename=filename, error_message=str(exc)))
            db.session.commit()
            errors.append({'filename': filename, 'uploaded_file_id': uploaded_file.id, 'error': str(exc)})
    batch.estado = 'completado_con_errores' if errors else 'completado'
    db.session.commit()
    return jsonify({'processed': saved, 'errors': errors, 'batch_id': batch.id})


@uploads_bp.route('/files', methods=['GET'])
@auth_required
def list_uploaded_files():
    args = request.args
    query = UploadedFile.query
    if args.get('category'):
        query = query.filter(UploadedFile.category == args.get('category'))
    if args.get('status'):
        query = query.filter(UploadedFile.status == args.get('status'))
    if args.get('batch_id'):
        query = query.filter(UploadedFile.batch_id == int(args.get('batch_id')))
    files = query.order_by(UploadedFile.created_at.desc()).limit(200).all()
    return jsonify([uploaded_file_to_dict(item) for item in files])


@uploads_bp.route('/files/<int:file_id>/download', methods=['GET'])
@auth_required
def download_uploaded_file(file_id):
    uploaded_file = UploadedFile.query.get_or_404(file_id)
    return send_file(
        BytesIO(uploaded_file.data),
        mimetype=uploaded_file.content_type or 'application/octet-stream',
        as_attachment=True,
        download_name=uploaded_file.original_filename or uploaded_file.filename,
    )
