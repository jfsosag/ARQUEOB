from flask import request
from flask_login import current_user

from app.extensions import db
from app.models.auditoria import Auditoria


def registrar_accion(accion: str, modulo: str, descripcion: str = "") -> None:
    """Registra una acción en la tabla de auditoría.

    *No* ejecuta commit; el caller debe encargarse.
    """
    uid = current_user.id if current_user.is_authenticated else None
    ip = request.remote_addr if request else None
    entry = Auditoria(usuario_id=uid, accion=accion, modulo=modulo, descripcion=descripcion, ip=ip)
    db.session.add(entry)
