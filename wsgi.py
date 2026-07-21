import os
import traceback

try:
    from app import create_app

    if os.getenv("DATABASE_URL"):
        from config import ProductionConfig
        app = create_app(ProductionConfig)
    else:
        from config import DevelopmentConfig
        app = create_app(DevelopmentConfig)

    with app.app_context():
        from app.extensions import db
        from flask_migrate import upgrade
        upgrade()
        from app.models.usuario import Usuario
        admin = db.session.scalar(db.select(Usuario).where(Usuario.username == "admin"))
        if not admin:
            admin = Usuario(
                nombre_completo="Administrador",
                username="admin",
                email="admin@arqueob.local",
                is_active=True,
                is_admin=True,
            )
            db.session.add(admin)
        if not admin.check_password("admin123"):
            admin.set_password("admin123")
            db.session.commit()
            print("Password del usuario admin reseteado.")
        else:
            print("Usuario admin OK.")
    print("App arrancó correctamente.")
except Exception:
    print("ERROR AL INICIAR:")
    traceback.print_exc()
    raise
