from datetime import datetime, timezone

import bcrypt
from flask_login import UserMixin

from app.extensions import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre_completo = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(200), nullable=True)
    telefono = db.Column(db.String(40), nullable=True)
    password_hash = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)

    permisos = db.relationship("Permiso", backref="usuario", lazy="dynamic", cascade="all, delete-orphan")

    # ---- password helpers ----
    def has_password(self) -> bool:
        return bool(self.password_hash)

    def set_password(self, raw: str) -> None:
        self.password_hash = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

    def clear_password(self) -> None:
        self.password_hash = None

    def check_password(self, raw: str) -> bool:
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(raw.encode(), self.password_hash.encode())
        except (ValueError, TypeError):
            return False

    # ---- permission helpers ----
    def tiene_permiso(self, modulo: str) -> bool:
        if self.is_admin:
            return True
        return self.permisos.filter_by(modulo=modulo).first() is not None

    def modulos_permitidos(self) -> list[str]:
        if self.is_admin:
            return ["dashboard", "clientes", "cobros", "cobros_informales", "arqueo", "conduces", "reportes", "configuracion"]
        return [p.modulo for p in self.permisos]

    def touch_login(self) -> None:
        self.last_login = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<Usuario {self.username}>"
