# Auditoría de PickearYa

Fecha: 2026-11-09. Base Git: `07b6a09`, con modificaciones locales previas. Alcance: fase 0 del pedido; análisis del código disponible y pruebas aisladas, sin cambios funcionales, migraciones ni despliegues.

**Actualización posterior a la aprobación:** este diagnóstico conserva la línea base de fase 0. La fase 1 corrigió la atribución de nuevos faltantes de stock en preparación, agregó contexto de cantidades/conversión a respuestas y logs existentes y evitó colisiones de incidencias por frescura. Los históricos no se reescribieron. Ver `CAMBIOS_REALIZADOS.md` y el inventario actualizado en `ARQUITECTURA_PICKEARYA.md`. Los demás riesgos y validaciones pendientes siguen vigentes.

## 1. Conclusión y límites de verificación

La evolución debe ampliar Flask, React y Android nativo Java. No hay una aplicación Flutter que migrar. El segundo control ya está integrado en la API principal: `control_cargas_mvp/` es un piloto separado y no debe convertirse en otro sistema operativo. PostgreSQL es el motor exigido por `backend/config.py`; SQLite está restringido a pruebas explícitas. `backend/schema.sql` conserva sintaxis MySQL y no representa el esquema operativo actual.

Se revisaron modelos, servicios, rutas, navegación web, cliente Android, voz, migraciones, pruebas y despliegue. No se consultó Railway ni se inspeccionaron credenciales, datos personales, respaldos o archivos operativos. Por tanto, el esquema realmente desplegado, volumen, índices físicos, integridad de históricos, flags activos y rendimiento de producción **REQUIEREN VALIDACIÓN**. Una prueba automatizada satisfactoria no certifica micrófono, auriculares ni operación real.

El árbol tenía previamente `android/gradle/wrapper/gradle-wrapper.properties` modificado y `frontend/public/downloads/` sin seguimiento. Se conservaron. Resultados reproducibles y limitaciones: [PRUEBAS_REGRESION.md](PRUEBAS_REGRESION.md).

## 2. Arquitectura actual

| Capa | Evidencia | Funcionamiento |
|---|---|---|
| API | `backend/app.py`, `backend/routes/`, `backend/services/` | Flask, SQLAlchemy, JWT, servicios de importación, planificación, control, personal y voz |
| Persistencia | `backend/models.py`, modelos adicionales en `services/` | PostgreSQL, entidades relacionales y documentos JSON versionados por camión |
| Web | `frontend/src/App.jsx`, `pages/`, `components/` | React, Vite, Tailwind, Axios, Chart.js; rutas por rol y componentes compartidos |
| Android | `android/app/build.gradle`, `MainActivity.java`, `Api.java` | Java 17, Android mínimo 26, versión declarada 0.25.0/33; HTTPS; token en memoria |
| Voz | `VoiceSessionService.java`, `frontend/src/voice/`, `voz/conversor.py` | Vosk local, TTS, interpretación determinista; configuración de frases y comandos |
| Avisos | `backend/push_worker.py`, `services/push.py` | Firebase y trabajador separado con reintentos; flag `PUSH_ENABLED` |
| Infraestructura | `Dockerfile`, `railway*.toml`, `docker-compose.yml` | Compilación React y servicio Flask/Gunicorn; trabajador push separado |

Detalle de contratos y dependencias: [ARQUITECTURA_PICKEARYA.md](ARQUITECTURA_PICKEARYA.md).

## 3. Matriz de compatibilidad y reutilización

Las clasificaciones describen el alcance exacto de cada fila, no todo el módulo. EXISTENTE Y FUNCIONAL se apoya en implementación y pruebas aisladas; no implica validación productiva.

| Funcionalidad solicitada | Clasificación | Evidencia y decisión compatible |
|---|---|---|
| Login, usuarios y roles | EXISTENTE Y FUNCIONAL | `auth.py`, `routes/auth.py`, `services/users.py`; reutilizar JWT, hash, `session_version` y alta única |
| Personal, legajo, activación y asignación | EXISTENTE Y FUNCIONAL | `Personnel.jsx`, `warehouse.py`, `users.py`; conservar controles sobre trabajo activo |
| Planificación semanal y refuerzos | EXISTENTE Y FUNCIONAL | `staffing.py`, `assistance.py`, componentes WeeklyStaffing/DailyAssistance; no duplicar asignaciones |
| Importación Chess | EXISTENTE Y FUNCIONAL | `pdf_parser.py`, `processing.py`, `csv_import.py`, `logistics_xlsx.py`; intercambio por archivos, no ajuste automático ERP |
| Planillas, canchas y pallets | EXISTENTE Y FUNCIONAL | `ControlLoad`, instantáneas, `pallet_planning.py`, `pallet_control.py`; conservar reparto y SKU + frescura |
| Picking y confirmaciones API | EXISTENTE Y FUNCIONAL | `routes/load_control.py`, recibos UUID, reservas, pausas; preservar contratos actuales |
| Voz/acústica Android en depósito | REQUIERE VALIDACIÓN | Java/Vosk/TTS implementados; prueba física pendiente y compilación de tests bloqueada por Gradle |
| Segundo control independiente | EXISTENTE Y FUNCIONAL | Etapas 1/2, asignaciones cruzadas, activos, autorizaciones y liberación; ampliar integración existente |
| Dashboard de cantidades planificadas | EXISTENTE CON MEJORAS NECESARIAS | `dashboard.py`, `DashboardPage.jsx`; mide importado/planificado, no productividad efectiva |
| Centro de operaciones con 14 indicadores | PARCIALMENTE IMPLEMENTADA | Monitor, tiempos y estados disponibles; faltan resumen coherente, presencia, horarios límite y filtros comunes |
| Actualización en vivo | EXISTENTE CON MEJORAS NECESARIAS | `DepotMonitorPage.jsx`: polling secuencial cada 5 s tras respuesta, timeout, cancelación, última actualización y error; dashboard sin polling |
| Productividad por hora/operario | PARCIALMENTE IMPLEMENTADA | `performance()`, `timing()`, respuestas; falta agregación validada de bultos, líneas, tiempos y complejidad |
| Calidad y diferencias | EXISTENTE CON MEJORAS NECESARIAS | Incidentes y faltantes; causas distintas según flujo, atribución de stock inconsistente; falta catálogo completo y KPIs |
| Excepciones y autorizaciones | PARCIALMENTE IMPLEMENTADA | Vista `/supervision/faltantes`, approve/adjusted, observaciones y auditoría; no se verificó flujo completo rechazar/solicitar recuento con estados propios |
| Cumplimiento de despacho | PARCIALMENTE IMPLEMENTADA | `released_at` y estados de control disponibles; falta horario comprometido y medición de demora |
| Estado operativo y técnico del personal | PARCIALMENTE IMPLEMENTADA | Tareas, pausas y cuenta activa existentes; cuenta activa o sin proceso no prueban presencia/disponibilidad |
| Configuración de voz | EXISTENTE CON MEJORAS NECESARIAS | `voice_templates.py`, `VoiceTemplatesPage.jsx`: frases, alias, velocidad, frescura; no inventar controles remotos de hardware |
| Telemetría de reconocimiento | NO IMPLEMENTADA | No se encontró serie persistida de comandos, rechazos, latencias y fallos de audio por dispositivo |
| Inventario Android y diagnóstico central | PARCIALMENTE IMPLEMENTADA | `push_devices`, PushDiagnostics; no guardan inventario completo, versión, batería o sincronización operativa |
| Comunicación supervisor-operario | PARCIALMENTE IMPLEMENTADA | Avisos de tareas Firebase; faltan mensajería dirigida, recibos de lectura, asistencia comunicacional y audio bidireccional |
| Offline operativo | NO IMPLEMENTADA | Existe recuperación de una respuesta incierta y consulta de recibo; no una cola offline transaccional general |
| Alertas operativas administrables | PARCIALMENTE IMPLEMENTADA | Advertencias de tiempos, bloqueos, faltantes y tareas; falta ciclo nueva/revisión/resuelta/descartada, deduplicación y umbrales |
| Simulador de dotación y productividad | NO IMPLEMENTADA | Simulación existente es de armado/capacidad de pallets, no de operarios × horas × bultos/h |
| Reportes KPI, CSV/Excel y Power BI | PARCIALMENTE IMPLEMENTADA | Dashboard, histórico y tiempos existentes; CSV de voz no equivale a reportes KPI; no se encontró suite de 12 reportes |
| Objetivos KPI e histórico de cambios | NO IMPLEMENTADA | Sin entidad/pantalla específica verificada; proponer extensión mínima luego de acordar definiciones |
| Vistas por rol | EXISTENTE CON MEJORAS NECESARIAS | Administrador/supervisor/operador/controlador/palletizador; no existe rol gerencia; definir permisos sin equipararlo a administrador |
| Auditoría sensible | EXISTENTE CON MEJORAS NECESARIAS | `logs`, `save_state`, edición de personal y actividad API; no todas las acciones tienen antes/después/motivo |
| Concurrencia PostgreSQL | REQUIERE VALIDACIÓN | Locks, versiones y restricciones presentes; suite dedicada existe, no ejecutada contra un PostgreSQL descartable en esta auditoría |
| Responsive y accesibilidad | REQUIERE VALIDACIÓN | Estilos adaptativos y controles accesibles parciales; monitor fuerza ancho mínimo de 720 px para procesos; falta prueba visual móvil |

## 4. Base de datos y dependencias

Inventario estático: **22 tablas ORM** (10 en `models.py` y 12 en servicios). No confundirlo con el estado real de Railway.

| Grupo | Tablas | Claves y vínculos relevantes |
|---|---|---|
| Identidad | `roles`, `users` | PK id; rol FK; username/email/legajo únicos; versión de sesión |
| Catálogo | `articulos`, `articulos_excluidos` | SKU único; logística, descripción de voz, origen e indicadores de actividad |
| Ingesta | `lotes_procesamiento`, `archivos_subidos`, `consolidados`, `consolidado_detalle`, `errores_procesamiento` | FK lote/archivo/consolidado; binarios persistidos; fecha reparto y frescura |
| Auditoría | `logs` | FK usuario; entidad, acción, timestamp y detalle textual JSON |
| Control | `control_camiones`, `control_planillas`, `control_temporizadores` | Camión único por sucursal/fecha/camión; planilla por sucursal/fecha/reparto; FK camión; temporizador PK usuario y check_id único |
| Asignación/capacidad | `user_court_assignments`, `depot_planning_settings`, `truck_pallet_capacities` | Usuario/cancha como PK compuesta; sucursal y camión para capacidad; asignación de cancha sin sucursal |
| Dotación | `staffing_weeks` | Semana como PK, JSON borrador/publicación, versión optimista y usuario publicador |
| Avisos | `push_devices` | Hash token PK, FK usuario e índice; caducidad, último contacto, fallos y próximas tentativas |
| Voz | `voice_templates` | Clave PK, texto, enabled y autor/fecha; también almacena ajustes y comandos |
| Reglas | `pallet_caliber_families`, `pallet_caliber_aliases`, `pallet_stacking_rules` | Familias/alias y reglas de apilado; autoría y relación alias/familia |

`control_planillas.source_id` es único, pero deliberadamente no tiene FK a consolidados. `content` conserva instantáneas; `control_camiones.state` guarda controles, respuestas, recibos, incidentes, planificación, históricos y liberación. Antes de proyectar KPIs hay que distinguir estructuras antiguas, controles por pallet y refuerzos.

Hay 11 revisiones Alembic encadenadas, desde `20261015_01` hasta `20261105_01`. La inicial valida un esquema existente de 13 tablas; no crea una base nueva. `migrations/env.py` exige `MIGRATION_DATABASE_URL` explícita. El arranque normal inspecciona tablas/columnas y no aplica DDL. No se verificó `alembic_version` productivo. Los índices explícitos adicionales encontrados son usuario de push y legajo único; PK/UNIQUE también generan estructuras de acceso en PostgreSQL. No se infiere que esos sean todos los índices físicos existentes.

## 5. Riesgos concretos

| Prioridad | Hallazgo verificable | Consecuencia y tratamiento propuesto |
|---|---|---|
| Alta | Asignaciones `(user_id, court_number)` sin sucursal; `auth.py` controla rol, no ámbito de sucursal | No prometer aislamiento multisucursal. Definir alcance y política, probar accesos directos y luego migrar con aprobación |
| Alta | `answer()` atribuye incidentes de etapas 0/4 al operario y origen picking, incluso motivo stock | No usar estos incidentes como errores individuales. El flujo por pallet ya distingue stock y `error_count=0`; armonizar sin reescribir históricos |
| Alta | Dashboard deriva volúmenes de importación y maestro actual; `tiempo_promedio` es constante 0 | No interpretarlo como preparado/tiempo medido. Agregar disponibilidad de dato y fuentes de confirmación; mantener compatibilidad API |
| Alta | Picking antiguo puede finalizar sin todas las respuestas (`finish`, test legacy) | `done` no garantiza cantidades confirmadas; KPI debe señalar cobertura incompleta, no completar cantidades por inferencia |
| Alta | Gradle local 9.7.1 y plugin Android 8.11.1 fallan al ejecutar pruebas | No certificar Android; reparar toolchain en etapa aprobada, respetando modificación previa |
| Alta | `history.delete` elimina consolidado/detalle; log general no guarda copia completa | El histórico de control tiene instantánea, pero reporting de origen puede perder datos. No usar borrado para limpieza; diseñar retención compatible |
| Alta | Secretos predeterminados en `Config`; errores crudos de inicialización expuestos por readiness/API | Verificar configuración efectiva sin revelar valores; endurecimiento separado con pruebas de arranque, sin rotar sesiones a ciegas |
| Media | JSON completo versionado/bloqueado por camión; bloqueos también por usuario en escrituras | Correctitud protegida, posible contención con muchos operarios; medir en clon antes de cambiar arquitectura |
| Media | Dashboard materializa detalles e IDs; performance puede leer todos los camiones si no se filtra fecha | Acotar consultas y paginar reportes; medir planes e índices antes de agregarlos |
| Media | `apply_dashboard_filters` selecciona IDs de consolidados por cancha y luego lee todos sus detalles | El filtro cancha puede incluir otras canchas del mismo consolidado; prueba específica requerida antes de exponerlo como filtro KPI |
| Media | Parte de las conversiones usa maestro actual, no factor histórico capturado | Cambios de embalaje pueden alterar métricas históricas; usar snapshot cuando exista y marcar factor ausente |
| Media | Tiempos mezclan UTC sin zona, ISO con zona y fecha operativa; temporizador sigue si se cierra app | Normalizar lectura y cortes de turno, sin corregir tiempos silenciosamente; usar advertencia existente >12 h |
| Media | Token web en localStorage, sin heartbeat de sesión operativa | Revisar exposición XSS y política de presencia; no deducir disponibilidad de `active` ni de último push |
| Media | README Android describe versiones anteriores y ausencia de persistencia distinta al código actual | La app conserva respuesta pendiente en preferencias privadas; auditar retención/cifrado antes de offline |
| Media | Bundle Vosk de aproximadamente 5.8 MB sin comprimir; advertencia de importación dinámica inefectiva | Medir carga en red de depósito; optimizar después de establecer pruebas, sin reemplazar motor |

## 6. Eventos y cobertura de medición

Reutilizar `logs`, respuestas con `saved_at`, `user_id`, `request_id`, cantidades físicas, incidentes y `checks` con tiempos. Ya hay acciones para iniciar, responder, pausar, finalizar, reabrir, asignar, autorizar y liberar. `api_activity` es telemetría HTTP, no una segunda confirmación de producto: sumarla a `respuesta_control` duplicaría eventos.

Faltan o no están normalizados: dispositivo por confirmación, origen voz/manual, duración de reconocimiento, causas de pausa, jornada/sucursal de asignación, límite comprometido de despacho y estados de alertas. No existe evidencia de telemetría acústica persistida ni cola offline general. No se recomienda crear un event store paralelo por defecto.

La clave de producto puede ser `SKU|fecha_frescura`; una línea original de PDF puede agruparse con otras. Control por pallet puede repartir el mismo SKU. La agregación debe resolver el grano antes de sumar, excluir controles del volumen preparado y mantener el trabajo de refuerzos sin duplicarlo.

## 7. Plan seguro y decisiones pendientes

Ver [PLAN_IMPLEMENTACION.md](PLAN_IMPLEMENTACION.md) y [DICCIONARIO_KPIS.md](DICCIONARIO_KPIS.md). Primero estabilizar evidencia y definiciones, después instrumentación mínima y dashboard, continuando por fases. Reutilizar polling, identidad, instantáneas, controles, auditoría y componentes existentes.

Antes de implementar se requiere la aprobación del plan, según la instrucción final del pedido. Decisiones funcionales a validar: equivalencia pedido/reparto/planilla, sucursales y alcance por rol, definición de línea y bulto equivalente, turnos y pausas autorizadas, hora prometida de despacho, objetivos oficiales y alcance offline. El plan permite avanzar primero en métricas con fuente verificable y mostrar el resto como no disponible.

No se considera completada la evolución solicitada: esta entrega es la auditoría previa, con propuestas revisables y bloqueos explícitos.
