import sqlite3
from datetime import datetime, timedelta

def seed_database():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    # 1. Clean existing data
    cursor.executescript("""
        DELETE FROM INVENTORY_EVENT;
        DELETE FROM ROLE_HISTORY;
        DELETE FROM ROLE;
        DELETE FROM PRODUCT;
        DELETE FROM CATEGORY;
        DELETE FROM SETTINGS;
    """)

    # 2. Global Settings
    cursor.executemany("INSERT INTO SETTINGS (key, value) VALUES (?, ?)", [
        ('global_ema_alpha', '0.3'),
        ('default_holding_penalty', '0.015')
    ])

    # 3. Categories
    categories = [
        (1, 'Skincare', 0.25),
        (2, 'Supplements', 0.40),
        (3, 'Household', 0.15)
    ]
    cursor.executemany("INSERT INTO CATEGORY (category_id, name, ema_alpha) VALUES (?, ?, ?)", categories)

    # 4. Products
    products = [
        (1, 'LRP', 'Cicaplast Baume B5+', 40.0, 'ml'),
        (2, 'COSRX', 'Low pH Cleanser', 150.0, 'ml'),
        (3, 'NATURIE', 'Hatomugi Skin Milk', 230.0, 'ml'),
        (4, 'MyProtein', 'Impact Whey', 1.0, 'kg'),
        (5, 'Now Foods', 'Magnesium', 180.0, 'caps'),
        (6, 'Muji', 'Cotton Pads', 180.0, 'pcs')
    ]
    cursor.executemany("INSERT INTO PRODUCT (product_id, brand, name, amount, unit_of_measure) VALUES (?, ?, ?, ?, ?)", products)

    # 5. Roles
    # (id, name, buffer, category, alpha, penalty)
    roles = [
        (1, 'Barrier Cream', 7, 1, None, 0.002),
        (2, 'Cleanser', 7, 1, None, 0.002),
        (3, 'Moisturizer', 14, 1, None, 0.002),
        (4, 'Protein', 10, 2, 0.5, 0.002),
        (5, 'Sleep Support', 30, 2, None, 0.002),
        (6, 'Daily Cotton', 5, 3, None, 0.002)
    ]
    cursor.executemany("""
        INSERT INTO ROLE (role_id, name, target_buffer_days, category_id, ema_alpha, holding_penalty) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, roles)

    # 6. Active Routine (Role History)
    history = [
        (1, 1, '2025-10-01'),
        (2, 2, '2026-01-01'),
        (3, 3, '2026-01-01'),
        (4, 4, '2025-11-01'),
        (5, 5, '2025-01-01'),
        (6, 6, '2024-10-01')
    ]
    cursor.executemany("INSERT INTO ROLE_HISTORY (role_id, product_id, start_date) VALUES (?, ?, ?)", history)

    # 7. Inventory Events (Realistic Math Testing)
    # We will simulate consumption intervals to give the dashboard actual data to crunch.
    today = datetime.now()
    events = []

    # SCENARIO A: Stable Routine (Cleanser - COSRX)
    # Finished every 45 days exactly.
    for i in range(4):
        date = (today - timedelta(days=180 - (i * 45))).strftime('%Y-%m-%d')
        events.append((2, 2, 'Finished (-)', date, None, 1))
    # Restock with fluctuating prices for EMA testing
    events.append((2, 2, 'Restock (+)', (today - timedelta(days=10)).strftime('%Y-%m-%d'), 12.50, 1)) # Cheaper
    events.append((2, 2, 'Restock (+)', (today - timedelta(days=180)).strftime('%Y-%m-%d'), 15.00, 2)) # Baseline

    # SCENARIO B: High Volatility (Protein - MyProtein)
    # Finished at random intervals: 20d, 35d, 15d. Testing Low Confidence rating.
    protein_dates = [120, 100, 65, 50]
    for d in protein_dates:
        events.append((4, 4, 'Finished (-)', (today - timedelta(days=d)).strftime('%Y-%m-%d'), None, 1))
    events.append((4, 4, 'Restock (+)', (today - timedelta(days=130)).strftime('%Y-%m-%d'), 45.00, 3))

    # SCENARIO C: The Early Buyer (Moisturizer - NATURIE)
    # Bought at a huge discount while still having stock to test Implied Penalty (h).
    events.append((3, 3, 'Init', '2026-01-01', 10.00, 1))
    events.append((3, 3, 'Finished (-)', (today - timedelta(days=30)).strftime('%Y-%m-%d'), None, 1))
    # Stock Before: 0. Buying early:
    events.append((3, 3, 'Restock (+)', (today - timedelta(days=5)).strftime('%Y-%m-%d'), 8.00, 2))

    # SCENARIO D: Bulk Stock (Cotton Pads - Muji)
    # Large quantity, slow burn.
    events.append((6, 6, 'Restock (+)', '2024-10-01', 5.50, 5))
    for i in range(4):
        date = (today - timedelta(days=400 - (i * 90))).strftime('%Y-%m-%d')
        events.append((6, 6, 'Finished (-)', date, None, 1))

    # SCENARIO E: Empty Stash (Barrier Cream - LRP)
    events.append((1, 1, 'Restock (+)', '2025-10-01', 10.00, 1))
    events.append((1, 1, 'Finished (-)', today.strftime('%Y-%m-%d'), None, 1))

    cursor.executemany("""
        INSERT INTO INVENTORY_EVENT (product_id, role_id, event_type, event_date, cost_sgd, quantity)
        VALUES (?, ?, ?, ?, ?, ?)
    """, events)

    conn.commit()
    conn.close()
    print("Database seeded with realistic routine data.")

if __name__ == "__main__":
    seed_database()