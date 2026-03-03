import sqlite3

def migrate_events_table():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    # List of columns to add for the learning engine [cite: 2026-03-03]
    new_columns = [
        ("role_id", "INTEGER"),
        ("unit_cost", "REAL"),
        ("stock_before_event", "REAL")
    ]
    
    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE INVENTORY_EVENT ADD COLUMN {col_name} {col_type} DEFAULT NULL")
            print(f"Added column: {col_name}")
        except sqlite3.OperationalError:
            print(f"Column already exists: {col_name}")

    conn.commit()
    conn.close()
    print("Migration complete. Your ledger now has memory.")

if __name__ == "__main__":
    migrate_events_table()