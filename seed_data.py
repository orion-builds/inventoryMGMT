import sqlite3
from datetime import datetime

def seed_db():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. UPGRADE SCHEMA: Ensure learning columns exist [cite: 2026-03-03]
    try:
        cursor.execute("ALTER TABLE INVENTORY_EVENT ADD COLUMN role_id INTEGER")
        cursor.execute("ALTER TABLE INVENTORY_EVENT ADD COLUMN unit_cost REAL")
        cursor.execute("ALTER TABLE INVENTORY_EVENT ADD COLUMN stock_before_event REAL")
        cursor.execute("ALTER TABLE ROLE ADD COLUMN learned_h REAL")
        print("Schema upgraded with learning columns.")
    except sqlite3.OperationalError:
        print("Schema already contains learning columns.")

    # 2. Clear existing data in dependency order [cite: 2025-12-28]
    tables = ["INVENTORY_EVENT", "ROLE_HISTORY", "ROLE", "PRODUCT", "CATEGORY", "SETTINGS"]
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
    
    # 3. Seed Settings [cite: 2026-03-03]
    cursor.execute("INSERT INTO SETTINGS (key, value) VALUES ('global_ema_alpha', '0.3')")
    cursor.execute("INSERT INTO SETTINGS (key, value) VALUES ('default_holding_penalty', '0.015')")

    # 4. Seed Category (3 columns: id, name, ema_alpha) [cite: 2026-03-03]
    categories = [
        (1, 'Skincare', 0.25),
        (2, 'Supplements', 0.40),
        (3, 'Household', None)
    ]
    cursor.executemany("INSERT INTO CATEGORY VALUES (?, ?, ?)", categories)
    
    # 5. Seed Product (5 columns: id, brand, name, amount, unit) [cite: 2026-03-03]
    products = [
        (1, 'LRP', 'Cicaplast Baume B5+', 40, 'ml'),
        (2, 'COSRX', 'Low pH Cleanser', 150, 'ml'),
        (3, 'NATURIE', 'Hatomugi Skin Milk', 230, 'ml'),
        (4, 'MyProtein', 'Impact Whey (Chocolate)', 1, 'kg'),
        (5, 'Now Foods', 'Magnesium Glycinate', 180, 'caps'),
        (6, 'Muji', 'Cotton Pads', 180, 'pcs')
    ]
    cursor.executemany("INSERT INTO PRODUCT VALUES (?, ?, ?, ?, ?)", products)

    # 6. Seed Role (6 columns: id, name, buffer, category_id, ema_alpha, learned_h) [cite: 2026-03-03]
    roles = [
        (21, 'Barrier Cream', 7, 1, None, 0.04),   
        (22, 'Cleanser', 7, 1, None, 0.015),      
        (23, 'Moisturiser', 14, 1, None, 0.005),  
        (24, 'Protein Powder', 10, 2, 0.5, 0.02), # Overridden EMA alpha [cite: 2026-03-03]
        (25, 'Sleep Support', 30, 2, None, 0.01), 
        (26, 'Daily Cotton', 5, 3, None, 0.002)   
    ]
    cursor.executemany("INSERT INTO ROLE VALUES (?, ?, ?, ?, ?, ?)", roles)

    # 7. Seed Role History
    for i in range(1, 7):
        cursor.execute("INSERT INTO ROLE_HISTORY VALUES (?, ?, ?, NULL)", (20+i, i, '2026-01-01'))

    # 8. Seed Events with Learning Snapshots [cite: 2026-03-03]
    events = [
        # Barrier Cream: URGENT (RED) [cite: 2026-03-03]
        (1, 21, 'Restock (+)', '2026-01-01', 22.00, 1, 22.00, 0),
        (1, 21, 'Finished (-)', '2026-02-28', None, 1, 22.00, 1),

        # Cleanser: WARNING (YELLOW) [cite: 2026-03-03]
        (2, 22, 'Restock (+)', '2026-01-01', 30.00, 3, 10.00, 0),
        (2, 22, 'Finished (-)', '2026-01-20', None, 1, 10.00, 3),
        (2, 22, 'Finished (-)', '2026-02-25', None, 1, 10.00, 2),

        # Protein: STABLE (GREEN) & HIGH CONFIDENCE [cite: 2026-01-08]
        (4, 24, 'Restock (+)', '2026-01-01', 80.00, 4, 20.00, 0),
        (4, 24, 'Finished (-)', '2026-01-15', None, 1, 20.00, 4),
        (4, 24, 'Finished (-)', '2026-01-30', None, 1, 20.00, 4),
        (4, 24, 'Finished (-)', '2026-02-14', None, 1, 20.00, 4),
        (4, 24, 'Finished (-)', '2026-03-01', None, 1, 20.00, 4),

        # Cotton Pads: LEDGER LEARNING (VALUE $H$) [cite: 2026-03-03]
        (6, 26, 'Restock (+)', '2026-01-01', 10.00, 2, 5.00, 0),
        (6, 26, 'Restock (+)', '2026-02-15', 20.00, 5, 5.00, 200) # Snapshot 200 days stock [cite: 2026-03-03]
    ]
    cursor.executemany("""
        INSERT INTO INVENTORY_EVENT 
        (product_id, role_id, event_type, event_date, cost_sgd, quantity, unit_cost, stock_before_event)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, events)

    conn.commit()
    conn.close()
    print("Full context data live. Refresh your app!")

if __name__ == "__main__":
    seed_db()