import sqlite3, json
conn = sqlite3.connect('arqueo.db')
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS arqueos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    cashier TEXT,
    shift TEXT,
    starting_fund REAL,
    counts_json TEXT,
    noncash_json TEXT,
    noncash_list_json TEXT,
    invoices_json TEXT,
    totals_json TEXT,
    created_at TEXT
)
''')
conn.commit()
print("Base de datos 'arqueo.db' inicializada con tabla 'arqueos'.")
