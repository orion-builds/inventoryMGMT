import sqlite3
from datetime import datetime, timedelta
import random

def seed():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Clear existing data in dependency order
    tables = ["INVENTORY_EVENT", "ROLE_HISTORY", "ROLE", "PRODUCT", "CATEGORY"]
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")

    # 2. Setup Category
    cursor.execute("INSERT INTO CATEGORY (name) VALUES ('Skincare')")
    skin_cat = cursor.lastrowid

    now = datetime.now()

    # 3. Realistic Skincare Test Data
    # (Brand, Name, Role, Buffer, BasePrice, PriceVar, ConsumDays)
    products_to_seed = [
        ('NATURIE', 'Hatomugi Skin Milk', 'Face Moisturiser', 7, 12.50, 3.00, 45),
        ('LRP', 'Cicaplast Baume B5+', 'Barrier Cream', 14, 22.00, 5.00, 25),
        ('MENARINI', 'Tretinoin Gel', 'Retinoid', 7, 35.00, 8.00, 75),
        ('COSRX', 'Low pH Cleanser', 'Cleanser', 7, 11.00, 2.50, 40)
    ]

    for brand, p_name, r_name, buffer, base_price, var, consume_days in products_to_seed:
        # Create Product
        cursor.execute("""
            INSERT INTO PRODUCT (brand, name, amount, unit_of_measure) 
            VALUES (?, ?, 100, 'ml')
        """, (brand, p_name))
        p_id = cursor.lastrowid

        # Create Role
        cursor.execute("""
            INSERT INTO ROLE (name, target_buffer_days, category_id) 
            VALUES (?, ?, ?)
        """, (r_name, buffer, skin_cat))
        r_id = cursor.lastrowid
        
        # Create History Era (Starts 14 months ago)
        start_date = now - timedelta(days=420)
        cursor.execute("""
            INSERT INTO ROLE_HISTORY (role_id, product_id, start_date) 
            VALUES (?, ?, ?)
        """, (r_id, p_id, start_date.strftime('%Y-%m-%d')))

        current_date = start_date
        stock = 0

        # 4. Realistic Event Simulation
        while current_date < now:
            # Logic for Restock
            if stock <= 1 or random.random() < 0.04:
                buy_qty = random.choice([1, 2])
                total_cost = (base_price + random.uniform(-var, var)) * buy_qty
                
                # FIX: 4 placeholders for 4 variables
                cursor.execute("""
                    INSERT INTO INVENTORY_EVENT (product_id, event_type, event_date, cost_sgd, quantity) 
                    VALUES (?, 'Restock (+)', ?, ?, ?)
                """, (p_id, current_date.strftime('%Y-%m-%d'), round(total_cost, 2), buy_qty))
                stock += buy_qty
                
            # Logic for Consumption
            usage_variance = random.randint(-5, 5)
            current_date += timedelta(days=consume_days + usage_variance)
            
            if current_date < now and stock > 0:
                # Matches schema: product_id, event_type, event_date, cost_sgd (None), quantity
                cursor.execute("""
                    INSERT INTO INVENTORY_EVENT (product_id, event_type, event_date, cost_sgd, quantity) 
                    VALUES (?, 'Finished (-)', ?, NULL, 1)
                """, (p_id, current_date.strftime('%Y-%m-%d')))
                stock -= 1

    conn.commit()
    conn.close()
    print("Database successfully seeded with realistic history and price fluctuations.")

if __name__ == "__main__":
    seed()