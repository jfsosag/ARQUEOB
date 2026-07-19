import os
from app import create_app

if os.getenv("DATABASE_URL"):
    from config import ProductionConfig
    app = create_app(ProductionConfig)
else:
    from config import DevelopmentConfig
    app = create_app(DevelopmentConfig)

with app.app_context():
    from app.extensions import db
    db.create_all()
