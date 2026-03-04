import sqlite3
from datetime import datetime

def seed_db():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Clear existing data [cite: 2025-12-28]
    tables = ["INVENTORY_EVENT", "ROLE_HISTORY", "ROLE", "PRODUCT", "CATEGORY", "SETTINGS"]
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
    
    # 2. Seed Settings [cite: 2026-03-03]
    cursor.execute("INSERT INTO SETTINGS (key, value) VALUES ('global_ema_alpha', '0.3')")
    cursor.execute("INSERT INTO SETTINGS (key, value) VALUES ('default_holding_penalty', '0.015')")

    # 3. Seed Category [cite: 2026-03-03]
    categories = [
        (1, 'Skincare', 0.25),
        (2, 'Supplements', 0.40),
        (3, 'Household', None)
    ]
    cursor.executemany("INSERT INTO CATEGORY VALUES (?, ?, ?)", categories)
    
    # 4. Seed 11 Products [cite: 2026-03-04]
    products = [
        (1, 'LRP', 'Cicaplast Baume B5+', 40, 'ml'),
        (2, 'COSRX', 'Low pH Cleanser', 150, 'ml'),
        (3, 'NATURIE', 'Hatomugi Skin Milk', 230, 'ml'),
        (4, 'MyProtein', 'Impact Whey (Chocolate)', 1, 'kg'),
        (5, 'Now Foods', 'Magnesium Glycinate', 180, 'caps'),
        (6, 'Muji', 'Cotton Pads', 180, 'pcs'),
        (7, 'Hada Labo', 'Gokujyun Lotion', 170, 'ml'),
        (8, 'The Ordinary', 'Niacinamide 10%', 30, 'ml'),
        (9, 'Eucerin', 'Dry Touch Sunscreen', 50, 'ml'),
        (10, 'Dettol', 'Hand Wash Refill', 900, 'ml'),
        (11, 'Kao', 'Attack Liquid Detergent', 1.6, 'kg')
    ]
    cursor.executemany("INSERT INTO PRODUCT VALUES (?, ?, ?, ?, ?)", products)

    # 5. Seed Roles [cite: 2026-03-03]
    roles = [
        (21, 'Barrier Cream', 7, 1, None, 0.04),   
        (22, 'Cleanser', 7, 1, None, 0.015),      
        (23, 'Body Moisturizer', 14, 1, None, 0.005),  
        (24, 'Protein Powder', 10, 2, 0.5, 0.02),
        (25, 'Sleep Support', 30, 2, None, 0.01), 
        (26, 'Daily Cotton', 5, 3, None, 0.002),
        (27, 'Hydrating Toner', 10, 1, None, 0.01),
        (28, 'Active Serum', 7, 1, None, 0.03),
        (29, 'Sun Protection', 7, 1, None, 0.02),
        (30, 'Hand Soap', 14, 3, None, 0.001),
        (31, 'Laundry', 7, 3, None, 0.008)
    ]
    cursor.executemany("INSERT INTO ROLE VALUES (?, ?, ?, ?, ?, ?)", roles)

    for i in range(1, 12):
        cursor.execute("INSERT INTO ROLE_HISTORY VALUES (?, ?, ?, NULL)", (20+i, i, '2026-01-01'))

    # 7. Seed Diverse Scenarios [cite: 2026-03-04]
    events = [
        # --- SCENARIO A: HIGH DATA / STABLE (The "Benchmark") ---
        # Cotton Pads: 5 logs = High Confidence [cite: 2026-03-03]
        (6, 26, 'Restock (+)', '2025-10-01', 10.00, 10, 1.00, 0),
        (6, 26, 'Finished (-)', '2025-11-01', None, 1, 1.00, 10),
        (6, 26, 'Finished (-)', '2025-12-01', None, 1, 1.00, 9),
        (6, 26, 'Finished (-)', '2026-01-01', None, 1, 1.00, 8),
        (6, 26, 'Finished (-)', '2026-02-01', None, 1, 1.00, 7),
        (6, 26, 'Finished (-)', '2026-03-01', None, 1, 1.00, 6),

        # --- SCENARIO B: THE "48-DAY BUG" FIX (Low Confidence) ---
        # Hada Labo: Partial Init + 2 logs = Now valid Medium Confidence [cite: 2026-03-04]
        (7, 27, 'Init', '2026-01-01', None, 0.4, 0, 0),
        (7, 27, 'Finished (-)', '2026-01-15', None, 0.4, 0, 0.4), # Anchor [cite: 2026-03-04]
        (7, 27, 'Restock (+)', '2026-01-16', 15.00, 2, 7.50, 0),
        (7, 27, 'Finished (-)', '2026-02-10', None, 1, 7.50, 2), # Finish 1
        (7, 27, 'Finished (-)', '2026-03-04', None, 1, 7.50, 1), # Finish 2 -> Calculated! [cite: 2026-03-04]

        # --- SCENARIO C: THE "INSURRECT DATA" STATE ("?") ---
        # Dettol: Only anchor exists = Still "?" [cite: 2026-03-04]
        (10, 30, 'Init', '2026-01-01', None, 5.5, 0, 0),
        (10, 30, 'Finished (-)', '2026-02-15', None, 0.5, 0, 5.5), # Anchor only [cite: 2026-03-04]

        # --- SCENARIO D: THE WHEY VELOCITY TEST (Calculated) ---
        # Whey: 2 logs = Calculated (Approx 20-day cycle) [cite: 2026-03-04]
        (4, 24, 'Restock (+)', '2026-01-01', 80.00, 5, 16.00, 0),
        (4, 24, 'Finished (-)', '2026-01-20', None, 1, 16.00, 5), # Anchor [cite: 2026-03-04]
        (4, 24, 'Finished (-)', '2026-02-10', None, 1, 16.00, 4), # Finish 1
        (4, 24, 'Finished (-)', '2026-03-01', None, 1, 16.00, 3), # Finish 2 -> Calculated! [cite: 2026-03-04]

        # --- SCENARIO E: URGENT / LOW STOCK ---
        # Barrier Cream: Stock is 0, should show Urgent Red [cite: 2026-03-03]
        (1, 21, 'Restock (+)', '2026-01-01', 22.00, 2, 11.00, 0),
        (1, 21, 'Finished (-)', '2026-01-20', None, 1, 11.00, 2), # Anchor
        (1, 21, 'Finished (-)', '2026-02-10', None, 1, 11.00, 1), # Finish 1
        (1, 21, 'Finished (-)', '2026-03-02', None, 1, 11.00, 0), # Finish 2 -> Empty [cite: 2026-03-03]
    ]
    cursor.executemany("""
        INSERT INTO INVENTORY_EVENT 
        (product_id, role_id, event_type, event_date, cost_sgd, quantity, unit_cost, stock_before_event)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, events)

    conn.commit()
    conn.close()
    print("Database seeded with High, Medium, and '?' scenarios.")

if __name__ == "__main__":
    seed_db()