# Cargas seleccionadas y cola de camiones

## Operación

1. Administración importa el PDF en Importaciones. Se usa la **fecha de reparto**, no la fecha en que se subió el archivo.
2. En **Supervisión → Planificar cargas**, elegir esa fecha, marcar los repartos y ordenar los camiones con las flechas. Guardar selección y orden.
   Al marcar repartos se recalculan HL y pallets completos/de picking, antes de guardar. Sin capacidad configurada se calcula la cantidad necesaria, pero no se afirma que entre en el camión. Si faltan artículos o factores, se muestran subtotales parciales y los SKU pendientes; nunca se completan con valores supuestos.
3. Para cada camión seleccionado, revisar la capacidad física, simular los pallets y aprobar el plan. Cambiar sus repartos invalida el plan anterior.
4. Android 0.7 y la web muestran el camión actual del operario. Los repartos permanecen separados y se muestran solamente sus canchas asignadas.
5. Al finalizar todas sus tareas del camión, el operario recibe el siguiente. No espera las canchas de otros operarios, los pallets completos ni los controles. El palletizador tiene su propia progresión por etapa 4.

El resumen incluye solamente los repartos seleccionados de ese camión: bultos, unidades, HL, canchas, repartos y pallets físicos previstos frente a la capacidad. Debajo se distingue el trabajo propio. Los pallets completos se registran aparte de los remanentes de picking.

La distribución identifica los pallets de picking como M001, M002, etc. Estos identificadores se conservan entre repartos del mismo camión. Si se permite mezclar canchas, un mismo pallet puede aparecer para varios operarios; **no se deben sumar esos contadores individuales** para obtener el total del camión.

La estimación usa la equivalencia de bultos del catálogo. No comprueba altura, peso, estabilidad ni compatibilidad de apilado: el supervisor debe revisar físicamente antes de aprobar. Los HL se calculan con el factor HECTOLITROS del catálogo por bulto y las unidades por bulto. Si faltan factores, se informa volumen incompleto.

## Seguridad y compatibilidad

- La API verifica selección, orden, rol, asignación de cancha y aprobación al iniciar. No basta con ocultar botones.
- La selección y orden se guardan en el JSON existente de `control_camiones`; no se agregan tablas ni migraciones.
- Se conservan tiempos, respuestas, auditoría y reportes anteriores. El nuevo monitor muestra solamente los repartos seleccionados de los camiones configurados.
- El orden queda fijo hasta el último camión que haya empezado. Se pueden ordenar o agregar los posteriores. Reasignar recursos continúa usando la asignación de canchas existente.
- Dos supervisores no pueden sobrescribir la selección del otro. Las confirmaciones ordinarias de productos no invalidan la edición de la cola.
- Las reservas anteriores siguen siendo retomables. Al configurar la primera cola, los trabajos nuevos de operadores usan la selección explícita.
- Finalizar picking conserva la regla anterior: se permite finalizar con productos sin registrar; el monitor lo advierte. El avance de cola se basa en la finalización de la tarea, no en un conteo de respuestas.
- El importador acepta productos sin vencimiento y limita cantidades a las columnas A CARGAR, excluyendo DESCARGA y las tablas de envases vacíos. No reescribe importaciones históricas.

## Validación

- Backend: 34 pruebas del flujo de cargas, incluidas selección, exclusión, aprobación, HL, pallets compartidos, vista previa sin escrituras ni capacidad configurada y avance individual entre varios repartos.
- PostgreSQL local descartable: dos supervisores concurrentes (uno recibe conflicto) y 10 operarios confirmando simultáneamente sin pérdida de respuestas.
- Parser PDF: tres regresiones de columnas y vencimiento opcional; planificación: cinco pruebas.
- Frontend: 20 pruebas y build; navegador con API simulada, selección de checkboxes y resumen a 390 px sin desbordamiento.
- Android: seis pruebas unitarias, lint y APK; emulador con navegación, faltantes, resumen/distribución y carga del modelo Vosk.

La prueba de trabajo real, audio y ruido de depósito requiere el teléfono físico y cargas aprobadas por el supervisor. No se cargan ni se aprueban documentos de producción durante estas pruebas.
