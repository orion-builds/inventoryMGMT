import sqlite3

def upgrade_db():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        # Adds the new column to your existing table
        cursor.execute("ALTER TABLE INVENTORY_EVENT ADD COLUMN implied_h REAL;")
        conn.commit()
        print("Success: 'implied_h' column added to INVENTORY_EVENT table.")
    except sqlite3.OperationalError as e:
        # Failsafe if the column was already added
        if "duplicate column name" in str(e).lower():
            print("Notice: Column 'implied_h' already exists. You are good to go!")
        else:
            print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_db()