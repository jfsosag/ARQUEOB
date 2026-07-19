import logging
import traceback

from flask import Flask, abort, redirect, request, url_for, render_template
from dotenv import load_dotenv
from datetime import date

from config import DevelopmentConfig
from app.extensions import db, migrate, login_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@login_manager.user_loader
def load_user(user_id):
    from app.models.usuario import Usuario
    return db.session.get(Usuario, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("auth.login", next=request.url))


# Module name -> URL prefix for permission checking
MODULO_URL_MAP = {
    "dashboard": "/",
    "clientes": "/clientes",
    "cobros": "/cobros",
    "cobros_informales": "/cobros-informales",
    "arqueo": "/arqueos",
    "conduces": "/conduces",
    "reportes": "/reportes",
    "configuracion": "/configuracion",
}


def create_app(config_object=DevelopmentConfig):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(config_object)
    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError("DATABASE_URL es obligatoria. Copie .env.example a .env y configure PostgreSQL.")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import arqueo, auditoria, cliente, conduce, cobro_informal, factura, pago, permiso, usuario  # noqa: F401
    from app.auth.routes import auth_bp
    from app.config_admin.routes import config_admin_bp
    from app.dashboard.routes import dashboard_bp
    from app.clientes.routes import clientes_bp
    from app.cobros.routes import cobros_bp
    from app.cobros_informales.routes import cobros_informales_bp
    from app.arqueo.routes import arqueo_bp
    from app.conduces.routes import conduces_bp
    from app.reportes.routes import reportes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(config_admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(clientes_bp, url_prefix="/clientes")
    app.register_blueprint(cobros_bp, url_prefix="/cobros")
    app.register_blueprint(cobros_informales_bp, url_prefix="/cobros-informales")
    app.register_blueprint(arqueo_bp, url_prefix="/arqueos")
    app.register_blueprint(conduces_bp, url_prefix="/conduces")
    app.register_blueprint(reportes_bp, url_prefix="/reportes")

    from app.seed_admin import seed_admin
    app.cli.add_command(seed_admin)

    @app.template_filter("currency")
    def currency(value):
        return f"RD$ {float(value or 0):,.2f}"

    @app.context_processor
    def common_context():
        from flask_login import current_user
        modulos_usuario = []
        if current_user.is_authenticated:
            modulos_usuario = current_user.modulos_permitidos() if current_user.is_admin else current_user.modulos_permitidos()
        return {
            "today": date.today().isoformat(),
            "modulos_usuario": modulos_usuario,
        }

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errores/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errores/403.html"), 403

    @app.errorhandler(500)
    def internal_error(e):
        logger.error("500 error: %s", traceback.format_exc())
        return render_template("errores/500.html"), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error("Unhandled exception: %s", traceback.format_exc())
        return render_template("errores/500.html"), 500

    return app
