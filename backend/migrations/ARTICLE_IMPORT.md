# Artículos: datos originales y descripción para voz

Revisión `20261027_02`, posterior a `20261027_01`. Agrega dos columnas opcionales:
`datos_origen` (JSON, todas las columnas originales del CSV, como texto sin perder
ceros iniciales) y `descripcion_voz` (255 caracteres, mantenimiento manual).
No hay DDL de arranque. Aplicar con Alembic y `MIGRATION_DATABASE_URL` explícita.

El importador exige las columnas Tipo de producto, Activo, Usado en dispositivo
móvil y Anulado. Solo activa MERCADERIA / SI / SI / NO, ignorando mayúsculas,
acentos y espacios exteriores. Los errores o SKU duplicados rechazan el archivo
completo. El archivo original se archiva en `archivos_subidos`.

Actualizar modifica los SKU incluidos, desactiva los excluidos ya existentes y
no crea artículos excluidos nuevos. Sincronizar también desactiva los ausentes.
Ningún modo borra artículos, identificadores ni descripciones de voz. El historial
y los planes iniciados conservan sus cantidades. Un plan aún no iniciado puede
requerir nueva aprobación si cambian datos logísticos del catálogo.

La descripción de voz es independiente del CSV. Administrador y supervisor
pueden editarla, con auditoría y control de modificaciones concurrentes. La web
y Android 0.3 la usan para lectura; mantienen la descripción original visible.
Si queda vacía, se lee la descripción original del producto en la planilla.

UI: `/importaciones` reúne PDF y CSV; `/upload` redirige a la opción PDF.
`/articulos` mantiene consulta, filtros de estado, edición de voz y datos originales.
Los reportes anteriores permanecen disponibles.

Validación: `python backend/tests/test_article_import.py`, controles existentes,
planificación, concurrencia PostgreSQL, frontend tests/build y Android unit/build.
