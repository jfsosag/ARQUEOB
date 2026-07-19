import enum
from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db


class EstadoCobroInformal(enum.StrEnum):
    PENDIENTE = "Pendiente"
    PAGADO = "Pagado"


class FormaPago(enum.StrEnum):
    EFECTIVO = "Efectivo"
    CHEQUE = "Cheque"
    TRANSFERENCIA = "Transferencia"
    TARJETA = "Tarjeta"


class CobroInformal(db.Model):
    __tablename__ = "cobros_informales"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id", ondelete="RESTRICT"), nullable=False, index=True)
    concepto = db.Column(db.String(255), nullable=False)
    monto_total = db.Column(db.Numeric(12, 2), nullable=False)
    saldo_pendiente = db.Column(db.Numeric(12, 2), nullable=False)
    estado = db.Column(db.Enum(EstadoCobroInformal, name="estado_cobro_informal"), default=EstadoCobroInformal.PENDIENTE, nullable=False, index=True)
    observaciones = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    cliente = db.relationship("Cliente", back_populates="cobros_informales")
    abonos = db.relationship("AbonoCobroInformal", back_populates="cobro", cascade="all, delete-orphan", order_by="AbonoCobroInformal.fecha")

    def registrar_abono(self, monto):
        monto = Decimal(str(monto))
        if monto <= 0 or monto > self.saldo_pendiente:
            raise ValueError("El monto debe ser mayor que cero y no superar el saldo pendiente.")
        self.saldo_pendiente -= monto
        if self.saldo_pendiente == 0:
            self.estado = EstadoCobroInformal.PAGADO

    @property
    def monto_pagado(self):
        return self.monto_total - self.saldo_pendiente


class AbonoCobroInformal(db.Model):
    __tablename__ = "abonos_cobro_informal"

    id = db.Column(db.Integer, primary_key=True)
    cobro_informal_id = db.Column(db.Integer, db.ForeignKey("cobros_informales.id", ondelete="CASCADE"), nullable=False, index=True)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    forma_pago = db.Column(db.Enum(FormaPago, name="forma_pago_informal"), nullable=False)
    banco = db.Column(db.String(120), nullable=True)
    numero = db.Column(db.String(60), nullable=True)
    fecha = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    usuario = db.Column(db.String(120), nullable=False, default="Sistema")

    cobro = db.relationship("CobroInformal", back_populates="abonos")
