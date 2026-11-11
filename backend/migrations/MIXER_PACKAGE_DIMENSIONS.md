# Medidas de bultos en reglas del mezclador

La revisión `20261111_02` agrega a `pallet_stacking_rules` unidades por bulto y largo, ancho y alto opcional en centímetros.

Todos los campos son opcionales para conservar sin cambios las reglas existentes. El Excel exportado permite completar los datos y reimportarlos con vista previa; las celdas vacías conservan los valores guardados.

La migración no se ejecuta durante el arranque y todavía no fue aplicada en Railway. Debe aplicarse explícitamente con Alembic y `MIGRATION_DATABASE_URL` después de desplegar el código correspondiente.
