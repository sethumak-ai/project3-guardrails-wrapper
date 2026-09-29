import sqlite3
from datetime import datetime

DB_FILE = "attack_log.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS attacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            attack_category TEXT,
            prompt TEXT,
            response TEXT,
            succeeded TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_attack(category, prompt, response, succeeded, notes=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO attacks (timestamp, attack_category, prompt, response, succeeded, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), category, prompt, response, succeeded, notes))
    conn.commit()
    conn.close()