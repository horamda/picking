# Personal

Administración → Usuarios y canchas (`/equipo`). Solo administradores crean y editan cuentas; supervisores consultan el equipo y administran canchas, planes semanales y refuerzos.

- Nombre, apellido y legajo opcionales; el legajo, cuando se informa, es único.
- Usuario, email y rol editables. Buscar por identidad, email o legajo; filtrar por rol y estado.
- Restablecer contraseña exige al menos 10 caracteres y revoca sesiones y dispositivos registrados. La nueva sesión vuelve a registrar el dispositivo.
- Desactivar conserva la persona, asignaciones e historial. Reactivar exige iniciar sesión otra vez. Revisar canchas y planificación semanal al reactivar.
- No se permite desactivarse ni quitarse el rol administrador. Las ediciones de cuentas se serializan en PostgreSQL antes de tomar los bloqueos de usuarios.
- Para cambiar rol o desactivar, resolver primero los procesos activos, incluidos los pausados, activos retornables y ayudas pendientes de revisión. No se redistribuye mercadería automáticamente.
- Los nombres guardados en respuestas y procesos históricos no se reescriben. La auditoría registra cambios de ficha, rol, estado y restablecimientos, nunca contraseñas.

Migración `20261102_01`: campos de identidad y versión de sesión. Aplicar explícitamente antes de desplegar esta versión; es aditiva y mantiene válidas las sesiones existentes hasta que cambie el acceso de esa cuenta. No hay DDL al iniciar la aplicación.

Verificación: `python backend/tests/test_personnel.py`, suite de control, pruebas de concurrencia en PostgreSQL descartable y build del frontend. Android usa la misma API y no necesita recompilar por este cambio.
