from datetime import date, datetime, timezone
from app.extensions import db


class Conduce(db.Model):
    __tablename__ = "conduces"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today, nullable=False)
    cliente = db.Column(db.String(160), nullable=False)
    direccion = db.Column(db.String(255), nullable=False)
    factura = db.Column(db.String(60), nullable=True)
    bultos = db.Column(db.Integer, nullable=True)
    descripcion = db.Column(db.Text, nullable=False)
    observaciones = db.Column(db.Text, nullable=True)
    creado_en = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
