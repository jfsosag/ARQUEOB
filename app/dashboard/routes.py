from datetime import datetime, time, timezone
from decimal import Decimal
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func, select

from app.extensions import db
from app.models import Cliente, CobroInformal, EstadoCobroInformal, EstadoFactura, Factura, Pago

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
@login_required
def index():
    hoy = datetime.now(timezone.utc).date()
    inicio_mes = hoy.replace(day=1)
    cards = {
        "clientes": db.session.scalar(select(func.count(Cliente.id))) or 0,
        "pendientes": db.session.scalar(select(func.count(Factura.id)).where(Factura.estado != EstadoFactura.PAGADA)) or 0,
        "pagadas": db.session.scalar(select(func.count(Factura.id)).where(Factura.estado == EstadoFactura.PAGADA)) or 0,
        "saldo_pendiente": db.session.scalar(select(func.coalesce(func.sum(Factura.saldo), 0)).where(Factura.estado != EstadoFactura.PAGADA)) or Decimal("0"),
        "cobrado_hoy": db.session.scalar(select(func.coalesce(func.sum(Pago.monto_pagado), 0)).where(func.date(Pago.fecha) == hoy)) or Decimal("0"),
        "cobrado_mes": db.session.scalar(select(func.coalesce(func.sum(Pago.monto_pagado), 0)).where(func.date(Pago.fecha) >= inicio_mes)) or Decimal("0"),
        "cobros_informales": db.session.scalar(select(func.count(CobroInformal.id)).where(CobroInformal.estado != EstadoCobroInformal.PAGADO)) or 0,
        "saldo_informales": db.session.scalar(select(func.coalesce(func.sum(CobroInformal.saldo_pendiente), 0)).where(CobroInformal.estado != EstadoCobroInformal.PAGADO)) or Decimal("0"),
    }
    return render_template("dashboard/index.html", cards=cards)
