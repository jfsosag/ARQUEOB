from datetime import date
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Conduce
from app.utils.pdf import conduce_pdf

conduces_bp = Blueprint("conduces", __name__)


@conduces_bp.route("/", methods=["GET", "POST"])
@login_required
def formulario():
    if request.method == "POST":
        cliente = request.form.get("cliente", "").strip()
        direccion = request.form.get("direccion", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        if not all((cliente, direccion, descripcion)):
            flash("Cliente, dirección y descripción son obligatorios.", "danger")
        else:
            conduce = Conduce(fecha=date.fromisoformat(request.form["fecha"]), cliente=cliente, direccion=direccion, factura=request.form.get("factura", "").strip() or None, bultos=int(request.form["bultos"]) if request.form.get("bultos") else None, descripcion=descripcion, observaciones=request.form.get("observaciones", "").strip() or None)
            db.session.add(conduce); db.session.commit()
            flash("Conduce creado correctamente.", "success")
            return redirect(url_for("conduces.reporte", conduce_id=conduce.id))
    return render_template("conduces/formulario.html", hoy=date.today().isoformat())


@conduces_bp.get("/<int:conduce_id>/reporte.pdf")
@login_required
def reporte(conduce_id):
    conduce = db.get_or_404(Conduce, conduce_id)
    empresa = {"nombre": current_app.config["COMPANY_NAME"], "telefono": current_app.config["COMPANY_PHONE"], "rnc": current_app.config["COMPANY_RNC"], "direccion": current_app.config["COMPANY_ADDRESS"]}
    return send_file(conduce_pdf(conduce, empresa), as_attachment=True, download_name=f"conduce_{conduce.id:06d}.pdf", mimetype="application/pdf")
