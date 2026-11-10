# Cambios realizados

## 2026-11-09 — Fase 0

Se agregaron exclusivamente estos documentos solicitados:

- `AUDITORIA_PICKEARYA.md`: arquitectura, matriz de compatibilidad, inventario de tablas, riesgos y límites.
- `ARQUITECTURA_PICKEARYA.md`: dependencias, API, invariantes y correspondencia de estados.
- `DICCIONARIO_KPIS.md`: fórmulas propuestas, unidades, fuentes, disponibilidad, responsables, objetivos e histórico.
- `PLAN_IMPLEMENTACION.md`: fases, aceptación, rollback y puertas de aprobación.
- `PRUEBAS_REGRESION.md`: pruebas ejecutadas, resultados y validaciones pendientes.
- `CAMBIOS_REALIZADOS.md`: este registro.
- `PLAN_ROLLBACK.md`: reversión documental y estrategia de fases futuras.

No se modificaron fuentes de aplicación, contratos, tablas, datos productivos ni dependencias. No se aplicaron migraciones, no se hizo commit y no se desplegó. Se ejecutaron tests existentes y una compilación local que regeneró `frontend/dist` como artefacto de build; Gradle generó cachés locales de trabajo. No son cambios funcionales de fuentes.

Se preservaron las modificaciones previas del wrapper Android y la carpeta de descargas sin seguimiento. No se inspeccionaron secretos ni se imprimieron credenciales del entorno.

Validación final: 181 pruebas aprobadas (117 backend, 39 conversor Python, 25 frontend) y build Vite satisfactorio por invocación directa. `npm run build` falló en el lanzamiento del script; la invocación directa del mismo entrypoint compiló. Tests Android bloqueados antes de ejecutarse por incompatibilidad Gradle/AGP. `git status` confirmó sólo los siete documentos nuevos además de los cambios preexistentes.

Riesgos abiertos: toolchain Android incompatible, esquema real no inspeccionado, aislamiento por sucursal sin modelado completo, semántica de KPIs aún por aprobar, atribución stock/picking diferente según flujo, QA física y concurrencia PostgreSQL pendientes. Los detalles y resultados finales están en los documentos vinculados.

## 2026-11-09 — Fase 1 aprobada

- `backend/services/load_control.py`: función compartida `answer_measurement`, contexto aditivo versionado dentro de respuestas/logs, factor de embalaje con fuente explícita y flag `KPI_INSTRUMENTATION_ENABLED`.
- `backend/routes/load_control.py`: reutilización en respuestas por cancha/pallet, process_id en auditoría, causa de faltante conservada; stock en preparación sin responsabilidad personal automática; identidad de incidencia por producto/frescura con compatibilidad de claves anteriores.
- `backend/tests/test_instrumentation.py`: siete pruebas de integración/unidad sobre la base temporal existente: contrato legacy, stock, factor y replay, flag, factor desconocido, permisos/validación y frescuras con claves legacy.
- Actualizados los siete documentos de auditoría, arquitectura, definiciones, plan, pruebas, cambios y rollback.

Sin endpoints nuevos, tablas, migraciones, dependencias, cambios de permisos ni de clientes web/Android. No se reescriben históricos. No se desplegó ni se ejecutaron pruebas contra Railway. Los tests verifican que el reenvío aceptado no genera un segundo evento de negocio; el registro HTTP general conserva su comportamiento.

Validación de fase 1: 150 pruebas aprobadas, incluidas siete nuevas; detalle en `PRUEBAS_REGRESION.md`. `git diff --check` satisfactorio. Permanecen pendientes la prueba de concurrencia PostgreSQL, el bloqueo Android anterior y las fases 2–8. Próxima fase: ampliar dashboard con agregaciones de lectura y cobertura explícita, sin presentar métricas todavía no medidas como datos operativos.

## 2026-11-09 — Fase 2 aprobada

- Nuevo `backend/services/operations_dashboard.py`: proyección de lectura, estados/avance, checks vigentes, cantidades medibles, tiempos, diferencias, alertas, filtros y cobertura.
- `backend/routes/dashboard.py`: endpoint protegido `GET /api/dashboard/operations` y filtro de sucursal para el dashboard histórico.
- `frontend/src/pages/DashboardPage.jsx`: centro de operaciones con 14 indicadores, tabla responsive, filtros y polling secuencial cada 15 segundos. Los datos no medidos muestran motivo; el bloque histórico permanece separado.
- Nuevo `backend/tests/test_dashboard_operations.py`: cuatro pruebas con casos pendientes, respuesta real, stock, filtros, fechas y permisos.

No se agregaron tablas, migraciones, paquetes, roles ni escrituras. No se modificó Android ni se desplegó. La tabla limita la representación a 100 planillas y expone el total filtrado. La proyección no reemplaza los endpoints existentes.

## 2026-11-09 — Fase 3 aprobada

- `backend/services/operations_dashboard.py`: proyección de productividad por persona, modalidad y día; tiempos activos/pausas, cobertura, tareas y diferencias sin stock.
- `backend/routes/dashboard.py`: nuevo endpoint protegido `GET /api/dashboard/productivity`.
- `frontend/src/pages/DashboardPage.jsx`: tabla de rendimiento por operario, tasas total/picking/pallets, tiempos, diferencias y cobertura.
- Nuevo `backend/tests/test_dashboard_productivity.py`: cinco pruebas sobre fórmula, pausas, stock, modalidad, exclusión de controles, filtros/permisos y timestamps legacy.

No hay DDL, paquetes ni escritura de datos. El endpoint totaliza únicamente estado existente. La evolución diaria queda disponible en API; la primera vista web prioriza la comparación tabular filtrada.

## 2026-11-09 — Fase 4 aprobada

- `backend/services/operations_dashboard.py`: proyección de calidad con exactitud de picking, diferencias de stock, retrabajo, exactitud de segundo control, causas e incidencias auditables.
- `backend/routes/dashboard.py`: endpoint protegido `GET /api/dashboard/quality`.
- `backend/routes/load_control.py`: revisión de faltantes con motivo obligatorio, estados `en_revision`, `recuento_solicitado` y `rechazado`, más historial de usuario y fecha; autorización y ajuste conservan su contrato anterior.
- `frontend/src/pages/DashboardPage.jsx`: panel de calidad, cobertura explícita, causas y detalle de incidencias.
- `frontend/src/pages/LoadControlPage.jsx`: acciones de revisión para supervisores sin automatizar el ajuste en Chess.
- `backend/tests/test_dashboard_quality.py`: cinco pruebas sobre fórmulas, stock, segundo control, filtros/permisos e historial de revisión.

No se agregaron tablas, migraciones, dependencias ni despliegues. La exactitud disponible es por productos respondidos; la exactitud por unidades permanece `null` y se presenta como “No medido”. Confirmar correctamente un faltante en control 2 no se contabiliza como error del controlador.

## 2026-11-09 — Fase 5, alcance compatible

- `backend/routes/load_control.py`: alertas derivadas y deduplicadas por entidad/tipo para planificación pendiente, segundo control pendiente, faltantes sin autorizar y procesos pausados.
- Se agregaron transiciones `reconocida`, `resuelta`, `descartada` y reapertura, con motivo obligatorio donde corresponde e historial de usuario/fecha dentro del estado JSON existente.
- El monitor devuelve alertas y conteos; sólo administrador/supervisor pueden consultarlas o modificarlas.
- `frontend/src/pages/WarehousePage.jsx`: panel de alertas, filtros, contador, acciones e historial reciente dentro de Supervisión.
- `backend/tests/test_supervision_alerts.py`: cinco pruebas de deduplicación, transición, motivos, permisos, segundo control, faltantes y pausas.

No se definieron SLA, demoras, presencia ni aislamiento por sucursal: esas fuentes/modelos no existen y continúan explícitamente pendientes. Resolver una alerta no cambia el proceso que la originó, no autoriza faltantes y no libera cargas.

## 2026-11-09 — Fase 6, diagnóstico técnico opcional

- `POST /api/load-control/device-events`: captura técnica allowlist, autenticada y desactivada por defecto mediante `DEVICE_TELEMETRY_ENABLED`.
- `GET /api/load-control/device-diagnostics`: resumen de 1–31 días para administrador/supervisor con conteos, plataforma y duraciones.
- `frontend/src/utils/deviceTelemetry.js` y `VoiceControl.jsx`: activación, disponibilidad, fallo, detención y reconocimiento aceptado/rechazado enviados en segundo plano sin bloquear la voz.
- `WarehousePage.jsx`: resumen técnico de siete días con estado de activación y aviso de privacidad.
- `backend/tests/test_device_telemetry.py`: cuatro pruebas de flag, privacidad, validación, agregación y permisos.

No se almacena audio, transcripción, token push ni identificador del dispositivo. No se instrumentó Android en esta fase porque su toolchain continúa bloqueado y no hubo dispositivo físico para validar micrófono, auriculares e interrupciones. Firebase y picking conservan su comportamiento.

## 2026-11-09 — Fase 7, simulador y CSV

- Nuevo `backend/services/capacity_simulator.py`: cálculo puro de capacidad, cobertura, diferencia, dotación adicional y horas necesarias.
- `POST /api/dashboard/capacity-simulator`: escenario etiquetado como hipotético, sin escrituras operativas.
- `GET /api/dashboard/export/{operations|productivity|quality}.csv`: exportaciones UTF-8 con rango obligatorio de hasta 366 días y las mismas proyecciones del dashboard.
- Nuevo `frontend/src/pages/CapacityReportsPage.jsx`, ruta y navegación para simulación y descargas.
- Nuevo `backend/tests/test_capacity_reports.py`: cuatro pruebas de fórmulas, ceros, límites, permisos, reconciliación y CSV injection.

No se agregaron objetivos automáticos, XLSX, tablas, dependencias ni integración directa con Power BI. El CSV es el contrato acotado de interoperabilidad; no modifica planificación, dotación o cargas.

## 2026-11-09 — Fase 8, optimización medida

- `frontend/src/App.jsx`: carga diferida de páginas por ruta con `React.lazy`/`Suspense`.
- Bundle inicial reducido de 475.03 kB a 215.27 kB; gzip de 134.52 kB a 72.94 kB. Las páginas se generan como chunks independientes.
- `warehouse_monitor`: carga anticipada de roles y consulta agrupada de asignaciones de canchas, eliminando consultas N+1 por trabajador.
- Dashboard operativo: carga anticipada de roles para opciones de operario.
- Nuevo `backend/tests/test_performance_guards.py`: límites de consultas y payload para tres proyecciones y monitor.

Vosk permanece en un chunk separado de 5.79 MB y sólo se solicita al activar voz; no se cambió el modelo. No se agregaron índices ni se hicieron pruebas de carga en Railway/PostgreSQL.

## Cierre local

Las fases 1–8 suman 217 pruebas aprobadas en la matriz integral disponible y build de producción web satisfactorio. No se hizo commit, migración, conexión de escritura a Railway ni despliegue. Se preservaron la modificación previa de `android/gradle/wrapper/gradle-wrapper.properties` y `frontend/public/downloads/`.
