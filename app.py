from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import sqlite3, json, io, datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

DB = 'arqueo.db'

DENOMINATIONS = [2000,1000,500,200,100,50,25,10,5,1]

def get_db():
    conn = sqlite3.connect(DB)
    return conn

# Asegurar que la tabla tenga las columnas esperadas
def ensure_schema():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("PRAGMA table_info(arqueos)")
        cols = [row[1] for row in c.fetchall()]
        if 'noncash_list_json' not in cols:
            c.execute("ALTER TABLE arqueos ADD COLUMN noncash_list_json TEXT")
            conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

# Ejecutar verificación de esquema al iniciar
ensure_schema()

def compute_totals(data):
    # counts: dict denom->qty
    counts = data.get('counts', {})
    cash_total = 0.0
    for k,v in counts.items():
        try:
            cash_total += float(k) * int(v)
        except:
            pass
    # noncash
    noncash = data.get('noncash', {})
    cheques = float(noncash.get('cheques') or 0)
    tarjetas = float(noncash.get('tarjetas') or 0)
    vales = float(noncash.get('vales') or 0)
    transferencias = float(noncash.get('transferencias') or 0)
    recibos = float(noncash.get('recibos') or 0)
    # facturas contado (range) - nuevo formato con 3 tipos
    fc = data.get('fact_contado', {})
    # Sumar montos de los 3 tipos de facturas
    fc_monto = 0.0
    if isinstance(fc, dict):
        # Nuevo formato con 3 tipos
        for tipo in ['consumidor_final', 'consumidor_fiscal', 'recibos']:
            tipo_data = fc.get(tipo, {})
            if isinstance(tipo_data, dict):
                fc_monto += float(tipo_data.get('monto') or 0)
        # Mantener compatibilidad con formato antiguo
        if 'monto' in fc and not any(k in fc for k in ['consumidor_final', 'consumidor_fiscal', 'recibos']):
            fc_monto = float(fc.get('monto') or 0)
    else:
        fc_monto = 0.0
    # credit invoices list
    credit_list = data.get('fact_credito', [])
    credito_total = 0.0
    for item in credit_list:
        try:
            credito_total += float(item.get('monto') or 0)
        except:
            pass
    balance_general = cash_total + cheques + tarjetas + vales + transferencias + recibos
    total_facturado_al_contado = fc_monto
    diferencia = balance_general - total_facturado_al_contado
    total_no_efectivo = cheques + tarjetas + vales + transferencias + recibos
    
    result = {
        'cash_total': cash_total,
        'cheques': cheques,
        'tarjetas': tarjetas,
        'vales': vales,
        'transferencias': transferencias,
        'recibos': recibos,
        'balance_general': balance_general,
        'total_facturado_al_contado': total_facturado_al_contado,
        'diferencia': diferencia,
        'credito_total': credito_total,
        'total_no_efectivo': total_no_efectivo
    }
    return result

@app.route('/')
def index():
    today = datetime.date.today().isoformat()
    return render_template('index.html', today=today, denominations=DENOMINATIONS)

@app.route('/save', methods=['POST'])
def save():
    data = request.get_json()
    # compute totals
    totals = compute_totals(data)
    # save to DB
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO arqueos (date, cashier, shift, starting_fund, counts_json, noncash_json, noncash_list_json, invoices_json, totals_json, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)', (
        data.get('date'),
        data.get('cashier'),
        data.get('shift'),
        float(data.get('starting_fund') or 0),
        json.dumps(data.get('counts') or {}),
        json.dumps(data.get('noncash') or {}),
        json.dumps(data.get('noncash_list') or []),
        json.dumps({
            'fact_contado': data.get('fact_contado'),
            'fact_credito': data.get('fact_credito')
        }),
        json.dumps(totals),
        datetime.datetime.now().isoformat()
    ))
    conn.commit()
    arqueo_id = c.lastrowid
    conn.close()
    return jsonify({'status':'ok','id':arqueo_id,'totals':totals})

@app.route('/report', methods=['POST'])
def report():
    # Guardar los datos primero
    data = request.get_json()
    
    # Calcular totales
    totals = compute_totals(data)
    
    # Guardar en la base de datos
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO arqueos (date, cashier, shift, starting_fund, counts_json, noncash_json, noncash_list_json, invoices_json, totals_json, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)', (
        data.get('date'),
        data.get('cashier'),
        data.get('shift'),
        float(data.get('starting_fund') or 0),
        json.dumps(data.get('counts') or {}),
        json.dumps(data.get('noncash') or {}),
        json.dumps(data.get('noncash_list') or []),
        json.dumps({
            'fact_contado': data.get('fact_contado'),
            'fact_credito': data.get('fact_credito')
        }),
        json.dumps(totals),
        datetime.datetime.now().isoformat()
    ))
    conn.commit()
    arqueo_id = c.lastrowid
    
    # Obtener los datos guardados
    c.execute('SELECT date,cashier,shift,starting_fund,counts_json,noncash_json,noncash_list_json,invoices_json,totals_json,created_at FROM arqueos WHERE id=?',(arqueo_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Error al guardar'}), 500
        
    date,cashier,shift,starting_fund,counts_json,noncash_json,noncash_list_json,invoices_json,totals_json,created_at = row
    counts = json.loads(counts_json or '{}')
    noncash = json.loads(noncash_json or '{}')
    noncash_list = json.loads(noncash_list_json or '[]')
    invoices = json.loads(invoices_json or '{}')
    totals = json.loads(totals_json or '{}')
    # generate PDF (Letter size)
    buffer = io.BytesIO()
    cpdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 40
    y = height - 40
    cpdf.setFont("Helvetica-Bold", 14)
    cpdf.drawString(x_margin, y, "ARQUEO DE CAJA")
    cpdf.setFont("Helvetica", 10)
    y -= 20
    cpdf.drawString(x_margin, y, f"ID: {arqueo_id}    Fecha: {date}    Turno: {shift}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Cajero/a: {cashier}    Fondo inicial: {starting_fund}")
    y -= 20
    cpdf.setFont("Helvetica-Bold", 12)
    cpdf.drawString(x_margin, y, "Desglose de billetes y monedas:")
    y -= 16
    cpdf.setFont("Helvetica", 10)
    for denom in sorted(counts.keys(), key=lambda x: -int(x)):
        qty = counts.get(denom,0)
        try:
            subtotal = int(qty) * int(denom)
        except:
            subtotal = 0
        cpdf.drawString(x_margin, y, f"{denom} x {qty} = {subtotal:.2f}")
        y -= 12
    y -= 6
    cpdf.drawString(x_margin, y, f"Efectivo (total): {totals.get('cash_total',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Cheques: {totals.get('cheques',0):.2f}    Tarjetas: {totals.get('tarjetas',0):.2f}    Vales: {totals.get('vales',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Transferencias: {totals.get('transferencias',0):.2f}    Recibos: {totals.get('recibos',0):.2f}")
    
    # Detalle de entradas no efectivo
    if noncash_list:
        y -= 16
        cpdf.setFont("Helvetica-Bold", 12)
        cpdf.drawString(x_margin, y, "Detalle de entradas no efectivo:")
        y -= 14
        cpdf.setFont("Helvetica", 10)
        
        # Agrupar por tipo para mejor visualización
        noncash_by_type = {}
        for item in noncash_list:
            tipo = item.get('tipo', 'otros')
            if tipo not in noncash_by_type:
                noncash_by_type[tipo] = []
            noncash_by_type[tipo].append(item)
        
        for tipo, items in noncash_by_type.items():
            tipo_total = sum(item.get('monto', 0) for item in items)
            cpdf.setFont("Helvetica-Bold", 10)
            cpdf.drawString(x_margin, y, f"{tipo.capitalize()}: ${tipo_total:.2f}")
            y -= 12
            cpdf.setFont("Helvetica", 9)
            
            for item in items:
                descripcion = item.get('descripcion', '')
                monto = item.get('monto', 0)
                descripcion_text = f" - {descripcion}" if descripcion else ""
                cpdf.drawString(x_margin + 20, y, f"${monto:.2f}{descripcion_text}")
                y -= 10
                if y < 80:
                    cpdf.showPage()
                    y = height - 40
            y -= 2
    
    y -= 10
    
    y -= 18
    cpdf.setFont("Helvetica-Bold", 12)
    cpdf.drawString(x_margin, y, "Facturas al contado:")
    y -= 14
    cpdf.setFont("Helvetica", 10)
    fc = invoices.get('fact_contado') or {}
    
    # Nuevo formato con 3 tipos
    if isinstance(fc, dict) and any(k in fc for k in ['consumidor_final', 'consumidor_fiscal', 'recibos']):
        for tipo in ['consumidor_final', 'consumidor_fiscal', 'recibos']:
            tipo_data = fc.get(tipo, {})
            if isinstance(tipo_data, dict) and tipo_data.get('monto', 0) > 0:
                tipo_nombre = tipo.replace('_', ' ').title()
                cpdf.drawString(x_margin, y, f"{tipo_nombre}: Desde {tipo_data.get('desde','')} Hasta {tipo_data.get('hasta','')} Monto: {tipo_data.get('monto',0):.2f}")
                y -= 12
    else:
        # Formato antiguo (compatibilidad)
        cpdf.drawString(x_margin, y, f"Desde: {fc.get('desde','')}    Hasta: {fc.get('hasta','')}    Monto: {fc.get('monto',0):.2f}")
        y -= 12
    
    y -= 16
    cpdf.setFont("Helvetica-Bold", 12)
    cpdf.drawString(x_margin, y, "Facturas a crédito (lista):")
    y -= 14
    cpdf.setFont("Helvetica", 10)
    for item in invoices.get('fact_credito',[]) :
        cpdf.drawString(x_margin, y, f"Tipo: {item.get('tipo')}  Nº: {item.get('numero')}  Monto: {item.get('monto')}")
        y -= 12
        if y < 80:
            cpdf.showPage()
            y = height - 40
    y -= 10
    cpdf.setFont("Helvetica-Bold", 12)
    cpdf.drawString(x_margin, y, "Resumen:")
    y -= 16
    cpdf.setFont("Helvetica", 11)
    cpdf.drawString(x_margin, y, f"Efectivo: {totals.get('cash_total',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"No Efectivo: {totals.get('total_no_efectivo',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Balance general: {totals.get('balance_general',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Total facturado al contado: {totals.get('total_facturado_al_contado',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Total facturas crédito: {totals.get('credito_total',0):.2f}")
    y -= 14
    diff = totals.get('diferencia',0)
    color = "SOBRA" if diff>0 else ("FALTA" if diff<0 else "CUADRADO")
    cpdf.drawString(x_margin, y, f"Diferencia: {diff:.2f}  ({color})")
    y -= 30
    cpdf.setFont("Helvetica-Oblique",9)
    cpdf.drawString(x_margin, y, f"Generado: {created_at}")
    cpdf.showPage()
    cpdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"arqueo_{arqueo_id}.pdf", mimetype='application/pdf')

@app.route('/list')
def listing():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id,date,cashier,shift,created_at FROM arqueos ORDER BY id DESC LIMIT 50')
    rows = c.fetchall()
    conn.close()
    items = [{'id':r[0],'date':r[1],'cashier':r[2],'shift':r[3],'created_at':r[4]} for r in rows]
    return jsonify(items)

@app.route('/report/<int:arqueo_id>')
def report_old(arqueo_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT date,cashier,shift,starting_fund,counts_json,noncash_json,noncash_list_json,invoices_json,totals_json,created_at FROM arqueos WHERE id=?',(arqueo_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "No encontrado", 404
    date,cashier,shift,starting_fund,counts_json,noncash_json,noncash_list_json,invoices_json,totals_json,created_at = row
    counts = json.loads(counts_json or '{}')
    noncash = json.loads(noncash_json or '{}')
    noncash_list = json.loads(noncash_list_json or '[]')
    invoices = json.loads(invoices_json or '{}')
    totals = json.loads(totals_json or '{}')
    
    return generate_pdf(arqueo_id, date, cashier, shift, starting_fund, counts, noncash, noncash_list, invoices, totals, created_at)

def generate_pdf(arqueo_id, date, cashier, shift, starting_fund, counts, noncash, noncash_list, invoices, totals, created_at):
    # generate PDF (Letter size)
    buffer = io.BytesIO()
    cpdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    x_margin = 40
    y = height - 40
    cpdf.setFont("Helvetica-Bold", 14)
    cpdf.drawString(x_margin, y, "ARQUEO DE CAJA")
    cpdf.setFont("Helvetica", 10)
    y -= 20
    cpdf.drawString(x_margin, y, f"ID: {arqueo_id}    Fecha: {date}    Turno: {shift}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Cajero/a: {cashier}    Fondo inicial: {starting_fund}")
    y -= 20
    cpdf.setFont("Helvetica-Bold", 12)
    cpdf.drawString(x_margin, y, "Desglose de billetes y monedas:")
    y -= 16
    cpdf.setFont("Helvetica", 10)
    for denom in sorted(counts.keys(), key=lambda x: -int(x)):
        qty = counts.get(denom,0)
        try:
            subtotal = int(qty) * int(denom)
        except:
            subtotal = 0
        cpdf.drawString(x_margin, y, f"{denom} x {qty} = {subtotal:.2f}")
        y -= 12
    y -= 6
    cpdf.drawString(x_margin, y, f"Efectivo (total): {totals.get('cash_total',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Cheques: {totals.get('cheques',0):.2f}    Tarjetas: {totals.get('tarjetas',0):.2f}    Vales: {totals.get('vales',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Transferencias: {totals.get('transferencias',0):.2f}    Recibos: {totals.get('recibos',0):.2f}")
    
    # Detalle de entradas no efectivo
    if noncash_list:
        y -= 16
        cpdf.setFont("Helvetica-Bold", 12)
        cpdf.drawString(x_margin, y, "Detalle de entradas no efectivo:")
        y -= 14
        cpdf.setFont("Helvetica", 10)
        
        # Agrupar por tipo para mejor visualización
        noncash_by_type = {}
        for item in noncash_list:
            tipo = item.get('tipo', 'otros')
            if tipo not in noncash_by_type:
                noncash_by_type[tipo] = []
            noncash_by_type[tipo].append(item)
        
        for tipo, items in noncash_by_type.items():
            tipo_total = sum(item.get('monto', 0) for item in items)
            cpdf.setFont("Helvetica-Bold", 10)
            cpdf.drawString(x_margin, y, f"{tipo.capitalize()}: ${tipo_total:.2f}")
            y -= 12
            cpdf.setFont("Helvetica", 9)
            
            for item in items:
                descripcion = item.get('descripcion', '')
                monto = item.get('monto', 0)
                descripcion_text = f" - {descripcion}" if descripcion else ""
                cpdf.drawString(x_margin + 20, y, f"${monto:.2f}{descripcion_text}")
                y -= 10
                if y < 80:
                    cpdf.showPage()
                    y = height - 40
            y -= 2
    
    y -= 10
    
    y -= 18
    cpdf.setFont("Helvetica-Bold", 12)
    cpdf.drawString(x_margin, y, "Facturas al contado:")
    y -= 14
    cpdf.setFont("Helvetica", 10)
    fc = invoices.get('fact_contado') or {}
    
    # Nuevo formato con 3 tipos
    if isinstance(fc, dict) and any(k in fc for k in ['consumidor_final', 'consumidor_fiscal', 'recibos']):
        for tipo in ['consumidor_final', 'consumidor_fiscal', 'recibos']:
            tipo_data = fc.get(tipo, {})
            if isinstance(tipo_data, dict) and tipo_data.get('monto', 0) > 0:
                tipo_nombre = tipo.replace('_', ' ').title()
                cpdf.drawString(x_margin, y, f"{tipo_nombre}: Desde {tipo_data.get('desde','')} Hasta {tipo_data.get('hasta','')} Monto: {tipo_data.get('monto',0):.2f}")
                y -= 12
    else:
        # Formato antiguo (compatibilidad)
        cpdf.drawString(x_margin, y, f"Desde: {fc.get('desde','')}    Hasta: {fc.get('hasta','')}    Monto: {fc.get('monto',0):.2f}")
        y -= 12
    
    y -= 16
    cpdf.setFont("Helvetica-Bold", 12)
    cpdf.drawString(x_margin, y, "Facturas a crédito (lista):")
    y -= 14
    cpdf.setFont("Helvetica", 10)
    for item in invoices.get('fact_credito',[]) :
        cpdf.drawString(x_margin, y, f"Tipo: {item.get('tipo')}  Nº: {item.get('numero')}  Monto: {item.get('monto')}")
        y -= 12
        if y < 80:
            cpdf.showPage()
            y = height - 40
    y -= 10
    cpdf.setFont("Helvetica-Bold", 12)
    cpdf.drawString(x_margin, y, "Resumen:")
    y -= 16
    cpdf.setFont("Helvetica", 11)
    cpdf.drawString(x_margin, y, f"Efectivo: {totals.get('cash_total',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"No Efectivo: {totals.get('total_no_efectivo',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Balance general: {totals.get('balance_general',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Total facturado al contado: {totals.get('total_facturado_al_contado',0):.2f}")
    y -= 14
    cpdf.drawString(x_margin, y, f"Total facturas crédito: {totals.get('credito_total',0):.2f}")
    y -= 14
    diff = totals.get('diferencia',0)
    color = "SOBRA" if diff>0 else ("FALTA" if diff<0 else "CUADRADO")
    cpdf.drawString(x_margin, y, f"Diferencia: {diff:.2f}  ({color})")
    y -= 30
    cpdf.setFont("Helvetica-Oblique",9)
    cpdf.drawString(x_margin, y, f"Generado: {created_at}")
    cpdf.showPage()
    cpdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"arqueo_{arqueo_id}.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
