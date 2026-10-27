# Planificación y seguimiento del depósito

La revisión `20261027_01` fue aplicada en Railway el 27/10/2026 con autorización del usuario. La integración de código está en `feature/voz-picking`.

## Flujo

1. Administración configura la capacidad física por camión/depósito y la mezcla predeterminada entre canchas.
2. Supervisión incorpora todos los repartos, simula, revisa apilado físico y aprueba. Capacidad insuficiente, simulación desactualizada o repartos pendientes impiden aprobar.
3. Picking recibe remanentes y unidades; pallets completos recibe los pallets enteros. Cada rol ve solo sus canchas. Los controles conservan el total original y comienzan después del armado.
4. El monitor `/monitor` consulta un resumen por fecha cada 5 segundos. `/tiempos` permite consultar tiempos e historial paginado.

El plan usa la versión del camión y una huella de productos/capacidad/mezcla para rechazar aprobaciones desactualizadas. Antes de comenzar, cambios de catálogo invalidan la aprobación. Una vez iniciado el armado, sus cantidades quedan congeladas: los cambios de catálogo se usan en planes futuros. No se permite modificar la capacidad ni incorporar nuevos repartos a ese camión mientras tiene trabajo iniciado. Los procesos históricos sin planificación pueden continuar, pero no comenzar un armado nuevo retroactivamente.

La mezcla es una estimación por equivalencias de catálogo, no un cálculo geométrico de altura, peso, estabilidad o compatibilidad. Se exige revisión física del supervisor. No se escribe en Chess.

## Tiempos y concurrencia

Los procesos registran inicio, tiempo activo, pausas, fin, usuario, cancha, carga y camión; cada respuesta conserva fecha y autor. Las reasignaciones archivan el tramo del operario anterior y preservan las respuestas. La aprobación registra espera desde la incorporación y tiempo transcurrido desde abrir la planificación; este último es tiempo de calendario, no presencia efectiva del supervisor.

Las escrituras bloquean en PostgreSQL al usuario y el camión mientras actualizan el estado, además del control optimista de versión. Una misma tarea tiene un solo responsable activo. Las lecturas del monitor no toman esos bloqueos ni generan auditoría en cada actualización.

La actividad autenticada de escritura registra endpoint, método, resultado y milisegundos del servidor en `logs`; no registra cuerpos, contraseñas ni tokens. Los eventos de negocio se guardan en su transacción. La telemetría adicional se registra después; si falla, se informa en los logs de aplicación sin revertir una operación ya confirmada. Las acciones anteriores a esta instrumentación no tienen tiempos inventados.

No se agregaron nuevas tablas fuera de las migraciones aprobadas. Pruebas de concurrencia: `backend/tests/test_warehouse_concurrency.py`, exclusivamente PostgreSQL local en puerto 55433, base `picking_test`. Nunca ejecutar ese script contra una base compartida.
