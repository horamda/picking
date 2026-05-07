import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models import ProcessingBatch, Consolidado, ConsolidadoDetalle, ProcessingError, Article, ExcludedArticle
from utils.db import db
from services.pdf_parser import parse_pdf_file
from services.processing import compute_consolidation_metrics

uploads_bp = Blueprint('uploads', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@uploads_bp.route('/pdf', methods=['POST'])
def upload_pdfs():
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No se recibieron archivos'}), 400

    batch = ProcessingBatch(nombre='Carga de PDFs', estado='procesando')
    db.session.add(batch)
    db.session.commit()

    saved = []
    errors = []
    excluded_skus = {
        item.sku for item in ExcludedArticle.query.filter_by(activo=True).all()
    }
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            target = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(target)
            try:
                parsed = parse_pdf_file(target)
                consolidado_items = parsed.get('consolidados') or [parsed]
                if not consolidado_items:
                    raise ValueError('No se encontraron items de carga en el PDF')

                for consolidado_data in consolidado_items:
                    consolidado = Consolidado(
                        batch_id=batch.id,
                        filename=filename,
                        reparto=consolidado_data.get('reparto'),
                        camion=consolidado_data.get('camion'),
                        chofer=consolidado_data.get('chofer'),
                        deposito=consolidado_data.get('deposito'),
                        cancha=consolidado_data.get('cancha'),
                        almacen=consolidado_data.get('almacen')
                    )
                    db.session.add(consolidado)
                    db.session.flush()
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
                    saved.append({
                        'filename': filename,
                        'reparto': consolidado.reparto,
                        'items': len(consolidado_data.get('items', [])) - skipped,
                        'excluded': skipped
                    })
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                db.session.add(ProcessingError(filename=filename, error_message=str(exc)))
                db.session.commit()
                errors.append({'filename': filename, 'error': str(exc)})
    batch.estado = 'completado_con_errores' if errors else 'completado'
    db.session.commit()
    return jsonify({'processed': saved, 'errors': errors, 'batch_id': batch.id})
