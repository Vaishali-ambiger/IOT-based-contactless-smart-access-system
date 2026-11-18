"""
database.py
-----------
This file handles everything related to the SQLite database:
- creating tables
- reading authorized RFID cards
- saving access log entries

Keeping all database code in one file makes app.py easier to read.
"""

import sqlite3
import os

# Path to the database file (database/smart_access.db)
DB_PATH = os.path.join(os.path.dirname(__file__), "database", "smart_access.db")


def get_connection():
    """Creates a connection to the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """Creates the required tables if they don't already exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Table 1: Authorized RFID cards
    cur.execute("""
        CREATE TABLE IF NOT EXISTS authorized_rfid (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_id TEXT UNIQUE NOT NULL
        )
    """)

    # Table 2: Access Logs (every simulated attempt)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            rfid_id TEXT,
            rfid_status TEXT,
            temperature REAL,
            mask_status TEXT,
            decision TEXT,
            door_status TEXT,
            reason TEXT
        )
    """)

    # Table 3: Safety Alerts (used starting Phase 2)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS safety_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            alert_type TEXT,
            message TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            name TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # If no RFID cards exist yet, add 3 example authorized cards
    cur.execute("SELECT COUNT(*) FROM authorized_rfid")
    if cur.fetchone()[0] == 0:
        default_ids = ["RFID001", "RFID002", "RFID003"]
        cur.executemany(
            "INSERT INTO authorized_rfid (rfid_id) VALUES (?)",
            [(rid,) for rid in default_ids]
        )

    cur.execute("INSERT OR IGNORE INTO settings (name, value) VALUES ('temp_threshold', '37.5')")

    conn.commit()
    conn.close()


def get_authorized_rfids():
    """Returns a list of all authorized RFID IDs, e.g. ['RFID001', 'RFID002']."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT rfid_id FROM authorized_rfid")
    rows = cur.fetchall()
    conn.close()
    return [row["rfid_id"] for row in rows]


def add_authorized_rfid(rfid_id):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO authorized_rfid (rfid_id) VALUES (?)", (rfid_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
    return True


def remove_authorized_rfid(rfid_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM authorized_rfid WHERE rfid_id = ?", (rfid_id,))
    conn.commit()
    removed = cur.rowcount > 0
    conn.close()
    return removed


def get_setting(name, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(name, value):
    conn = get_connection()
    conn.execute("""
        INSERT INTO settings (name, value) VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET value = excluded.value
    """, (name, str(value)))
    conn.commit()
    conn.close()


def get_access_logs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM access_logs ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_alerts():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM safety_alerts ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_safety_alert(date, time, alert_type, message):
    conn = get_connection()
    conn.execute("""
        INSERT INTO safety_alerts (date, time, alert_type, message)
        VALUES (?, ?, ?, ?)
    """, (date, time, alert_type, message))
    conn.commit()
    conn.close()


def get_statistics():
    conn = get_connection()
    stats = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN decision = 'GRANTED' THEN 1 ELSE 0 END) AS granted,
               SUM(CASE WHEN decision = 'DENIED' THEN 1 ELSE 0 END) AS denied
        FROM access_logs
    """).fetchone()
    alert_count = conn.execute("SELECT COUNT(*) AS count FROM safety_alerts").fetchone()["count"]
    conn.close()
    return {
        "total": stats["total"] or 0,
        "granted": stats["granted"] or 0,
        "denied": stats["denied"] or 0,
        "alerts": alert_count
    }


def add_access_log(date, time, rfid_id, rfid_status, temperature, mask_status,
                    decision, door_status, reason):
    """Inserts one access attempt into the access_logs table."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO access_logs
            (date, time, rfid_id, rfid_status, temperature, mask_status, decision, door_status, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (date, time, rfid_id, rfid_status, temperature, mask_status, decision, door_status, reason))
    conn.commit()
    conn.close()
