# Sistema inteligente de analisis de consolidados, pallets y picking

Proyecto modular basado en Flask + React para una distribuidora de bebidas. Permite carga masiva de PDFs de consolidados, extraccion automatica de datos, deteccion de pallets completos, calculo de picking y trazabilidad historica.

## Tecnologias

- Backend: Python 3, Flask, SQLAlchemy, PostgreSQL, JWT, pdfplumber, OpenPyXL
- Frontend: React, TailwindCSS, React Router, Axios, Chart.js
- Infraestructura: Docker compatible con Railway

## Estructura

- `backend/`: API REST, modelos, procesamiento de PDF, importacion CSV y seguridad
- `frontend/`: SPA React con dashboard operativo
- `docker-compose.yml`: orquesta backend + PostgreSQL + frontend local

## Primeros pasos

1. Copiar `backend/.env.example` a `backend/.env`.
2. Configurar `DATABASE_URL`.
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

La URL local del frontend es `http://localhost:4173` y la API queda en `http://localhost:5000/api`.

## Modulos principales

- Autenticacion y roles
- Dashboard de KPIs operativos
- Carga masiva de PDFs
- Parser de consolidados PDF
- Logica de conversion a bultos y pallets
- Resultados: pallets completos vs picking manual
- Historial de operacion
- Gestion de articulos
