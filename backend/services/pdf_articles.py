"""Enable catalog articles explicitly requested by a load PDF."""
import json
from sqlalchemy import text

from models import Article, LogEntry
from utils.db import db


def enable_pdf_articles(skus, user_id, source_id):
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(text('SELECT pg_advisory_xact_lock(2710202602)'))
    # Ordered row locks serialize with catalog imports; never overwrite voice data.
    articles = Article.query.filter(Article.sku.in_(set(skus))).order_by(Article.sku).with_for_update().populate_existing().all()
    enabled = []
    for article in articles:
        if article.activo:
            continue
        article.activo = True
        enabled.append(article.sku)
        db.session.add(LogEntry(user_id=user_id, action='habilitar_articulo_por_pdf',
            entity='articles', entity_id=article.id,
            details=json.dumps({'sku': article.sku, 'consolidado_id': source_id, 'motivo': 'Incluido en PDF de carga'})))
    return enabled
