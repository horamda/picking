# Peso y altura en la planificación

La revisión `20261111_01` agrega límites opcionales de altura y peso a la configuración existente de depósitos y camiones. Está encadenada a `20261105_01`.

No se aplica desde el arranque ni fue ejecutada contra Railway. Debe aplicarse mediante Alembic con `MIGRATION_DATABASE_URL` y autorización explícita.

Los planes guardan una copia de la configuración efectiva. La huella incluye esa configuración y el peso logístico de los artículos. Los planes cuyo armado ya comenzó continúan congelados; los no iniciados se invalidan si cambian datos o límites.

`Peso` se lee desde `articulos.datos_logisticos` como kilogramos por bulto cerrado. Los valores ausentes no se estiman.
