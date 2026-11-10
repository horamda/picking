# Diccionario de KPIs propuesto

Fecha: 2026-11-09. Diseño para aprobación; **no implementado ni configurado como objetivo oficial**.

Actualización fase 1: fórmulas, agregaciones y objetivos aún pendientes; sí se implementó captura de `measurement` en nuevas respuestas, con cantidades esperadas y factor de conversión junto a su procedencia. Los datos anteriores sin este bloque conservan cobertura desconocida y no se rellenan automáticamente. Un factor `catalog_at_confirmation` acredita el maestro al confirmar, no garantiza que fuera el factor histórico de importación. No mezclar ambas procedencias sin mostrar su cobertura.

Actualización fase 2: el centro de operaciones implementa conteos de planillas, avance por unidades de preparación, operarios con cronómetro en curso, bultos confirmados medibles, productividad preliminar, diferencias, cargas liberadas y alertas. La API devuelve cobertura. `operarios_disponibles`, `bultos_pendientes` y `cargas_demoradas` siguen nulos hasta disponer de heartbeat/jornada, factores históricos completos y horario comprometido. No hay objetivos ni semáforos oficiales configurados.

Actualización fase 3: productividad por operario y día implementada con modalidades separadas, tiempo activo/pausa, cobertura y diferencias atribuibles. La columna “líneas” representa productos respondidos dentro de tareas; no sustituye todavía el KPI de líneas originales de Chess. El total entre modalidades es informativo y no debe usarse como ranking hasta aprobar complejidad, pausas autorizadas y muestra mínima.

Actualización fase 4: exactitud de picking, diferencias de stock y retrabajo se calculan sobre productos respondidos en preparación, con numerador y denominador expuestos. La exactitud de segundo control por línea usa diferencias atribuibles específicamente a etapa 2; confirmar un faltante originado antes no es un error. La variante por unidades sigue `null` porque no existe cobertura histórica consistente. Las causas provienen de `error_type`, `shortage_reason` u origen como último recurso; su homologación operativa sigue pendiente.

Actualización fase 6: con el flag técnico habilitado se dispone de conteos de activación lista/fallida y reconocimiento aceptado/rechazado en web, además de duración de activación. Son diagnósticos, no productividad ni exactitud lingüística: “aceptado” significa que el parser produjo un comando, no que la acción física fuera correcta. La cobertura Android sigue ausente y debe mostrarse por separado.

Actualización fase 7: el simulador implementa las fórmulas documentadas con unidad bultos y etiqueta hipotética. Demanda cero deja cobertura nula; dotación o productividad cero dejan horas necesarias nulas; capacidad cero con demanda positiva no inventa dotación cuando no existe rendimiento por persona. Las exportaciones heredan las definiciones y cobertura de los builders, sin una segunda fórmula.

## Convenciones comunes

- Pedido: no hay entidad inequívoca de pedido comercial. Proponer inicialmente planilla/reparto como unidad, con etiqueta explícita y aprobación operativa.
- Línea: clave de producto dentro de tarea (`load_id`, cancha o pallet, etapa, `product_key`); conservar trazabilidad a líneas PDF. No intercambiar ambos conteos.
- Bulto preparado: cantidad física confirmada por servidor en preparación, sin volver a sumar controles. Informar bultos y unidades sueltas separados. Bulto equivalente sólo si se conoce el factor histórico: `bultos + unidades / unidades_por_bulto`.
- Tiempo efectivo: segundos activos de preparación / 3600; excluir pausas, controles, activos y procesos invalidados del denominador correspondiente. Separar retrabajo. Tareas sin tiempos válidos quedan fuera de productividad y se informa cobertura.
- Fecha de reparto y fecha de evento son dimensiones diferentes. Agrupación operativa en America/Argentina/Buenos_Aires; timestamps de intercambio en UTC con zona.
- División por cero o fuente ausente: valor no disponible con motivo, nunca un cero inventado. Publicar numerador, denominador, unidad y cobertura.
- No atribuir a personas stock, fallos técnicos, esperas externas o pausas autorizadas. Comparar modalidades y complejidad semejantes; no hay factor de complejidad oficial todavía.
- Reaperturas, refuerzos y controles legacy requieren deduplicación por proceso/producto; no contar `api_activity` como evento de producción.

## Fichas

Fuentes abreviadas: **C** = consolidados/detalles y snapshot; **E** = checks/answers/receipts de `control_camiones.state`; **T** = `timing()` y cronómetros; **I** = incidents/shortages/logs; **D** = dispatch, controles, activos y released_at; **N** = dato nuevo no disponible. Frecuencia objetivo: operación 5–15 s mediante polling sin solapamiento; históricos bajo demanda con rango acotado. Responsables propuestos, pendientes de aceptación.

| KPI / descripción | Fórmula y unidad | Fuente y disponibilidad | Frecuencia / responsable |
|---|---|---|---|
| Bultos por hora: producción efectiva | Σ bultos confirmados / Σ horas efectivas; bultos/h | E+T; agregación pendiente; equivalentes separados si factor disponible | Operativa / supervisión |
| Líneas por hora: velocidad de resolución | Líneas de preparación completas distintas / horas efectivas; líneas/h | E+T; definir línea completa frente a faltante | Operativa / supervisión |
| Tiempo por pedido: esfuerzo medio | Segundos activos atribuibles a planillas terminadas / planillas terminadas; min/planilla tras dividir por 60 | E+T+C; definición pedido pendiente; suma de personas no es duración de pared | Histórica / operaciones |
| Tiempo por cancha | Segundos activos de canchas terminadas / canchas terminadas / 60; min/cancha | E+T; excluir duplicación por pallets/refuerzos | Histórica / supervisión |
| Productividad individual | Bultos, líneas y planillas; horas activas, pausas y bultos/h por persona | E+T+I+users; no contar una planilla compartida como completada íntegra por cada persona | Operativa e histórica / supervisión |
| Exactitud picking | Líneas verificadas sin error de picking / líneas verificadas ×100; % | E+I; elegir control válido y no contar ambos controles; stock separado | Operativa e histórica / calidad |
| Diferencias stock | Líneas trabajadas con diferencia de stock / líneas trabajadas ×100; % | I+E; normalizar causas entre flujos | Operativa / inventario |
| Retrabajo | Líneas corregidas / líneas preparadas ×100; % | I+E; conservar primera incidencia y evitar duplicación por reenvíos | Histórica / calidad |
| Exactitud segundo control | Unidades verificadas correctamente / unidades verificadas ×100; % | E+I+C; factor histórico y criterio de cantidad correcta requeridos; error SKU/frescura no inferible sólo de diferencia numérica | Histórica / calidad |
| Planillas preparadas | Planillas con preparación completa / planillas programadas ×100; % | C+E+D; incluir pendientes sin iniciar; excluir canceladas según política documentada | Operativa / operaciones |
| Canchas finalizadas | Canchas con preparación completa / canchas requeridas ×100; % | E+C; separar canchas sin trabajo propio | Operativa / supervisión |
| Cargas listas a tiempo | Cargas liberadas antes o en límite / cargas con límite evaluable ×100; % | D+N horario comprometido; no disponible hoy | Operativa / despacho |
| Pedidos demorados | Planillas pendientes pasado límite; cantidad | C+E+N límite; universo debe incluir programadas | Operativa / despacho |
| Demora promedio | Σ max(0, liberación−límite) / cargas demoradas terminadas; minutos | D+N; mostrar demora en curso por separado | Histórica / despacho |
| Trabajos bloqueados | Conteo distinto de tareas no habilitadas, agrupado por causa | E+D; motivos ya parciales en monitor | Operativa / supervisión |
| Pendientes segundo control | Tareas con control 1 completo y control 2 incompleto; cantidad | E+D; distinguir pallet y cancha legacy | Operativa / control |
| Cumplimiento turno/sucursal | Misma fórmula de cumplimiento segmentada; % | E+D+N turno y alcance; sucursal existe en carga, no asignación personal | Operativa e histórica / operaciones |
| Operarios activos/disponibles | Personas con presencia vigente y estado operativo clasificable; cantidad | N heartbeat/jornada, E tareas; cuenta activa no basta | Operativa / supervisión |
| Comandos reconocidos/rechazados | Conteos y proporción por intento de reconocimiento | N telemetría de voz; no disponible | Agregación técnica / sistemas |
| Repeticiones y latencia voz | Repeticiones por tarea; mediana/p95 de tiempo de reconocimiento en ms | N telemetría; no medir con latencia HTTP | Técnica / sistemas |
| Fallos y conectividad dispositivos | Eventos por tipo y dispositivos con heartbeat vencido | push_devices sólo cubre avisos; N telemetría operativa | Técnica / sistemas |

## Filtros, objetivos, semáforos e histórico

Cada ficha heredará filtros fecha/rango, sucursal, turno, operario, camión, planilla y estado sólo cuando la dimensión esté respaldada. Añadir modalidad picking/pallet y complejidad documentada. Los filtros no disponibles deben indicar la causa; no ignorarlos silenciosamente. Semana y mes se calculan desde el mismo calendario acordado.

Cada KPI requiere catálogo con nombre, descripción, fórmula/versionado, unidad, fuentes, frecuencia, responsable, objetivo, período, sucursal, umbral y dirección de mejora. Objetivos inicialmente nulos: semáforo gris «sin objetivo». Umbrales y responsable aprobados habilitan verde/amarillo/rojo; calidad insuficiente mantiene gris. Objetivos y cambios conservan autor, fecha, valores anterior/posterior y motivo; no alterar retrospectivamente el objetivo de un período cerrado.

Histórico y exportaciones deben usar exactamente la misma fórmula y filtros que la pantalla, incluir fecha de extracción y cobertura. Exportación CSV/XLSX y consumo Power BI se proponen en fase 7; no existen hoy como suite KPI. No duplicar datos operativos sólo para alimentar BI.

## Simulador de capacidad propuesto

Variables separadas de operación: N operarios, H horas efectivas por persona, P productividad comparable en bultos/h, D demanda pendiente en bultos. `Capacidad=N×H×P`; `cobertura=capacidad/D×100`; `diferencia=capacidad−D`; `adicionales=max(0,ceil(D/(H×P))−N)`; `horas=D/(N×P)`. Entradas negativas se rechazan; denominadores cero se muestran como no calculables; demanda cero significa sin demanda, no cobertura infinita.

Comparar horas necesarias con tiempo efectivo restante hasta despacho. Complejidad y demoras modifican supuestos explícitos, no datos operativos. Líneas requieren una productividad independiente en líneas/h; no sumar líneas y bultos. Escenarios normal, alta demanda, menor dotación, mayor productividad y demoras mantienen visibles sus supuestos. Productividad histórica sólo con muestra y calidad suficientes; de lo contrario entrada manual etiquetada como hipótesis. Sin escrituras en pedidos o asignaciones.
