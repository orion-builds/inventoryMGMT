import sqlite3

def get_full_schema():
    # Connect to your existing test database [cite: 2025-12-06]
    db_name = "inventory.db"
    try:
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Fetch all table names [cite: 2025-12-06]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = cursor.fetchall()

        print(f"--- FULL SCHEMA FOR: {db_name} ---")

        for table in tables:
            table_name = table['name']
            print(f"\nTABLE: {table_name}")
            print("-" * 30)
            
            # 2. Use PRAGMA to get column details [cite: 2026-03-05]
            # Column info returns: (id, name, type, notnull, default_value, pk)
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            for col in columns:
                pk_star = " [PK]" if col['pk'] == 1 else ""
                not_null = " NOT NULL" if col['notnull'] == 1 else ""
                print(f"  - {col['name']} ({col['type']}){not_null}{pk_star}")
        
        conn.close()
    except sqlite3.Error as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    get_full_schema()