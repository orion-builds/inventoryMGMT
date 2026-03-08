import sqlite3

def check_and_migrate():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()
    
    # 1. Let's see what columns ACTUALLY exist right now
    cursor.execute("PRAGMA table_info(ROLE)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"Current columns in 'ROLE': {columns}")
    
    # 2. Try to add the column and print the EXACT error if it fails
    if "learned_h" not in columns:
        try:
            cursor.execute("ALTER TABLE ROLE ADD COLUMN learned_h REAL DEFAULT NULL")
            conn.commit()
            print("Migration successful: added learned_h")
        except Exception as e:
            print(f"FAILED to add column. The exact database error is: {e}")
    else:
        print("Confirmed: learned_h is already in the database!")
        
    conn.close()

check_and_migrate()