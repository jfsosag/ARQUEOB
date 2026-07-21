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
            for tipo, concepto, monto in zip(
                request.form.getlist("tipo_no_efectivo[]"),
                request.form.getlist("concepto_no_efectivo[]"),
                request.form.getlist("monto_no_efectivo[]"),
            ):
                if monto.strip():
                    valor = Decimal(monto)
                    if valor < 0:
                        raise ValueError("Los montos no pueden ser negativos.")
                    no_efectivo.append({"tipo": tipo, "concepto": concepto.strip(), "monto": float(valor)})

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
            for tipo, numero, monto in zip(
                request.form.getlist("credito_tipo[]"),
                request.form.getlist("credito_numero[]"),
                request.form.getlist("credito_monto[]"),
            ):
                if monto.strip():
                    valor = Decimal(monto)
                    if not valor or valor <= 0:
                        raise ValueError("Las facturas a crédito requieren monto positivo.")
                    credito.append({
                        "tipo": tipo.strip(),
                        "numero": numero.strip(),
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
    ahora = datetime.now()
    username = current_user.username if current_user.is_authenticated else "Sistema"
    empresa = {
        "nombre": current_app.config.get("COMPANY_NAME", ""),
        "rnc": current_app.config.get("COMPANY_RNC", ""),
        "direccion": current_app.config.get("COMPANY_ADDRESS", ""),
        "telefono": current_app.config.get("COMPANY_PHONE", ""),
        "email": current_app.config.get("COMPANY_EMAIL", ""),
    }
    from app.utils.pdf_arqueo import generar_arqueo_pdf
    buffer = generar_arqueo_pdf(arqueo, empresa, username, ahora)
    return send_file(buffer, as_attachment=True, download_name=f"arqueo_{arqueo.id}.pdf", mimetype="application/pdf")
