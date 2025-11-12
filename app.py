from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import sqlite3, json, io, datetime
from reportlab.lib.pagesizes import letter, A4
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
    noncash_aggregated = data.get('noncash', {})
    noncash_total_sum = 0.0
    # Sum all aggregated non-cash types
    for k, v in noncash_aggregated.items():
        try:
            noncash_total_sum += float(v)
        except:
            pass

    # facturas contado (range) - nuevo formato con 3 tipos
    fc = data.get('fact_contado', {})
    # Sumar montos de los 3 tipos de facturas
    fc_monto = 0.0
    if isinstance(fc, dict):
        # Nuevo formato con 3 tipos
        for tipo in ['consumidor_final', 'consumidor_fiscal', 'recibos']: # 'recibos' here refers to the invoice type, not non-cash
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
    total_no_efectivo = noncash_total_sum
    
    result = {
        'cash_total': cash_total,
        'balance_general': balance_general,
        'total_facturado_al_contado': total_facturado_al_contado,
        'diferencia': diferencia,
        'credito_total': credito_total,
        'total_no_efectivo': total_no_efectivo
    }
    # Add individual noncash types to result for easy access in PDF
    for k, v in noncash_aggregated.items():
        result[k] = float(v)
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
    
    # Obtener los datos guardados para pasarlos a generate_pdf
    c.execute('SELECT date,cashier,shift,starting_fund,counts_json,noncash_json,noncash_list_json,invoices_json,totals_json,created_at FROM arqueos WHERE id=?',(arqueo_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Error al guardar'}), 500
        
    date,cashier,shift,starting_fund,counts_json,noncash_json,noncash_list_json,invoices_json,totals_json,created_at = row
    counts = json.loads(counts_json or '{}')
    noncash = json.loads(noncash_json or '{}')
    invoices = json.loads(invoices_json or '{}')
    totals = json.loads(totals_json or '{}')
    noncash_list = json.loads(noncash_list_json or '[]') # Detailed noncash list
    
    # Call the refactored generate_pdf function
    return generate_pdf(arqueo_id, date, cashier, shift, starting_fund, counts, noncash, noncash_list, invoices, totals, created_at)

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
def get_report_pdf(arqueo_id): # Renamed from report_old for clarity
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT date,cashier,shift,starting_fund,counts_json,noncash_json,noncash_list_json,invoices_json,totals_json,created_at FROM arqueos WHERE id=?',(arqueo_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "Arqueo no encontrado", 404
    date,cashier,shift,starting_fund,counts_json,noncash_json,noncash_list_json,invoices_json,totals_json,created_at = row
    counts = json.loads(counts_json or '{}')
    # noncash here is the aggregated one from the DB, not the detailed list
    noncash = json.loads(noncash_json or '{}') 
    noncash_list = json.loads(noncash_list_json or '[]') # Detailed noncash list
    invoices = json.loads(invoices_json or '{}')
    totals = json.loads(totals_json or '{}')
    
    return generate_pdf(arqueo_id, date, cashier, shift, starting_fund, counts, noncash, noncash_list, invoices, totals, created_at)

# Helper function for drawing separator lines
def _draw_line(cpdf, y_pos, x_start, x_end, width=0.5):
    cpdf.setLineWidth(width)
    cpdf.line(x_start, y_pos, x_end, y_pos)

# Helper function for page breaks
def check_page_break(cpdf, y_pos, height, x_margin, min_space=80):
    if y_pos < min_space:
        cpdf.showPage()
        return height - 40 # Reset y for new page
    return y_pos

def generate_pdf(arqueo_id, date, cashier, shift, starting_fund, counts, noncash_aggregated, noncash_list, invoices, totals, created_at):
    # generate PDF (A4 size)
    buffer = io.BytesIO()
    cpdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    x_margin = 40
    y = height - 40

    # --- HEADER ---
    cpdf.setFont("Helvetica-Bold", 14)
    cpdf.setFont("Helvetica-Bold", 16)
    cpdf.drawCentredString(width / 2, y, "ARQUEO DE CAJA")
    y -= 20
    _draw_line(cpdf, y, x_margin, width - x_margin)
    y -= 15

    cpdf.setFont("Helvetica", 11)
    cpdf.setFont("Helvetica", 10)
    cpdf.drawString(x_margin, y, f"CAJERO/A: {cashier}")
    cpdf.drawString(x_margin + 200, y, f"FECHA: {date}")
    cpdf.drawString(x_margin + 400, y, f"TURNO: {shift}")
    y -= 15
    _draw_line(cpdf, y, x_margin, width - x_margin)
    y -= 20

    # --- DESGLOSE DE ARQUEO ---
    cpdf.setFont("Helvetica-Bold", 13)
    cpdf.setFont("Helvetica-Bold", 12)
    y = check_page_break(cpdf, y, height, x_margin)
    cpdf.drawString(x_margin, y, "DESGLOSE DE ARQUEO")
    y -= 15
    cpdf.setFont("Helvetica", 11)
    cpdf.setFont("Helvetica", 10)

    total_facturado_al_contado = totals.get('total_facturado_al_contado', 0)
    balance_general = totals.get('balance_general', 0)
    diferencia = totals.get('diferencia', 0)
    color_diff = "SOBRA" if diferencia > 0 else ("FALTA" if diferencia < 0 else "CUADRADO")

    cpdf.drawString(x_margin, y, f"TOTAL FACTURADO: {total_facturado_al_contado:.2f}")
    cpdf.drawString(x_margin + 250, y, f"FONDO: {starting_fund:.2f}")
    y -= 15
    cpdf.drawString(x_margin, y, f"BALANCE GENERAL: {balance_general:.2f}")
    cpdf.drawString(x_margin + 250, y, f"DIFERENCIA: {diferencia:.2f} ({color_diff})")
    y -= 15
    _draw_line(cpdf, y, x_margin, width - x_margin)
    y -= 20

    # --- BALANCE GENERAL (detailed) ---
    cpdf.setFont("Helvetica-Bold", 13)
    cpdf.setFont("Helvetica-Bold", 12)
    y = check_page_break(cpdf, y, height, x_margin)
    cpdf.drawString(x_margin, y, "BALANCE GENERAL")
    y -= 15
    cpdf.setFont("Helvetica", 11)
    cpdf.setFont("Helvetica", 10)
    cpdf.drawString(x_margin, y, f"EFECTIVO: {totals.get('cash_total',0):.2f}")
    y -= 12
    cpdf.drawString(x_margin, y, f"CHEQUES: {totals.get('cheques',0):.2f}")
    y -= 12
    cpdf.drawString(x_margin, y, f"TARJETAS: {totals.get('tarjetas',0):.2f}")
    y -= 12
    cpdf.drawString(x_margin, y, f"VALES: {totals.get('vales',0):.2f}")
    y -= 12
    cpdf.drawString(x_margin, y, f"TRANSFERENCIAS: {totals.get('transferencias',0):.2f}")
    y -= 12
    cpdf.drawString(x_margin, y, f"RECIBOS (no efectivo): {totals.get('recibos',0):.2f}")
    y -= 12
    cpdf.drawString(x_margin, y, f"DEPOSITOS: {totals.get('depositos',0):.2f}")
    y -= 12
    cpdf.drawString(x_margin, y, f"OTROS (no efectivo): {totals.get('otros',0):.2f}")
    y -= 12
    cpdf.drawString(x_margin, y, f"TOTAL (Balance General): {totals.get('balance_general',0):.2f}")
    y -= 15
    _draw_line(cpdf, y, x_margin, width - x_margin)
    y -= 20

    # --- FACTURAS EN EFECTIVO AL CONTADO ---
    cpdf.setFont("Helvetica-Bold", 13)
    cpdf.setFont("Helvetica-Bold", 12)
    y = check_page_break(cpdf, y, height, x_margin)
    cpdf.drawString(x_margin, y, "FACTURAS EN EFECTIVO AL CONTADO")
    y -= 15
    cpdf.setFont("Helvetica", 11)
    cpdf.setFont("Helvetica", 10)

    fc = invoices.get('fact_contado') or {}
    
    col1_x = x_margin
    col2_x = x_margin + 180
    col3_x = x_margin + 360

    cpdf.drawString(col1_x, y, "CONSUMIDOR FINAL")
    cpdf.drawString(col2_x, y, "COMPROBANTE FISCAL")
    cpdf.drawString(col3_x, y, "RECIBO")
    y -= 12

    cf_data = fc.get('consumidor_final', {})
    fiscal_data = fc.get('consumidor_fiscal', {})
    recibo_data = fc.get('recibos', {})

    cpdf.drawString(col1_x, y, f"DESDE: {cf_data.get('desde','')}")
    cpdf.drawString(col2_x, y, f"DESDE: {fiscal_data.get('desde','')}")
    cpdf.drawString(col3_x, y, f"DESDE: {recibo_data.get('desde','')}")
    y -= 12

    cpdf.drawString(col1_x, y, f"HASTA: {cf_data.get('hasta','')}")
    cpdf.drawString(col2_x, y, f"HASTA: {fiscal_data.get('hasta','')}")
    cpdf.drawString(col3_x, y, f"HASTA: {recibo_data.get('hasta','')}")
    y -= 12

    cpdf.drawString(col1_x, y, f"TOTAL: {cf_data.get('monto',0):.2f}")
    cpdf.drawString(col2_x, y, f"TOTAL: {fiscal_data.get('monto',0):.2f}")
    cpdf.drawString(col3_x, y, f"TOTAL: {recibo_data.get('monto',0):.2f}")
    y -= 15
    _draw_line(cpdf, y, x_margin, width - x_margin)
    y -= 20

    # --- DESGLOSE DE EFECTIVO ---
    cpdf.setFont("Helvetica-Bold", 13)
    cpdf.setFont("Helvetica-Bold", 12)
    y = check_page_break(cpdf, y, height, x_margin)
    cpdf.drawString(x_margin, y, "DESGLOSE DE EFECTIVO")
    y -= 15
    cpdf.setFont("Helvetica", 11)
    cpdf.setFont("Helvetica", 10)

    denoms_col1 = [2000, 1000, 500, 200, 100, 50]
    denoms_col2 = [25, 10, 5, 1]

    col1_x_cant = x_margin
    col1_x_denom = x_margin + 50
    col1_x_total = x_margin + 120

    col2_x_cant = x_margin + 250
    col2_x_denom = x_margin + 300
    col2_x_total = x_margin + 370

    cpdf.drawString(col1_x_cant, y, "CANT")
    cpdf.drawString(col1_x_denom, y, "DENOMINACION")
    cpdf.drawString(col1_x_total, y, "TOTAL")

    cpdf.drawString(col2_x_cant, y, "CANT")
    cpdf.drawString(col2_x_denom, y, "DENOMINACION")
    cpdf.drawString(col2_x_total, y, "TOTAL")
    y -= 12

    max_rows = max(len(denoms_col1), len(denoms_col2))
    current_y = y

    for i in range(max_rows):
        # Column 1
        if i < len(denoms_col1):
            denom = denoms_col1[i]
            qty = counts.get(str(denom), 0)
            subtotal = float(qty) * denom
            cpdf.drawString(col1_x_cant, current_y, str(qty))
            cpdf.drawString(col1_x_denom, current_y, str(denom))
            cpdf.drawString(col1_x_total, current_y, f"{subtotal:.2f}")

        # Column 2
        if i < len(denoms_col2):
            denom = denoms_col2[i]
            qty = counts.get(str(denom), 0)
            subtotal = float(qty) * denom
            cpdf.drawString(col2_x_cant, current_y, str(qty))
            cpdf.drawString(col2_x_denom, current_y, str(denom))
            cpdf.drawString(col2_x_total, current_y, f"{subtotal:.2f}")
        current_y -= 12
        y = check_page_break(cpdf, current_y, height, x_margin)
        if y != current_y: # If page break occurred
            current_y = y
            cpdf.setFont("Helvetica", 10) # Reset font after page break
            cpdf.drawString(col1_x_cant, current_y, "CANT")
            cpdf.drawString(col1_x_denom, current_y, "DENOMINACION")
            cpdf.drawString(col1_x_total, current_y, "TOTAL")
            cpdf.drawString(col2_x_cant, current_y, "CANT")
            cpdf.drawString(col2_x_denom, current_y, "DENOMINACION")
            cpdf.drawString(col2_x_total, current_y, "TOTAL")
            current_y -= 12

    y = current_y # Update y after the loop

    cpdf.drawString(col1_x_total, y, f"TOTAL: {totals.get('cash_total',0):.2f}")
    y -= 15
    _draw_line(cpdf, y, x_margin, width - x_margin)
    y -= 20

    # --- ENTRADA NO EFECTIVO (Detalle) ---
    if noncash_list:
        cpdf.setFont("Helvetica-Bold", 13)
        cpdf.setFont("Helvetica-Bold", 12)
        y = check_page_break(cpdf, y, height, x_margin)
        cpdf.drawString(x_margin, y, "ENTRADA NO EFECTIVO (Detalle)")
        y -= 15
        cpdf.setFont("Helvetica", 10)
        
        noncash_by_type = {}
        for item in noncash_list:
            tipo = item.get('tipo', 'otros')
            if tipo not in noncash_by_type:
                noncash_by_type[tipo] = []
            noncash_by_type[tipo].append(item)
        
        for tipo, items in noncash_by_type.items():
            tipo_total = sum(item.get('monto', 0) for item in items)
            cpdf.setFont("Helvetica-Bold", 10)
            y = check_page_break(cpdf, y, height, x_margin)
            cpdf.drawString(x_margin, y, f"{tipo.capitalize()}: ${tipo_total:.2f}")
            y -= 12
            cpdf.setFont("Helvetica", 9)
            
            for item in items:
                descripcion = item.get('descripcion', '')
                monto = item.get('monto', 0)
                descripcion_text = f" - {descripcion}" if descripcion else ""
                y = check_page_break(cpdf, y, height, x_margin)
                cpdf.drawString(x_margin + 20, y, f"${monto:.2f}{descripcion_text}")
                y -= 10
            y -= 5 # Small gap between types
        y -= 15
        _draw_line(cpdf, y, x_margin, width - x_margin)
        y -= 20

    # --- FACTURAS A CREDITO ---
    cpdf.setFont("Helvetica-Bold", 13)
    cpdf.setFont("Helvetica-Bold", 12)
    y = check_page_break(cpdf, y, height, x_margin)
    cpdf.drawString(x_margin, y, "FACTURAS A CREDITO")
    y -= 15
    cpdf.setFont("Helvetica", 10)

    credit_by_type = {
        'consumidor final': [],
        'comprobante fiscal': [],
        'viaje': []
    }
    for item in invoices.get('fact_credito', []):
        if item.get('tipo') in credit_by_type:
            credit_by_type[item.get('tipo')].append(item)

    col1_x = x_margin
    col2_x = x_margin + 180
    col3_x = x_margin + 360

    cpdf.drawString(col1_x, y, "CONSUMIDOR FINAL")
    cpdf.drawString(col2_x, y, "COMPROBANTE FISCAL")
    cpdf.drawString(col3_x, y, "VIAJE")
    y -= 12

    cpdf.drawString(col1_x, y, "NUMERO")
    cpdf.drawString(col1_x + 60, y, "MONTO")
    cpdf.drawString(col2_x, y, "NUMERO")
    cpdf.drawString(col2_x + 60, y, "MONTO")
    cpdf.drawString(col3_x, y, "NUMERO")
    cpdf.drawString(col3_x + 60, y, "MONTO")
    y -= 12

    max_credit_rows = max(len(credit_by_type['consumidor final']),
                          len(credit_by_type['comprobante fiscal']),
                          len(credit_by_type['viaje']))
    
    current_y = y
    for i in range(max_credit_rows):
        # Consumidor Final
        if i < len(credit_by_type['consumidor final']):
            item = credit_by_type['consumidor final'][i]
            cpdf.drawString(col1_x, current_y, item.get('numero', ''))
            cpdf.drawString(col1_x + 60, current_y, f"{float(item.get('monto',0)):.2f}")
        
        # Comprobante Fiscal
        if i < len(credit_by_type['comprobante fiscal']):
            item = credit_by_type['comprobante fiscal'][i]
            cpdf.drawString(col2_x, current_y, item.get('numero', ''))
            cpdf.drawString(col2_x + 60, current_y, f"{float(item.get('monto',0)):.2f}")
        
        # Viaje
        if i < len(credit_by_type['viaje']):
            item = credit_by_type['viaje'][i]
            cpdf.drawString(col3_x, current_y, item.get('numero', ''))
            cpdf.drawString(col3_x + 60, current_y, f"{float(item.get('monto',0)):.2f}")
        
        current_y -= 12
        y = check_page_break(cpdf, current_y, height, x_margin)
        if y != current_y: # If page break occurred
            current_y = y
            cpdf.setFont("Helvetica", 10) # Reset font after page break
            cpdf.drawString(col1_x, current_y, "CONSUMIDOR FINAL (Cont.)")
            cpdf.drawString(col2_x, current_y, "COMPROBANTE FISCAL (Cont.)")
            cpdf.drawString(col3_x, current_y, "VIAJE (Cont.)")
            current_y -= 12
            cpdf.drawString(col1_x, current_y, "NUMERO")
            cpdf.drawString(col1_x + 60, current_y, "MONTO")
            cpdf.drawString(col2_x, current_y, "NUMERO")
            cpdf.drawString(col2_x + 60, current_y, "MONTO")
            cpdf.drawString(col3_x, current_y, "NUMERO")
            cpdf.drawString(col3_x + 60, current_y, "MONTO")
            current_y -= 12
    
    y = current_y
    y -= 15
    _draw_line(cpdf, y, x_margin, width - x_margin)
    y -= 20

    # --- FOOTER ---
    y = check_page_break(cpdf, y, height, x_margin, min_space=60)
    cpdf.setFont("Helvetica-Oblique", 9)
    cpdf.drawString(x_margin, 40, f"Generado: {created_at}")
    cpdf.showPage()
    cpdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"arqueo_{arqueo_id}.pdf", mimetype='application/pdf')
    

if __name__ == '__main__':
    app.run(debug=True)
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
                if tipo == 'consumidor_fiscal':
                    tipo_nombre = 'Comprobante Fiscal'
                else:
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
