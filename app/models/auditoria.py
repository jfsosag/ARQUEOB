from datetime import datetime, timezone

from app.extensions import db


class Auditoria(db.Model):
    __tablename__ = "auditoria"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True)
    fecha = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    accion = db.Column(db.String(60), nullable=False)
    modulo = db.Column(db.String(60), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    ip = db.Column(db.String(120), nullable=True)

    usuario = db.relationship("Usuario", backref="auditorias", lazy="joined")

    def __repr__(self) -> str:
        return f"<Auditoria {self.accion} {self.modulo}>"
