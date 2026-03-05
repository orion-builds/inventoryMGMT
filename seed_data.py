import sqlite3
import random
from datetime import datetime, timedelta

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
    
    # 2. Global Settings & Categories [cite: 2026-03-03]
    cursor.execute("INSERT INTO SETTINGS (key, value) VALUES ('global_ema_alpha', '0.3')")
    cursor.execute("INSERT INTO SETTINGS (key, value) VALUES ('default_holding_penalty', '0.015')")
    
    categories = [(1, 'Skincare', 0.25), (2, 'Supplements', 0.40), (3, 'Household', None)]
    cursor.executemany("INSERT INTO CATEGORY VALUES (?, ?, ?)", categories)
    
    # 3. Products (ID, Brand, Name, Amount, Unit) [cite: 2026-03-04]
    products = [
        (1, 'LRP', 'Cicaplast Baume B5+', 40, 'ml'),
        (2, 'COSRX', 'Low pH Cleanser', 150, 'ml'),
        (3, 'NATURIE', 'Hatomugi Skin Milk', 230, 'ml'),
        (4, 'MyProtein', 'Impact Whey', 1, 'kg'),
        (5, 'Now Foods', 'Magnesium', 180, 'caps'),
        (6, 'Muji', 'Cotton Pads', 180, 'pcs')
    ]
    cursor.executemany("INSERT INTO PRODUCT VALUES (?, ?, ?, ?, ?)", products)

    # 4. Roles (ID, Name, Buffer, Category_ID, EMA, Penalty) [cite: 2026-03-03]
    roles = [
        (21, 'Barrier Cream', 7, 1, None, 0.04),   
        (22, 'Cleanser', 7, 1, None, 0.015),      
        (23, 'Moisturizer', 14, 1, None, 0.005),  
        (24, 'Protein', 10, 2, 0.5, 0.02),
        (25, 'Sleep Support', 30, 2, None, 0.01), 
        (26, 'Daily Cotton', 5, 3, None, 0.002)
    ]
    cursor.executemany("INSERT INTO ROLE VALUES (?, ?, ?, ?, ?, ?)", roles)

    # Historical assignments [cite: 2026-03-04]
    history = [
        (21, 1, '2025-10-01'), (22, 2, '2026-01-01'), (23, 3, '2026-01-01'),
        (24, 4, '2025-11-01'), (25, 5, '2025-01-01'), (26, 6, '2024-10-01')
    ]
    cursor.executemany("INSERT INTO ROLE_HISTORY VALUES (?, ?, ?, NULL)", history)

    events = []

    # --- SCENARIO 1: MASSIVE DATA / INCONSISTENT (15 Points) - Cotton Pads ---
    # Testing: Does High CV expand the margin despite the high sample size? [cite: 2026-03-04]
    current_stock = 30
    events.append((6, 26, 'Restock (+)', '2024-10-01', 30.00, 30, 1.00, 0))
    last_date = datetime(2024, 10, 1)
    for i in range(1, 16):
        # Add random inconsistency: usage varies between 22 and 38 days [cite: 2026-03-04]
        days_passed = random.randint(22, 38)
        last_date += timedelta(days=days_passed)
        events.append((6, 26, 'Finished (-)', last_date.strftime('%Y-%m-%d'), None, 1, 1.00, current_stock))
        current_stock -= 1
        
        # Mid-stream restock: Buying 10 more in July 2025 [cite: 2026-03-04]
        if i == 8:
            events.append((6, 26, 'Restock (+)', last_date.strftime('%Y-%m-%d'), 10.00, 10, 1.00, current_stock))
            current_stock += 10

    # --- SCENARIO 2: HIGH DATA / STABLE (10 Points) - Magnesium ---
    # Consistent 60-day cycle with very low variance [cite: 2026-03-04]
    current_stock = 15
    events.append((5, 25, 'Restock (+)', '2025-01-01', 300.00, 15, 20.00, 0))
    last_date = datetime(2025, 1, 1)
    for i in range(1, 11):
        days_passed = 60 + random.randint(-2, 2) # High consistency [cite: 2026-03-04]
        last_date += timedelta(days=days_passed)
        events.append((5, 25, 'Finished (-)', last_date.strftime('%Y-%m-%d'), None, 1, 20.00, current_stock))
        current_stock -= 1

    # --- SCENARIO 3: MEDIUM DATA (6 Points) - Protein Powder ---
    # Fast 18-25 day cycle [cite: 2026-03-04]
    current_stock = 12
    events.append((4, 24, 'Restock (+)', '2025-11-01', 240.00, 12, 20.00, 0))
    last_date = datetime(2025, 11, 1)
    for i in range(1, 7):
        days_passed = random.randint(18, 25)
        last_date += timedelta(days=days_passed)
        events.append((4, 24, 'Finished (-)', last_date.strftime('%Y-%m-%d'), None, 1, 20.00, current_stock))
        current_stock -= 1

    # --- SCENARIO 4: LOW DATA (2 Points) - Skin Milk ---
    # Shows Yellow/Low Confidence due to only 1 interval [cite: 2026-03-04]
    events.append((3, 23, 'Restock (+)', '2026-01-01', 50.00, 5, 10.00, 0))
    events.append((3, 23, 'Finished (-)', '2026-01-25', None, 1, 10.00, 5))
    events.append((3, 23, 'Finished (-)', '2026-02-28', None, 1, 10.00, 4))

    # --- SCENARIO 5: URGENT / EMPTY - Barrier Cream ---
    # Ran out today (Mar 4th) after 3 bottles [cite: 2026-03-03]
    events.append((1, 21, 'Restock (+)', '2025-10-01', 40.00, 4, 10.00, 0))
    events.append((1, 21, 'Finished (-)', '2025-11-15', None, 1, 10.00, 4))
    events.append((1, 21, 'Finished (-)', '2026-01-05', None, 1, 10.00, 3))
    events.append((1, 21, 'Finished (-)', '2026-02-10', None, 1, 10.00, 2))
    events.append((1, 21, 'Finished (-)', '2026-03-04', None, 1, 10.00, 1))

    # --- SCENARIO 6: INSUFFICIENT DATA ("?") - Cleanser ---
    # Only anchor point exists [cite: 2026-03-04]
    events.append((2, 22, 'Restock (+)', '2026-01-01', 30.00, 3, 10.00, 0))
    events.append((2, 22, 'Finished (-)', '2026-02-15', None, 1, 10.00, 3))

    cursor.executemany("""
        INSERT INTO INVENTORY_EVENT 
        (product_id, role_id, event_type, event_date, cost_sgd, quantity, unit_cost, stock_before_event)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, events)

    conn.commit()
    conn.close()
    print("Database seeded with high-variance and multi-restock scenarios.")

if __name__ == "__main__":
    seed_db()