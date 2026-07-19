from flask import Blueprint

config_admin_bp = Blueprint("config_admin", __name__, url_prefix="/configuracion")

from app.config_admin import routes  # noqa: E402, F401
