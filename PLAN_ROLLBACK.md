# Plan de rollback

Fecha: 2026-11-09. Fase actual: auditoría documental.

## Reversión de esta entrega

No hay cambios funcionales, de esquema o de datos que revertir. Si se decide retirar la auditoría, eliminar sólo los siete documentos creados, después de comprobar que no contienen ediciones posteriores del usuario. No usar `git reset --hard` ni `git clean`: existen cambios locales previos que deben preservarse.

La compilación regeneró `frontend/dist`. Si otro proceso local lo estuviera sirviendo, se puede regenerar desde el mismo código y lockfile previos; no se cambió fuente ni se desplegó. El intento de tests Android no cambió intencionalmente el wrapper. No se requiere restaurar Railway.

## Reversión por fase futura, propuesta

1. Registrar commit base, cambios existentes, flags, contratos y versiones de clientes antes de editar. Crear cambios pequeños por fase.
2. Ante fallo de métricas, ocultar tarjetas/reportes nuevos mediante flag; conservar flujo operativo y datos capturados. No borrar eventos para esconder un error de agregación.
3. Revertir únicamente código de la fase, manteniendo compatibilidad con campos aditivos y clientes desplegados. Verificar login, consulta de tareas, respuesta idempotente, pausa y doble control.
4. Para esquema, priorizar expansión compatible: código anterior debe tolerar columnas/tablas nuevas. No ejecutar downgrade destructivo ni restaurar un respaldo antiguo sobre escrituras actuales.
5. Si hay daño de datos, detener las escrituras afectadas bajo procedimiento aprobado, respaldar estado actual, comparar con auditoría y restaurar/conciliar en entorno aislado. La restitución productiva requiere aprobación específica.
6. Desactivar telemetría/comunicación independientemente de voz y picking. No descartar respuestas pendientes de Android; conciliarlas por recibos con el servidor.
7. Después de revertir, confirmar trazabilidad, reservas, autorizaciones y ausencia de doble confirmación; registrar causa, alcance, resultado y responsable.

## Disparadores y verificación

Activar reversión ante acceso no autorizado, duplicación de confirmaciones, pérdida de histórico, liberación incorrecta, discrepancia de KPI no identificada como tal o degradación significativa frente a línea base acordada. Los umbrales concretos de rendimiento se definirán con medición aislada; no hay SLA inventado.

Una migración/despliegue futuro no se considera reversible hasta ensayar restauración y compatibilidad en copia aislada. Este documento no aprueba ni ejecuta esos cambios.

## Fase 1 — reversión concreta

Para detener sólo la captura de contexto nuevo, configurar `KPI_INSTRUMENTATION_ENABLED=0` en el proceso correspondiente y reiniciarlo mediante el procedimiento de ese entorno. Esta entrega no cambia variables de Railway. Los registros ya capturados permanecen consultables; process_id en log y correcciones de stock/frescura siguen vigentes.

Si se necesita revertir código, retirar únicamente el cambio de fase 1 en `backend/services/load_control.py` y `backend/routes/load_control.py`, preservando cambios de terceros. No ejecutar reversión completa del árbol. Los campos JSON aditivos no necesitan migración inversa; no borrar measurement ni incidentes guardados. El código anterior volvería a atribuir stock al operario y podría sobrescribir incidencias de distinta frescura: evaluar ese riesgo antes de una reversión total; preferir apagar la captura.

Verificar en base temporal login, inicio/pausa/finalización, doble control, recibos e igualdad de históricos. No cambiar el wrapper Android ni las descargas preexistentes. Si aparecen incidencias antiguas y nuevas potencialmente duplicadas cuya clave de producto es desconocida, conservarlas para revisión y no fusionarlas por suposición.

## Fase 2 — reversión concreta

La fase es de lectura. Para revertirla, retirar la llamada y el bloque `OperationsCenter` de `DashboardPage`, la ruta `/api/dashboard/operations`, el servicio `operations_dashboard.py` y su prueba. Conservar fase 1 y el dashboard histórico. No hay datos ni migraciones que revertir.

Ante lentitud, retirar primero el polling del centro o exigir rango de fechas; picking y doble control no dependen de esta ruta. Un fallo del centro no debe motivar cambios en `control_camiones.state`. Verificar después que `/api/dashboard/summary`, `/charts`, login y tareas Android continúan operativos.

## Fase 3 — reversión concreta

Retirar `ProductivityPanel` y la llamada `/api/dashboard/productivity`, luego la ruta y `build_productivity_dashboard`; conservar el centro de operaciones de fase 2. No hay datos ni esquema que revertir. Si sólo falla una duración legacy, mantener el reporte y dejar la tasa nula antes de retirar toda la vista. Picking, controles y cronómetros no dependen de esta proyección.

## Fase 4 — reversión concreta

Retirar `QualityPanel`, la llamada y ruta `/api/dashboard/quality` y `build_quality_dashboard` sin tocar las proyecciones de fases 2/3. Para revertir únicamente el flujo de revisión, ocultar las tres acciones nuevas y dejar de aceptar `review`, `recount` y `reject`; conservar `approve` y `adjusted`.

Los campos JSON `review_status` y `review_history` son aditivos: no borrarlos ni reescribir históricos. El código previo los ignora. Una reversión no debe transformar un rechazo en autorización, eliminar un faltante pendiente ni confirmar Chess. Verificar doble control, bloqueo de liberación y autorización manual después del cambio.

## Fase 5 — reversión concreta

Retirar `AlertsPanel`, los campos `alerts/alert_counts` del monitor, la ruta de acciones y `supervision_alerts`. Conservar `alert_reviews` ya escritos: son aditivos y el código anterior los ignora. No borrar historiales para simular una reversión.

La gestión de alertas no controla liberación ni autorización, por lo que retirarla no requiere reparar estados operativos. Verificar después monitor, planificación, pausa, doble control y faltantes. Si sólo falla una clase de alerta, retirar esa derivación antes de desactivar todo el panel.

## Fase 6 — reversión concreta

Configurar `DEVICE_TELEMETRY_ENABLED=0` y reiniciar el backend detiene inmediatamente nuevas escrituras técnicas; la web seguirá recibiendo una respuesta no bloqueante. Para retirar código, eliminar las llamadas de `VoiceControl`, el resumen de supervisión y ambos endpoints. No modificar Vosk, TTS, Firebase ni las respuestas de picking.

Los eventos técnicos ya almacenados son logs aditivos. Conservarlos según la política de logs o depurarlos sólo bajo un procedimiento de retención aprobado; no borrarlos como parte de una reversión de código. Verificar voz manual, comandos, ausencia de bloqueo y dashboard después del cambio.

## Fase 7 — reversión concreta

Retirar la ruta y navegación `capacidad-reportes`, los endpoints de simulación/exportación y `capacity_simulator.py`. No hay datos que revertir porque los escenarios no se guardan y las exportaciones son de lectura.

El dashboard y sus builders deben conservarse: las exportaciones dependen de ellos, pero las fases 2–4 no dependen de la exportación. Verificar dashboard, filtros y planificación física de pallets tras retirar esta fase.

## Fase 8 — reversión concreta

Para revertir la división del frontend, restaurar imports estáticos y retirar `lazy`/`Suspense`; las rutas y páginas no cambian. Para revertir consultas agrupadas, volver a la lectura individual preservando resultados, aunque se recuperará el coste N+1.

Las guardas de rendimiento no modifican producción y conviene conservarlas. No hay índices, migraciones, cachés persistentes ni datos que revertir. Comparar nuevamente tamaños y pruebas antes de aceptar una reversión por incompatibilidad.
