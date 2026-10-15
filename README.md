# Sistema inteligente de analisis de consolidados, pallets y picking

Proyecto modular basado en Flask + React para una distribuidora de bebidas. Permite carga masiva de PDFs de consolidados, extraccion automatica de datos, deteccion de pallets completos, calculo de picking y trazabilidad historica.

## Tecnologias

- Backend: Python 3, Flask, SQLAlchemy, PostgreSQL, JWT, pdfplumber, OpenPyXL
- Frontend: React, TailwindCSS, React Router, Axios, Chart.js
- Infraestructura: Docker compatible con Railway

## Estructura

- `backend/`: API REST, modelos, procesamiento de PDF, importacion CSV y seguridad
- `frontend/`: SPA React con dashboard operativo
- `docker-compose.yml`: ejecuta la aplicacion completa en el puerto 5001 usando PostgreSQL de Railway

## Primeros pasos

1. Copiar `backend/.env.example` a `backend/.env`.
2. Configurar `DATABASE_URL` con la conexión PostgreSQL de Railway. Desde la PC usar la URL pública del servicio PostgreSQL; la URL `*.railway.internal` solo funciona dentro de Railway.
3. Instalar backend: `pip install -r backend/requirements.txt`.
4. Instalar frontend: `npm install` dentro de `frontend/`.
5. Iniciar backend y frontend con Docker o localmente.

## PostgreSQL en Railway

1. Crear un proyecto desde el repo de GitHub usando el `Dockerfile` de la raiz.
2. Crear un servicio PostgreSQL en Railway.
3. En el servicio web, definir estas variables:
   - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
   - `SECRET_KEY=<valor_seguro>`
   - `JWT_SECRET=<valor_seguro>`
   - `INIT_DB_ON_STARTUP=1`
   - `ADMIN_USER=admin`
   - `ADMIN_PASSWORD=<valor_seguro>`
   - `FLASK_DEBUG=0`
4. El backend acepta la URL `postgresql://...` que entrega Railway y la convierte internamente al driver `psycopg`.
5. En produccion, el backend corre con Gunicorn y escucha el puerto entregado por Railway en `PORT`.

El frontend se compila dentro del mismo contenedor y Flask sirve la SPA. No hace falta crear un servicio separado para React.

Los articulos, historicos, PDFs y CSV subidos persisten en PostgreSQL. En Railway la app falla al iniciar si no existe `DATABASE_URL`, para evitar usar SQLite efimero y perder datos en cada deploy.

## Ejecucion local sin Docker

La ejecución local de prueba usa la misma base PostgreSQL de Railway. Definir en `backend/.env`:

```dotenv
APP_MODE=prueba
DATABASE_URL=postgresql://USUARIO:CLAVE@HOST_PUBLICO:PUERTO/railway
PORT=5001
```

Copiar el valor de `DATABASE_PUBLIC_URL` del PostgreSQL del proyecto correcto de Railway. No usar la URL interna desde la PC. Las credenciales de acceso a la aplicación son las de Railway, no las antiguas de SQLite. No guardar credenciales en Git. La interfaz muestra un aviso de base compartida en modo prueba.

Backend:

```powershell
cd backend
pip install -r requirements.txt
python app.py
```

Frontend:

```powershell
cd frontend
npm install
node node_modules\vite\bin\vite.js --host 0.0.0.0
```

La URL local del frontend es `http://localhost:4173` y la API queda en `http://localhost:5001/api`.
Si el frontend ya esta compilado (`npm run build` dentro de `frontend/`), tambien podes abrir la aplicacion en `http://localhost:5001` ejecutando solo el backend. El puerto local predeterminado es 5001 y se puede cambiar con la variable `PORT`.

## Modulos principales

- Autenticacion y roles
- Dashboard de KPIs operativos
- Carga masiva de PDFs
- Parser de consolidados PDF
- Logica de conversion a bultos y pallets
- Resultados: pallets completos vs picking manual
- Historial de operacion
- Gestion de articulos


## Control de cargas integrado

Abrir **Operacion > Control de cargas** (`/operacion?tab=control`). El enlace anterior `/control-cargas` redirige a esa misma seccion. Reutiliza los PDFs y repartos de **Carga PDF**, las cantidades originales, los usuarios, los roles, la base PostgreSQL y la auditoría de Picking. No se ejecuta el servidor FastAPI de `control_cargas_mvp` ni se vuelven a importar los PDF. Esa carpeta queda como referencia del piloto.

- Elegir un reparto ya cargado. Se conserva una instantánea del detalle para auditar qué se verificó. Agrupa SKU repetidos dentro de cada cancha, manteniendo el orden y referencias a las líneas originales. Usa los detalles que conserva el importador existente. Los SKU excluidos durante la importacion no aparecen en esos detalles ni se recuperan automaticamente desde el PDF.
- Iniciar picking (si se prepara desde la aplicación), control 1 y control 2. Cada proceso registra usuario, inicio, fin y tiempo activo. El segundo control exige otra persona. Picking ya realizado puede omitirse, en cuyo caso no se inventa un tiempo de preparación.
- Pausar y reanudar; cada usuario tiene como máximo un temporizador activo. Al cerrar el navegador sin pausar, el tiempo sigue corriendo. Las reservas se recuperan con el mismo usuario; supervisor/administrador puede reabrir una cancha con motivo, conservando tiempos e historial.
- Registrar correctos, errores corregidos o faltantes. Las incidencias exigen responsable y origen (picking/control); se distingue quién detectó el problema de a quién se asignó. La confirmación del mismo faltante en control 2 no duplica la incidencia. Las incidencias informadas quedan conservadas aunque después se marque el producto como correcto; las modificaciones quedan en auditoría.
- Si el segundo control no coincide con el faltante inicial, un supervisor debe reabrir la cancha y repetir ambos controles. Una reapertura invalida activos ya registrados y preserva la auditoría.
- Registrar activos por camión, con operador y tiempo. La liberación **en la aplicación** requiere todos los repartos del camión/fecha/depósito, doble control, activos y faltantes autorizados. La autorización del faltante y la confirmación del ajuste manual en Chess son acciones distintas. No se modifica Chess automáticamente.
- Pantalla operativa adaptable a celular/tablet: botones táctiles, un producto a la vez, cantidades grandes y temporizador visible. Supervisores y administradores disponen de tiempos por usuario/proceso, incidencias, trazabilidad y usuarios en la vista de escritorio.

Las tablas de control existentes son `control_camiones`, `control_planillas` y `control_temporizadores`. El arranque contra PostgreSQL, tanto en modo prueba como produccion, verifica tablas y columnas sin ejecutar `create_all`, ajustes de esquema ni semillas. El importador de articulos tampoco modifica el esquema. Las bases temporales de pruebas conservan su inicializacion aislada. Las reservas y escrituras concurrentes usan restricciones unicas y version de registro.

El alta de usuarios usa una unica implementacion en `backend/services/users.py`. La interfaz llama a `/api/auth/register`; `/api/load-control/users` conserva compatibilidad. Ambas rutas requieren administrador y contrasenas nuevas de al menos 10 caracteres. Las cuentas y contrasenas existentes no cambian.

### Migraciones y respaldo

La revision inicial Alembic `20261015_01` verifica la estructura existente de las 13 tablas y registra su version. No crea ni reemplaza tablas de la aplicacion. Requiere una base existente o una restauracion de respaldo; no usar `stamp` para omitir la validacion.

El 15/10/2026 se genero un respaldo `pg_dump` de Railway, se restauro en PostgreSQL 18 temporal y se ensayaron dos ejecuciones de la revision. Las huellas de todos los registros de las 13 tablas permanecieron iguales. El archivo y el manifiesto de verificacion estan en `.backups/`, excluido de Git. Este respaldo local no sustituye una politica de respaldos periodicos fuera de esta PC.

Las migraciones exigen `MIGRATION_DATABASE_URL` explicita y no cargan automaticamente la conexion del `.env`. Desde la raiz:

```powershell
python -m alembic -c backend/alembic.ini current
python -m alembic -c backend/alembic.ini upgrade head
```

Antes de cada revision nueva, verificar respaldo recuperable, revisar el cambio y ensayarlo sobre una restauracion. La revision inicial no admite una reversa que borre tablas. El vinculo `control_planillas.source_id` se conserva sin agregar una clave foranea: primero debe definirse como mantener el historial si se elimina un consolidado desde el modulo existente.

Las pruebas cubren controles, tiempos, diferencias, permisos, usuarios, consultas de operacion/historial/dashboard y la importacion real de PDF sinteticos (varios repartos, paginas continuadas, duplicados, exclusiones, cantidades, descarga y errores con rollback). No reemplazan la verificacion visual en dispositivos reales.

### Verificación aislada

```powershell
pip install -r backend/tests/requirements.txt
python backend/tests/test_load_control.py
cd frontend
npm run build
```

La suite crea una base temporal independiente con `ALLOW_SQLITE_FOR_TESTS=1`; nunca ejecuta sus fixtures contra Railway. SQLite está deshabilitado en la ejecución normal, incluso en modo prueba. No configurar `ALLOW_SQLITE_FOR_TESTS` en Railway ni en `backend/.env`.

Con Docker: `docker compose up --build` desde la raiz. Usa `backend/.env` y abre `http://localhost:5001`; no crea una base PostgreSQL local.
