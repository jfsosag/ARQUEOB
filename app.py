import os
import importlib.util
import sys
from pathlib import Path

_package_dir = Path(__file__).with_name("app")
_spec = importlib.util.spec_from_file_location(
    "app", _package_dir / "__init__.py", submodule_search_locations=[str(_package_dir)]
)
_package = importlib.util.module_from_spec(_spec)
sys.modules["app"] = _package
assert _spec.loader
_spec.loader.exec_module(_package)

create_app = _package.create_app

if os.getenv("DATABASE_URL"):
    from config import ProductionConfig
    app = create_app(ProductionConfig)
else:
    from config import DevelopmentConfig
    app = create_app(DevelopmentConfig)

with app.app_context():
    from app.extensions import db
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"])
