from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cliente, DetallePago, Factura

clientes_bp = Blueprint("clientes", __name__)


def _cliente_desde_form(cliente):
    cliente.nombre = request.form.get("nombre", "").strip()
    cliente.telefono = request.form.get("telefono", "").strip()
    cliente.direccion = request.form.get("direccion", "").strip()
    cliente.rnc_cedula = request.form.get("rnc_cedula", "").strip() or None
    cliente.observaciones = request.form.get("observaciones", "").strip() or None
    if not all((cliente.nombre, cliente.telefono, cliente.direccion)):
        raise ValueError("Nombre, teléfono y dirección son obligatorios.")


@clientes_bp.get("/")
@login_required
def listado():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    stmt = select(Cliente).order_by(Cliente.nombre)
    if q:
        patron = f"%{q}%"
        stmt = stmt.where(or_(Cliente.nombre.ilike(patron), Cliente.telefono.ilike(patron), Cliente.rnc_cedula.ilike(patron)))
    clientes = db.paginate(stmt, page=page, per_page=12, error_out=False)
    return render_template("clientes/listado.html", clientes=clientes, q=q)


@clientes_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    if request.method == "POST":
        cliente = Cliente()
        try:
            _cliente_desde_form(cliente)
            db.session.add(cliente)
            db.session.commit()
            flash("Cliente creado correctamente.", "success")
            return redirect(url_for("clientes.detalle", cliente_id=cliente.id))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash("Ya existe un cliente con ese RNC/cédula." if isinstance(exc, IntegrityError) else str(exc), "danger")
    return render_template("clientes/formulario.html", cliente=None)


@clientes_bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_required
def editar(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    if request.method == "POST":
        try:
            _cliente_desde_form(cliente)
            db.session.commit()
            flash("Cliente actualizado.", "success")
            return redirect(url_for("clientes.detalle", cliente_id=cliente.id))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash("El cliente no pudo guardarse: " + ("RNC/cédula duplicado." if isinstance(exc, IntegrityError) else str(exc)), "danger")
    return render_template("clientes/formulario.html", cliente=cliente)


@clientes_bp.post("/<int:cliente_id>/eliminar")
@login_required
def eliminar(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    db.session.delete(cliente)
    db.session.commit()
    flash("Cliente eliminado.", "success")
    return redirect(url_for("clientes.listado"))


@clientes_bp.get("/<int:cliente_id>")
@login_required
def detalle(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    facturas = db.session.scalars(select(Factura).where(Factura.cliente_id == cliente.id).order_by(Factura.fecha.desc())).all()
    return render_template("clientes/detalle.html", cliente=cliente, facturas=facturas)


@clientes_bp.get("/facturas")
@login_required
def facturas_listado():
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "").strip()
    page = request.args.get("page", 1, type=int)
    stmt = select(Factura).join(Cliente).order_by(Factura.fecha.desc(), Factura.id.desc())
    if q:
        patron = f"%{q}%"
        stmt = stmt.where(or_(Factura.numero.ilike(patron), Factura.concepto.ilike(patron), Cliente.nombre.ilike(patron)))
    if estado:
        try:
            from app.models import EstadoFactura
            stmt = stmt.where(Factura.estado == EstadoFactura(estado))
        except ValueError:
            pass
    facturas = db.paginate(stmt, page=page, per_page=15, error_out=False)
    return render_template("clientes/facturas.html", facturas=facturas, q=q, estado=estado)


@clientes_bp.post("/<int:cliente_id>/facturas")
@login_required
def crear_facturas(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    numeros = request.form.getlist("numero[]")
    conceptos = request.form.getlist("concepto[]")
    montos = request.form.getlist("monto[]")
    fechas = request.form.getlist("fecha[]")
    facturas = []
    try:
        for numero, concepto, monto, fecha_texto in zip(numeros, conceptos, montos, fechas):
            if not any((numero.strip(), concepto.strip(), monto.strip())):
                continue
            valor = Decimal(monto)
            if not numero.strip() or not concepto.strip() or valor <= 0:
                raise ValueError("Cada factura requiere número, concepto y monto positivo.")
            facturas.append(Factura(cliente=cliente, numero=numero.strip(), concepto=concepto.strip(), monto=valor, saldo=valor, fecha=date.fromisoformat(fecha_texto)))
        if not facturas:
            raise ValueError("Agregue al menos una factura válida.")
        db.session.add_all(facturas)
        db.session.commit()
        flash(f"{len(facturas)} factura(s) registrada(s).", "success")
    except (ValueError, InvalidOperation, IntegrityError) as exc:
        db.session.rollback()
        flash("No se guardaron las facturas. Revise que no haya números repetidos y que los montos sean válidos.", "danger")
    return redirect(url_for("clientes.detalle", cliente_id=cliente.id))


@clientes_bp.route("/<int:cliente_id>/facturas/<int:factura_id>/editar", methods=["GET", "POST"])
@login_required
def editar_factura(cliente_id, factura_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    factura = db.get_or_404(Factura, factura_id)
    if factura.cliente_id != cliente.id:
        abort(404)
    if request.method == "POST":
        try:
            factura.numero = request.form["numero"].strip()
            factura.concepto = request.form["concepto"].strip()
            nuevo_monto = Decimal(request.form["monto"])
            if nuevo_monto <= 0:
                raise ValueError("El monto debe ser mayor que cero.")
            factura.fecha = date.fromisoformat(request.form["fecha"])
            pagado = factura.monto - factura.saldo
            if nuevo_monto < pagado:
                raise ValueError(f"El monto no puede ser menor al ya pagado ({pagado}).")
            factura.monto = nuevo_monto
            factura.saldo = nuevo_monto - pagado
            db.session.commit()
            flash("Factura actualizada.", "success")
            return redirect(url_for("clientes.detalle", cliente_id=cliente.id))
        except (ValueError, InvalidOperation, IntegrityError) as exc:
            db.session.rollback()
            flash("No se pudo guardar la factura. Verifique los datos.", "danger")
    return render_template("clientes/factura_formulario.html", cliente=cliente, factura=factura)


@clientes_bp.post("/<int:cliente_id>/facturas/<int:factura_id>/eliminar")
@login_required
def eliminar_factura(cliente_id, factura_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    factura = db.get_or_404(Factura, factura_id)
    if factura.cliente_id != cliente.id:
        abort(404)
    tiene_pagos = db.session.scalars(select(DetallePago).where(DetallePago.factura_id == factura_id)).first()
    if tiene_pagos:
        flash("No se puede eliminar una factura que tiene pagos aplicados.", "danger")
        return redirect(url_for("clientes.detalle", cliente_id=cliente.id))
    db.session.delete(factura)
    db.session.commit()
    flash("Factura eliminada.", "success")
    return redirect(url_for("clientes.detalle", cliente_id=cliente.id))


@clientes_bp.get("/api/buscar")
@login_required
def buscar_api():
    q = request.form.get("q", "").strip() if request.method == "POST" else request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    patron = f"%{q}%"
    clientes = db.session.scalars(select(Cliente).where(or_(Cliente.nombre.ilike(patron), Cliente.telefono.ilike(patron), Cliente.rnc_cedula.ilike(patron))).order_by(Cliente.nombre).limit(10)).all()
    return jsonify([{"id": c.id, "nombre": c.nombre, "telefono": c.telefono, "rnc_cedula": c.rnc_cedula} for c in clientes])


@clientes_bp.post("/api/crear")
@login_required
def crear_cliente_api():
    try:
        cliente = Cliente(
            nombre=request.form["nombre"].strip(),
            telefono=request.form.get("telefono", "").strip() or "",
            direccion=request.form.get("direccion", "").strip() or "N/A",
            rnc_cedula=request.form.get("rnc_cedula", "").strip() or None,
        )
        db.session.add(cliente)
        db.session.commit()
        return jsonify({"id": cliente.id, "nombre": cliente.nombre, "telefono": cliente.telefono, "rnc_cedula": cliente.rnc_cedula})
    except (ValueError, IntegrityError):
        db.session.rollback()
        return jsonify({"error": "No se pudo crear el cliente."}), 400
