# Notificaciones Android

## Configuración cliente 0.14.0

Proyecto Firebase: `picking-24bf0`. Aplicación: `com.delpalacio.picking`.
Configuración: `android/app/google-services.json`, excluida de Git. Este archivo no es una credencial de administración y no permite que Railway envíe mensajes.

Firebase Messaging se integra sin Analytics, con canal «Avisos de trabajo» y recepción en primer plano. Las notificaciones en segundo plano las maneja Firebase/Android. Enviar texto genérico, sin datos de cargas ni nombres de operarios. Abrir un aviso no confirma productos ni cambia el trabajo activo.

## Prueba desde Firebase

1. Instalar el APK 0.14.0 e iniciar sesión.
2. Abrir «Mi sesión → Notificaciones · Probar Firebase». Aceptar el permiso y volver al diagnóstico si fue necesario.
3. Usar «Copiar token de prueba». No publicarlo ni incluirlo en logs.
4. En Cloud Messaging del proyecto crear una notificación genérica y usar «Enviar mensaje de prueba» con ese token; no enviar una campaña a todos los dispositivos.
5. Comprobar con app visible y luego en segundo plano/pantalla bloqueada. Tocar el aviso e iniciar sesión si corresponde; actualizar las tareas.

Obtener un token no demuestra recepción. La prueba física queda pendiente: no hay teléfono conectado durante la integración. No prometer entrega con la app forzada a detenerse, sin servicios Google o sin conexión.

## Envío automático: preparado, pendiente de activar

- Credencial de servidor del mismo proyecto como secreto en Railway; nunca dentro del APK ni en Git.
- Implementado registro autenticado por operario/dispositivo, renovación y desvinculación al cerrar sesión. Sin conexión no se garantiza la revocación remota inmediata.
- Migración `20261030_01` aplicada y verificada en Railway el 30/10/2026 con autorización. Ver `backend/migrations/PUSH_NOTIFICATIONS.md`.
- Worker separado `backend/push_worker.py`: consulta trabajo aprobado cada 15 segundos, fuera de las peticiones operativas; conserva los avisos enviados y reintenta fallos con espera creciente.
- Consultar la cola autenticada al abrir: Firebase no decide permisos, reservas ni orden de camiones.
- Pruebas con usuarios distintos, cambio de asignación, logout, renovación de tokens, permiso rechazado y pérdida de red.

El inicio mantiene la consulta cada 15 segundos y los avisos por voz de tareas habilitadas. El envío automático desde Railway todavía no está habilitado: faltan la credencial privada del servidor y desplegar la API y el worker.

Referencia: https://firebase.google.com/docs/cloud-messaging/android/get-started
