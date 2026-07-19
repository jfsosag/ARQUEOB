from app.extensions import db


class Permiso(db.Model):
    __tablename__ = "permisos"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    modulo = db.Column(db.String(60), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("usuario_id", "modulo", name="uq_permiso_usuario_modulo"),
    )

    def __repr__(self) -> str:
        return f"<Permiso {self.modulo} u={self.usuario_id}>"
