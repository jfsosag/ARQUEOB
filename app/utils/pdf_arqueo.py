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

FONT = "Helvetica"
FONT_B = "Helvetica-Bold"
FS = 7          # font size filas
FS_HDR = 7      # font size headers
FS_TOTAL = 7.5  # font size totales
ROW_H = 11      # alto de fila
HDR_H = 12      # alto header
TOTAL_H = 13    # alto fila total
ZEBRA_H = 11    # alto fondo zebra


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
    W, H = A4
    ML, MR = 40, W - 40
    CW = MR - ML  # content width

    y = H - 30
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

    # ── Helpers ───────────────────────────────────────────────────────
    def _footer():
        pdf.setFont(FONT, 6.5)
        pdf.setFillColor(HexColor("#666666"))
        pdf.drawString(ML, 15, "ARQUEOB — Sistema de Arqueo de Caja")
        pdf.drawCentredString(W / 2, 15, f"Página {page_num[0]}")
        pdf.drawRightString(MR, 15, f"Impreso: {print_time} · {username}")
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.4)
        pdf.line(ML, 25, MR, 25)

    def _chk(need=50):
        nonlocal y
        if y < need:
            _footer()
            pdf.showPage()
            page_num[0] += 1
            y = H - 30

    def _sec(title):
        nonlocal y
        y -= 4
        _chk(28)
        pdf.setFillColor(_C_PRIMARY)
        pdf.rect(ML, y - 12, CW, 14, fill=1, stroke=0)
        pdf.setFillColor(white)
        pdf.setFont(FONT_B, 8)
        pdf.drawString(ML + 6, y - 9, title)
        y -= 17

    def _hdr(cols, labels):
        """Encabezado de tabla. cols = [(x, align), ...]"""
        nonlocal y
        _chk(22)
        pdf.setFillColor(_C_HEADER_BG)
        pdf.rect(ML, y - 10, CW, HDR_H, fill=1, stroke=0)
        pdf.setFillColor(black)
        pdf.setFont(FONT_B, FS_HDR)
        for (x, align), label in zip(cols, labels):
            if align == 'r':
                pdf.drawRightString(x, y - 8, label)
            else:
                pdf.drawString(x, y - 8, label)
        y -= HDR_H

    def _row(cols, vals):
        """Fila de datos. cols = [(x, align), ...]"""
        nonlocal y
        _chk(14)
        pdf.setFillColor(black)
        pdf.setFont(FONT, FS)
        for (x, align), v in zip(cols, vals):
            if align == 'r':
                pdf.drawRightString(x, y - 8, v)
            else:
                pdf.drawString(x, y - 8, v)
        y -= ROW_H

    def _row_z(cols, vals, idx):
        nonlocal y
        if idx % 2 == 1:
            pdf.setFillColor(_C_ZEBRA)
            pdf.rect(ML, y - 10, CW, ZEBRA_H, fill=1, stroke=0)
        _row(cols, vals)

    def _row_wrap(cols, vals, idx, wrap_i=0, wrap_max=40):
        """Fila con texto envuelto en la columna wrap_i."""
        nonlocal y
        lines = _wrap(vals[wrap_i], wrap_max)
        n = len(lines)
        rh = ROW_H + (n - 1) * 10
        _chk(rh + 4)
        if idx % 2 == 1:
            pdf.setFillColor(_C_ZEBRA)
            pdf.rect(ML, y - rh + 1, CW, rh, fill=1, stroke=0)
        pdf.setFillColor(black)
        pdf.setFont(FONT, FS)
        for i, ((x, align), v) in enumerate(zip(cols, vals)):
            if i == wrap_i:
                for li, line in enumerate(lines):
                    pdf.drawString(x, y - 8 - li * 10, line)
            elif align == 'r':
                pdf.drawRightString(x, y - 8, v)
            else:
                pdf.drawString(x, y - 8, v)
        y -= rh

    def _tot(label, val, left_x, right_x):
        nonlocal y
        _chk(16)
        pdf.setFillColor(_C_TOTAL_BG)
        pdf.rect(ML, y - 10, CW, TOTAL_H, fill=1, stroke=0)
        pdf.setFillColor(black)
        pdf.setFont(FONT_B, FS_TOTAL)
        pdf.drawString(left_x + 2, y - 8, label)
        pdf.drawRightString(right_x, y - 8, val)
        y -= TOTAL_H

    # ── Columnas base ─────────────────────────────────────────────────
    L = ML + 5       # left margin + padding
    R = MR - 5       # right margin - padding

    # ═══════════════════════════════════════════════════════════════════
    # 1. ENCABEZADO
    # ═══════════════════════════════════════════════════════════════════
    pdf.setFont(FONT_B, 14)
    pdf.setFillColor(_C_PRIMARY)
    pdf.drawCentredString(W / 2, y, empresa.get("nombre", ""))
    y -= 12
    pdf.setFont(FONT, 7.5)
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
        pdf.drawCentredString(W / 2, y, " · ".join(info_parts))
        y -= 12

    pdf.setFont(FONT_B, 12)
    pdf.setFillColor(_C_PRIMARY)
    pdf.drawCentredString(W / 2, y, "ARQUEO DE CAJA")
    y -= 14
    pdf.setFillColor(_C_HEADER_BG)
    pdf.rect(ML, y - 12, CW, 14, fill=1, stroke=0)
    pdf.setFillColor(black)
    pdf.setFont(FONT, 8)
    pdf.drawString(ML + 6, y - 9, f"Fecha: {arqueo.fecha.strftime('%d/%m/%Y')}")
    pdf.drawString(ML + 160, y - 9, f"Cajero: {arqueo.cajero or ''}")
    pdf.drawString(ML + 310, y - 9, f"Turno: {arqueo.turno or ''}")
    pdf.drawRightString(MR - 6, y - 9, f"Hora: {ahora.strftime('%H:%M')}")
    y -= 18

    # ═══════════════════════════════════════════════════════════════════
    # 2. TARJETAS DE RESUMEN
    # ═══════════════════════════════════════════════════════════════════
    card_w = (CW - 32) / 5
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
        cx = ML + i * (card_w + 8)
        pdf.setFillColor(_C_CARD_BG)
        pdf.roundRect(cx, y - card_h, card_w, card_h, 3, fill=1, stroke=0)
        pdf.setFillColor(color)
        pdf.roundRect(cx, y - bar_h, card_w, bar_h, 3, fill=1, stroke=0)
        pdf.rect(cx, y - bar_h, 3, 3, fill=1, stroke=0)
        pdf.rect(cx + card_w - 3, y - bar_h, 3, 3, fill=1, stroke=0)
        pdf.setFillColor(white)
        pdf.setFont(FONT_B, 6)
        pdf.drawCentredString(cx + card_w / 2, y - bar_h + 4, label)
        pdf.setFillColor(black)
        pdf.setFont(FONT_B, 8.5)
        pdf.drawCentredString(cx + card_w / 2, y - card_h + 8, f"RD$ {amount:,.2f}")
    y -= card_h + 6

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
    pdf.roundRect(ML, y - 22, CW, 24, 4, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont(FONT_B, 13)
    pdf.drawCentredString(W / 2, y - 17, estado_label)
    y -= 30

    # ═══════════════════════════════════════════════════════════════════
    # 3. DESGLOSE DE EFECTIVO
    # ═══════════════════════════════════════════════════════════════════
    _sec("DESGLOSE DE EFECTIVO")
    # Col 0: Denominación (izq), Col 1: Cantidad (centro), Col 2: Total (der)
    c_denom = (L, 'l')
    c_cant = (ML + CW * 0.65, 'c')  # 65% del ancho → centro
    c_tot = (R, 'r')
    c3 = [c_denom, c_cant, c_tot]
    _hdr(c3, ["Denominación", "Cantidad", "Total"])
    for idx, (denom, cant) in enumerate(arqueo.conteos.items()):
        total_denom = int(denom) * cant
        _chk(14)
        _row_z(c3, [f"RD$ {int(denom):,}", str(cant), f"RD$ {total_denom:,.2f}"], idx)
    _tot("TOTAL EFECTIVO", f"RD$ {efectivo:,.2f}", L, R)

    # ═══════════════════════════════════════════════════════════════════
    # 4. FORMAS DE PAGO NO EFECTIVO (listado simple)
    # ═══════════════════════════════════════════════════════════════════
    _chk(50)
    _sec("FORMAS DE PAGO NO EFECTIVO")
    grupos = {"Vales": [], "Tarjetas": [], "Transferencias": [], "Cheques": [], "Otros": []}
    for item in no_efectivo:
        tipo = item.get("tipo", "Otros")
        grupos.get(tipo, grupos["Otros"]).append(item)
    for item in vales:
        grupos["Vales"].append({"concepto": item.get("concepto", ""),
                                "monto": item.get("monto", 0), "banco": "", "numero": ""})

    for tipo, items in grupos.items():
        if not items:
            continue
        total_grupo = sum(it.get("monto", 0) for it in items)
        n_items = len(items)

        # ── Encabezado del grupo ──────────────────────────────────────
        _chk(20)
        pdf.setFont(FONT_B, 7.5)
        pdf.setFillColor(_C_PRIMARY)
        pdf.drawString(L, y, tipo)
        pdf.setFont(FONT, 7)
        pdf.setFillColor(HexColor("#666666"))
        pdf.drawString(L + pdf.stringWidth(tipo, FONT_B, 7.5) + 6, y,
                       f"({n_items} registro{'s' if n_items != 1 else ''})")
        pdf.setFillColor(black)
        y -= 8
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.3)
        pdf.line(L, y, R, y)
        y -= 4

        # ── Listado de ítems ──────────────────────────────────────────
        if tipo in ("Transferencias", "Cheques"):
            ref_label = "Ref." if tipo == "Transferencias" else "Nº Chq."
            c_monto = (ML + CW * 0.22, 'r')
            c_desc = (ML + CW * 0.24, 'l')
            c_ref = (R, 'l')
            for idx, it in enumerate(items):
                _chk(12)
                monto_str = f"RD$ {it.get('monto', 0):,.2f}"
                desc = it.get("concepto", "") or it.get("banco", "") or "—"
                ref = it.get("numero", "") or "—"
                pdf.setFont(FONT_B, 7)
                pdf.drawRightString(c_monto[0], y - 7, monto_str)
                pdf.setFont(FONT, 7)
                pdf.drawString(c_desc[0], y - 7, desc[:45])
                pdf.drawString(c_ref[0], y - 7, f"{ref_label}: {ref}")
                y -= 10
        else:
            c_monto = (ML + CW * 0.22, 'r')
            c_desc = (ML + CW * 0.24, 'l')
            for idx, it in enumerate(items):
                _chk(12)
                monto_str = f"RD$ {it.get('monto', 0):,.2f}"
                desc = it.get("concepto", "") or "—"
                pdf.setFont(FONT_B, 7)
                pdf.drawRightString(c_monto[0], y - 7, monto_str)
                pdf.setFont(FONT, 7)
                pdf.drawString(c_desc[0], y - 7, desc[:70])
                y -= 10

        # ── Total del grupo ───────────────────────────────────────────
        _chk(14)
        pdf.setFillColor(_C_TOTAL_BG)
        pdf.rect(ML, y - 10, CW, 12, fill=1, stroke=0)
        pdf.setFillColor(black)
        pdf.setFont(FONT_B, 7.5)
        pdf.drawString(L + 2, y - 8, f"Total {tipo}")
        pdf.drawRightString(R, y - 8, f"RD$ {total_grupo:,.2f}")
        y -= 14

    # ═══════════════════════════════════════════════════════════════════
    # 5. FACTURAS AL CONTADO
    # ═══════════════════════════════════════════════════════════════════
    _chk(50)
    _sec("FACTURAS AL CONTADO")
    contado_rows = [
        ("Sin Comprobante", contado.get("sc")),
        ("Con Comprobante", contado.get("cc")),
        ("Recibos de Ingreso", contado.get("ri")),
    ]
    for label, fc in contado_rows:
        if not fc or not isinstance(fc, dict):
            continue
        monto = fc.get("monto", 0)
        desde = fc.get("desde", "") or "—"
        hasta = fc.get("hasta", "") or "—"
        if monto == 0 and desde == "—" and hasta == "—":
            continue
        _chk(28)
        # Subtítulo del tipo
        pdf.setFont(FONT_B, 7.5)
        pdf.setFillColor(_C_PRIMARY)
        pdf.drawString(L, y, label)
        y -= 10
        # Datos en 3 columnas: Desde | Hasta | Monto
        pdf.setFont(FONT, 7.5)
        pdf.setFillColor(black)
        col1 = L + 10
        col2 = ML + CW * 0.40
        col3 = R
        pdf.drawString(col1, y - 7, f"Desde: {desde}")
        pdf.drawString(col2, y - 7, f"Hasta: {hasta}")
        pdf.drawRightString(col3, y - 7, f"Monto: RD$ {monto:,.2f}")
        y -= 12
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.2)
        pdf.line(L, y, R, y)
        y -= 4

    sc = contado.get("sc", {})
    cc = contado.get("cc", {})
    ri = contado.get("ri", {})
    total_c = ((sc.get("monto", 0) if isinstance(sc, dict) else 0) +
               (cc.get("monto", 0) if isinstance(cc, dict) else 0) +
               (ri.get("monto", 0) if isinstance(ri, dict) else 0))
    _tot("TOTAL CONTADO", f"RD$ {total_c:,.2f}", L, R)

    # ═══════════════════════════════════════════════════════════════════
    # 6. FACTURAS A CRÉDITO
    # ═══════════════════════════════════════════════════════════════════
    if credito:
        _chk(40)
        _sec("FACTURAS A CRÉDITO")
        c_tipo_cr = (L, 'l')
        c_num = (ML + CW * 0.50, 'l')
        c_mon_cr = (R, 'r')
        cols_cr = [c_tipo_cr, c_num, c_mon_cr]
        _hdr(cols_cr, ["Tipo", "Nº Factura", "Total"])
        total_cr = 0
        for idx, fc in enumerate(credito):
            total_cr += fc.get("monto", 0)
            _row_z(cols_cr, [str(fc.get("tipo", ""))[:35],
                   str(fc.get("numero", ""))[:30],
                   f"RD$ {fc.get('monto', 0):,.2f}"], idx)
        _tot(f"Total: {len(credito)} factura(s)", f"RD$ {total_cr:,.2f}", L, R)

    # ═══════════════════════════════════════════════════════════════════
    # 7. TOTALES FINALES
    # ═══════════════════════════════════════════════════════════════════
    _chk(50)
    y -= 2
    pdf.setStrokeColor(_C_BORDER)
    pdf.setLineWidth(0.4)
    pdf.line(ML, y, MR, y)
    y -= 6
    pdf.setFillColor(_C_PRIMARY)
    pdf.rect(ML, y - 16, CW, 18, fill=1, stroke=0)
    pdf.setFillColor(white)
    pdf.setFont(FONT_B, 10)
    pdf.drawString(ML + 8, y - 12, "TOTAL GENERAL DEL ARQUEO")
    pdf.drawRightString(MR - 8, y - 12, f"RD$ {balance:,.2f}")
    y -= 24

    # ═══════════════════════════════════════════════════════════════════
    # 8. FIRMAS
    # ═══════════════════════════════════════════════════════════════════
    y -= 6
    sig_w = CW / 3
    firmas = ["Preparado por", "Revisado por", "Autorizado por"]
    for i, titulo in enumerate(firmas):
        sx = ML + i * sig_w + sig_w / 2
        pdf.setStrokeColor(_C_BORDER)
        pdf.setLineWidth(0.4)
        pdf.line(sx - 50, y, sx + 50, y)
        y -= 10
        pdf.setFont(FONT, 7.5)
        pdf.setFillColor(HexColor("#555555"))
        pdf.drawCentredString(sx, y, titulo)

    _footer()
    pdf.save()
    buffer.seek(0)
    return buffer
