import sqlite3
from datetime import datetime, timedelta

def seed():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Clear existing data
    for table in ["INVENTORY_EVENT", "ROLE_HISTORY", "ROLE", "PRODUCT", "CATEGORY"]:
        cursor.execute(f"DELETE FROM {table}")

    # 1. Create Category
    cursor.execute("INSERT INTO CATEGORY (name) VALUES ('Skincare')")
    cat_id = cursor.lastrowid

    now = datetime.now()

    # 2. Define Test Cases
    # (Brand, Name, Role, Buffer, DaysSinceFirstFinish, CurrentStock)
    test_cases = [
        ('NATURIE', 'Hatomugi Skin Milk', 'Moisturiser', 7, 60, 1),  # Stable (60 days left)
        ('LRP', 'Cicaplast Baume B5+', 'Barrier Cream', 14, 12, 1), # Warning (12 days left)
        ('MENARINI', 'Tretinoin Gel', 'Retinoid', 7, 4, 1)          # Urgent (4 days left)
    ]

    for brand, p_name, r_name, buffer, days_ago, stock in test_cases:
        # Create Product
        cursor.execute("INSERT INTO PRODUCT (brand, name, amount, unit_of_measure) VALUES (?, ?, 100, 'ml')", (brand, p_name))
        p_id = cursor.lastrowid

        # Create Role
        cursor.execute("INSERT INTO ROLE (name, target_buffer_days, category_id) VALUES (?, ?, ?)", (r_name, buffer, cat_id))
        r_id = cursor.lastrowid

        # Create History
        start_date = (now - timedelta(days=100)).strftime('%Y-%m-%d')
        cursor.execute("INSERT INTO ROLE_HISTORY (role_id, product_id, start_date) VALUES (?, ?, ?)", (r_id, p_id, start_date))

        # Create Events
        # Initial Restock
        first_restock_date = (now - timedelta(days=days_ago + 10)).strftime('%Y-%m-%d')
        cursor.execute("INSERT INTO INVENTORY_EVENT (product_id, event_type, event_date, quantity) VALUES (?, 'Restock (+)', ?, ?)", (p_id, first_restock_date, stock + 1))
        
        # First Finished Event (This sets the "Burn Rate")
        finish_date = (now - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        cursor.execute("INSERT INTO INVENTORY_EVENT (product_id, event_type, event_date, quantity) VALUES (?, 'Finished (-)', ?, 1)", (p_id, finish_date))

    conn.commit()
    conn.close()
    print("Database seeded with Green, Yellow, and Red test cases.")

if __name__ == "__main__":
    seed()