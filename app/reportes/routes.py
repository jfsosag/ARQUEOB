import io
from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, HexColor, white, black
from reportlab.pdfgen import canvas as pdf_canvas
from sqlalchemy import func, or_, select

from app.extensions import db
from app.models import (
    AbonoCobroInformal, Arqueo, Cliente, CobroInformal, EstadoCobroInformal,
    EstadoFactura, Factura, FormaPago, Pago, TipoCobro,
)

reportes_bp = Blueprint("reportes", __name__)

# ── Colores corporativos ────────────────────────────────────────────
_C_PRIMARY    = HexColor("#1B3A5C")
_C_HEADER_BG  = HexColor("#E8EDF2")
_C_ZEBRA      = HexColor("#F4F6F8")
_C_BORDER     = HexColor("#C5CED6")
_C_GREEN      = HexColor("#27AE60")
_C_YELLOW     = HexColor("#F39C12")
_C_RED        = HexColor("#E74C3C")
_C_CARD_BG    = HexColor("#F8F9FA")


def _empresa():
    return {
        "nombre": current_app.config["COMPANY_NAME"],
        "telefono": current_app.config["COMPANY_PHONE"],
        "rnc": current_app.config["COMPANY_RNC"],
        "direccion": current_app.config["COMPANY_ADDRESS"],
    }


def _es_admin():
    return current_user.is_authenticated and current_user.is_admin


def _usuario_actual():
    return current_user.username if current_user.is_authenticated else "Sistema"


# ── Helpers de permisos ──────────────────────────────────────────────

def _filtrar_pagos_usuario(stmt):
    if not _es_admin():
        stmt = stmt.where(Pago.usuario == _usuario_actual())
    return stmt


def _filtrar_arqueos_usuario(stmt):
    if not _es_admin():
        stmt = stmt.where(Arqueo.cajero == _usuario_actual())
    return stmt


def _filtrar_facturas_usuario(stmt):
    if not _es_admin():
        stmt = stmt.join(Cliente)
    return stmt


# ── 1. Reimpresión de Facturas ───────────────────────────────────────

@reportes_bp.get("/facturas")
@login_required
def facturas():
    q = request.args.get("q", "").strip()
    cliente_q = request.args.get("cliente", "").strip()
    estado = request.args.get("estado", "").strip()
    fecha_ini = request.args.get("fecha_ini", "").strip()
    fecha_fin = request.args.get("fecha_fin", "").strip()

    stmt = select(Factura).join(Cliente).order_by(Factura.fecha.desc(), Factura.id.desc())

    if q:
        stmt = stmt.where(Factura.numero.ilike(f"%{q}%"))
    if cliente_q:
        stmt = stmt.where(Cliente.nombre.ilike(f"%{cliente_q}%"))
    if estado:
        try:
            stmt = stmt.where(Factura.estado == EstadoFactura(estado))
        except ValueError:
            pass
    if fecha_ini:
        stmt = stmt.where(Factura.fecha >= date.fromisoformat(fecha_ini))
    if fecha_fin:
        stmt = stmt.where(Factura.fecha <= date.fromisoformat(fecha_fin))

    facturas = db.session.scalars(stmt).all()
    return render_template("reportes/facturas.html", facturas=facturas, q=q, cliente_q=cliente_q, estado=estado, fecha_ini=fecha_ini, fecha_fin=fecha_fin)


@reportes_bp.get("/facturas/<int:factura_id>/pdf")
@login_required
def factura_pdf(factura_id):
    factura = db.get_or_404(Factura, factura_id)
    empresa = _empresa()
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    ancho, alto = A4
    y = alto - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(ancho / 2, y, empresa["nombre"])
    y -= 20
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(ancho / 2, y, f"Tel. {empresa['telefono']} · RNC {empresa['rnc']}")
    y -= 14
    pdf.drawCentredString(ancho / 2, y, empresa["direccion"])
    y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(ancho / 2, y, f"FACTURA #{factura.numero}")
    y -= 25

    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, y, f"Cliente: {factura.cliente.nombre}")
    pdf.drawRightString(ancho - 45, y, f"Fecha: {factura.fecha.strftime('%d/%m/%Y')}")
    y -= 16
    if factura.cliente.rnc_cedula:
        pdf.drawString(45, y, f"RNC/Cédula: {factura.cliente.rnc_cedula}")
        y -= 16
    pdf.drawString(45, y, f"Concepto: {factura.concepto}")
    y -= 20

    pdf.line(45, y, ancho - 45, y)
    y -= 20
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(45, y, "Detalle")
    y -= 18

    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, y, "Descripción")
    pdf.drawRightString(ancho - 45, y, "Monto")
    y -= 16
    pdf.line(45, y, ancho - 45, y)
    y -= 16

    pdf.drawString(45, y, factura.concepto)
    pdf.drawRightString(ancho - 45, y, f"RD$ {factura.monto:,.2f}")
    y -= 20

    pdf.line(45, y, ancho - 45, y)
    y -= 20
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(45, y, "Total:")
    pdf.drawRightString(ancho - 45, y, f"RD$ {factura.monto:,.2f}")
    y -= 18
    pdf.drawString(45, y, "Pagado:")
    pdf.drawRightString(ancho - 45, y, f"RD$ {factura.monto - factura.saldo:,.2f}")
    y -= 18
    pdf.drawString(45, y, "Pendiente:")
    pdf.drawRightString(ancho - 45, y, f"RD$ {factura.saldo:,.2f}")
    y -= 30

    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(ancho / 2, y, f"Generado por {_usuario_actual()} · {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"factura_{factura.numero}.pdf", mimetype="application/pdf")


# ── 2. Reporte de Cobros ─────────────────────────────────────────────

@reportes_bp.get("/cobros")
@login_required
def cobros():
    fecha_ini = request.args.get("fecha_ini", "").strip()
    fecha_fin = request.args.get("fecha_fin", "").strip()
    cliente_q = request.args.get("cliente", "").strip()
    usuario_q = request.args.get("usuario", "").strip()
    forma_pago = request.args.get("forma_pago", "").strip()
    tipo_cobro = request.args.get("tipo_cobro", "").strip()

    stmt = select(Pago).join(Cliente).order_by(Pago.fecha.desc())
    stmt = _filtrar_pagos_usuario(stmt)

    if fecha_ini:
        stmt = stmt.where(func.date(Pago.fecha) >= date.fromisoformat(fecha_ini))
    if fecha_fin:
        stmt = stmt.where(func.date(Pago.fecha) <= date.fromisoformat(fecha_fin))
    if cliente_q:
        stmt = stmt.where(Cliente.nombre.ilike(f"%{cliente_q}%"))
    if usuario_q and _es_admin():
        stmt = stmt.where(Pago.usuario.ilike(f"%{usuario_q}%"))
    if forma_pago:
        try:
            stmt = stmt.where(Pago.forma_pago == FormaPago(forma_pago))
        except ValueError:
            pass
    if tipo_cobro:
        try:
            stmt = stmt.where(Pago.tipo == TipoCobro(tipo_cobro))
        except ValueError:
            pass

    pagos = db.session.scalars(stmt).all()

    total_cobrado = sum(float(p.monto_pagado) for p in pagos)
    cantidad = len(pagos)
    por_forma = {}
    for fp in FormaPago:
        por_forma[fp.value] = sum(float(p.monto_pagado) for p in pagos if p.forma_pago == fp)

    return render_template("reportes/cobros.html",
        pagos=pagos, total_cobrado=total_cobrado, cantidad=cantidad, por_forma=por_forma,
        fecha_ini=fecha_ini, fecha_fin=fecha_fin, cliente_q=cliente_q, usuario_q=usuario_q,
        forma_pago=forma_pago, tipo_cobro=tipo_cobro, es_admin=_es_admin(),
    )


@reportes_bp.get("/cobros/pdf")
@login_required
def cobros_pdf():
    fecha_ini = request.args.get("fecha_ini", "").strip()
    fecha_fin = request.args.get("fecha_fin", "").strip()
    cliente_q = request.args.get("cliente", "").strip()
    usuario_q = request.args.get("usuario", "").strip()
    forma_pago = request.args.get("forma_pago", "").strip()
    tipo_cobro = request.args.get("tipo_cobro", "").strip()

    stmt = select(Pago).join(Cliente).order_by(Pago.fecha.desc())
    stmt = _filtrar_pagos_usuario(stmt)

    if fecha_ini:
        stmt = stmt.where(func.date(Pago.fecha) >= date.fromisoformat(fecha_ini))
    if fecha_fin:
        stmt = stmt.where(func.date(Pago.fecha) <= date.fromisoformat(fecha_fin))
    if cliente_q:
        stmt = stmt.where(Cliente.nombre.ilike(f"%{cliente_q}%"))
    if usuario_q and _es_admin():
        stmt = stmt.where(Pago.usuario.ilike(f"%{usuario_q}%"))
    if forma_pago:
        try:
            stmt = stmt.where(Pago.forma_pago == FormaPago(forma_pago))
        except ValueError:
            pass
    if tipo_cobro:
        try:
            stmt = stmt.where(Pago.tipo == TipoCobro(tipo_cobro))
        except ValueError:
            pass

    pagos = db.session.scalars(stmt).all()
    empresa = _empresa()
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=landscape(A4), pageCompression=1)
    ancho, alto = landscape(A4)
    y = alto - 30

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(ancho / 2, y, f"{empresa['nombre']} — Reporte de Cobros")
    y -= 16
    pdf.setFont("Helvetica", 9)
    rango = ""
    if fecha_ini: rango += f"Desde: {fecha_ini}"
    if fecha_fin: rango += f"  Hasta: {fecha_fin}"
    pdf.drawCentredString(ancho / 2, y, rango or "Todos los registros")
    y -= 14
    pdf.drawCentredString(ancho / 2, y, f"Generado por {_usuario_actual()} · {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 20

    headers = ["Fecha", "Cliente", "Concepto", "Forma", "Monto", "Usuario"]
    col_x = [30, 100, 230, 380, 470, 550]
    pdf.setFont("Helvetica-Bold", 8)
    for i, h in enumerate(headers):
        pdf.drawString(col_x[i], y, h)
    y -= 12
    pdf.line(30, y, ancho - 30, y)
    y -= 12

    pdf.setFont("Helvetica", 8)
    for p in pagos:
        if y < 40:
            pdf.showPage()
            y = alto - 30
        concepto = p.concepto_manual or ", ".join(d.factura.numero for d in p.detalles if d.factura)[:30]
        pdf.drawString(col_x[0], y, p.fecha.strftime("%d/%m/%Y"))
        pdf.drawString(col_x[1], y, p.cliente.nombre[:25])
        pdf.drawString(col_x[2], y, concepto[:28])
        pdf.drawString(col_x[3], y, p.forma_pago.value[:15])
        pdf.drawRightString(col_x[4] + 60, y, f"RD$ {p.monto_pagado:,.2f}")
        pdf.drawString(col_x[5], y, p.usuario[:15])
        y -= 12

    y -= 10
    pdf.line(30, y, ancho - 30, y)
    y -= 16
    total = sum(float(p.monto_pagado) for p in pagos)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(30, y, f"Total cobrado: RD$ {total:,.2f}")
    pdf.drawRightString(ancho - 30, y, f"Cantidad: {len(pagos)}")
    y -= 14
    pdf.setFont("Helvetica", 9)
    for fp in FormaPago:
        subtotal = sum(float(p.monto_pagado) for p in pagos if p.forma_pago == fp)
        if subtotal > 0:
            pdf.drawString(30, y, f"{fp.value}: RD$ {subtotal:,.2f}")
            y -= 12

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="reporte_cobros.pdf", mimetype="application/pdf")


@reportes_bp.get("/cobros/excel")
@login_required
def cobros_excel():
    fecha_ini = request.args.get("fecha_ini", "").strip()
    fecha_fin = request.args.get("fecha_fin", "").strip()
    cliente_q = request.args.get("cliente", "").strip()
    usuario_q = request.args.get("usuario", "").strip()
    forma_pago = request.args.get("forma_pago", "").strip()
    tipo_cobro = request.args.get("tipo_cobro", "").strip()

    stmt = select(Pago).join(Cliente).order_by(Pago.fecha.desc())
    stmt = _filtrar_pagos_usuario(stmt)

    if fecha_ini:
        stmt = stmt.where(func.date(Pago.fecha) >= date.fromisoformat(fecha_ini))
    if fecha_fin:
        stmt = stmt.where(func.date(Pago.fecha) <= date.fromisoformat(fecha_fin))
    if cliente_q:
        stmt = stmt.where(Cliente.nombre.ilike(f"%{cliente_q}%"))
    if usuario_q and _es_admin():
        stmt = stmt.where(Pago.usuario.ilike(f"%{usuario_q}%"))
    if forma_pago:
        try:
            stmt = stmt.where(Pago.forma_pago == FormaPago(forma_pago))
        except ValueError:
            pass
    if tipo_cobro:
        try:
            stmt = stmt.where(Pago.tipo == TipoCobro(tipo_cobro))
        except ValueError:
            pass

    pagos = db.session.scalars(stmt).all()

    output = io.StringIO()
    output.write("Fecha,Cliente,Concepto,Forma de Pago,Monto,Usuario\n")
    for p in pagos:
        concepto = p.concepto_manual or ", ".join(d.factura.numero for d in p.detalles if d.factura)
        output.write(f'{p.fecha.strftime("%d/%m/%Y")},"{p.cliente.nombre}","{concepto}","{p.forma_pago.value}",{p.monto_pagado},"{p.usuario}"\n')

    buffer = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    return send_file(buffer, as_attachment=True, download_name="reporte_cobros.csv", mimetype="text/csv")


# ── 3. Estado de Cuenta ──────────────────────────────────────────────

@reportes_bp.get("/estado-cuenta")
@login_required
def estado_cuenta():
    cliente_id = request.args.get("cliente_id", "", type=str)
    cliente = None
    facturas = []
    total_facturado = Decimal("0")
    total_pagado = Decimal("0")

    if cliente_id:
        try:
            cliente = db.get_or_404(Cliente, int(cliente_id))
            facturas = db.session.scalars(
                select(Factura).where(Factura.cliente_id == cliente.id).order_by(Factura.fecha.desc())
            ).all()
            total_facturado = sum(f.monto for f in facturas)
            total_pagado = total_facturado - sum(f.saldo for f in facturas)
        except (ValueError, TypeError):
            pass

    return render_template("reportes/estado_cuenta.html",
        cliente=cliente, facturas=facturas,
        total_facturado=total_facturado, total_pagado=total_pagado,
        cliente_id=cliente_id,
    )


@reportes_bp.get("/estado-cuenta/<int:cliente_id>/pdf")
@login_required
def estado_cuenta_pdf(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    facturas = db.session.scalars(
        select(Factura).where(Factura.cliente_id == cliente.id).order_by(Factura.fecha.desc())
    ).all()
    empresa = _empresa()
    total_facturado = sum(f.monto for f in facturas)
    total_pagado = total_facturado - sum(f.saldo for f in facturas)

    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    ancho, alto = A4
    y = alto - 50

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(ancho / 2, y, empresa["nombre"])
    y -= 18
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(ancho / 2, y, f"Tel. {empresa['telefono']} · RNC {empresa['rnc']}")
    y -= 14
    pdf.drawCentredString(ancho / 2, y, empresa["direccion"])
    y -= 22

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(ancho / 2, y, "ESTADO DE CUENTA")
    y -= 25

    pdf.setFont("Helvetica", 10)
    pdf.drawString(45, y, f"Cliente: {cliente.nombre}")
    y -= 14
    pdf.drawString(45, y, f"Teléfono: {cliente.telefono}")
    if cliente.rnc_cedula:
        pdf.drawRightString(ancho - 45, y, f"RNC/Cédula: {cliente.rnc_cedula}")
    y -= 14
    if cliente.direccion:
        pdf.drawString(45, y, f"Dirección: {cliente.direccion}")
        y -= 14
    pdf.drawString(45, y, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 20

    pdf.line(45, y, ancho - 45, y)
    y -= 18
    pdf.setFont("Helvetica-Bold", 10)
    headers = ["No.", "Fecha", "Concepto", "Total", "Pagado", "Pendiente", "Estado"]
    col_x = [45, 80, 150, 260, 340, 420, 500]
    for i, h in enumerate(headers):
        pdf.drawString(col_x[i], y, h)
    y -= 12
    pdf.line(45, y, ancho - 45, y)
    y -= 14

    pdf.setFont("Helvetica", 9)
    for f in facturas:
        if y < 60:
            pdf.showPage()
            y = alto - 50
        pagado = f.monto - f.saldo
        pdf.drawString(col_x[0], y, f.numero)
        pdf.drawString(col_x[1], y, f.fecha.strftime("%d/%m/%Y"))
        pdf.drawString(col_x[2], y, f.concepto[:22])
        pdf.drawRightString(col_x[3] + 50, y, f"RD$ {f.monto:,.2f}")
        pdf.drawRightString(col_x[4] + 50, y, f"RD$ {pagado:,.2f}")
        pdf.drawRightString(col_x[5] + 50, y, f"RD$ {f.saldo:,.2f}")
        pdf.drawString(col_x[6], y, f.estado.value)
        y -= 12

    y -= 10
    pdf.line(45, y, ancho - 45, y)
    y -= 16
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(45, y, f"Total facturado: RD$ {total_facturado:,.2f}")
    y -= 14
    pdf.drawString(45, y, f"Total pagado: RD$ {total_pagado:,.2f}")
    y -= 14
    pdf.drawString(45, y, f"Balance pendiente: RD$ {total_facturado - total_pagado:,.2f}")

    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"estado_cuenta_{cliente.nombre[:20]}.pdf", mimetype="application/pdf")


# ── 4. Historial de Arqueos ──────────────────────────────────────────

@reportes_bp.get("/arqueos")
@login_required
def historial_arqueos():
    fecha_ini = request.args.get("fecha_ini", "").strip()
    fecha_fin = request.args.get("fecha_fin", "").strip()
    usuario_q = request.args.get("usuario", "").strip()

    stmt = select(Arqueo).order_by(Arqueo.fecha.desc(), Arqueo.id.desc())
    stmt = _filtrar_arqueos_usuario(stmt)

    if fecha_ini:
        stmt = stmt.where(Arqueo.fecha >= date.fromisoformat(fecha_ini))
    if fecha_fin:
        stmt = stmt.where(Arqueo.fecha <= date.fromisoformat(fecha_fin))
    if usuario_q and _es_admin():
        stmt = stmt.where(Arqueo.cajero.ilike(f"%{usuario_q}%"))

    arqueos = db.session.scalars(stmt).all()
    return render_template("reportes/historial_arqueos.html",
        arqueos=arqueos, fecha_ini=fecha_ini, fecha_fin=fecha_fin, usuario_q=usuario_q, es_admin=_es_admin(),
    )


@reportes_bp.get("/arqueos/<int:arqueo_id>/pdf")
@login_required
def arqueo_pdf(arqueo_id):
    arqueo = db.get_or_404(Arqueo, arqueo_id)
    empresa = _empresa()
    empresa_email = current_app.config.get("COMPANY_EMAIL", "")
    ahora = datetime.now()
    totales = arqueo.totales or {}
    no_efectivo = arqueo.no_efectivo or []
    contado = arqueo.facturas_contado or {}
    credito = arqueo.facturas_credito or []
    vales_list = arqueo.vales if hasattr(arqueo, 'vales') and arqueo.vales else []

    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    ancho, alto = A4
    ml, mr = 45, ancho - 45
    y = alto - 35
    page_num = [1]
    username = _usuario_actual()
    print_time = ahora.strftime('%d/%m/%Y %H:%M')

    def _draw_footer():
        pdf.setFont("Helvetica", 7)
        pdf.setFillColor(HexColor("#666666"))
        pdf.drawString(ml, 18, "ARQUEOB — Sistema de Arqueo de Caja")
        pdf.drawCentredString(ancho / 2, 18, f"Página {page_num[0]}")
        pdf.drawRightString(mr, 18, f"Impreso: {print_time} · {username}")
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.5)
        pdf.line(ml, 30, mr, 30)

    def _goto(new_y):
        nonlocal y
        y = new_y

    def _check_page(needed=60):
        nonlocal y
        if y < needed:
            _draw_footer()
            pdf.showPage()
            page_num[0] += 1
            y = alto - 35

    def _hline():
        nonlocal y
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.5)
        pdf.line(ml, y, mr, y)
        y -= 4

    def _section(title):
        nonlocal y
        y -= 6
        _check_page(40)
        pdf.setFillColor(_C_PRIMARY)
        pdf.rect(ml, y - 14, mr - ml, 16, fill=1, stroke=0)
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(ml + 8, y - 10, title)
        y -= 20

    def _tbl_header(cols, labels):
        nonlocal y
        _check_page(30)
        pdf.setFillColor(_C_HEADER_BG)
        pdf.rect(ml, y - 12, mr - ml, 14, fill=1, stroke=0)
        pdf.setFillColor(black)
        pdf.setFont("Helvetica-Bold", 7.5)
        for x, label in zip(cols, labels):
            if x < ancho / 2:
                pdf.drawString(x, y - 9, label)
            else:
                pdf.drawRightString(x, y - 9, label)
        y -= 14

    def _tbl_row(cols, vals, bolds=None, right_from=None):
        nonlocal y
        _check_page(16)
        pdf.setFillColor(black)
        for i, (x, v) in enumerate(zip(cols, vals)):
            is_bold = bolds and i in bolds
            pdf.setFont("Helvetica-Bold" if is_bold else "Helvetica", 7.5)
            if right_from and i >= right_from:
                pdf.drawRightString(x, y - 9, v)
            else:
                pdf.drawString(x, y - 9, v)
        y -= 12

    def _tbl_row_zebra(cols, vals, idx, bolds=None, right_from=None):
        nonlocal y
        if idx % 2 == 1:
            pdf.setFillColor(_C_ZEBRA)
            pdf.rect(ml, y - 12, mr - ml, 13, fill=1, stroke=0)
        _tbl_row(cols, vals, bolds, right_from)

    def _tbl_total(label, val, cols):
        nonlocal y
        _check_page(18)
        pdf.setFillColor(HexColor("#E3EDF5"))
        pdf.rect(ml, y - 13, mr - ml, 15, fill=1, stroke=0)
        pdf.setFillColor(black)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(cols[0] + 2, y - 10, label)
        pdf.drawRightString(cols[-1], y - 10, val)
        y -= 15

    # ─────────────────────────────────────────────────────────────────
    # 1. ENCABEZADO
    # ─────────────────────────────────────────────────────────────────
    pdf.setFont("Helvetica-Bold", 15)
    pdf.setFillColor(_C_PRIMARY)
    pdf.drawCentredString(ancho / 2, y, empresa["nombre"])
    y -= 14
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(HexColor("#444444"))
    info_parts = [f"RNC {empresa['rnc']}", empresa["direccion"], f"Tel. {empresa['telefono']}"]
    if empresa_email:
        info_parts.append(empresa_email)
    pdf.drawCentredString(ancho / 2, y, " · ".join(info_parts))
    y -= 18

    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(_C_PRIMARY)
    pdf.drawCentredString(ancho / 2, y, "ARQUEO DE CAJA")
    y -= 16
    pdf.setFillColor(_C_HEADER_BG)
    pdf.rect(ml, y - 14, mr - ml, 16, fill=1, stroke=0)
    pdf.setFillColor(black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(ml + 8, y - 10, f"Fecha: {arqueo.fecha.strftime('%d/%m/%Y')}")
    pdf.drawString(ml + 180, y - 10, f"Cajero: {arqueo.cajero}")
    pdf.drawString(ml + 350, y - 10, f"Turno: {arqueo.turno}")
    pdf.drawRightString(mr - 8, y - 10, f"Hora: {ahora.strftime('%H:%M')}")
    y -= 22

    # ─────────────────────────────────────────────────────────────────
    # 2. TARJETAS DE RESUMEN (Dashboard)
    # ─────────────────────────────────────────────────────────────────
    efectivo = totales.get("efectivo", 0)
    tarjetas = totales.get("tarjetas", 0)
    transferencias = totales.get("transferencias", 0)
    cheques = totales.get("cheques", 0)
    vales_t = totales.get("vales", 0)
    otros_ne = totales.get("otros_ne", 0)
    no_efectivo_total = totales.get("no_efectivo", 0)
    contado_total = totales.get("contado", 0)
    credito_total = totales.get("credito", 0)
    vendido = contado_total + credito_total
    balance = totales.get("balance", 0)
    diferencia = totales.get("diferencia", 0)

    card_w = (mr - ml - 32) / 5
    card_h = 48
    bar_h = 16
    cards = [
        ("VENTA TOTAL", vendido, _C_PRIMARY),
        ("EFECTIVO", efectivo, _C_GREEN),
        ("NO EFECTIVO", no_efectivo_total, _C_YELLOW),
        ("CRÉDITO", credito_total, HexColor("#8E44AD")),
        ("DIFERENCIA", diferencia, _C_GREEN if diferencia == 0 else (_C_YELLOW if diferencia > 0 else _C_RED)),
    ]
    for i, (label, amount, color) in enumerate(cards):
        cx = ml + i * (card_w + 8)
        pdf.setFillColor(_C_C_CARD_BG)
        pdf.roundRect(cx, y - card_h, card_w, card_h, 4, fill=1, stroke=0)
        pdf.setFillColor(color)
        pdf.roundRect(cx, y - bar_h, card_w, bar_h, 4, fill=1, stroke=0)
        pdf.rect(cx, y - bar_h, bar_h, 3, fill=1, stroke=0)
        pdf.rect(cx + card_w - bar_h, y - bar_h, bar_h, 3, fill=1, stroke=0)
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 6.5)
        pdf.drawCentredString(cx + card_w / 2, y - bar_h + 5, label)
        pdf.setFillColor(black)
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(cx + card_w / 2, y - card_h + 10, f"RD$ {amount:,.2f}")
    y -= card_h + 10

    # ── Indicador de cuadre ──────────────────────────────────────────
    if diferencia == 0:
        estado_label = "CUADRADO"
        estado_color = _C_GREEN
    elif diferencia > 0:
        estado_label = f"SOBRA  RD$ {diferencia:,.2f}"
        estado_color = _C_YELLOW
    else:
        estado_label = f"FALTA  RD$ {abs(diferencia):,.2f}"
        estado_color = _C_RED

    pdf.setFillColor(estado_color)
    pdf.roundRect(ml, y - 20, mr - ml, 22, 4, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(ancho / 2, y - 15, estado_label)
    y -= 30

    # ─────────────────────────────────────────────────────────────────
    # 3. DESGLOSE DEL EFECTIVO
    # ─────────────────────────────────────────────────────────────────
    _section("DESGLOSE DE EFECTIVO")
    col_d, col_c, col_t = ml + 5, ml + 140, mr - 5
    _tbl_header([col_d, col_c, col_t], ["Denominación", "Cantidad", "Total"])
    for idx, (denom, cant) in enumerate(arqueo.conteos.items()):
        total_denom = int(denom) * cant
        _check_page(16)
        _tbl_row_zebra(
            [col_d, col_c, col_t],
            [f"RD$ {int(denom):,}", str(cant), f"RD$ {total_denom:,.2f}"],
            idx, right_from=2,
        )
    _tbl_total("TOTAL EFECTIVO", f"RD$ {efectivo:,.2f}", [col_d, col_t])

    # ─────────────────────────────────────────────────────────────────
    # 4. FORMAS DE PAGO NO EFECTIVO
    # ─────────────────────────────────────────────────────────────────
    _check_page(60)
    _section("FORMAS DE PAGO NO EFECTIVO")
    grupos = {"Tarjetas": [], "Transferencias": [], "Cheques": [], "Vales": [], "Otros": []}
    for item in no_efectivo:
        tipo = item.get("tipo", "Otros")
        grupos.get(tipo, grupos["Otros"]).append(item)
    for item in vales_list:
        grupos["Vales"].append({"tipo": "Vales", "concepto": item.get("concepto", ""), "monto": item.get("monto", 0), "banco": "", "numero": ""})

    for tipo, items in grupos.items():
        if not items:
            continue
        _check_page(40)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.setFillColor(_C_PRIMARY)
        pdf.drawString(ml + 5, y, tipo)
        y -= 12

        if tipo in ("Transferencias", "Cheques"):
            ref_label = "Referencia" if tipo == "Transferencias" else "Nº Cheque"
            _tbl_header([col_d, col_c, col_t], ["Banco", ref_label, "Monto"])
            total_g = 0
            for idx, it in enumerate(items):
                _check_page(16)
                total_g += it.get("monto", 0)
                _tbl_row_zebra(
                    [col_d, col_c, col_t],
                    [it.get("banco", "")[:28], it.get("numero", "")[:22], f"RD$ {it.get('monto', 0):,.2f}"],
                    idx, right_from=2,
                )
            _tbl_total(f"Total {tipo}", f"RD$ {total_g:,.2f}", [col_d, col_t])
        else:
            _tbl_header([col_d, col_t], ["Concepto", "Monto"])
            total_g = 0
            for idx, it in enumerate(items):
                _check_page(16)
                total_g += it.get("monto", 0)
                _tbl_row_zebra(
                    [col_d, col_t],
                    [(it.get("concepto", "") or "")[:50], f"RD$ {it.get('monto', 0):,.2f}"],
                    idx, right_from=1,
                )
            _tbl_total(f"Total {tipo}", f"RD$ {total_g:,.2f}", [col_d, col_t])

    # ─────────────────────────────────────────────────────────────────
    # 5. FACTURAS AL CONTADO
    # ─────────────────────────────────────────────────────────────────
    _check_page(80)
    _section("FACTURAS AL CONTADO")
    for key, label in [("sc", "Sin Comprobante"), ("cc", "Con Comprobante"), ("ri", "Recibos de Ingreso")]:
        fc = contado.get(key)
        if not fc or not isinstance(fc, dict):
            continue
        _check_page(40)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.setFillColor(_C_PRIMARY)
        pdf.drawString(ml + 5, y, label)
        y -= 12
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(black)
        pdf.drawString(ml + 15, y, f"Monto Total:  RD$ {fc.get('monto', 0):,.2f}")
        pdf.drawString(ml + 230, y, f"Desde: {fc.get('desde', '') or '—'}")
        pdf.drawRightString(mr, y, f"Hasta: {fc.get('hasta', '') or '—'}")
        y -= 14
        _hline()

    # ─────────────────────────────────────────────────────────────────
    # 6. FACTURAS A CRÉDITO
    # ─────────────────────────────────────────────────────────────────
    if credito:
        _check_page(60)
        _section("FACTURAS A CRÉDITO")
        col_num = ml + 5
        col_cliente = ml + 65
        col_con = ml + 200
        col_mon = mr - 5
        _tbl_header([col_num, col_cliente, col_con, col_mon], ["Nº Factura", "Cliente", "Concepto", "Total"])
        total_cr = 0
        for idx, fc in enumerate(credito):
            _check_page(16)
            total_cr += fc.get("monto", 0)
            _tbl_row_zebra(
                [col_num, col_cliente, col_con, col_mon],
                [str(fc.get("numero", ""))[:14], str(fc.get("cliente", ""))[:20], str(fc.get("concepto", ""))[:28], f"RD$ {fc.get('monto', 0):,.2f}"],
                idx, right_from=3,
            )
        _tbl_total(f"Total: {len(credito)} factura(s)", f"RD$ {total_cr:,.2f}", [col_num, col_mon])

    # ─────────────────────────────────────────────────────────────────
    # 7. TOTALES FINALES
    # ─────────────────────────────────────────────────────────────────
    _check_page(80)
    _hline()
    y -= 4
    pdf.setFillColor(_C_PRIMARY)
    pdf.rect(ml, y - 18, mr - ml, 20, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(ml + 10, y - 13, "TOTAL GENERAL DEL ARQUEO")
    pdf.drawRightString(mr - 10, y - 13, f"RD$ {balance:,.2f}")
    y -= 28

    # ─────────────────────────────────────────────────────────────────
    # 8. FIRMAS
    # ─────────────────────────────────────────────────────────────────
    y -= 10
    sig_w = (mr - ml) / 3
    firmas = ["Preparado por", "Revisado por", "Autorizado por"]
    for i, titulo in enumerate(firmas):
        sx = ml + i * sig_w + sig_w / 2
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.5)
        pdf.line(sx - 55, y, sx + 55, y)
        y -= 12
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(HexColor("#555555"))
        pdf.drawCentredString(sx, y, titulo)

    _draw_footer()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"arqueo_{arqueo.id}.pdf", mimetype="application/pdf")


# ── API: buscar clientes para autocompletado ─────────────────────────

@reportes_bp.get("/api/clientes")
@login_required
def api_clientes():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    patron = f"%{q}%"
    clientes = db.session.scalars(
        select(Cliente).where(or_(Cliente.nombre.ilike(patron), Cliente.telefono.ilike(patron), Cliente.rnc_cedula.ilike(patron))).order_by(Cliente.nombre).limit(10)
    ).all()
    return jsonify([{"id": c.id, "nombre": c.nombre, "telefono": c.telefono, "rnc_cedula": c.rnc_cedula} for c in clientes])


# ── 5. Reimpresión de Recibos ────────────────────────────────────────

@reportes_bp.get("/recibos")
@login_required
def recibos():
    q = request.args.get("q", "").strip()
    cliente_q = request.args.get("cliente", "").strip()
    fecha_ini = request.args.get("fecha_ini", "").strip()
    fecha_fin = request.args.get("fecha_fin", "").strip()
    usuario_q = request.args.get("usuario", "").strip()
    tipo_cobro = request.args.get("tipo_cobro", "").strip()

    recibos = []

    # Cobros por Facturas (model Pago)
    stmt_pagos = select(Pago).join(Cliente).order_by(Pago.fecha.desc())
    stmt_pagos = _filtrar_pagos_usuario(stmt_pagos)

    if q:
        stmt_pagos = stmt_pagos.where(or_(
            func.cast(Pago.id, db.String).ilike(f"%{q}%"),
            Pago.concepto_manual.ilike(f"%{q}%"),
        ))
    if cliente_q:
        stmt_pagos = stmt_pagos.where(Cliente.nombre.ilike(f"%{cliente_q}%"))
    if fecha_ini:
        stmt_pagos = stmt_pagos.where(func.date(Pago.fecha) >= date.fromisoformat(fecha_ini))
    if fecha_fin:
        stmt_pagos = stmt_pagos.where(func.date(Pago.fecha) <= date.fromisoformat(fecha_fin))
    if usuario_q and _es_admin():
        stmt_pagos = stmt_pagos.where(Pago.usuario.ilike(f"%{usuario_q}%"))

    if tipo_cobro != "Informal":
        for p in db.session.scalars(stmt_pagos).all():
            concepto = p.concepto_manual or ", ".join(d.factura.numero for d in p.detalles if d.factura)
            recibos.append({
                "id": p.id,
                "numero": f"R-{p.id:05d}",
                "fecha": p.fecha,
                "cliente": p.cliente.nombre,
                "tipo_cobro": "Factura",
                "monto": p.monto_pagado,
                "usuario": p.usuario,
                "forma_pago": p.forma_pago.value,
                "concepto": concepto,
                "url_pdf": url_for("cobros.recibo_pdf", pago_id=p.id),
            })

    # Cobros Informales (model CobroInformal)
    stmt_inf = select(CobroInformal).join(Cliente).order_by(CobroInformal.creado_en.desc())
    if not _es_admin():
        # Admin sees all; cajero sees only their own via abonos
        stmt_inf = stmt_inf.join(AbonoCobroInformal).where(AbonoCobroInformal.usuario == _usuario_actual())

    if q:
        stmt_inf = stmt_inf.where(or_(
            func.cast(CobroInformal.id, db.String).ilike(f"%{q}%"),
            CobroInformal.concepto.ilike(f"%{q}%"),
        ))
    if cliente_q:
        stmt_inf = stmt_inf.where(Cliente.nombre.ilike(f"%{cliente_q}%"))
    if fecha_ini:
        stmt_inf = stmt_inf.where(func.date(CobroInformal.creado_en) >= date.fromisoformat(fecha_ini))
    if fecha_fin:
        stmt_inf = stmt_inf.where(func.date(CobroInformal.creado_en) <= date.fromisoformat(fecha_fin))

    if tipo_cobro != "Factura":
        seen_inf = set()
        for ci in db.session.scalars(stmt_inf).all():
            if ci.id in seen_inf:
                continue
            seen_inf.add(ci.id)
            monto_pagado = ci.monto_total - ci.saldo_pendiente
            primer_abono = ci.abonos[0] if ci.abonos else None
            usuario = primer_abono.usuario if primer_abono else "Sistema"
            forma_pago = primer_abono.forma_pago.value if primer_abono else "N/A"
            recibos.append({
                "id": f"inf-{ci.id}",
                "numero": f"CI-{ci.id:05d}",
                "fecha": ci.creado_en,
                "cliente": ci.cliente.nombre,
                "tipo_cobro": "Informal",
                "monto": monto_pagado,
                "usuario": usuario,
                "forma_pago": forma_pago,
                "concepto": ci.concepto,
                "url_pdf": url_for("cobros_informales.recibo", cobro_id=ci.id),
            })

    recibos.sort(key=lambda r: r["fecha"], reverse=True)

    return render_template("reportes/recibos.html",
        recibos=recibos, q=q, cliente_q=cliente_q, fecha_ini=fecha_ini, fecha_fin=fecha_fin,
        usuario_q=usuario_q, tipo_cobro=tipo_cobro, es_admin=_es_admin(),
    )
