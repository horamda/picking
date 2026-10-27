"""Prepare the official Spanish Vosk model from a locally downloaded ZIP."""
import hashlib
import sys
import zipfile
from pathlib import Path

archive = Path(sys.argv[1])
expected = '09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f'
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit('El ZIP no coincide con vosk-model-small-es-0.42 verificado.')
target = Path(__file__).resolve().parent / 'app/src/main/assets/model-es'
with zipfile.ZipFile(archive) as source:
    for member in source.infolist():
        if member.is_dir():
            continue
        relative = Path(member.filename.split('/', 1)[1])
        if relative.is_absolute() or '..' in relative.parts:
            raise SystemExit('Ruta inválida en el archivo del modelo.')
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read(member))
(target / 'uuid').write_text('vosk-small-es-0.42-delpalacio-v1', encoding='utf-8')
print('Modelo español preparado; los archivos del modelo están excluidos de Git.')
