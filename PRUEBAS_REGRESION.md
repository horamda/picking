# Pruebas y línea base

Fecha: 2026-11-09. Auditoría de código sin modificación funcional. No se ejecutaron fixtures ni carga contra Railway. Las suites Python seleccionadas establecen SQLite temporal y desactivan inicialización automática antes de importar la aplicación; las de cálculo puro no requieren base.

## Resultados de esta ejecución

Resultado final: **181 pruebas aprobadas** (117 backend, 39 conversor Python, 25 frontend). Android no llegó a ejecutar sus pruebas. Ninguna compilación equivale a una prueba visual o acústica.

| Comando / alcance | Resultado |
|---|---|
| `python -m pytest tests -q` | 39 aprobadas; conversor de voz |
| `python backend/tests/test_text_encoding.py` | 2 aprobadas |
| Node test runner, los 8 archivos `*.test.js` de `frontend/src/voice` y `frontend/src/utils` | 25 aprobadas; comandos, lectura, producto, roles, filtros, agrupación y CSV seguro |
| `npm run build` en frontend | Falló el lanzamiento del script en el entorno Windows: ruta no encontrada |
| `node node_modules/vite/bin/vite.js build` en frontend | Aprobado; 119 módulos, advertencias de bundle Vosk grande, importación dinámica inefectiva y catálogo Browserslist antiguo |
| `android/gradlew.bat --offline testDebugUnitTest` | Falló antes de ejecutar tests: AGP 8.11.1 depende de API interna removida en Gradle; wrapper local 9.7.1. No modificado |
| `python backend/tests/test_load_control.py` | 49 aprobadas, 124.313 s; flujo API y regresión de operación |
| `python backend/tests/test_article_import.py` | 13 aprobadas |
| `python backend/tests/test_assistance.py` | 5 aprobadas |
| `python backend/tests/test_pallet_control.py` | 5 aprobadas |
| `python backend/tests/test_pallet_planning.py` | 21 aprobadas |
| `python backend/tests/test_personnel.py` | 7 aprobadas |
| `python backend/tests/test_pdf_parser.py` | 4 aprobadas |
| `python backend/tests/test_reparto_planning.py` | 4 aprobadas |
| `python backend/tests/test_staffing.py` | 3 aprobadas |
| `python backend/tests/test_push.py` | 4 aprobadas; no prueba de recepción real Firebase |
| `backend/tests/test_warehouse_concurrency.py` | No ejecutada: requiere PostgreSQL descartable dedicado en 127.0.0.1:55433; su fixture elimina/recrea tablas |
| Android instrumentado y pruebas de micrófono/auriculares | No ejecutadas; requieren dispositivo físico y toolchain funcional |
| QA visual responsive, accesibilidad, latencia y carga | No ejecutado; no se levantó aplicación contra base compartida |

Las suites específicas se ejecutaron en procesos Python separados. Se observaron advertencias por `datetime.utcnow()`, `Query.get()` y detección automática de módulos ES en Node; no provocaron fallos. El primer intento Node con comodines literales no encontró archivos en Windows. Se repitió con expansión explícita de PowerShell y pasó. Para reproducir:

```powershell
$testFiles = @(Get-ChildItem frontend/src/voice/*.test.js,frontend/src/utils/*.test.js | ForEach-Object FullName)
node --test @testFiles
```

## Cobertura crítica existente y ampliación necesaria

| Área | Evidencia existente | Casos obligatorios para las próximas fases |
|---|---|---|
| Autenticación/personal | test_load_control, test_personnel | Inactivo, sesión revocada, último administrador, cambios con tarea activa; nuevo ámbito sucursal |
| Pedidos/importación | test_pdf_parser, test_article_import, test_load_control | PDF varias planillas, duplicados, rollback, maestro cambiado e históricos |
| Picking/control | test_load_control, test_pallet_control | Independencia controles, reserva, pausa, finalización, faltante, activos y liberación |
| Planificación/refuerzo | test_pallet_planning, test_reparto_planning, test_assistance, test_staffing | Trabajo dividido y reapertura sin doble conteo; expiración de refuerzo |
| Idempotencia/concurrencia | Pruebas de recibos y optimistic locking; suite PostgreSQL dedicada | Mismo UUID/mismo payload; distinto payload; dos usuarios misma tarea; tareas distintas; corte entre commit y respuesta |
| KPIs | No existe suite específica completa | Cero/ausente, factores históricos, línea SKU/frescura, control 1/2, pausas, turnos, archivo de checks y cobertura |
| Voz Android | 7 clases de unit tests y SmokeRunner | Sonido real, rechazo de ambiguos, TTS no se autoconfirma, llamadas/interrupciones, cambio pantalla y micrófono |
| Offline | Recuperación de respuesta pendiente en cliente | Persistencia segura, sesión distinta, conflictos multidispositivo, confirmación local sin liberación |
| Reportes/alertas | Fuentes parciales, sin suite general | CSV injection, exportación consistente, rangos máximos, deduplicación, permiso para resolver y motivo de descarte |

Aceptación por fase: pruebas críticas satisfactorias, ausencia de cambios no autorizados, documentación de resultado y rollback. SQLite valida lógica, no garantiza semántica de bloqueo ni rendimiento de PostgreSQL. No extrapolar prueba unitaria de voz al reconocimiento en ruido de depósito.

## Fase 1 — ejecución posterior a cambios aprobados

**150 pruebas aprobadas**, sin sumar las ejecuciones repetidas durante desarrollo ni las 181 de la línea base. Se ejecutaron en procesos aislados, sin base compartida:

| Suite | Aprobadas |
|---|---:|
| `python backend/tests/test_instrumentation.py` | 7 |
| `python backend/tests/test_load_control.py` | 49 |
| `python backend/tests/test_assistance.py` | 5 |
| `python backend/tests/test_reparto_planning.py` | 4 |
| `python backend/tests/test_pallet_control.py` | 5 |
| `python backend/tests/test_personnel.py` | 7 |
| `python backend/tests/test_staffing.py` | 3 |
| `python backend/tests/test_push.py` | 4 |
| `python backend/tests/test_text_encoding.py` | 2 |
| Node, ocho archivos de voz/utilidades | 25 |
| `python -m pytest tests -q` | 39 |

`git diff --check` satisfactorio. La suite nueva se volvió a ejecutar después de agregar compatibilidad con claves de incidentes legacy: 7/7 aprobadas. Verifica payload anterior sin campos nuevos, diferencia entre cantidad esperada y real, stock sin responsabilidad personal automática, conservación del detector, replay sin segundo evento, conflicto de UUID, factor inmutable tras cambio de maestro, fuente snapshot, factor desconocido nulo, flag apagado, permiso y causa inválida, frescuras distintas y actualización de incidencia legacy sin duplicación.

No se repitió build frontend ni Android: no hay cambios en clientes; permanece el resultado y bloqueo de fase 0. Concurrencia real PostgreSQL, carga y QA en teléfono siguen pendientes. El cambio está validado localmente para este alcance; no certifica producción ni completa las fases 2–8.

## Fase 2 — ejecución posterior al dashboard

- `python backend/tests/test_dashboard_operations.py`: 4 pruebas aprobadas tras el ajuste final. Cubre datos no disponibles, estado/avance, bultos confirmados, cobertura, operario, stock/alerta, filtros, fechas y permiso.
- `python backend/tests/test_load_control.py`: 49 pruebas aprobadas; regresión principal.
- Node, ocho archivos de voz/utilidades: 25 pruebas aprobadas.
- `python backend/tests/test_instrumentation.py`: 7 pruebas aprobadas antes del ajuste visual; su lógica no cambió.
- Build Vite directo: aprobado, 119 módulos. Persisten advertencias conocidas de tamaño del bundle Vosk e importación dinámica de voz.
- `py_compile` del servicio/ruta y `git diff --check`: satisfactorios; Git sólo informó normalización futura LF/CRLF en dos archivos.

No se ejecutaron PostgreSQL concurrente, Android, QA visual con navegador real ni Railway. El centro recorre JSON de camiones seleccionados; su rendimiento debe medirse con volumen representativo antes de producción.

## Fase 3 — productividad

- `python backend/tests/test_dashboard_productivity.py`: 5 pruebas aprobadas tras el ajuste final. Fórmula con una hora activa, pausa derivada, cobertura, stock excluido, error picking atribuido, modalidad pallets, controles excluidos, permisos/filtros y timestamp naive legacy.
- `python backend/tests/test_dashboard_operations.py`: 4 pruebas aprobadas después de compartir manejo seguro de tiempos.
- `python backend/tests/test_load_control.py`: 49 pruebas aprobadas en 184.957 s; regresión principal.
- Node: 25 pruebas aprobadas. Conversor Python: 39 aprobadas.
- Build Vite: aprobado, 119 módulos; persisten las advertencias conocidas del bundle de voz.

Sin prueba PostgreSQL concurrente, Android, navegador físico o producción. La comparación entre personas no tiene todavía ajuste de complejidad ni muestra mínima oficial.

## Fase 4 — calidad y diferencias

- `python backend/tests/test_dashboard_quality.py`: 5 aprobadas. Cubre ausencia de denominador, separación stock/picking, causas, confirmación correcta en segundo control, métrica por unidades no disponible, revisión/recuento, motivo obligatorio, historial, autorización posterior, filtros y permisos.
- `python backend/tests/test_dashboard_operations.py`: 4 aprobadas.
- `python backend/tests/test_dashboard_productivity.py`: 5 aprobadas.
- `python backend/tests/test_instrumentation.py`: 7 aprobadas.
- `python backend/tests/test_load_control.py`: 49 aprobadas en 95.315 s; regresión completa del flujo principal.
- `python -m py_compile` sobre servicio y rutas: aprobado.
- Build Vite directo: aprobado, 119 módulos. `npm run build` conserva el fallo de lanzamiento por ruta en este entorno; el mismo entrypoint invocado directamente compila.
- `git diff --check`: aprobado; sólo advertencias conocidas de futura normalización LF/CRLF.

No se ejecutaron concurrencia PostgreSQL, Android, QA visual en navegador/dispositivo ni Railway. Estas pruebas validan lógica local y compatibilidad API, no rendimiento productivo ni usabilidad física.

## Fase 5 — supervisión y alertas

- `python backend/tests/test_supervision_alerts.py`: 5 aprobadas. Verifica clave estable sin duplicados, reconocimiento, resolución, descarte, reapertura, motivo obligatorio, historial, permisos, alerta de pausa, faltante y segundo control.
- `python backend/tests/test_dashboard_quality.py`: 5 aprobadas después de integrar alertas.
- `python backend/tests/test_load_control.py`: 49 aprobadas en 106.592 s; regresión principal.
- Build Vite directo: aprobado, 119 módulos; sólo advertencias conocidas del bundle de voz.
- `py_compile` de la ruta y `git diff --check`: aprobados.

Pendientes: concurrencia PostgreSQL de las escrituras JSON, alcance por sucursal, SLA/umbrales aprobados, presencia real, QA visual y producción.

## Fase 6 — voz y dispositivos, alcance seguro

- `python backend/tests/test_device_telemetry.py`: 4 aprobadas. Verifica flag apagado sin escritura, allowlist, omisión de datos sensibles, duración/agregación, permisos y rango.
- `python backend/tests/test_load_control.py`: 49 aprobadas en 115.693 s.
- Node, ocho archivos de voz/utilidades: 25 aprobadas.
- Build Vite directo: aprobado, 120 módulos; advertencias conocidas de Vosk y carga dinámica.
- `py_compile` y `git diff --check`: aprobados.

No se pudo validar Android por la incompatibilidad Gradle/AGP ya documentada. Tampoco se probaron micrófono, auricular, bloqueo de pantalla, llamada entrante, Firebase real ni Railway. La captura permanece apagada hasta configurar explícitamente `DEVICE_TELEMETRY_ENABLED=1` y reiniciar el backend.

## Fase 7 — simulador y exportaciones

- `python backend/tests/test_capacity_reports.py`: 4 aprobadas. Fórmulas nominales, demanda/capacidad cero, límites, permisos, rango máximo, tres reportes, cantidad de filas reconciliada, BOM y neutralización de fórmula.
- Dashboard operación: 4 aprobadas; productividad: 5; calidad: 5.
- `python backend/tests/test_load_control.py`: 49 aprobadas en 135.239 s.
- Build Vite: aprobado, 121 módulos.
- `py_compile` y `git diff --check`: aprobados.

No se realizó una apertura manual en Excel/LibreOffice ni consumo real desde Power BI. Tampoco se ejecutaron pruebas de volumen PostgreSQL; los reportes operativos/calidad ya limitan detalle y la exportación exige máximo 366 días.

## Fase 8 — optimización y guardas

- `python backend/tests/test_performance_guards.py`: 2 aprobadas. Cada proyección ejecuta como máximo 8 consultas en el fixture; monitor, máximo 20; cada respuesta permanece debajo de 1 MB.
- Dashboard operativo: 4 aprobadas; alertas de supervisión: 5 aprobadas.
- `python backend/tests/test_load_control.py`: 49 aprobadas en 114.597 s.
- Build Vite: aprobado, 121 módulos y chunks por pantalla.
- Bundle inicial: 475.03→215.27 kB (−54.7%); gzip 134.52→72.94 kB (−45.8%).
- `py_compile` y `git diff --check`: aprobados.

Estos límites son guardas locales sobre fixture SQLite, no SLA de producción. Siguen pendientes PostgreSQL con volumen representativo, p95 real, dispositivo móvil, accesibilidad/QA visual y Railway.

## Cierre integral posterior a fases 1–8

Se ejecutaron secuencialmente todos los archivos `backend/tests/test_*.py` salvo `test_warehouse_concurrency.py`, que requiere el PostgreSQL descartable dedicado y destructivo definido por su fixture. Resultado: **153 pruebas backend aprobadas**.

También se aprobaron **39 pruebas** del conversor Python y **25 pruebas** Node de voz/utilidades. Total reproducible de cierre: **217 pruebas aprobadas**. El build Vite desde `frontend` aprobó con 121 módulos y división por rutas. Una invocación previa desde la raíz falló porque Vite buscó `index.html` en el directorio incorrecto; no fue un fallo del código y se repitió desde el directorio documentado.

`git diff --check` y `py_compile` resultaron satisfactorios. Persisten advertencias no bloqueantes de APIs de fecha/SQLAlchemy antiguas, catálogo Browserslist y tamaño del chunk Vosk. Android, concurrencia PostgreSQL, navegador/dispositivo físico y Railway continúan sin ejecutarse.
