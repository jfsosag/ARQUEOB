import enum
from datetime import date, datetime, timezone
from decimal import Decimal
from app.extensions import db


class EstadoFactura(enum.StrEnum):
    PENDIENTE = "Pendiente"
    PARCIAL = "Parcial"
    PAGADA = "Pagada"


class Factura(db.Model):
    __tablename__ = "facturas"
    __table_args__ = (db.UniqueConstraint("cliente_id", "numero", name="uq_factura_cliente_numero"),)

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)
    numero = db.Column(db.String(60), nullable=False, index=True)
    concepto = db.Column(db.String(255), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    saldo = db.Column(db.Numeric(12, 2), nullable=False)
    fecha = db.Column(db.Date, default=date.today, nullable=False)
    estado = db.Column(db.Enum(EstadoFactura, name="estado_factura"), default=EstadoFactura.PENDIENTE, nullable=False, index=True)
    creado_en = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    cliente = db.relationship("Cliente", back_populates="facturas")
    detalles_pago = db.relationship("DetallePago", back_populates="factura")

    def aplicar(self, monto):
        monto = Decimal(str(monto))
        if monto <= 0 or monto > self.saldo:
            raise ValueError("El monto aplicado debe ser mayor que cero y no superar el saldo pendiente.")
        self.saldo -= monto
        self.estado = EstadoFactura.PAGADA if self.saldo == 0 else EstadoFactura.PARCIAL
