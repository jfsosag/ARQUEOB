from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import login_required
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cliente, CobroInformal, AbonoCobroInformal, EstadoCobroInformal, FormaPago

cobros_informales_bp = Blueprint("cobros_informales", __name__)


@cobros_informales_bp.get("/")
@login_required
def historial():
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "").strip()
    forma = request.form.get("forma_pago", "").strip() if request.method == "POST" else request.args.get("forma_pago", "").strip()
    page = request.args.get("page", 1, type=int)
    stmt = select(CobroInformal).join(Cliente).order_by(CobroInformal.creado_en.desc())
    if q:
        patron = f"%{q}%"
        stmt = stmt.where(or_(CobroInformal.concepto.ilike(patron), Cliente.nombre.ilike(patron), Cliente.telefono.ilike(patron)))
    if estado:
        try:
            stmt = stmt.where(CobroInformal.estado == EstadoCobroInformal(estado))
        except ValueError:
            pass
    cobros = db.paginate(stmt, page=page, per_page=15, error_out=False)
    return render_template("cobros_informales/historial.html", cobros=cobros, q=q, estado=estado)


@cobros_informales_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo():
    if request.method == "POST":
        try:
            cliente_id = int(request.form["cliente_id"])
            cliente = db.get_or_404(Cliente, cliente_id)
            concepto = request.form["concepto"].strip()
            monto_total = Decimal(request.form["monto_total"])
            monto_pagado = Decimal(request.form["monto_pagado"])
            forma_pago = FormaPago(request.form["forma_pago"])
            usuario = request.form.get("usuario", "Sistema").strip() or "Sistema"
            observaciones = request.form.get("observaciones", "").strip() or None
            if not concepto:
                raise ValueError("El concepto es obligatorio.")
            if monto_total <= 0:
                raise ValueError("El monto total debe ser mayor que cero.")
            if monto_pagado <= 0:
                raise ValueError("El monto pagado debe ser mayor que cero.")
            if monto_pagado > monto_total:
                raise ValueError("El monto pagado no puede ser mayor al total adeudado.")
            banco = request.form.get("banco", "").strip() or None
            numero = request.form.get("numero", "").strip() or None
            cobro = CobroInformal(
                cliente=cliente,
                concepto=concepto,
                monto_total=monto_total,
                saldo_pendiente=monto_total,
                observaciones=observaciones,
            )
            abono = AbonoCobroInformal(
                monto=monto_pagado,
                forma_pago=forma_pago,
                banco=banco,
                numero=numero,
                usuario=usuario,
            )
            cobro.registrar_abono(monto_pagado)
            cobro.abonos.append(abono)
            db.session.add(cobro)
            db.session.commit()
            flash("Cobro informal registrado.", "success")
            return redirect(url_for("cobros_informales.detalle", cobro_id=cobro.id))
        except (ValueError, InvalidOperation, IntegrityError) as exc:
            db.session.rollback()
            flash("No se pudo registrar el cobro: " + str(exc), "danger")
    return render_template("cobros_informales/formulario.html")


@cobros_informales_bp.get("/<int:cobro_id>")
@login_required
def detalle(cobro_id):
    cobro = db.get_or_404(CobroInformal, cobro_id)
    return render_template("cobros_informales/detalle.html", cobro=cobro)


@cobros_informales_bp.route("/<int:cobro_id>/abonar", methods=["GET", "POST"])
@login_required
def abonar(cobro_id):
    cobro = db.get_or_404(CobroInformal, cobro_id)
    if cobro.estado == EstadoCobroInformal.PAGADO:
        flash("Este cobro ya está completamente pagado.", "warning")
        return redirect(url_for("cobros_informales.detalle", cobro_id=cobro.id))
    if request.method == "POST":
        try:
            monto = Decimal(request.form["monto"])
            if monto <= 0 or monto > cobro.saldo_pendiente:
                raise ValueError("El monto debe ser mayor que cero y no superar el saldo pendiente.")
            forma_pago = FormaPago(request.form["forma_pago"])
            banco = request.form.get("banco", "").strip() or None
            numero = request.form.get("numero", "").strip() or None
            usuario = request.form.get("usuario", "Sistema").strip() or "Sistema"
            abono = AbonoCobroInformal(
                monto=monto,
                forma_pago=forma_pago,
                banco=banco,
                numero=numero,
                usuario=usuario,
            )
            cobro.registrar_abono(monto)
            cobro.abonos.append(abono)
            db.session.commit()
            flash("Abono registrado.", "success")
            return redirect(url_for("cobros_informales.detalle", cobro_id=cobro.id))
        except (ValueError, InvalidOperation) as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    return render_template("cobros_informales/abonar.html", cobro=cobro)


@cobros_informales_bp.post("/<int:cobro_id>/eliminar")
@login_required
def eliminar(cobro_id):
    cobro = db.get_or_404(CobroInformal, cobro_id)
    db.session.delete(cobro)
    db.session.commit()
    flash("Cobro informal eliminado.", "success")
    return redirect(url_for("cobros_informales.historial"))


@cobros_informales_bp.get("/<int:cobro_id>/recibo.pdf")
@login_required
def recibo(cobro_id):
    cobro = db.get_or_404(CobroInformal, cobro_id)
    empresa = {
        "nombre": current_app.config["COMPANY_NAME"],
        "telefono": current_app.config["COMPANY_PHONE"],
        "rnc": current_app.config["COMPANY_RNC"],
        "direccion": current_app.config["COMPANY_ADDRESS"],
    }
    return send_file(_recibo_pdf(cobro, empresa), as_attachment=True, download_name=f"cobro_informal_{cobro.id:06d}.pdf", mimetype="application/pdf")


def _recibo_pdf(cobro, empresa):
    import io
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as cv

    ancho, alto = 80 * mm, 200 * mm
    buffer = io.BytesIO()
    pdf = cv.Canvas(buffer, pagesize=(ancho, alto))

    def copia(etiqueta):
        y, margen = alto - 10 * mm, 7 * mm
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(ancho / 2, y, empresa["nombre"]); y -= 5 * mm
        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(ancho / 2, y, f"Tel. {empresa['telefono']} · RNC {empresa['rnc']}"); y -= 4 * mm
        pdf.drawCentredString(ancho / 2, y, empresa["direccion"][:55]); y -= 6 * mm
        pdf.line(margen, y, ancho - margen, y); y -= 5 * mm
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(ancho / 2, y, f"COBRO INFORMAL · {etiqueta}"); y -= 6 * mm
        pdf.setFont("Helvetica", 8)
        pdf.drawString(margen, y, f"No. {cobro.id:06d}"); pdf.drawRightString(ancho - margen, y, cobro.creado_en.strftime("%d/%m/%Y")); y -= 5 * mm
        pdf.drawString(margen, y, f"Cliente: {cobro.cliente.nombre[:35]}"); y -= 5 * mm
        pdf.drawString(margen, y, f"Concepto: {cobro.concepto[:38]}"); y -= 6 * mm
        pdf.line(margen, y, ancho - margen, y); y -= 5 * mm

        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawString(margen, y, "FORMA DE PAGO"); pdf.drawRightString(ancho - margen, y, "MONTO"); y -= 4 * mm
        pdf.setFont("Helvetica", 8)
        for abono in cobro.abonos:
            fp = abono.forma_pago.value
            if abono.banco:
                fp += f" ({abono.banco})"
            if abono.numero:
                fp += f" #{abono.numero}"
            pdf.drawString(margen, y, fp[:38])
            pdf.drawRightString(ancho - margen, y, f"RD$ {abono.monto:,.2f}")
            y -= 4.5 * mm

        pdf.line(margen, y, ancho - margen, y); y -= 6 * mm
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(margen, y, "TOTAL ADEUDADO")
        pdf.drawRightString(ancho - margen, y, f"RD$ {cobro.monto_total:,.2f}"); y -= 5 * mm
        pdf.drawString(margen, y, "TOTAL PAGADO")
        pdf.drawRightString(ancho - margen, y, f"RD$ {cobro.monto_pagado:,.2f}"); y -= 5 * mm
        pdf.drawString(margen, y, "SALDO PENDIENTE")
        pdf.drawRightString(ancho - margen, y, f"RD$ {cobro.saldo_pendiente:,.2f}"); y -= 8 * mm

        pdf.setFont("Helvetica", 7)
        pdf.drawString(margen, y, f"Estado: {cobro.estado.value}"); y -= 4 * mm
        pdf.drawString(margen, y, f"Cobrado por: {cobro.abonos[0].usuario if cobro.abonos else 'N/A'}"); y -= 8 * mm

        pdf.drawCentredString(ancho / 2, y, "Gracias por su pago")
        pdf.showPage()

    copia("ORIGINAL")
    copia("COPIA")
    pdf.save()
    buffer.seek(0)
    return buffer
