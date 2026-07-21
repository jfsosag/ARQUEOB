from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.config_admin import config_admin_bp
from app.extensions import db
from app.models.permiso import Permiso
from app.models.usuario import Usuario
from app.utils.auditoria import registrar_accion

MODULOS_SISTEMA = [
    ("dashboard", "Dashboard"),
    ("clientes", "Clientes"),
    ("cobros", "Recibo de Cobro"),
    ("cobros_informales", "Cobro Informal"),
    ("arqueo", "Arqueo de Caja"),
    ("conduces", "Conduce de Envío"),
    ("reportes", "Reportes"),
    ("configuracion", "Configuración"),
]


def _admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


# ---- Listar usuarios ----
@config_admin_bp.route("/usuarios")
@login_required
def usuarios():
    _admin_required()
    q = request.args.get("q", "").strip()
    query = db.select(Usuario).order_by(Usuario.created_at.desc())
    if q:
        like = f"%{q}%"
        query = query.where(
            db.or_(
                Usuario.nombre_completo.ilike(like),
                Usuario.username.ilike(like),
                Usuario.email.ilike(like),
            )
        )
    items = db.session.scalars(query).all()
    return render_template("config_admin/usuarios.html", usuarios=items, q=q)


# ---- Crear usuario ----
@config_admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_usuario():
    _admin_required()
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        nombre = request.form.get("nombre_completo", "").strip()
        email = request.form.get("email", "").strip() or None
        telefono = request.form.get("telefono", "").strip() or None
        password = request.form.get("password", "").strip()
        sin_contrasena = request.form.get("sin_contrasena") == "on"
        is_admin = request.form.get("is_admin") == "on"

        errors = []
        if not username:
            errors.append("El nombre de usuario es obligatorio.")
        if not nombre:
            errors.append("El nombre completo es obligatorio.")
        if db.session.scalar(db.select(Usuario).where(Usuario.username == username)):
            errors.append("Ya existe un usuario con ese nombre de usuario.")
        if not sin_contrasena and not password:
            errors.append("Debe ingresar una contraseña o marcar 'Sin contraseña'.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("config_admin/usuario_form.html", usuario=None, modulos=MODULOS_SISTEMA, form_data=request.form)

        user = Usuario(nombre_completo=nombre, username=username, email=email, telefono=telefono, is_admin=is_admin)
        if sin_contrasena:
            user.clear_password()
        else:
            user.set_password(password)
        db.session.add(user)
        db.session.flush()

        modulos_seleccionados = request.form.getlist("modulos")
        for m in modulos_seleccionados:
            db.session.add(Permiso(usuario_id=user.id, modulo=m))
        registrar_accion("crear_usuario", "configuracion", f"Usuario creado: {user.username}")
        db.session.commit()
        flash("Usuario creado correctamente.", "success")
        return redirect(url_for("config_admin.usuarios"))

    return render_template("config_admin/usuario_form.html", usuario=None, modulos=MODULOS_SISTEMA, form_data={})


# ---- Editar usuario ----
@config_admin_bp.route("/usuarios/<int:uid>/editar", methods=["GET", "POST"])
@login_required
def editar_usuario(uid):
    _admin_required()
    user = db.get_or_404(Usuario, uid)

    if request.method == "POST":
        nombre = request.form.get("nombre_completo", "").strip()
        email = request.form.get("email", "").strip() or None
        telefono = request.form.get("telefono", "").strip() or None
        is_active = request.form.get("is_active") == "on"
        is_admin = request.form.get("is_admin") == "on"
        sin_contrasena = request.form.get("sin_contrasena") == "on"
        new_password = request.form.get("password", "").strip()

        errors = []
        if not nombre:
            errors.append("El nombre completo es obligatorio.")
        if not sin_contrasena and not new_password and not user.has_password():
            errors.append("Debe ingresar una contraseña o marcar 'Sin contraseña'.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("config_admin/usuario_form.html", usuario=user, modulos=MODULOS_SISTEMA, form_data=request.form)

        user.nombre_completo = nombre
        user.email = email
        user.telefono = telefono
        user.is_active = is_active
        user.is_admin = is_admin

        if sin_contrasena:
            user.clear_password()
        elif new_password:
            user.set_password(new_password)

        if user.is_admin:
            Permiso.query.filter_by(usuario_id=user.id).delete()
        else:
            Permiso.query.filter_by(usuario_id=user.id).delete()
            for m in request.form.getlist("modulos"):
                db.session.add(Permiso(usuario_id=user.id, modulo=m))

        try:
            registrar_accion("editar_usuario", "configuracion", f"Usuario editado: {user.username}")
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Error al guardar los cambios. Intente de nuevo.", "danger")
            return render_template("config_admin/usuario_form.html", usuario=user, modulos=MODULOS_SISTEMA, form_data=request.form)

        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for("config_admin.usuarios"))

    return render_template("config_admin/usuario_form.html", usuario=user, modulos=MODULOS_SISTEMA, form_data={})


# ---- Eliminar usuario ----
@config_admin_bp.route("/usuarios/<int:uid>/eliminar", methods=["POST"])
@login_required
def eliminar_usuario(uid):
    _admin_required()
    user = db.get_or_404(Usuario, uid)
    if user.id == current_user.id:
        flash("No puede eliminar su propio usuario.", "danger")
        return redirect(url_for("config_admin.usuarios"))

    username = user.username
    db.session.delete(user)
    registrar_accion("eliminar_usuario", "configuracion", f"Usuario eliminado: {username}")
    db.session.commit()
    flash("Usuario eliminado.", "success")
    return redirect(url_for("config_admin.usuarios"))


# ---- Activar / desactivar ----
@config_admin_bp.route("/usuarios/<int:uid>/toggle", methods=["POST"])
@login_required
def toggle_usuario(uid):
    _admin_required()
    user = db.get_or_404(Usuario, uid)
    if user.id == current_user.id:
        flash("No puede desactivar su propio usuario.", "danger")
        return redirect(url_for("config_admin.usuarios"))
    user.is_active = not user.is_active
    estado = "activado" if user.is_active else "desactivado"
    registrar_accion("toggle_usuario", "configuracion", f"Usuario {estado}: {user.username}")
    db.session.commit()
    flash(f"Usuario {estado}.", "success")
    return redirect(url_for("config_admin.usuarios"))


# ---- Restablecer contraseña ----
@config_admin_bp.route("/usuarios/<int:uid>/reset-password", methods=["POST"])
@login_required
def reset_password(uid):
    _admin_required()
    user = db.get_or_404(Usuario, uid)
    password = request.form.get("password", "")
    user.set_password(password)
    registrar_accion("reset_password", "configuracion", f"Contraseña reiniciada: {user.username}")
    db.session.commit()
    flash("Contraseña restablecida correctamente.", "success")
    return redirect(url_for("config_admin.editar_usuario", uid=uid))
