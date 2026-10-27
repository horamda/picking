# Asignaciones de canchas

La revisión `20261024_01` fue aplicada en Railway el 27/10/2026 con autorización del usuario.

La integración de la rama `feature/voz-picking` permite una o varias canchas por usuario y varios operarios por cancha. Se valida el acceso en la API y no se infieren permisos del historial. Sin asignaciones, la cuenta no recibe cargas. Las asignaciones usan números de cancha compartidos entre depósitos; todavía no hay asignaciones distintas por depósito.

Administración crea usuarios y asigna canchas; supervisión puede reasignarlas. Al retirar una cancha se pausa su proceso, se archiva el tiempo del operario anterior y se conserva el avance para el siguiente. La nueva persona comienza su propio tramo de tiempo. Los controles terminados conservan su autor.

La tabla tiene clave compuesta y cancha positiva. No se ejecuta DDL al iniciar Flask. No aplicar nuevas migraciones ni revertir datos sin autorización.
