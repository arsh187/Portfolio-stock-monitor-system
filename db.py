import sqlite3, os, time

DB_PATH = os.environ.get("DB_PATH", "stocks.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol   TEXT NOT NULL,
                price    REAL,
                open     REAL,
                high     REAL,
                low      REAL,
                volume   INTEGER,
                pct      REAL,
                ts       INTEGER DEFAULT (strftime('%s','now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                symbol   TEXT PRIMARY KEY,
                signal   TEXT,
                reason   TEXT,
                anomaly  INTEGER DEFAULT 0,
                zscore   REAL,
                updated  INTEGER
            )
        """)
        conn.commit()

def insert_price(sym, price, open_, high, low, volume, pct):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO prices (symbol,price,open,high,low,volume,pct) VALUES (?,?,?,?,?,?,?)",
            (sym, price, open_, high, low, volume, pct)
        )
        conn.commit()

def get_recent_prices(sym, n=60):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT price,pct,volume FROM prices WHERE symbol=? ORDER BY ts DESC LIMIT ?",
            (sym, n)
        ).fetchall()
    return rows

def upsert_signal(sym, signal, reason, anomaly, zscore):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO signals (symbol,signal,reason,anomaly,zscore,updated)
            VALUES (?,?,?,?,?,strftime('%s','now'))
            ON CONFLICT(symbol) DO UPDATE SET
              signal=excluded.signal, reason=excluded.reason,
              anomaly=excluded.anomaly, zscore=excluded.zscore,
              updated=excluded.updated
        """, (sym, signal, reason, int(anomaly), round(zscore, 3)))
        conn.commit()

def get_all_signals():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM signals").fetchall()]