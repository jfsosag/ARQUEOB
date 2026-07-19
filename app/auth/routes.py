from datetime import datetime, timezone

from flask import flash, redirect, render_template, request, url_for
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
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = db.session.scalar(db.select(Usuario).where(Usuario.username == username))
        if user and user.is_active and user.check_password(password):
            login_user(user, remember=True)
            user.touch_login()
            db.session.commit()
            registrar_accion("inicio_sesion", "auth", f"Sesión iniciada: {user.username}")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Credenciales inválidas o usuario desactivado.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        registrar_accion("cierre_sesion", "auth", f"Sesión cerrada: {current_user.username}")
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/mi-cuenta", methods=["GET", "POST"])
def mi_cuenta():
    if request.method == "POST":
        actual = request.form.get("password_actual", "")
        nueva = request.form.get("password_nueva", "")
        confirmar = request.form.get("password_confirmar", "")

        if not current_user.check_password(actual):
            flash("La contraseña actual es incorrecta.", "danger")
        elif nueva != confirmar:
            flash("Las contraseñas nuevas no coinciden.", "danger")
        elif len(nueva) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "danger")
        else:
            current_user.set_password(nueva)
            db.session.commit()
            flash("Contraseña actualizada correctamente.", "success")

    return render_template("auth/mi_cuenta.html")
