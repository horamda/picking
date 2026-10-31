# Planificación semanal y refuerzos — Android 0.15.0

## Uso

En **Supervisión → Asignar recursos**, elegir el lunes de la semana, indicar las canchas por persona y guardar el borrador. Se puede copiar la última semana publicada. Publicar confirma la programación; un borrador por sí solo no cambia los permisos.

El worker activa el plan publicado de la semana vigente, con fecha de Argentina (UTC−3), en su siguiente ciclo de 15 segundos. Los planes futuros no alteran el trabajo actual. Si no se publica una nueva semana, se mantienen las asignaciones anteriores. Una semana activada no se reescribe; los cambios quedan auditados. La asignación manual anterior sigue disponible y es inmediata.

La activación conserva respuestas e historial, pausa y libera las reservas de las canchas que la persona deja de tener. La aplicación obtiene las nuevas canchas desde el mismo servidor. Android actualiza su inicio cada 15 segundos y la web cada 10; una pantalla sin conexión no representa información en vivo.

## Refuerzo diario

1. El titular pausa su cancha antes de ceder productos.
2. El supervisor selecciona carga, cancha, proceso, operario disponible y productos pendientes. Se ceden **SKU completos**, sin partir las cantidades de un mismo SKU.
3. La persona de refuerzo debe tener el rol correspondiente, no tener otro proceso pendiente y haber terminado sus canchas de ese camión.
4. Cada producto queda reservado para un solo participante. Titular y ayudantes pueden confirmar productos diferentes de la misma cancha simultáneamente.
5. El refuerzo aparece en Android 0.15.0 y en la web con sus cantidades personales. Usa el mismo flujo de voz, verificación, faltantes y comprobantes. La asignación semanal no cambia.
6. Los controles esperan a que terminen todos los participantes. El ayudante debe registrar todos sus productos antes de finalizar.

Al vencer el día se pausa el refuerzo. **No se redistribuyen automáticamente cantidades sin confirmar**, porque podrían estar físicamente preparadas. El supervisor debe revisar, pausar si sigue activo y devolver los pendientes desde el panel. Las respuestas confirmadas y los tiempos se conservan. Una persona puede recibir un refuerzo por cancha y proceso; para colaborar en otra cancha se crea otra asignación.

Los refuerzos figuran individualmente en el monitor y en tiempos/actividad. El registro conserva supervisor, asignación, día, inicio, pausas, finalización, respuestas y devolución. El resumen personal calcula cantidades y pallets a partir de los productos asignados, manteniendo la planificación física aprobada del camión.

## Despliegue

- Migración `20261030_02`: tabla `staffing_weeks`; aplicación autorizada expresamente por el usuario el 30/10/2026 después de las pruebas.
- `STAFFING_ENABLED=1` tanto en API como en `picking-notificaciones`.
- Worker separado: activar semanas y pausar refuerzos vencidos antes de procesar avisos Firebase.
- La nueva APK usa `versionName 0.15.0`, `versionCode 16`. Las versiones anteriores no muestran canchas de refuerzo ajenas a su asignación base.
- No se utiliza creación automática de tablas en producción.

## Validación

Pruebas aisladas: 40 de cargas, 3 de planificación semanal, 4 de refuerzos, 4 de notificaciones. PostgreSQL local: migraciones reales y 4 pruebas de concurrencia, incluida confirmación simultánea del titular y ayudante en una misma cancha. Frontend: 21 pruebas, build y flujo de publicación/asignación en navegador con API simulada, escritorio y móvil en modo oscuro. Android: compilación, 10 pruebas unitarias y lint.

Pendiente de aceptación en depósito: dos teléfonos reales, lectura/escucha con ruido, recepción Firebase en segundo plano y reconexión de red. Los resultados locales no sustituyen esas pruebas.
