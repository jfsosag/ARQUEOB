# Arqueo de Caja - Flask (Proyecto descargable)

Pequeño sistema de arqueo de caja hecho en Python + Flask con SQLite y generación de reporte PDF (tamaño carta).
Incluye:
- Formulario para ingresar cajero/a, turno (12:00 pm / 5:30 pm), fecha, fondo inicial.
- Ingreso de billetes/monedas (denominaciones), entradas no-efectivo (cheques, tarjetas, vales, transferencias).
- Facturas al contado (rango) y facturas a crédito con 3 tipos (consumidor final, comprobante fiscal, vieje) con posibilidad de agregar varias entradas.
- Cálculos de totales, balance general, diferencia (verde si sobra, rojo si falta).
- Guardado en base de datos SQLite y reporte PDF por arqueo.
- Botón para limpiar campos.
- Archivo `requirements.txt` con dependencias.

Instrucciones rápidas:
1. Crear un entorno virtual: `python -m venv venv`.
2. Activar (Windows): `venv\\Scripts\\activate` o (mac/linux): `source venv/bin/activate`.
3. Instalar dependencias: `pip install -r requirements.txt`.
4. Inicializar BD: `python init_db.py` (crea `arqueo.db`).
5. Ejecutar: `flask run` o `python app.py`.
6. Abrir http://127.0.0.1:5000

Generado automáticamente para el usuario.
