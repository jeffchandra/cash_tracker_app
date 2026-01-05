import sqlite3

DB_PATH = "cash.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cash_entries (
        date TEXT,
        cashier TEXT,
        denomination INTEGER,
        count INTEGER,
        parking INTEGER,
        saving INTEGER,
        debt_credit INTEGER,
        PRIMARY KEY (date, cashier, denomination)
    )
    """)

    conn.commit()
    conn.close()
