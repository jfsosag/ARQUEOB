import enum
from datetime import datetime, timezone
from app.extensions import db


class TipoCobro(enum.StrEnum):
    FACTURA = "Factura"
    MANUAL = "Manual"


class FormaPago(enum.StrEnum):
    EFECTIVO = "Efectivo"
    CHEQUE = "Cheque"
    TRANSFERENCIA = "Transferencia Bancaria"
    TARJETA = "Tarjeta"


class Pago(db.Model):
    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False, index=True)
    fecha = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    usuario = db.Column(db.String(120), nullable=False, default="Sistema")
    monto_pagado = db.Column(db.Numeric(12, 2), nullable=False)
    observaciones = db.Column(db.Text, nullable=True)

    tipo = db.Column(db.Enum(TipoCobro, name="tipo_cobro"), default=TipoCobro.FACTURA, nullable=False)
    forma_pago = db.Column(db.Enum(FormaPago, name="forma_pago"), default=FormaPago.EFECTIVO, nullable=False)
    banco = db.Column(db.String(120), nullable=True)
    numero_cheque = db.Column(db.String(60), nullable=True)
    fecha_cheque = db.Column(db.Date, nullable=True)
    nombre_titular = db.Column(db.String(160), nullable=True)
    numero_referencia = db.Column(db.String(60), nullable=True)
    fecha_transferencia = db.Column(db.Date, nullable=True)
    tipo_tarjeta = db.Column(db.String(20), nullable=True)
    ultimos_4_digitos = db.Column(db.String(4), nullable=True)
    numero_autorizacion = db.Column(db.String(60), nullable=True)
    concepto_manual = db.Column(db.String(255), nullable=True)

    cliente = db.relationship("Cliente", back_populates="pagos")
    detalles = db.relationship("DetallePago", back_populates="pago", cascade="all, delete-orphan")


class DetallePago(db.Model):
    __tablename__ = "detalle_pagos"

    id = db.Column(db.Integer, primary_key=True)
    pago_id = db.Column(db.Integer, db.ForeignKey("pagos.id", ondelete="CASCADE"), nullable=False, index=True)
    factura_id = db.Column(db.Integer, db.ForeignKey("facturas.id", ondelete="RESTRICT"), nullable=True, index=True)
    monto_aplicado = db.Column(db.Numeric(12, 2), nullable=False)

    pago = db.relationship("Pago", back_populates="detalles")
    factura = db.relationship("Factura", back_populates="detalles_pago")
