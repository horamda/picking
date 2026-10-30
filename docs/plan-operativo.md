# Plan operativo integral

## Avance verificado al 30/10/2026

- Publicados en la rama de trabajo y Railway: comprobantes de respuestas para recuperación, verificación del SKU completo, advertencias de tiempos mayores a 12 horas y registro de teléfonos autenticados.
- Android 0.14.1 publicado. Firebase configurado en un worker separado; migración de dispositivos aplicada con autorización. API y worker en SUCCESS. Falta probar entrega en un teléfono real.
- Pruebas: 40 de flujo backend, 4 de notificaciones, 3 de concurrencia/migración en PostgreSQL local (10 operarios), 10 Android y 7 de parser web; builds y lint Android correctos.
- Decisión del usuario: verificar todos los dígitos del SKU. Sin impresora ni datos de peso/altura: mantener simulación revisada por supervisor, sin afirmar ajuste físico garantizado.
- Pendiente del plan integral: pedidos de ayuda y seguimiento de faltantes, investigación/corrección auditada de tiempos históricos, aviso de actualización dentro de Android, revisión final del simulador y aceptación completa en el depósito. El enlace de descarga administrativo ya apunta a 0.14.1.

Mantener Flask/PostgreSQL, React y Android nativo. Rama feature/voz-picking; sin PR ni cambios de esquema implícitos. Preservar reportes y auditoría.

## Orden y criterios de cierre

1. Estados y confiabilidad: distinguir ausencia de tareas, espera, reserva ajena, pausa y desconexión. Cada respuesta debe tener un identificador único; poder consultar si se guardó y reintentar sin duplicarla. No anunciar guardado sin confirmación del servidor.
2. Tiempos: investigar duraciones anómalas y mostrar advertencias sin alterar registros históricos. Definir pausas y medir demoras de red separadamente de trabajo.
3. Verificación: código de producto/ubicación y etiquetas de pallets únicas por camión y fecha; mantener trazabilidad de reparto y cancha. Modalidad de verificación y disponibilidad de impresora pendientes de respuesta del usuario.
4. Excepciones: ayuda con motivos y seguimiento de faltantes, responsable y resolución auditada visibles al supervisor.
5. Distribución: aviso de versión Android y descarga oficial; notificaciones de nuevas tareas. Firebase aprobado para configurar m?s adelante; avisos actuales con la pantalla de tareas abierta. No afirmar funcionamiento con app cerrada hasta configurar y probar Firebase.
6. Pallets: validar capacidad, peso, altura y compatibilidad cuando exista información. No presentar equivalencia de bultos como validación física.
7. Prueba integral: PDF, selección y aprobación, dos operarios, reservas simultáneas, faltante, respuesta perdida/reintento, pausa, controles y cierre. PostgreSQL de prueba aislado; pruebas acústicas y físicas en el depósito.

## Límites

- La confirmación de faltantes sigue siendo manual.
- Ninguna prueba automática escribe sobre cargas reales.
- Cambios de esquema deben prepararse y presentarse antes de solicitar autorización para aplicarlos.
- Trabajo sin conexión requiere persistencia, deduplicación y resolución de conflictos; no se habilita una cola de escrituras sin esos controles.
