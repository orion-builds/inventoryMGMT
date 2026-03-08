import sqlite3
import os

def rewrite_database():
    db_file = "inventory.db"
    
    # 1. Close any ghost connections and remove the old file [cite: 2026-03-05]
    if os.path.exists(db_file):
        print(f"🗑️  Removing existing {db_file}...")
        os.remove(db_file)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    print("🏗️  Rebuilding tables from your verified schema...")

    # 2. Re-create the tables exactly as they appeared in your schema
    cursor.executescript("""
        CREATE TABLE CATEGORY (
            category_id INTEGER PRIMARY KEY,
            name TEXT,
            ema_alpha REAL
        );

        CREATE TABLE PRODUCT (
            product_id INTEGER PRIMARY KEY,
            brand TEXT,
            name TEXT,
            amount REAL,
            unit_of_measure TEXT
        );

        CREATE TABLE ROLE (
            role_id INTEGER PRIMARY KEY,
            name TEXT,
            target_buffer_days INTEGER,
            category_id INTEGER,
            ema_alpha REAL,
            learned_h REAL,
            holding_penalty REAL,
            FOREIGN KEY(category_id) REFERENCES CATEGORY(category_id)
        );

        CREATE TABLE ROLE_HISTORY (
            role_id INTEGER,
            product_id INTEGER,
            start_date DATETIME,
            end_date DATETIME,
            FOREIGN KEY(role_id) REFERENCES ROLE(role_id),
            FOREIGN KEY(product_id) REFERENCES PRODUCT(product_id)
        );

        CREATE TABLE INVENTORY_EVENT (
            product_id INTEGER,
            role_id INTEGER,
            event_type TEXT,
            event_date DATETIME,
            cost_sgd REAL,
            quantity INTEGER,
            unit_cost REAL,
            stock_before_event REAL,
            implied_h REAL,
            FOREIGN KEY(product_id) REFERENCES PRODUCT(product_id),
            FOREIGN KEY(role_id) REFERENCES ROLE(role_id)
        );

        CREATE TABLE SETTINGS (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    # 3. Re-insert your essential Global Defaults
    cursor.executemany("INSERT INTO SETTINGS (key, value) VALUES (?, ?)", [
        ('global_ema_alpha', '0.3'),
        ('default_holding_penalty', '0.015')
    ])

    conn.commit()
    conn.close()
    print("✅ Database successfully rewritten. It is now empty and ready for real data.")

if __name__ == "__main__":
    rewrite_database()