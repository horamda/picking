# Control de Cargas — MVP piloto Casa Central

Aplicación web móvil con FastAPI y SQLite/PostgreSQL. **Versión piloto, no apta para liberaciones reales sin validación operativa y controles de seguridad adicionales.**

## Qué incluye

- Usuarios y contraseñas individuales; perfiles administrador, supervisor, controlador.
- Importación múltiple de PDF ChessERP v6 (PDF con texto seleccionable, **no escaneado**). El importador rechaza documentos con líneas ambiguas.
- Agrupación de SKU repetidos **dentro de la misma cancha**, manteniendo las líneas originales en la base de datos.
- Selección libre de cancha, productos en orden Chess, dos controles independientes por personas distintas.
- Reservas por etapa, respuestas correctas, diferencias corregidas y faltantes reales.
- Faltantes: supervisor autoriza que viaje menos mercadería; **ajuste Chess permanece pendiente** y se confirma manualmente. Ninguna operación modifica Chess.
- Activos de salida: carga manual por camión al completar todas las planillas; no incluye regreso.
- Liberación automática **solo en la aplicación**, al completar todos los controles, registrar activos y autorizar faltantes.
- Supervisores pueden reabrir una cancha antes de liberación; reinicia sus dos controles.

## Ejecutar en la PC

Requiere Python 3.11+, `pdftotext` (Poppler) y dependencias de Python.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
# Configurar entorno en su terminal o mediante Railway:
# SECRET_KEY=<cadena aleatoria de 32+ caracteres>
# ADMIN_USER=admin
# ADMIN_PASSWORD=<clave inicial robusta>
uvicorn main:app --reload
```

Abrir http://127.0.0.1:8000. Crear controlador y supervisor desde **Usuarios**. El primer administrador solo se crea cuando está definida `ADMIN_PASSWORD`, al inicializar la base.

## Railway

Crear proyecto desde repositorio GitHub; agregar servicio PostgreSQL y vincular `DATABASE_URL`. Definir `SECRET_KEY`, `ADMIN_USER`, `ADMIN_PASSWORD`. Para el importador, el servicio necesita Poppler. Incluir el Dockerfile provisto (instala `poppler-utils`). Usar HTTPS y acceso limitado al piloto.

## Límites y tareas antes del uso productivo

1. **Revisar lectura PDF contra muestras de las tres sedes**, unidades sueltas, SKU repetidos y productos sin vencimiento.
2. PDF deja un snapshot de Chess; los cambios posteriores en facturación/reparto deben reconciliarse por un responsable.
3. Faltante autorizado no es ajuste automático de stock ni factura. Hay que resolverlo desde Chess.
4. Validar nombres de activos contra el formulario Excel original; la lista se puede editar en `ASSET_NAMES`.
5. Falta recuperación de cuenta, cambio de contraseña, bloqueo por intentos, expiración/renovación configurable y autorización granular de sucursales.
6. Reservas permanecen tomadas si se abandona el control; falta mecanismo de liberación por supervisor.
7. Sin modo offline: una acción solo queda guardada si el servidor confirma.
8. Falta reconciliar discrepancias del segundo control cuando un faltante se corrige o cambia físicamente.
9. Faltan pruebas de concurrencia de alta carga, respaldo/restore, monitoreo y flujo formal de salida real.
10. Reapertura tras liberación no está permitida en MVP: debe gestionarse mediante incidencia operativa.

## Prueba del PDF proporcionado

Para `00067813`, se detectan canchas 1–6 y **7 SKU en cancha 5, 23 bultos**. El SKU Rockstar 24118 se consolida en cancha 2 (3 bultos).
