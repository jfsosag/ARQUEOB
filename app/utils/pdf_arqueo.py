import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas


_C_PRIMARY    = HexColor("#1B3A5C")
_C_HEADER_BG  = HexColor("#E8EDF2")
_C_ZEBRA      = HexColor("#F4F6F8")
_C_BORDER     = HexColor("#C5CED6")
_C_GREEN      = HexColor("#27AE60")
_C_YELLOW     = HexColor("#F39C12")
_C_RED        = HexColor("#E74C3C")
_C_CARD_BG    = HexColor("#F8F9FA")
_C_TOTAL_BG   = HexColor("#E3EDF5")
_C_PURPLE     = HexColor("#8E44AD")


def _wrap(text, max_chars):
    words = str(text).split()
    lines, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 > max_chars:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}".strip()
    return lines + ([current] if current else [])


def generar_arqueo_pdf(arqueo, empresa, username, ahora):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    ancho, alto = A4
    ml, mr = 40, ancho - 40
    y = alto - 30
    page_num = [1]
    print_time = ahora.strftime('%d/%m/%Y %H:%M')

    totales = arqueo.totales or {}
    no_efectivo = arqueo.no_efectivo or []
    contado = arqueo.facturas_contado or {}
    credito = arqueo.facturas_credito or []
    vales = getattr(arqueo, 'vales', None) or []

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

    # ── Helper functions ──────────────────────────────────────────────
    def _draw_footer():
        pdf.setFont("Helvetica", 6.5)
        pdf.setFillColor(HexColor("#666666"))
        pdf.drawString(ml, 15, "ARQUEOB — Sistema de Arqueo de Caja")
        pdf.drawCentredString(ancho / 2, 15, f"Página {page_num[0]}")
        pdf.drawRightString(mr, 15, f"Impreso: {print_time} · {username}")
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.4)
        pdf.line(ml, 25, mr, 25)

    def _check_page(needed=50):
        nonlocal y
        if y < needed:
            _draw_footer()
            pdf.showPage()
            page_num[0] += 1
            y = alto - 30

    def _section(title):
        nonlocal y
        y -= 4
        _check_page(30)
        pdf.setFillColor(_C_PRIMARY)
        pdf.rect(ml, y - 12, mr - ml, 14, fill=1, stroke=0)
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(ml + 6, y - 9, title)
        y -= 17

    def _tbl_header(cols, labels):
        nonlocal y
        _check_page(24)
        pdf.setFillColor(_C_HEADER_BG)
        pdf.rect(ml, y - 10, mr - ml, 12, fill=1, stroke=0)
        pdf.setFillColor(black)
        pdf.setFont("Helvetica-Bold", 7)
        for x, label in zip(cols, labels):
            if x < ancho / 2:
                pdf.drawString(x, y - 8, label)
            else:
                pdf.drawRightString(x, y - 8, label)
        y -= 12

    def _tbl_row(cols, vals, bolds=None, right_from=None):
        nonlocal y
        _check_page(14)
        pdf.setFillColor(black)
        for i, (x, v) in enumerate(zip(cols, vals)):
            is_bold = bolds and i in bolds
            pdf.setFont("Helvetica-Bold" if is_bold else "Helvetica", 7)
            if right_from and i >= right_from:
                pdf.drawRightString(x, y - 8, v)
            else:
                pdf.drawString(x, y - 8, v)
        y -= 11

    def _tbl_row_zebra(cols, vals, idx, bolds=None, right_from=None):
        nonlocal y
        if idx % 2 == 1:
            pdf.setFillColor(_C_ZEBRA)
            pdf.rect(ml, y - 10, mr - ml, 11, fill=1, stroke=0)
        _tbl_row(cols, vals, bolds, right_from)

    def _tbl_total(label, val, cols):
        nonlocal y
        _check_page(16)
        pdf.setFillColor(_C_TOTAL_BG)
        pdf.rect(ml, y - 11, mr - ml, 13, fill=1, stroke=0)
        pdf.setFillColor(black)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawString(cols[0] + 2, y - 9, label)
        pdf.drawRightString(cols[-1], y - 9, val)
        y -= 13

    def _tbl_row_wrapped(cols, vals, idx, wrap_col=1, wrap_max=40):
        nonlocal y
        lines = _wrap(vals[wrap_col], wrap_max)
        row_h = 11 + (len(lines) - 1) * 10
        _check_page(row_h + 4)
        if idx % 2 == 1:
            pdf.setFillColor(_C_ZEBRA)
            pdf.rect(ml, y - row_h + 1, mr - ml, row_h, fill=1, stroke=0)
        pdf.setFillColor(black)
        for i, (x, v) in enumerate(zip(cols, vals)):
            if i == wrap_col:
                pdf.setFont("Helvetica", 7)
                for li, line in enumerate(lines):
                    pdf.drawString(x, y - 8 - li * 10, line)
            else:
                pdf.setFont("Helvetica", 7)
                pdf.drawString(x, y - 8, v)
        y -= row_h

    # ═══════════════════════════════════════════════════════════════════
    # 1. ENCABEZADO
    # ═══════════════════════════════════════════════════════════════════
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(_C_PRIMARY)
    pdf.drawCentredString(ancho / 2, y, empresa.get("nombre", ""))
    y -= 12
    pdf.setFont("Helvetica", 7.5)
    pdf.setFillColor(HexColor("#444444"))
    info_parts = []
    if empresa.get("rnc"):
        info_parts.append(f"RNC {empresa['rnc']}")
    if empresa.get("direccion"):
        info_parts.append(empresa["direccion"])
    if empresa.get("telefono"):
        info_parts.append(f"Tel. {empresa['telefono']}")
    if empresa.get("email"):
        info_parts.append(empresa["email"])
    if info_parts:
        pdf.drawCentredString(ancho / 2, y, " · ".join(info_parts))
        y -= 12

    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(_C_PRIMARY)
    pdf.drawCentredString(ancho / 2, y, "ARQUEO DE CAJA")
    y -= 14
    pdf.setFillColor(_C_HEADER_BG)
    pdf.rect(ml, y - 12, mr - ml, 14, fill=1, stroke=0)
    pdf.setFillColor(black)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(ml + 6, y - 9, f"Fecha: {arqueo.fecha.strftime('%d/%m/%Y')}")
    pdf.drawString(ml + 160, y - 9, f"Cajero: {arqueo.cajero or ''}")
    pdf.drawString(ml + 310, y - 9, f"Turno: {arqueo.turno or ''}")
    pdf.drawRightString(mr - 6, y - 9, f"Hora: {ahora.strftime('%H:%M')}")
    y -= 18

    # ═══════════════════════════════════════════════════════════════════
    # 2. TARJETAS DE RESUMEN
    # ═══════════════════════════════════════════════════════════════════
    card_w = (mr - ml - 32) / 5
    card_h = 40
    bar_h = 14
    cards = [
        ("VENTA TOTAL", vendido, _C_PRIMARY),
        ("EFECTIVO", efectivo, _C_GREEN),
        ("NO EFECTIVO", no_efectivo_total, _C_YELLOW),
        ("CRÉDITO", credito_total, _C_PURPLE),
        ("DIFERENCIA", diferencia, _C_GREEN if diferencia == 0 else (_C_YELLOW if diferencia > 0 else _C_RED)),
    ]
    for i, (label, amount, color) in enumerate(cards):
        cx = ml + i * (card_w + 8)
        pdf.setFillColor(_C_CARD_BG)
        pdf.roundRect(cx, y - card_h, card_w, card_h, 3, fill=1, stroke=0)
        pdf.setFillColor(color)
        pdf.roundRect(cx, y - bar_h, card_w, bar_h, 3, fill=1, stroke=0)
        pdf.rect(cx, y - bar_h, 3, 3, fill=1, stroke=0)
        pdf.rect(cx + card_w - 3, y - bar_h, 3, 3, fill=1, stroke=0)
        pdf.setFillColor(white)
        pdf.setFont("Helvetica-Bold", 6)
        pdf.drawCentredString(cx + card_w / 2, y - bar_h + 4, label)
        pdf.setFillColor(black)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawCentredString(cx + card_w / 2, y - card_h + 8, f"RD$ {amount:,.2f}")
    y -= card_h + 6

    # ── Indicador de cuadre (grande y llamativo) ──────────────────────
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
    pdf.roundRect(ml, y - 22, mr - ml, 24, 4, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(ancho / 2, y - 17, estado_label)
    y -= 30

    # ═══════════════════════════════════════════════════════════════════
    # 3. DESGLOSE DE EFECTIVO
    # ═══════════════════════════════════════════════════════════════════
    _section("DESGLOSE DE EFECTIVO")
    col_d, col_c, col_t = ml + 5, ml + 140, mr - 5
    _tbl_header([col_d, col_c, col_t], ["Denominación", "Cantidad", "Total"])
    for idx, (denom, cant) in enumerate(arqueo.conteos.items()):
        total_denom = int(denom) * cant
        _check_page(14)
        _tbl_row_zebra(
            [col_d, col_c, col_t],
            [f"RD$ {int(denom):,}", str(cant), f"RD$ {total_denom:,.2f}"],
            idx, right_from=2,
        )
    _tbl_total("TOTAL EFECTIVO", f"RD$ {efectivo:,.2f}", [col_d, col_t])

    # ═══════════════════════════════════════════════════════════════════
    # 4. FORMAS DE PAGO NO EFECTIVO
    # ═══════════════════════════════════════════════════════════════════
    _check_page(50)
    _section("FORMAS DE PAGO NO EFECTIVO")
    grupos = {"Tarjetas": [], "Transferencias": [], "Cheques": [], "Vales": [], "Otros": []}
    for item in no_efectivo:
        tipo = item.get("tipo", "Otros")
        grupos.get(tipo, grupos["Otros"]).append(item)
    for item in vales:
        grupos["Vales"].append({"tipo": "Vales", "concepto": item.get("concepto", ""), "monto": item.get("monto", 0), "banco": "", "numero": ""})

    for tipo, items in grupos.items():
        if not items:
            continue
        _check_page(30)
        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.setFillColor(_C_PRIMARY)
        pdf.drawString(ml + 5, y, tipo)
        y -= 10

        if tipo in ("Transferencias", "Cheques"):
            ref_label = "Referencia" if tipo == "Transferencias" else "Nº Cheque"
            col_banco, col_ref, col_mon = ml + 5, ml + 180, mr - 5
            _tbl_header([col_banco, col_ref, col_mon], ["Banco", ref_label, "Monto"])
            total_grupo = 0
            for idx, it in enumerate(items):
                total_grupo += it.get("monto", 0)
                _tbl_row_wrapped(
                    [col_banco, col_ref, col_mon],
                    [it.get("banco", ""), it.get("numero", ""), f"RD$ {it.get('monto', 0):,.2f}"],
                    idx, wrap_col=0, wrap_max=32,
                )
            _tbl_total(f"Total {tipo}", f"RD$ {total_grupo:,.2f}", [col_banco, col_mon])
        else:
            col_con, col_mon = ml + 5, mr - 5
            _tbl_header([col_con, col_mon], ["Concepto", "Monto"])
            total_grupo = 0
            for idx, it in enumerate(items):
                total_grupo += it.get("monto", 0)
                _tbl_row_wrapped(
                    [col_con, col_mon],
                    [it.get("concepto", "") or "", f"RD$ {it.get('monto', 0):,.2f}"],
                    idx, wrap_col=0, wrap_max=70,
                )
            _tbl_total(f"Total {tipo}", f"RD$ {total_grupo:,.2f}", [col_con, col_mon])

    # ═══════════════════════════════════════════════════════════════════
    # 5. FACTURAS AL CONTADO (tabla)
    # ═══════════════════════════════════════════════════════════════════
    _check_page(50)
    _section("FACTURAS AL CONTADO")
    col_tipo_c, col_desde, col_hasta, col_monto_c = ml + 5, ml + 130, ml + 290, mr - 5
    _tbl_header([col_tipo_c, col_desde, col_hasta, col_monto_c], ["Tipo", "Desde", "Hasta", "Monto"])
    contado_rows = [
        ("Sin Comprobante", contado.get("sc")),
        ("Con Comprobante", contado.get("cc")),
        ("Recibos de Ingreso", contado.get("ri")),
    ]
    for idx, (label, fc) in enumerate(contado_rows):
        if not fc or not isinstance(fc, dict):
            continue
        monto = fc.get("monto", 0)
        if monto == 0 and not fc.get("desde") and not fc.get("hasta"):
            continue
        _check_page(14)
        _tbl_row_zebra(
            [col_tipo_c, col_desde, col_hasta, col_monto_c],
            [label, str(fc.get("desde", "") or "—"), str(fc.get("hasta", "") or "—"), f"RD$ {monto:,.2f}"],
            idx, right_from=3,
        )
    contado_sc = contado.get("sc", {})
    contado_cc = contado.get("cc", {})
    contado_ri = contado.get("ri", {})
    total_contado_sum = (contado_sc.get("monto", 0) if isinstance(contado_sc, dict) else 0) + \
                        (contado_cc.get("monto", 0) if isinstance(contado_cc, dict) else 0) + \
                        (contado_ri.get("monto", 0) if isinstance(contado_ri, dict) else 0)
    _tbl_total("TOTAL CONTADO", f"RD$ {total_contado_sum:,.2f}", [col_tipo_c, col_monto_c])

    # ═══════════════════════════════════════════════════════════════════
    # 6. FACTURAS A CRÉDITO
    # ═══════════════════════════════════════════════════════════════════
    if credito:
        _check_page(40)
        _section("FACTURAS A CRÉDITO")
        col_tipo_cr, col_num, col_mon_cr = ml + 5, ml + 150, mr - 5
        _tbl_header([col_tipo_cr, col_num, col_mon_cr], ["Tipo", "Nº Factura", "Total"])
        total_cr = 0
        for idx, fc in enumerate(credito):
            total_cr += fc.get("monto", 0)
            _tbl_row_zebra(
                [col_tipo_cr, col_num, col_mon_cr],
                [str(fc.get("tipo", ""))[:35], str(fc.get("numero", ""))[:30], f"RD$ {fc.get('monto', 0):,.2f}"],
                idx, right_from=2,
            )
        _tbl_total(f"Total: {len(credito)} factura(s)", f"RD$ {total_cr:,.2f}", [col_tipo_cr, col_mon_cr])

    # ═══════════════════════════════════════════════════════════════════
    # 7. TOTALES FINALES
    # ═══════════════════════════════════════════════════════════════════
    _check_page(50)
    y -= 2
    pdf.setStrokeColor(_C_BORDER)
    pdf.setLineWidth(0.4)
    pdf.line(ml, y, mr, y)
    y -= 6
    pdf.setFillColor(_C_PRIMARY)
    pdf.rect(ml, y - 16, mr - ml, 18, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(ml + 8, y - 12, "TOTAL GENERAL DEL ARQUEO")
    pdf.drawRightString(mr - 8, y - 12, f"RD$ {balance:,.2f}")
    y -= 24

    # ═══════════════════════════════════════════════════════════════════
    # 8. FIRMAS
    # ═══════════════════════════════════════════════════════════════════
    y -= 6
    sig_w = (mr - ml) / 3
    firmas = ["Preparado por", "Revisado por", "Autorizado por"]
    for i, titulo in enumerate(firmas):
        sx = ml + i * sig_w + sig_w / 2
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.4)
        pdf.line(sx - 50, y, sx + 50, y)
        y -= 10
        pdf.setFont("Helvetica", 7.5)
        pdf.setFillColor(HexColor("#555555"))
        pdf.drawCentredString(sx, y, titulo)

    _draw_footer()
    pdf.save()
    buffer.seek(0)
    return buffer
