from datetime import datetime, timezone
from app.extensions import db


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(160), nullable=False, index=True)
    telefono = db.Column(db.String(40), nullable=False, index=True)
    direccion = db.Column(db.String(255), nullable=False)
    rnc_cedula = db.Column(db.String(40), unique=True, nullable=True, index=True)
    observaciones = db.Column(db.Text, nullable=True)
    saldo_a_favor = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    creado_en = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    facturas = db.relationship("Factura", back_populates="cliente", cascade="all, delete-orphan")
    pagos = db.relationship("Pago", back_populates="cliente", cascade="all, delete-orphan")
    cobros_informales = db.relationship("CobroInformal", back_populates="cliente", cascade="all, delete-orphan")

    @property
    def saldo_pendiente(self):
        return sum(f.saldo for f in self.facturas)
