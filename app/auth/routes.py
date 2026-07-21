from datetime import datetime, timezone

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.auth import auth_bp
from app.extensions import db
from app.models.usuario import Usuario
from app.utils.auditoria import registrar_accion


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        user_id = request.form.get("user_id", "")
        password = request.form.get("password", "")
        user = db.session.get(Usuario, int(user_id)) if user_id.isdigit() else None
        if user and user.is_active:
            if user.has_password():
                if not password:
                    flash("Este usuario requiere contraseña.", "warning")
                    usuarios = db.session.scalars(
                        db.select(Usuario).where(Usuario.is_active == True).order_by(Usuario.nombre_completo)
                    ).all()
                    return render_template("auth/login.html", usuarios=usuarios, focus_user=user.id)
                if not user.check_password(password):
                    flash("Contraseña incorrecta.", "danger")
                    usuarios = db.session.scalars(
                        db.select(Usuario).where(Usuario.is_active == True).order_by(Usuario.nombre_completo)
                    ).all()
                    return render_template("auth/login.html", usuarios=usuarios, focus_user=user.id)
            login_user(user, remember=True)
            user.touch_login()
            db.session.commit()
            registrar_accion("inicio_sesion", "auth", f"Sesión iniciada: {user.username}")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Usuario no encontrado o desactivado.", "danger")

    usuarios = db.session.scalars(
        db.select(Usuario).where(Usuario.is_active == True).order_by(Usuario.nombre_completo)
    ).all()
    return render_template("auth/login.html", usuarios=usuarios)


@auth_bp.route("/verificar-clave", methods=["POST"])
def verificar_clave():
    data = request.get_json() or {}
    user_id = data.get("user_id", "")
    password = data.get("password", "")

    if not user_id or not str(user_id).isdigit():
        return jsonify({"ok": False, "error": "Solicitud inválida."}), 400

    user = db.session.get(Usuario, int(user_id))
    if not user or not user.is_active:
        return jsonify({"ok": False, "error": "Usuario no encontrado o desactivado."}), 404

    if not user.check_password(password):
        return jsonify({"ok": False, "error": "Contraseña incorrecta."}), 401

    return jsonify({"ok": True})


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        registrar_accion("cierre_sesion", "auth", f"Sesión cerrada: {current_user.username}")
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/mi-cuenta")
def mi_cuenta():
    return render_template("auth/mi_cuenta.html")
