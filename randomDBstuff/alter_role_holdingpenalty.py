import sqlite3

def upgrade_role_table():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    try:
        # 1. Add the new column to store the learned penalty
        cursor.execute("ALTER TABLE ROLE ADD COLUMN holding_penalty REAL;")
        
        # 2. Backfill existing roles with the default 0.2% penalty (0.002)
        cursor.execute("UPDATE ROLE SET holding_penalty = 0.002 WHERE holding_penalty IS NULL;")
        
        conn.commit()
        print("Success: 'holding_penalty' column added to ROLE table and seeded.")
    except sqlite3.OperationalError as e:
        # Failsafe just in case you run it twice
        if "duplicate column name" in str(e).lower():
            print("Notice: Column 'holding_penalty' already exists in ROLE table.")
        else:
            print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_role_table()