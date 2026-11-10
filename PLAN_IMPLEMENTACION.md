# Plan de implementación seguro

Fecha: 2026-11-09. **Plan aprobado por el usuario; fases 1–4, los alcances compatibles de fases 5–6 y fases 7–8 implementados localmente**. Se mantienen las puertas específicas para migraciones, cambios de arquitectura y producción. Las validaciones externas y fuentes faltantes continúan pendientes.

## Criterios generales

Mantener rutas y campos consumidos por Android/web. Reutilizar identidad, controles, instantáneas, logs y polling. Agregar pruebas por comportamiento, flags de nuevas vistas cuando corresponda y rollback por fase. Ningún dato desconocido se representa como medición real. No eliminar históricos ni ajustar Chess automáticamente.

## Secuencia y aceptación

| Fase | Cambio propuesto y reutilización | Criterio de aceptación y pruebas | Reversión |
|---|---|---|---|
| 0 Auditoría | Documentos de esta entrega; matriz de código y límites | Pruebas disponibles registradas, sin cambios funcionales; decisión del usuario sobre plan | Retirar sólo documentos nuevos si se solicita |
| 1 Instrumentación | Inventario campo/evento en logs/checks; identificar huecos por cliente; agregar sólo metadatos faltantes con contratos aditivos | Un mismo request_id no duplica evento; causa stock no penaliza; reenvío conflictivo 409; histórico legacy legible; pruebas API/voz vigentes | Desactivar captura nueva; conservar eventos recogidos |
| 2 Dashboard | Ampliar DashboardPage y agregadores existentes; reutilizar monitor, filtros y polling; volumen planificado separado de confirmado | Totales reconciliados con fixtures: carga pendiente sin check, varios repartos, SKU/frescura, faltante, refuerzo, reapertura; sin doble conteo; móvil 360 px y escritorio; errores visibles | Flag de tarjetas nuevas apagado; dashboard previo operativo |
| 3 Productividad | Agregación de E/T, segmentación modalidad, cobertura, pausas y calendario | Divisiones por cero, tiempo sin zona/medianoche, pausas, >12 h, planillas compartidas y legacy; no ranking punitivo por stock | Desactivar métricas nuevas sin alterar checks |
| 4 Calidad | Ampliar faltantes/control existente; homologar taxonomía y detector/responsable/autorizador; métricas de calidad | Control 2 independiente, discrepancia no libera, errores stock sin atribución automática; auditoría y autorizaciones; prueba de compatibilidad de ambos flujos | Desactivar vistas; preservar incidencias y decisiones |
| 5 Supervisión | Estados de alertas, deduplicación, umbrales, excepciones, presencia y límites de despacho previamente definidos | Permisos servidor y accesos entre sucursales; transiciones auditadas, descarte con motivo, alerta única por entidad/tipo/período | Desactivar generación/visualización; conservar historial |
| 6 Voz/dispositivos | Ampliar configuración y registro push con diagnóstico técnico mínimo; no audio persistente; comunicación opcional por etapas | Android real, auricular/micrófono, interrupciones y reconexión; fallar telemetría/mensajería no interrumpe picking; permisos y minimización | Flags telemetría/comunicación apagados; picking actual intacto |
| 7 Simulador/reportes | Simulador separado de planificación pallets; exportaciones y endpoints acotados para BI; objetivos con historial | Fórmulas límite, escenarios etiquetados, CSV seguro, Excel reconciliado, autorización/rango/paginación, igualdad pantalla/exportación | Desactivar vistas/exports nuevos, no borrar configuración |
| 8 Optimización | Medir en clon consultas, tamaño JSON, locks, bundles y UX; optimizar sólo con evidencia | Regresión integral, concurrencia PostgreSQL, p95 y errores antes/después, validación móvil; no carga intensiva productiva | Volver al código compatible y flags previos; índices sólo según plan aprobado |

## Puertas previas a cambios sensibles

1. Aprobación del plan por el usuario, tal como exige el apartado 28 del pedido: recibida en conversación el 2026-11-09.
2. Corregir en trabajo aprobado la incompatibilidad del toolchain Android y obtener línea base crítica satisfactoria antes de dar por terminado cualquier cambio móvil.
3. Validar definiciones: pedido/planilla, grano de línea, turnos, sucursales, personas con acceso y objetivos. Ningún rol nuevo se crea por inferencia.
4. Si se necesita esquema nuevo: inventario físico de sólo lectura, respaldo verificable y restauración ensayada; propuesta DDL revisable y aprobación específica. No ejecutar `upgrade head` sobre base compartida como parte de pruebas.
5. Producción: candidato validado en entorno aislado, resultados y reversión disponibles; aprobación explícita de despliegue. Esta fase no prepara ni realiza despliegue.

## Offline y comunicación: propuestas previas obligatorias

Offline no debe confundirse con reconocimiento Vosk local o recuperación de una respuesta incierta. Diseñar después de fase 1 una cola cifrada con identidad de usuario/servidor/dispositivo, UUID estable, versión de tarea, secuencia, estado local/pendiente/confirmado/rechazado/revisión, política de caducidad y manejo de cambio de usuario. La API actual de recibos se reutiliza; no puede finalizar/liberar una tarea con operaciones pendientes. Probar dos dispositivos, reasignación, logout, reloj incorrecto, muerte de proceso y reenvío tras cambio de estado. El almacenamiento, permisos y migraciones requieren revisión antes de activar.

Mensajería: reutilizar Firebase como aviso de disponibilidad, con contenido autorizado consultado a API y recibos separados. Primera opción, texto y asistencia sin ocupar micrófono. Audio bidireccional sólo tras diseño de exclusión de recursos con Vosk/TTS, prioridad de picking y prueba de fallo. Todo opcional y deshabilitable.

## Próximo incremento concreto sugerido

Tras aprobación, cerrar definiciones y pruebas de agregación para planillas, preparación, controles y tiempos usando datos existentes. Entregar primero indicadores con cobertura verificable en el dashboard actual; presencia, demoras y voz quedan «no disponible» hasta instrumentación aprobada. No crear una nueva aplicación, un segundo control ni una tabla genérica de eventos redundante.

## Avance de fase 1

Se agregaron contexto de medición y correlación de proceso sobre respuestas/logs existentes, sin tablas ni endpoints nuevos. Se corrigió la atribución automática de stock en preparación y la colisión de incidentes por frescura en pallets. El inventario de campos y eventos actualizado está en `ARQUITECTURA_PICKEARYA.md`; pruebas y reversión, en sus documentos correspondientes. No se modificaron clientes móviles ni se implementó telemetría de voz/dispositivo: sus fuentes siguen explícitamente desconocidas.

## Avance de fase 2

Se agregó una proyección de sólo lectura en `/api/dashboard/operations` y se amplió `DashboardPage` sin sustituir el dashboard anterior. Presenta los 14 indicadores solicitados; disponibilidad, bultos pendientes y demoras permanecen `null` con explicación porque sus fuentes no existen. El detalle usa preparación real, excluye controles como volumen adicional, limita la tabla a 100 filas e informa el total. Polling secuencial cada 15 segundos, cancelación al cambiar filtros y conservación del último dato ante error.

Filtros operativos: fecha/rango, sucursal, camión, planilla, operario y estado. Turno sigue pendiente de modelo. El bloque histórico de importación aplica sólo fecha, sucursal y planilla; la UI explica la diferencia. Sin DDL, dependencias ni cambios Android.

## Avance de fase 3

`/api/dashboard/productivity` agrega preparación por operario usando checks vigentes de etapas 0 y 4. Informa bultos confirmados medibles, productos respondidos, tiempos activos, pausas, tareas finalizadas, participación en planillas, diferencias atribuibles, cobertura y evolución diaria. Picking y pallets completos se separan por modalidad; los controles 1/2 y stock quedan fuera de la productividad personal. La interfaz consume la proyección con los filtros de fase 2.

El total combinado se etiqueta como informativo: todavía no existe factor oficial de complejidad. Los timestamps legacy incompatibles no interrumpen el reporte; conservan cantidades y dejan la tasa sin calcular. Sin migraciones ni cambios al flujo de picking.

## Avance de fase 4

`/api/dashboard/quality` agrega calidad usando respuestas e incidencias existentes. Separa errores atribuibles al picking de diferencias de stock, limita retrabajo a correcciones de origen picking y calcula el segundo control por diferencias atribuibles a esa etapa, de modo que confirmar un faltante no lo penaliza. La granularidad actual es producto respondido; la exactitud por unidades se mantiene indisponible con causa explícita.

Los faltantes de cancha y pallet admiten revisión, solicitud de recuento y rechazo con motivo obligatorio e historial aditivo. Autorizar y confirmar el ajuste manual en Chess mantienen las rutas y reglas existentes. No se elimina el faltante al rechazarlo ni se libera automáticamente una carga. Sin DDL, paquetes, cambios Android o despliegue.

## Avance de fase 5

El monitor genera una alerta vigente por combinación entidad/tipo para condiciones verificables: planificación pendiente, segundo control pendiente, faltante sin autorización y proceso pausado. El estado de gestión se superpone sin alterar la condición operativa y conserva todas las transiciones. Reconocer no exige comentario; resolver, descartar y reabrir exigen motivo.

La supervisión muestra alertas activas e históricas todavía vigentes, con severidad descriptiva y último cambio. No se implementaron alertas de demora, presencia o límite de despacho porque faltan horario comprometido, heartbeat y umbrales aprobados. El modelo actual tampoco asigna sucursales a usuarios; se mantienen los permisos globales existentes de administrador/supervisor en lugar de inferir aislamiento.

## Avance de fase 6

La web reporta eventos técnicos mínimos de voz mediante una llamada de mejor esfuerzo con timeout corto. Un fallo de red, validación o servidor se ignora deliberadamente en el cliente y nunca cambia el comando ni la respuesta de picking. El backend sólo escribe si `DEVICE_TELEMETRY_ENABLED=1`; apagado responde satisfactoriamente sin registrar.

La supervisión puede consultar conteos, plataforma y latencia media/máxima, sin contenido reconocido ni identidad del equipo. Android queda sin cambios hasta corregir su toolchain y ejecutar la matriz física obligatoria. No se agregó mensajería ni audio bidireccional; Firebase conserva únicamente los avisos de tarea existentes.

## Avance de fase 7

El simulador aplica `capacidad=N×H×P`, cobertura, diferencia, operarios adicionales y horas requeridas con manejo explícito de denominadores cero. Todos los resultados declaran unidad e hipótesis y no se persisten. No reutiliza ni modifica el simulador físico de pallets.

Las exportaciones de operación, productividad y calidad llaman a los mismos builders que la pantalla. Exigen fecha desde/hasta, máximo 366 días, permisos del dashboard y neutralización de prefijos de fórmula. Incluyen cantidad de filas y fecha de extracción en cabeceras HTTP. XLSX, objetivos persistentes y conexión directa BI quedan fuera para evitar contratos o dependencias no aprobadas.

## Avance de fase 8

La medición local confirmó que el bundle inicial incluía todas las pantallas. La división por rutas redujo más de 45% el tamaño inicial comprimido sin cambiar URLs ni componentes. Vosk ya estaba diferido y se conserva separado para no cargar 5.79 MB hasta activar voz.

El monitor repetía consultas de rol y canchas por trabajador; ahora precarga roles y agrupa asignaciones. Las pruebas fijan techos de consultas y 1 MB de respuesta para detectar crecimiento accidental. No se propusieron índices porque no hubo perfil PostgreSQL representativo; optimizar esquema sin evidencia violaría las puertas del plan.
