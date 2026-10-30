# Migración propuesta: avisos a teléfonos

Revisión `20261030_01`, posterior a `20261027_02`.

Crea únicamente `push_devices`, con token FCM, hash único, usuario, vencimiento de la asociación, última actualización, tareas notificadas, reintentos y próximo intento. No modifica cargas, artículos, canchas ni tiempos históricos. La asociación dura siete días desde la última actualización autenticada; un teléfono compartido se vincula al último operario que inicia sesión con ese token.

**Aplicada en Railway production el 30/10/2026 con autorización del usuario.** Se verificó el cambio de revisión `20261027_02` a `20261030_01`, la tabla y sus nueve columnas; inicialmente tiene cero dispositivos. El envío sigue deshabilitado hasta configurar la credencial y desplegar API/worker.

## Activación pendiente

1. Migración aplicada mediante Alembic y `MIGRATION_DATABASE_URL`; no repetir ni revertir sin revisión.
2. Configurar `PUSH_ENABLED=1` en la API y en el worker.
3. Worker separado: `python backend/push_worker.py`, con la misma base PostgreSQL y `FIREBASE_PROJECT_ID=picking-24bf0`. Usar `FIREBASE_SERVICE_ACCOUNT_JSON` como variable secreta de Railway o `GOOGLE_APPLICATION_CREDENTIALS` apuntando al archivo privado montado como secreto. No incluir esa clave en Git, APK ni mensajes de chat. La credencial solo se instala en el worker.
4. El worker necesita las variables normales del backend, incluido el mismo JWT_SECRET si la configuración lo exige, pero no inicia un servidor HTTP ni migra tablas.
5. Instalar el APK con registro de dispositivos y permitir notificaciones. Confirmar el estado desde el diagnóstico.

## Garantías y límites

- Sin llamadas a Firebase dentro de confirmar productos, aprobar cargas o registrar faltantes.
- El worker revisa tareas aprobadas, asignadas y disponibles en el camión actual. Los avisos son genéricos; abrirlos no concede permisos ni registra productos.
- Bloqueo por dispositivo con `SKIP LOCKED` para evitar envíos simultáneos entre workers. Reintentos con espera creciente; tokens inválidos quedan vencidos.
- Entrega al menos una vez: un cierre entre el envío a Firebase y el commit puede repetir un aviso. Se usa el mismo tag para reemplazarlo, no para duplicar trabajo.
- Cerrar sesión intenta desvincular el token y eliminarlo en Firebase. Sin conexión no se puede garantizar la revocación remota inmediata; el aviso no contiene datos privados y la API siempre exige sesión.
- Renovación de token sin una sesión en memoria se vincula al siguiente inicio de sesión.
- Nunca anunciar entrega real basándose solamente en compilación o mocks. Probar dos teléfonos/usuarios, reasignación, logout y pérdida de red.
