"""Punto de entrada compatible con ``python app.py``.

El paquete de la aplicación también se llama ``app``. Al ejecutar este archivo
directamente Python prioriza este archivo sobre el paquete, por lo que se carga
explícitamente el paquete para conservar el comando histórico de arranque.
"""
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
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"])
