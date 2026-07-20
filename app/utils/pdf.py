import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def recibo_pdf(pago, empresa):
    """Genera un recibo profesional de dos copias en formato térmico."""
    ancho, alto = 80 * mm, 180 * mm
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(ancho, alto), pageCompression=1)

    def copia(etiqueta):
        y, margen = alto - 10 * mm, 7 * mm
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(ancho / 2, y, empresa["nombre"]); y -= 5 * mm
        pdf.setFont("Helvetica", 7)
        pdf.drawCentredString(ancho / 2, y, f"Tel. {empresa['telefono']} · RNC {empresa['rnc']}"); y -= 4 * mm
        pdf.drawCentredString(ancho / 2, y, empresa["direccion"][:55]); y -= 6 * mm
        pdf.line(margen, y, ancho - margen, y); y -= 5 * mm
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawCentredString(ancho / 2, y, f"RECIBO DE COBRO · {etiqueta}"); y -= 6 * mm
        pdf.setFont("Helvetica", 8)
        pdf.drawString(margen, y, f"No. {pago.id:06d}"); pdf.drawRightString(ancho - margen, y, pago.fecha.strftime("%d/%m/%Y %H:%M")); y -= 5 * mm
        pdf.drawString(margen, y, f"Cliente: {pago.cliente.nombre[:35]}"); y -= 4 * mm
        pdf.drawString(margen, y, f"Tipo: {pago.tipo.value}"); y -= 4 * mm
        pdf.drawString(margen, y, f"Forma de pago: {pago.forma_pago.value}"); y -= 5 * mm

        if pago.banco:
            pdf.drawString(margen, y, f"Banco: {pago.banco}"); y -= 4 * mm
        if pago.numero_cheque:
            pdf.drawString(margen, y, f"Cheque No.: {pago.numero_cheque}"); y -= 4 * mm
        if pago.numero_referencia:
            pdf.drawString(margen, y, f"Referencia: {pago.numero_referencia}"); y -= 4 * mm
        if pago.tipo_tarjeta:
            tarjeta_info = f"Tarjeta: {pago.tipo_tarjeta}"
            if pago.ultimos_4_digitos:
                tarjeta_info += f" ****{pago.ultimos_4_digitos}"
            pdf.drawString(margen, y, tarjeta_info); y -= 4 * mm
        if pago.numero_autorizacion:
            pdf.drawString(margen, y, f"Autorización: {pago.numero_autorizacion}"); y -= 4 * mm

        pdf.line(margen, y, ancho - margen, y); y -= 5 * mm

        if pago.tipo.value == "Factura" and pago.detalles:
            pdf.setFont("Helvetica-Bold", 7)
            pdf.drawString(margen, y, "FACTURA"); pdf.drawRightString(ancho - margen, y, "APLICADO"); y -= 4 * mm
            pdf.setFont("Helvetica", 8)
            for detalle in pago.detalles:
                pdf.drawString(margen, y, detalle.factura.numero[:22])
                pdf.drawRightString(ancho - margen, y, f"RD$ {detalle.monto_aplicado:,.2f}")
                y -= 4.5 * mm
        elif pago.tipo.value == "Manual" and pago.concepto_manual:
            pdf.setFont("Helvetica-Bold", 7)
            pdf.drawString(margen, y, "CONCEPTO"); y -= 4 * mm
            pdf.setFont("Helvetica", 8)
            concepto = pago.concepto_manual[:40]
            pdf.drawString(margen, y, concepto); y -= 4.5 * mm

        pdf.line(margen, y, ancho - margen, y); y -= 6 * mm
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(margen, y, "TOTAL PAGADO")
        pdf.drawRightString(ancho - margen, y, f"RD$ {pago.monto_pagado:,.2f}"); y -= 6 * mm

        saldo = pago.cliente.saldo_pendiente
        pdf.setFont("Helvetica", 8)
        pdf.drawString(margen, y, "Balance restante")
        pdf.drawRightString(ancho - margen, y, f"RD$ {saldo:,.2f}"); y -= 6 * mm

        pdf.drawString(margen, y, f"Cobrado por: {pago.usuario}"); y -= 8 * mm

        pdf.drawCentredString(ancho / 2, y, "Gracias por su pago")
        pdf.showPage()

    copia("ORIGINAL")
    copia("COPIA")
    pdf.save()
    buffer.seek(0)
    return buffer


def conduce_pdf(conduce, empresa):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1)
    ancho, alto = A4

    def cuadro(superior, etiqueta):
        x, y, w, h = 42, superior - 280, ancho - 84, 250
        pdf.setLineWidth(1)
        pdf.roundRect(x, y, w, h, 8)
        cursor = superior - 25
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(x + 14, cursor, empresa["nombre"])
        pdf.drawRightString(x + w - 14, cursor, f"CONDUCE DE ENVÍO · {etiqueta}"); cursor -= 17
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x + 14, cursor, f"Tel. {empresa['telefono']} · RNC {empresa['rnc']}"); cursor -= 14
        pdf.drawString(x + 14, cursor, empresa["direccion"]); cursor -= 18
        pdf.line(x, cursor, x + w, cursor); cursor -= 18
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x + 14, cursor, "CLIENTE:"); pdf.setFont("Helvetica", 9); pdf.drawString(x + 70, cursor, conduce.cliente)
        pdf.setFont("Helvetica-Bold", 9); pdf.drawString(x + w - 170, cursor, "FECHA:"); pdf.setFont("Helvetica", 9); pdf.drawRightString(x + w - 14, cursor, conduce.fecha.strftime("%d/%m/%Y")); cursor -= 18
        pdf.setFont("Helvetica-Bold", 9); pdf.drawString(x + 14, cursor, "DIRECCIÓN:"); pdf.setFont("Helvetica", 9); pdf.drawString(x + 78, cursor, conduce.direccion[:55])
        pdf.setFont("Helvetica-Bold", 9); pdf.drawString(x + w - 170, cursor, "FACTURA:"); pdf.setFont("Helvetica", 9); pdf.drawRightString(x + w - 14, cursor, conduce.factura or "—"); cursor -= 22
        pdf.setFont("Helvetica-Bold", 9); pdf.drawString(x + 14, cursor, "DESCRIPCIÓN DEL CONTENIDO"); cursor -= 15
        pdf.setFont("Helvetica", 9)
        for linea in _wrap(conduce.descripcion, 92)[:4]:
            pdf.drawString(x + 18, cursor, linea); cursor -= 13
        cursor -= 4
        pdf.setFont("Helvetica-Bold", 9); pdf.drawString(x + 14, cursor, "OBSERVACIONES:"); cursor -= 13
        pdf.setFont("Helvetica", 8)
        for linea in _wrap(conduce.observaciones or "", 105)[:2]:
            pdf.drawString(x + 14, cursor, linea); cursor -= 11
        firma = y + 25
        pdf.line(x + 50, firma, x + 210, firma); pdf.line(x + w - 210, firma, x + w - 50, firma)
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(x + 130, firma - 12, "RECIBIDO POR")
        pdf.drawCentredString(x + w - 130, firma - 12, "ENTREGADO POR")

    cuadro(alto - 25, "ORIGINAL")
    cuadro(alto - 310, "COPIA")
    pdf.save(); buffer.seek(0)
    return buffer


def _wrap(text, max_chars):
    palabras, lineas, actual = str(text).split(), [], ""
    for palabra in palabras:
        if len(actual) + len(palabra) + 1 > max_chars:
            lineas.append(actual); actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    return lineas + ([actual] if actual else [])
