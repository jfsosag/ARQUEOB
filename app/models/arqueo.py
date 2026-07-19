from datetime import date, datetime, timezone
from app.extensions import db


class Arqueo(db.Model):
    __tablename__ = "arqueos"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today, nullable=False, index=True)
    cajero = db.Column(db.String(160), nullable=False)
    turno = db.Column(db.String(40), nullable=False)
    fondo_inicial = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    conteos = db.Column(db.JSON, nullable=False, default=dict)
    no_efectivo = db.Column(db.JSON, nullable=False, default=list)
    facturas_contado = db.Column(db.JSON, nullable=False, default=dict)
    facturas_credito = db.Column(db.JSON, nullable=False, default=list)
    vales = db.Column(db.JSON, nullable=False, default=list)
    totales = db.Column(db.JSON, nullable=False, default=dict)
    creado_en = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
