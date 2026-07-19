"""Crea el usuario administrador inicial.

Uso:
    flask --app wsgi seed-admin
"""
import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models.usuario import Usuario


@click.command("seed-admin")
@with_appcontext
def seed_admin():
    """Crea un usuario admin si no existe ninguno."""
    if db.session.scalar(db.select(Usuario).where(Usuario.username == "admin")):
        click.echo("El usuario 'admin' ya existe.")
        return

    admin = Usuario(
        nombre_completo="Administrador",
        username="admin",
        email="admin@arqueob.local",
        is_active=True,
        is_admin=True,
    )
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.commit()
    click.echo("Usuario admin creado: admin / admin123")
