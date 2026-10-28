"""Persist generated voice text only when the existing field is empty."""
from voz.conversor import descripcion_para_voz


def proposed_voice(description):
    value = descripcion_para_voz(description or '')
    return value if value and len(value) <= 255 else None


def fill_missing_voice(article):
    if (article.descripcion_voz or '').strip():
        return False
    value = proposed_voice(article.descripcion)
    if not value:
        return False
    article.descripcion_voz = value
    return True
