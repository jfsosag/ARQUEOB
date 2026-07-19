# Plan de migración y operación

## Fases realizadas

1. **Inventario y compatibilidad.** El monolito original fue reemplazado por una app factory con Blueprints. Los conceptos de arqueo, conduce y recibo se conservan, con rutas y PDFs implementados dentro de sus módulos.
2. **Datos y configuración.** SQLite deja de ser una dependencia de la aplicación. Los modelos SQLAlchemy describen clientes, facturas, pagos, detalle de pagos, arqueos y conduces. La conexión se toma exclusivamente de `DATABASE_URL`.
3. **Cuentas por cobrar.** Clientes, facturas en lote, pagos aplicados por factura, saldo y estados se manejan transaccionalmente. El pago actualiza el estado de cada factura y conserva su detalle.
4. **Experiencia de uso.** Se agregó dashboard, navegación responsive, Bootstrap 5, toasts, confirmación de eliminación, búsqueda de clientes y reportes PDF profesionales.

## Puesta en marcha PostgreSQL

1. Cree una base de datos PostgreSQL y un usuario con permisos sobre ella.
2. Copie `.env.example` a `.env` y cambie `DATABASE_URL` y `SECRET_KEY`.
3. Cree el entorno e instale dependencias: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`.
4. Cree y aplique la migración inicial:

   ```bash
   .venv/bin/flask --app wsgi db init
   .venv/bin/flask --app wsgi db migrate -m "esquema inicial"
   .venv/bin/flask --app wsgi db upgrade
   ```

5. Ejecute ` .venv/bin/python app.py` y abra `http://127.0.0.1:5000`.

## Migración de los datos históricos

Los registros del `arqueo.db` anterior no se eliminan automáticamente. Antes de retirar el sistema legado, exporte la información que desee conservar y cárguela en PostgreSQL mediante un script de importación revisado. La aplicación nueva no abre ni escribe SQLite.

## Siguientes pasos de producción

- Definir usuarios y autenticación antes de desplegar para sustituir el valor temporal de `usuario` en los pagos.
- Usar Gunicorn/uWSGI detrás de un proxy TLS y mantener `DEBUG=False`.
- Ejecutar `flask db migrate` y `flask db upgrade` con cada cambio de modelo.
