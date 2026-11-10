# Arquitectura de PickearYa

Fecha: 2026-11-09. Describe código actual; propuestas identificadas expresamente. Complementa [AUDITORIA_PICKEARYA.md](AUDITORIA_PICKEARYA.md).

## Flujo actual

1. PDFs Chess y maestros CSV/XLSX ingresan por rutas de uploads/artículos, se validan y producen lotes, archivos, consolidados y detalles.
2. Control importa el consolidado existente y conserva `ControlLoad.content`, agrupado por cancha y producto/frescura con referencias a líneas originales.
3. Supervisión configura cola de camiones, capacidad, asignaciones y plan aprobado; palletización usa catálogo y reglas de apilado.
4. Android o React consultan las tareas habilitadas. Etapa 0: picking; 4: pallets completos; 1/2: controles independientes. Activos tienen proceso separado.
5. Reservas, cronómetros y respuestas se guardan en JSON de camión bajo transacción, bloqueo y versión optimista. El recibo opcional `request_id` permite detectar reenvíos y payload contradictorio.
6. Liberación en la aplicación depende de controles, activos y faltantes aprobados. Confirmar ajuste manual en Chess es una acción distinta; no hay escritura automática de inventario ERP.
7. Monitor consulta cada cinco segundos después de terminar la petición anterior. Dashboard e histórico consultan importación; tiempos y performance consultan estado de control. El trabajador push notifica tareas y atiende activaciones programadas/refuerzos.

## Superficies de API existentes a preservar

| Prefijo | Función | Dependientes y autorización |
|---|---|---|
| `/api/auth` | login, me, register | Web y Android; registro administrador; usuarios existentes y hash legacy con actualización segura |
| `/api/dashboard` | summary, charts | Dashboard; administración/supervisión por guardia central |
| `/api/operations` | trucks, picking, pallets, picking-by-cancha, by-court | Operación web; datos de consolidados |
| `/api/history` | search, detalle, eliminación, fix-fechas | Histórico; escrituras sensibles por rol |
| `/api/uploads`, `/api/articles`, `/api/exclusions` | importación, catálogo, descargas y exclusiones | Mantener originales y validaciones; sin reinterpretar exclusiones históricas |
| `/api/load-control` | sources, trucks, loads, checks, receipts, assets | Picking web/Android, controles y liberación; autorización por etapa y pertenencia a tarea |
| `/api/load-control` | monitor, performance, activity, planning, dispatch, settings | Supervisión y administración; reutilizar proyecciones existentes |
| `/api/load-control` | users, assignments, staffing, assistance, push/device | Personal, rotaciones, refuerzos y avisos; rutas auxiliares registradas en el mismo blueprint |
| `/api/voice-templates` | runtime y edición de configuración | Android/web consumen runtime; edición administrativa protegida |
| `/api/pallet-rules` | familias, alias y apilado | Planificación y administración |

Esta tabla agrupa contratos; firmas y métodos exactos están en `backend/routes/`. No se ha publicado ni implementado una API nueva.

## Invariantes de compatibilidad

- Conservar identificadores de planilla y separar camión por fecha/sucursal. No tratar matrícula sola como identidad global.
- Conservar SKU como texto, ceros iniciales y clave de frescura. No agrupar sólo por SKU cuando hay fechas distintas.
- No sumar picking, armado y verificaciones como si fueran cantidades preparadas independientes.
- Conservar respaldo de estados reabiertos y recibos; no equiparar un proceso archivado a trabajo vigente.
- Conservar separación entre detector, responsable y autorizador; stock no debe convertirse en error personal.
- Mantener respuesta incierta pendiente hasta consultar recibo del servidor; no liberar por confirmación local.
- Mantener el control de permisos en API, además de `ProtectedRoute` y `roleAccess.js`.
- Mantener datos históricos y estados legacy legibles. Nuevos campos deben ser aditivos y opcionales para clientes anteriores.

## Correspondencia de estados propuesta, sin cambiar persistencia

| Presentación | Estado/fuente actual | Precaución |
|---|---|---|
| Pendiente | Sin check; monitor pending | Puede estar bloqueado por etapa previa o aprobación |
| Asignado | Cancha, cola, asignación de control/refuerzo | No equivale a conectado ni trabajando |
| En preparación | check active con timer_started_at | Etapa 0 o 4; identificar modalidad |
| Pausado | check active sin timer_started_at | No hay motivo normalizado de pausa |
| Con diferencia | shortage/incidente | Dimensión adicional, no reemplazo de estado de tarea |
| Esperando supervisor | Bloqueo/autorización pendiente | Derivar motivo concreto; no inventar estado persistido |
| Preparado | check done en etapas de preparación | Legacy puede tener respuestas incompletas |
| En segundo control | Etapa 2 activa | Persona independiente del primer control |
| Verificado | Controles 1 y 2 completos | Aún pueden faltar activos o autorizaciones |
| Liberado | state.released_at | Liberación en aplicación, no salida física demostrada |

## Extensión propuesta

Comenzar con funciones de agregación de lectura sobre fuentes existentes y componentes del dashboard actual. Utilizar feature flags para tarjetas/reportes nuevos, conservar contratos anteriores y no tocar el motor de voz. Catálogo KPI y reglas de agregación deben ser únicos para pantalla, exportación y Power BI.

Sólo tras revisar cobertura de campos se propondrán migraciones para objetivos, alertas, telemetría o ámbito de sucursal. Cada propuesta debe explicar por qué no basta el modelo existente, especificar índices, retención y compatibilidad. No se autoriza por este documento ningún DDL ni cambio de infraestructura.

## Instrumentación implementada — fase 1

Los dos endpoints de respuesta existentes (cancha y pallet) agregan `answers[product_key].measurement` al guardar una respuesta nueva. Se incluye en el mismo log de negocio, bajo la misma transacción; no se crea otro evento. Los clientes anteriores pueden seguir enviando exactamente el mismo payload.

| Campo / evento necesario | Fuente actual y tratamiento |
|---|---|
| Identidad del evento | `logs.id`; `request_id` del cliente si fue enviado. No fabricar un segundo UUID |
| Tarea y etapa | `check.id`, stage; ahora `process_id` también explícito en el log de respuesta |
| Planilla, cancha, camión, sucursal | load_id y court en log; pallet_id cuando corresponda; entidad log identifica camión; planilla/camión conservan datos de contexto |
| SKU y frescura | `product_key`, sku, fecha_frescura; incidentes nuevos no colisionan por SKU con distinta frescura |
| Cantidad esperada | `measurement.expected_b/expected_u`: cantidades de la tarea validada, no cantidades enviadas por cliente |
| Cantidad confirmada | `physical_b/physical_u`, ya existentes; en control corregido, interpretar según semántica de ese flujo |
| Conversión a bultos | `measurement.units_per_case`, factor capturado; prioridad al producto de la tarea (`task_snapshot`), o catálogo al confirmar (`catalog_at_confirmation`); nulo si falta |
| Versión de semántica | `measurement.version=1`; nunca recalcular históricamente con maestro actual como si fuera factor original |
| Persona y momento | `user_id/username/saved_at`, existentes; actor servidor, no dato confiado al cliente |
| Causa de faltante | `shortage_reason` también conservado en respuesta/log de cancha; catálogo actual sin ampliación en esta fase |
| Voz o manual | `measurement.confirmation_source='unknown'`; los clientes actuales no informan evidencia fiable; no inferir del dispositivo o verificación SKU |
| Dispositivo y sincronización | No se incorporó identificación nueva. Recibo servidor acredita persistencia; no demuestra dispositivo ni entrega offline |
| Duraciones, pausas, inicio/fin | Checks/timing y logs existentes; no se duplican. Motivos de pausa siguen pendientes |
| Asignación y autorización | Logs existentes de asignaciones/refuerzos, faltante approve y liberación; sin otro evento equivalente |
| Repetición y latencia de voz | No hay fuente técnica persistida; pendiente fase 6, no confundir con tiempo HTTP |

Activación: `KPI_INSTRUMENTATION_ENABLED` vale 1 por defecto; valor exacto `0` omite el bloque measurement en nuevas respuestas. No modifica respuestas antiguas ni apaga correcciones de stock/frescura. Puede requerir reinicio del proceso al cambiar variables del despliegue. Sin nuevos paquetes, DDL o ajustes de autenticación.

Idempotencia: la instrumentación se ejecuta después de verificar el recibo, conservando factor y timestamp del primer guardado en reenvíos con el mismo UUID/payload. La política vigente sigue rechazando conflictos y tareas fuera de estado; los recibos se consultan por la ruta existente. Clientes sin request_id mantienen comportamiento previo, sin una garantía nueva de deduplicación por reenvío. `api_activity` sigue siendo telemetría HTTP y no se suma como producción.

Coste: una consulta escalar por SKU indexado sólo cuando la tarea no trae factor válido; ninguna consulta adicional en replay aceptado ni con el flag apagado. El impacto PostgreSQL bajo concurrencia requiere medición aislada antes de producción.

Stock en etapas 0/4 por cancha: conserva detector/autor, pero `responsible_user_id=null`, origen stock y `error_count=0`. No modifica incidentes antiguos. Los consumidores existentes aceptan responsable nulo y origen stock. Los incidentes antiguos por pallet con clave SKU se actualizan en esa clave cuando su product_key coincide, evitando contar dos veces la misma incidencia al corregirla; frescuras distintas conservan entradas distintas.

## Dashboard operativo implementado — fase 2

`services/operations_dashboard.py` proyecta datos sin escribir estado. `/api/dashboard/operations` conserva la protección central: administrador y supervisor acceden; los roles operativos reciben 403. Lee camiones con cargas precargadas, selección/cancelaciones, checks vigentes, refuerzos, pallets físicos, respuestas e incidentes.

- Pendiente: ninguna tarea de preparación iniciada. En preparación: existe trabajo iniciado o avance parcial. Finalizada: todas las unidades de progreso requeridas terminaron.
- Avance: unidades finalizadas / requeridas. Según el plan, la unidad declarada puede ser pallet o tarea.
- Bultos confirmados: cantidades físicas de respuestas de etapas 0/4 con conversión medible. Etapas 1/2 no se suman otra vez.
- Productividad preliminar: bultos confirmados medibles / horas activas de preparación. Comparaciones por complejidad corresponden a fase 3.
- Diferencias: incidentes vigentes filtrados. Alertas: faltantes de preparación más autorizaciones pendientes, con desglose.
- Cargas liberadas: camiones distintos con `released_at`; no equivale a salida física ni a planillas individuales.

La respuesta incluye cobertura, razones de métricas no disponibles, filtros y hasta 100 filas; `rows_total` informa el universo. Sin rango consulta el histórico disponible. Medir el recorrido de JSON con PostgreSQL representativo antes de producción.

## Productividad implementada — fase 3

`GET /api/dashboard/productivity` comparte el ámbito de fecha, sucursal, camión, planilla, operario y estado. Considera solamente checks vigentes de preparación: etapa 0 para picking y 4 para pallets completos. Los refuerzos se identifican por check y no duplican el proceso principal. Checks archivados por reapertura no se suman.

Por operario devuelve cantidades medibles, productos respondidos, tiempo activo, pausa derivada, tareas finalizadas, planillas participadas, planillas con aporte terminado, diferencias atribuibles y cobertura. `modalidades` conserva picking y pallets completos por separado; `evolution` agrega por fecha operativa. Una incidencia de stock, responsable nulo o `error_count=0` no aumenta diferencias personales.

La tasa es `bultos medibles / (segundos activos / 3600)`. Sin tiempo válido o sin respuestas medibles devuelve `null`. Timestamps históricos incompatibles se aíslan por proceso para que el reporte continúe, sin inventar duración. “Líneas” significa productos respondidos en la tarea, no líneas originales del PDF. No se afirma que una planilla compartida fue completada íntegramente por cada participante.

## Calidad y revisión implementadas — fase 4

`GET /api/dashboard/quality` comparte los filtros operativos y proyecta respuestas, incidencias y faltantes existentes sin escribirlos. Expone métricas, cobertura, causas y hasta 100 incidencias recientes con cantidades, responsable, detector, estado e historial de revisión. No suma una confirmación de faltante como una segunda incidencia.

Las rutas de faltantes de cancha y pallet conservan `approve` y `adjusted` y agregan `review`, `recount` y `reject` para administrador/supervisor. Cada transición exige motivo de 3–500 caracteres y agrega a `review_history` estado, id/usuario y timestamp del servidor. Un faltante autorizado no admite estas revisiones; debe usarse la reapertura existente cuando corresponda. Los estados nuevos no liberan cargas ni escriben en Chess.

## Supervisión y alertas implementadas — fase 5

`GET /api/load-control/monitor` agrega `alerts` y `alert_counts`. Las claves deterministas combinan tipo y entidad, evitando una alerta nueva en cada polling. La condición se deriva del estado operativo; la gestión se guarda bajo `control_camiones.state.alert_reviews[key]` con estado e historial.

`POST /api/load-control/trucks/{id}/alerts/{key}/{action}` acepta `acknowledge`, `resolve`, `dismiss` y `reopen` sólo para administrador/supervisor y únicamente si la alerta sigue vigente. La escritura usa el reemplazo versionado y `save_state`, por lo que también queda en el log general. Resolver o descartar una alerta no resuelve la condición, no autoriza faltantes ni libera cargas.

## Diagnóstico técnico implementado — fase 6

`POST /api/load-control/device-events` acepta exclusivamente eventos técnicos enumerados, plataforma web/Android, versión corta, duración acotada y código técnico sin texto libre. Los detalles se guardan en `logs` con `entity=device_telemetry` sólo cuando el flag está habilitado. Campos adicionales se descartan y no existe endpoint para audio o transcripciones.

`GET /api/load-control/device-diagnostics?days=N` agrega hasta 31 días para roles de gestión. La web envía los eventos en paralelo al trabajo y absorbe cualquier error. Esta ruta no participa en inicio, reconocimiento, confirmación, idempotencia ni liberación. Android y push no fueron modificados.

## Simulador y exportaciones implementados — fase 7

`POST /api/dashboard/capacity-simulator` invoca una función pura y devuelve `hypothetical=true`. Valida límites y no consulta ni escribe cargas. Su unidad es bultos; no mezcla líneas, pallets o unidades.

`GET /api/dashboard/export/{report}.csv` reutiliza `build_operations_dashboard`, `build_productivity_dashboard` o `build_quality_dashboard`. El rango es obligatorio y acotado; la salida usa UTF-8 con BOM, delimitador punto y coma y protección de celdas iniciadas por `=`, `+`, `-`, `@`, tabulación o retorno. No existe job, archivo persistido ni escritura de negocio.

## Optimización implementada — fase 8

El router web conserva las mismas rutas pero importa cada página de manera dinámica bajo un único `Suspense`. El shell, autenticación y navegación forman el chunk inicial; dashboard, supervisión, carga y configuración se descargan al visitarlos. Vosk mantiene su importación dinámica propia.

El monitor obtiene usuarios con roles mediante `joinedload` y todas las asignaciones mediante un único `IN`, en vez de consultar por persona. El dashboard operativo aplica la misma precarga para roles. No hay caché compartida: el polling continúa mostrando estado confirmado por servidor y evita invalidez de datos.
