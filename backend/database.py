import sqlite3
import os

# Define where user data will live [cite: 2025-12-06, 2026-03-05]
DATA_DIR = "data/user_stores"

def get_db_connection(user_id: str):
    """
    Connects to a specific user's database and initializes 
    the schema if it doesn't exist. [cite: 2026-03-05]
    """
    # 1. Ensure the directory exists [cite: 2026-03-05]
    os.makedirs(DATA_DIR, exist_ok=True)
    db_path = os.path.join(DATA_DIR, f"{user_id}.db")
    
    # 2. Connect to the siloed database [cite: 2026-03-05]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name [cite: 2026-03-06]
    cursor = conn.cursor()
    
    # 3. Enforce Foreign Keys [cite: 2026-03-06]
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 4. Initialize Schema (Consolidated from your select_all.py output) [cite: 2026-03-05, 2026-03-08]
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS CATEGORY (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ema_alpha REAL
        );

        CREATE TABLE IF NOT EXISTS PRODUCT (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            unit_of_measure TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ROLE (
            role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_buffer_days INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            ema_alpha REAL,
            learned_h REAL,
            holding_penalty REAL,
            FOREIGN KEY (category_id) REFERENCES CATEGORY(category_id)
        );

        CREATE TABLE IF NOT EXISTS ROLE_HISTORY (
            role_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            start_date DATETIME NOT NULL,
            end_date DATETIME,
            PRIMARY KEY (role_id, product_id, start_date),
            FOREIGN KEY (role_id) REFERENCES ROLE(role_id),
            FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id)
        );

        CREATE TABLE IF NOT EXISTS INVENTORY_EVENT (
            product_id INTEGER NOT NULL,
            role_id INTEGER,
            event_type TEXT NOT NULL,
            event_date DATETIME NOT NULL,
            cost_sgd REAL,
            quantity REAL,  -- Changed to REAL to support 0.3 entries [cite: 2026-03-06]
            unit_cost REAL,
            stock_before_event REAL,
            implied_h REAL,
            PRIMARY KEY (product_id, event_type, event_date),
            FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id),
            FOREIGN KEY (role_id) REFERENCES ROLE(role_id)
        );

        CREATE TABLE IF NOT EXISTS SETTINGS (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        -- Seed initial default settings [cite: 2026-03-05]
        INSERT OR IGNORE INTO SETTINGS (key, value) VALUES ('global_ema_alpha', '0.3');
    """)
    
    conn.commit()
    return conn