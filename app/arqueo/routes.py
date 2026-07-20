from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import io
from flask import Blueprint, current_app, jsonify, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, HexColor, white, black
from reportlab.pdfgen import canvas
from sqlalchemy import func, select

from app.extensions import db
from app.models import Arqueo

arqueo_bp = Blueprint("arqueo", __name__)
DENOMINACIONES = [2000, 1000, 500, 200, 100, 50, 25, 10, 5, 1]

# ── Colores corporativos ────────────────────────────────────────────
_C_PRIMARY    = HexColor("#1B3A5C")
_C_HEADER_BG  = HexColor("#E8EDF2")
_C_ZEBRA      = HexColor("#F4F6F8")
_C_BORDER     = HexColor("#C5CED6")
_C_GREEN      = HexColor("#27AE60")
_C_YELLOW     = HexColor("#F39C12")
_C_RED        = HexColor("#E74C3C")
_C_CARD_BG    = HexColor("#F8F9FA")


def calcular_totales(conteos, no_efectivo, contado, credito, vales):
    efectivo = sum(Decimal(str(d)) * Decimal(str(c or 0)) for d, c in conteos.items())
    tarjetas = sum(Decimal(str(item.get("monto", 0))) for item in no_efectivo if item.get("tipo") == "Tarjetas")
    transferencias = sum(Decimal(str(item.get("monto", 0))) for item in no_efectivo if item.get("tipo") == "Transferencias")
    cheques = sum(Decimal(str(item.get("monto", 0))) for item in no_efectivo if item.get("tipo") == "Cheques")
    vales_total = sum(Decimal(str(item.get("monto", 0))) for v in vales for item in [v])
    otros_ne = sum(Decimal(str(item.get("monto", 0))) for item in no_efectivo if item.get("tipo") not in ("Tarjetas", "Transferencias", "Cheques"))
    no_efectivo_total = tarjetas + transferencias + cheques + vales_total + otros_ne
    contado_total = sum(Decimal(str(item.get("monto", 0))) for item in contado.values())
    credito_total = sum(Decimal(str(item.get("monto", 0))) for item in credito)
    facturado = contado_total + credito_total
    return {
        "efectivo": float(efectivo),
        "tarjetas": float(tarjetas),
        "transferencias": float(transferencias),
        "cheques": float(cheques),
        "vales": float(vales_total),
        "otros_ne": float(otros_ne),
        "no_efectivo": float(no_efectivo_total),
        "balance": float(efectivo + no_efectivo_total),
        "facturado": float(facturado),
        "contado": float(contado_total),
        "credito": float(credito_total),
        "diferencia": float(efectivo + no_efectivo_total - facturado),
        "cant_contado": len(contado),
        "cant_credito": len(credito),
        "cant_vales": len(vales),
        "cant_no_efectivo": len(no_efectivo) + len(vales),
    }


@arqueo_bp.route("/", methods=["GET", "POST"])
@login_required
def formulario():
    if request.method == "POST":
        try:
            cajero = request.form.get("cajero", "").strip()
            if not cajero:
                raise ValueError("El nombre del cajero es obligatorio.")
            conteos = {str(d): int(request.form.get(f"denom_{d}", 0) or 0) for d in DENOMINACIONES}
            if any(v < 0 for v in conteos.values()):
                raise ValueError("Las cantidades no pueden ser negativas.")

            no_efectivo = []
            for tipo, monto in zip(request.form.getlist("tipo_no_efectivo[]"), request.form.getlist("monto_no_efectivo[]")):
                if monto.strip():
                    valor = Decimal(monto)
                    if valor < 0:
                        raise ValueError("Los montos no pueden ser negativos.")
                    no_efectivo.append({"tipo": tipo, "monto": float(valor)})

            contado = {}
            for tipo, key in [("sc", "Sin Comprobante"), ("cc", "Con Comprobante"), ("ri", "Recibos de Ingreso")]:
                monto = request.form.get(f"contado_{tipo}_monto", "0").strip()
                desde = request.form.get(f"contado_{tipo}_desde", "").strip()
                hasta = request.form.get(f"contado_{tipo}_hasta", "").strip()
                if monto:
                    valor = Decimal(monto)
                    if valor < 0:
                        raise ValueError("Los montos no pueden ser negativos.")
                    contado[tipo] = {"monto": float(valor), "desde": desde, "hasta": hasta, "key": key}

            vales = []
            for concepto, monto in zip(request.form.getlist("vale_concepto[]"), request.form.getlist("vale_monto[]")):
                if monto.strip():
                    valor = Decimal(monto)
                    if valor < 0:
                        raise ValueError("Los montos no pueden ser negativos.")
                    vales.append({"concepto": concepto.strip(), "monto": float(valor)})

            credito = []
            for desde, hasta, cantidad, monto in zip(
                request.form.getlist("credito_desde[]"),
                request.form.getlist("credito_hasta[]"),
                request.form.getlist("credito_cantidad[]"),
                request.form.getlist("credito_monto[]"),
            ):
                if monto.strip():
                    valor = Decimal(monto)
                    if not valor or valor <= 0:
                        raise ValueError("Las facturas a crédito requieren monto positivo.")
                    credito.append({
                        "desde": desde.strip(),
                        "hasta": hasta.strip(),
                        "cantidad": int(cantidad or 0),
                        "monto": float(valor),
                    })

            totales = calcular_totales(conteos, no_efectivo, contado, credito, vales)
            arqueo = Arqueo(
                fecha=date.fromisoformat(request.form["fecha"]),
                cajero=cajero,
                turno=request.form["turno"],
                fondo_inicial=Decimal(request.form.get("fondo_inicial", 0) or 0),
                conteos=conteos,
                no_efectivo=no_efectivo,
                facturas_contado=contado,
                facturas_credito=credito,
                vales=vales,
                totales=totales,
            )
            db.session.add(arqueo)
            db.session.commit()
            return redirect(url_for("arqueo.reporte", arqueo_id=arqueo.id))
        except (ValueError, InvalidOperation) as exc:
            db.session.rollback()
            flash(f"No se pudo guardar el arqueo: {exc}", "danger")

    return render_template("arqueo/formulario.html", denominaciones=DENOMINACIONES, hoy=date.today().isoformat())


@arqueo_bp.get("/api/arqueos")
@login_required
def api_arqueos():
    fecha_ini = request.args.get("fecha_ini", "").strip()
    fecha_fin = request.args.get("fecha_fin", "").strip()
    usuario_q = request.args.get("usuario", "").strip()

    stmt = select(Arqueo).order_by(Arqueo.fecha.desc(), Arqueo.id.desc())
    if not current_user.is_admin:
        stmt = stmt.where(Arqueo.cajero == current_user.username)
    if fecha_ini:
        stmt = stmt.where(Arqueo.fecha >= date.fromisoformat(fecha_ini))
    if fecha_fin:
        stmt = stmt.where(Arqueo.fecha <= date.fromisoformat(fecha_fin))
    if usuario_q and current_user.is_admin:
        stmt = stmt.where(Arqueo.cajero.ilike(f"%{usuario_q}%"))

    arqueos = db.session.scalars(stmt.limit(50)).all()
    return jsonify([{
        "id": a.id,
        "fecha": a.fecha.isoformat(),
        "cajero": a.cajero,
        "turno": a.turno,
        "totales": a.totales,
    } for a in arqueos])


@arqueo_bp.get("/api/arqueo/<int:arqueo_id>")
@login_required
def api_arqueo_detalle(arqueo_id):
    arqueo = db.get_or_404(Arqueo, arqueo_id)
    return jsonify({
        "id": arqueo.id,
        "fecha": arqueo.fecha.isoformat(),
        "cajero": arqueo.cajero,
        "turno": arqueo.turno,
        "fondo_inicial": float(arqueo.fondo_inicial),
        "conteos": arqueo.conteos,
        "no_efectivo": arqueo.no_efectivo,
        "facturas_contado": arqueo.facturas_contado,
        "facturas_credito": arqueo.facturas_credito,
        "vales": arqueo.vales if hasattr(arqueo, 'vales') and arqueo.vales else [],
        "totales": arqueo.totales,
    })


@arqueo_bp.get("/<int:arqueo_id>/reporte.pdf")
@login_required
def reporte(arqueo_id):
    arqueo = db.get_or_404(Arqueo, arqueo_id)
    empresa_nombre = current_app.config.get("COMPANY_NAME", "")
    empresa_rnc = current_app.config.get("COMPANY_RNC", "")
    empresa_dir = current_app.config.get("COMPANY_ADDRESS", "")
    empresa_tel = current_app.config.get("COMPANY_PHONE", "")
    empresa_email = current_app.config.get("COMPANY_EMAIL", "")
    ahora = datetime.now()
    totales = arqueo.totales or {}
    no_efectivo = arqueo.no_efectivo or []
    contado = arqueo.facturas_contado or {}
    credito = arqueo.facturas_credito or []
    vales = arqueo.vales if hasattr(arqueo, 'vales') and arqueo.vales else []

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    ancho, alto = A4
    ml, mr = 45, ancho - 45
    y = alto - 35
    page_num = [1]
    username = current_user.username if current_user.is_authenticated else "Sistema"
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
    pdf.drawCentredString(ancho / 2, y, empresa_nombre)
    y -= 14
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(HexColor("#444444"))
    info_parts = [f"RNC {empresa_rnc}", empresa_dir, f"Tel. {empresa_tel}"]
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
    vales_total = totales.get("vales", 0)
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
        pdf.setFillColor(_C_CARD_BG)
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
        if tipo in grupos:
            grupos[tipo].append(item)
        else:
            grupos["Otros"].append(item)
    for item in vales:
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
            total_grupo = 0
            for idx, it in enumerate(items):
                _check_page(16)
                total_grupo += it.get("monto", 0)
                _tbl_row_zebra(
                    [col_d, col_c, col_t],
                    [it.get("banco", "")[:28], it.get("numero", "")[:22], f"RD$ {it.get('monto', 0):,.2f}"],
                    idx, right_from=2,
                )
            _tbl_total(f"Total {tipo}", f"RD$ {total_grupo:,.2f}", [col_d, col_t])
        else:
            _tbl_header([col_d, col_t], ["Concepto", "Monto"])
            total_grupo = 0
            for idx, it in enumerate(items):
                _check_page(16)
                total_grupo += it.get("monto", 0)
                _tbl_row_zebra(
                    [col_d, col_t],
                    [(it.get("concepto", "") or "")[:50], f"RD$ {it.get('monto', 0):,.2f}"],
                    idx, right_from=1,
                )
            _tbl_total(f"Total {tipo}", f"RD$ {total_grupo:,.2f}", [col_d, col_t])

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
        monto = fc.get("monto", 0)
        desde = fc.get("desde", "")
        hasta = fc.get("hasta", "")
        pdf.setFont("Helvetica-Bold", 8)
        pdf.setFillColor(_C_PRIMARY)
        pdf.drawString(ml + 5, y, label)
        y -= 12
        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(black)
        pdf.drawString(ml + 15, y, f"Monto Total:  RD$ {monto:,.2f}")
        pdf.drawString(ml + 230, y, f"Desde: {desde or '—'}")
        pdf.drawRightString(mr, y, f"Hasta: {hasta or '—'}")
        y -= 14
        _hline()

    # ─────────────────────────────────────────────────────────────────
    # 6. FACTURAS A CRÉDITO
    # ─────────────────────────────────────────────────────────────────
    if credito:
        _check_page(60)
        _section("FACTURAS A CRÉDITO")
        col_num, col_cli, col_con, col_mon = ml + 5, ml + 65, ml + 200, mr - 5
        _tbl_header([col_num, col_cli, col_con, col_mon], ["Nº Factura", "Cliente", "Concepto", "Total"])
        total_cr = 0
        for idx, fc in enumerate(credito):
            _check_page(16)
            total_cr += fc.get("monto", 0)
            _tbl_row_zebra(
                [col_num, col_cli, col_con, col_mon],
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
