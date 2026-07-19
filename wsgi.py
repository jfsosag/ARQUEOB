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
        from app.models.usuario import Usuario
        db.create_all()
        if not db.session.scalar(db.select(Usuario).where(Usuario.username == "admin")):
            admin = Usuario(
                nombre_completo="Administrador",
                username="admin",
                email="admin@arqueob.local",
                is_active=True,
                is_admin=True,
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Usuario admin creado.")
        else:
            print("Usuario admin ya existe.")
    print("App arrancó correctamente.")
except Exception:
    print("ERROR AL INICIAR:")
    traceback.print_exc()
    raise
