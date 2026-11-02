# Repartos separados y supermercado — 0.16.0

Cada carga pertenece exclusivamente a su camión, depósito y fecha. Los pallets nunca mezclan repartos, ni siquiera para hacer entrar una carga en el camión. La capacidad física se verifica sobre la suma de todos los repartos seleccionados de ese camión; si se excede, no se permite aprobar. No se reasignan cargas a otros camiones.

## Supervisor

En Supervisión → Planificar cargas, seleccionar repartos, guardar la selección y abrir **Revisar pallets y aprobar**. Para cada reparto elegir:

- **Normal:** canchas separadas si entran; puede habilitarse su combinación dentro del mismo reparto. Si exceden la capacidad, la simulación propone esa combinación manteniendo la separación entre repartos.
- **Supermercado / autoelevador:** combina canchas dentro de ese reparto y ordena las piezas por ocupación descendente para reducir pallets. La lista de picking conserva su orden original.

Simular, revisar el total y los pallets exclusivos de cada reparto, verificar físicamente altura/estabilidad/compatibilidad y presionar **Aprobar y enviar al equipo**. Es una estimación por equivalencia de bultos; el algoritmo no garantiza el óptimo físico ni sustituye la revisión del supervisor.

La opción queda almacenada en el documento de planificación aprobado, junto con su huella. Cambiarla después de simular exige una nueva simulación. El servidor recalcula la propuesta al aprobar y rechaza identificadores de cargas ajenas al camión, manipulaciones, versiones desactualizadas y exceso de capacidad.

## Operarios

Web y Android 0.16.0 muestran y leen el reparto, la condición de supermercado y la instrucción de no mezclar repartos ni camiones. El resumen muestra pallets estimados por reparto; cada producto informa los destinos de pallet y cantidades. Los grupos F identifican pallets completos y los M pallets de picking dentro de ese camión. Titular y refuerzos utilizan los mismos destinos aprobados.

Los planes ya iniciados mantienen sus cantidades y destinos aprobados. Los anteriores a esta política se señalan al supervisor; no se reemplazan durante el armado. La inspección de solo lectura realizada antes del despliegue no encontró planes pendientes de salida con pallets compartidos entre repartos. Los planes anteriores aún sin iniciar requieren volver a simular y aprobar con la nueva regla.

## Validación y despliegue

No hay migraciones de esquema. Se publica API y worker con la misma lógica de aprobación; las notificaciones dependen de ella. APK `0.16.0`, código `17`.

Pruebas: 40 del flujo de cargas, 8 del simulador, 2 de separación y aprobación por API, 4 de refuerzos, 4 de notificaciones, 3 de asignaciones semanales y 4 de concurrencia PostgreSQL. Frontend: 22 pruebas, build y flujo de selección/simulación/aprobación con API simulada en escritorio y móvil oscuro. Android: build, 11 pruebas unitarias y lint. Falta probar la lectura y el armado con teléfonos reales en el depósito.
