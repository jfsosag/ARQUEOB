"""Guía de inicialización para el esquema PostgreSQL.

No crea tablas directamente: Flask-Migrate/Alembic mantiene el historial de
migraciones. Configure DATABASE_URL en .env antes de ejecutarlo.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("DATABASE_URL"):
    sys.exit("DATABASE_URL no está configurada. Copie .env.example a .env.")

print("Ejecute los siguientes comandos una única vez:")
print("  flask --app wsgi db init")
print("  flask --app wsgi db migrate -m 'esquema inicial'")
print("  flask --app wsgi db upgrade")
