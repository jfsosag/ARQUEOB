from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_, select

from app.extensions import db
from app.models import Cliente, DetallePago, EstadoFactura, Factura, FormaPago, Pago, TipoCobro
from app.utils.auditoria import registrar_accion
from app.utils.pdf import recibo_pdf as generar_recibo_pdf

cobros_bp = Blueprint("cobros", __name__)


@cobros_bp.get("/")
@login_required
def listar_clientes():
    q = request.args.get("q", "").strip()
    stmt = (
        db.session.query(
            Cliente.id, Cliente.nombre, Cliente.telefono, Cliente.rnc_cedula,
            func.count(Factura.id).label("facturas_pendientes"),
            func.coalesce(func.sum(Factura.saldo), 0).label("total_pendiente"),
            func.min(Factura.fecha).label("fecha_mas_antigua"),
        )
        .join(Factura, Factura.cliente_id == Cliente.id)
        .filter(Factura.estado != EstadoFactura.PAGADA)
        .group_by(Cliente.id, Cliente.nombre, Cliente.telefono, Cliente.rnc_cedula)
        .order_by(Cliente.nombre)
    )
    if q:
        patron = f"%{q}%"
        stmt = stmt.filter(or_(Cliente.nombre.ilike(patron), Cliente.telefono.ilike(patron), Cliente.rnc_cedula.ilike(patron)))
    clientes = stmt.all()
    return render_template("cobros/listar_clientes.html", clientes=clientes, q=q)


@cobros_bp.get("/api/clientes-pendientes")
@login_required
def api_clientes_pendientes():
    q = request.args.get("q", "").strip()
    stmt = (
        db.session.query(
            Cliente.id, Cliente.nombre, Cliente.telefono, Cliente.rnc_cedula,
            func.count(Factura.id).label("facturas_pendientes"),
            func.coalesce(func.sum(Factura.saldo), 0).label("total_pendiente"),
        )
        .join(Factura, Factura.cliente_id == Cliente.id)
        .filter(Factura.estado != EstadoFactura.PAGADA)
        .group_by(Cliente.id, Cliente.nombre, Cliente.telefono, Cliente.rnc_cedula)
        .order_by(Cliente.nombre)
    )
    if q:
        patron = f"%{q}%"
        stmt = stmt.filter(or_(Cliente.nombre.ilike(patron), Cliente.telefono.ilike(patron), Cliente.rnc_cedula.ilike(patron)))
    rows = stmt.limit(50).all()
    return jsonify([{"id": r.id, "nombre": r.nombre, "telefono": r.telefono, "rnc_cedula": r.rnc_cedula, "facturas_pendientes": r.facturas_pendientes, "total_pendiente": float(r.total_pendiente)} for r in rows])


@cobros_bp.get("/<int:cliente_id>")
@login_required
def cobrar(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    facturas = db.session.scalars(
        select(Factura).where(Factura.cliente_id == cliente.id, Factura.estado != EstadoFactura.PAGADA).order_by(Factura.fecha)
    ).all()
    total_pendiente = sum(f.saldo for f in facturas)
    return render_template("cobros/cobrar.html", cliente=cliente, facturas=facturas, total_pendiente=total_pendiente)


@cobros_bp.get("/api/cliente/<int:cliente_id>/facturas")
@login_required
def facturas_cliente(cliente_id):
    facturas = db.session.scalars(
        select(Factura).where(Factura.cliente_id == cliente_id, Factura.estado != EstadoFactura.PAGADA).order_by(Factura.fecha)
    ).all()
    return jsonify([{"id": f.id, "numero": f.numero, "concepto": f.concepto, "saldo": float(f.saldo), "fecha": f.fecha.isoformat()} for f in facturas])


@cobros_bp.get("/api/cliente/<int:cliente_id>/simular-fifo")
@login_required
def simular_fifo(cliente_id):
    """Simula la distribución FIFO de un monto dado sobre las facturas pendientes."""
    monto = Decimal(request.args.get("monto", "0"))
    facturas = db.session.scalars(
        select(Factura).where(Factura.cliente_id == cliente_id, Factura.estado != EstadoFactura.PAGADA).order_by(Factura.fecha)
    ).all()
    distribucion = []
    restante = monto
    for f in facturas:
        if restante <= 0:
            break
        aplicar = min(restante, f.saldo)
        distribucion.append({"id": f.id, "numero": f.numero, "saldo": float(f.saldo), "aplicado": float(aplicar)})
        restante -= aplicar
    excedente = float(restante) if restante > 0 else 0
    return jsonify({"distribucion": distribucion, "excedente": excedente, "total_pendiente": float(sum(f.saldo for f in facturas))})


@cobros_bp.post("/")
@login_required
def registrar_cobro():
    try:
        cliente_id = int(request.form["cliente_id"])
        cliente = db.get_or_404(Cliente, cliente_id)
        monto_recibido = Decimal(request.form.get("monto_recibido", "0"))
        if monto_recibido <= 0:
            raise ValueError("El monto recibido debe ser mayor que cero.")

        forma_pago = FormaPago(request.form.get("forma_pago", "Efectivo"))
        pago = Pago(
            cliente=cliente,
            usuario=current_user.username if current_user.is_authenticated else "Sistema",
            monto_pagado=0,
            observaciones=request.form.get("observaciones", "").strip() or None,
            tipo=TipoCobro.FACTURA,
            forma_pago=forma_pago,
            banco=request.form.get("banco", "").strip() or None,
            numero_cheque=request.form.get("numero_cheque", "").strip() or None,
            nombre_titular=request.form.get("nombre_titular", "").strip() or None,
            numero_referencia=request.form.get("numero_referencia", "").strip() or None,
            tipo_tarjeta=request.form.get("tipo_tarjeta", "").strip() or None,
            ultimos_4_digitos=request.form.get("ultimos_4_digitos", "").strip() or None,
            numero_autorizacion=request.form.get("numero_autorizacion", "").strip() or None,
        )
        if forma_pago == FormaPago.CHEQUE:
            fecha_str = request.form.get("fecha_cheque", "").strip()
            if fecha_str:
                pago.fecha_cheque = date.fromisoformat(fecha_str)
        elif forma_pago == FormaPago.TRANSFERENCIA:
            fecha_str = request.form.get("fecha_transferencia", "").strip()
            if fecha_str:
                pago.fecha_transferencia = date.fromisoformat(fecha_str)

        facturas = db.session.scalars(
            select(Factura).where(Factura.cliente_id == cliente.id, Factura.estado != EstadoFactura.PAGADA).order_by(Factura.fecha)
        ).all()
        total_pendiente = sum(f.saldo for f in facturas)

        if not facturas:
            raise ValueError("El cliente no tiene facturas pendientes.")

        restante = monto_recibido
        total_aplicado = Decimal("0")
        for factura in facturas:
            if restante <= 0:
                break
            aplicar = min(restante, factura.saldo)
            factura.aplicar(aplicar)
            pago.detalles.append(DetallePago(factura=factura, monto_aplicado=aplicar))
            total_aplicado += aplicar
            restante -= aplicar

        excedente = monto_recibido - total_pendiente
        if excedente > 0:
            manejo = request.form.get("excedente_manejo", "credito")
            if manejo == "credito":
                cliente.saldo_a_favor = getattr(cliente, 'saldo_a_favor', Decimal("0")) + excedente
                obs = (pago.observaciones or "") + f" [Excedente RD$ {excedente:,.2f} registrado como crédito]"
                pago.observaciones = obs.strip()
            elif manejo == "devolver":
                obs = (pago.observaciones or "") + f" [Excedente RD$ {excedente:,.2f} devuelto al cliente]"
                pago.observaciones = obs.strip()
            else:
                pass

        pago.monto_pagado = total_aplicado
        db.session.add(pago)
        db.session.commit()
        registrar_accion("registrar_cobro", "cobros", f"Pago #{pago.id:06d} - {cliente.nombre} - RD$ {total_aplicado:,.2f}")
        flash("Pago registrado y facturas actualizadas.", "success")
        return redirect(url_for("cobros.recibo_pdf", pago_id=pago.id))
    except (ValueError, InvalidOperation) as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("cobros.cobrar", cliente_id=request.form.get("cliente_id", "")))


@cobros_bp.get("/<int:pago_id>/recibo.pdf")
@login_required
def recibo_pdf(pago_id):
    pago = db.get_or_404(Pago, pago_id)
    empresa = {
        "nombre": current_app.config["COMPANY_NAME"],
        "telefono": current_app.config["COMPANY_PHONE"],
        "rnc": current_app.config["COMPANY_RNC"],
        "direccion": current_app.config["COMPANY_ADDRESS"],
    }
    return send_file(generar_recibo_pdf(pago, empresa), as_attachment=True, download_name=f"recibo_{pago.id:06d}.pdf", mimetype="application/pdf")


@cobros_bp.get("/historial")
@login_required
def historial():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    stmt = select(Pago).join(Cliente).order_by(Pago.fecha.desc())
    if q:
        patron = f"%{q}%"
        stmt = stmt.where(or_(Cliente.nombre.ilike(patron), Cliente.telefono.ilike(patron), Cliente.rnc_cedula.ilike(patron)))
    pagos = db.paginate(stmt, page=page, per_page=15, error_out=False)
    return render_template("cobros/historial.html", pagos=pagos, q=q)
