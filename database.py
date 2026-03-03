import sqlite3

conn = sqlite3.connect("inventory.db") # connect to DB
cursor = conn.cursor() # cursor to do SQL queriess

cursor.execute("PRAGMA foreign_keys = ON;") # enforce FKs in SQLite
# RESTRICT by default in SQLite.

# 3. Use executescript() to run multiple SQL commands in our strict dependency order
cursor.executescript("""
    -- 1. Create CATEGORY
    CREATE TABLE IF NOT EXISTS CATEGORY (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );

    -- 2. Create PRODUCT
    CREATE TABLE IF NOT EXISTS PRODUCT (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand TEXT NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        unit_of_measure TEXT NOT NULL
    );

    -- 3. Create ROLE
    CREATE TABLE IF NOT EXISTS ROLE (
        role_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        target_buffer_days INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES CATEGORY(category_id)
    );

    -- 4. Create ROLE_HISTORY (Composite Primary Key)
    CREATE TABLE IF NOT EXISTS ROLE_HISTORY (
        role_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        start_date DATETIME NOT NULL,
        end_date DATETIME,
        PRIMARY KEY (role_id, product_id, start_date),
        FOREIGN KEY (role_id) REFERENCES ROLE(role_id),
        FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id)
    );

    -- 5. Create INVENTORY_EVENT (Composite Primary Key)
    CREATE TABLE IF NOT EXISTS INVENTORY_EVENT (
        product_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        event_date DATETIME NOT NULL,
        cost_sgd REAL,
        quantity INTEGER NOT NULL,
        PRIMARY KEY (product_id, event_type, event_date),
        FOREIGN KEY (product_id) REFERENCES PRODUCT(product_id)
    );
    -- 1. Global Settings Table
    CREATE TABLE IF NOT EXISTS SETTINGS (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    INSERT OR IGNORE INTO SETTINGS (key, value) VALUES ('global_ema_alpha', '0.3');

    -- 2. Add override columns to existing tables
    ALTER TABLE CATEGORY ADD COLUMN ema_alpha REAL;
    ALTER TABLE ROLE ADD COLUMN ema_alpha REAL;
""")



# 4. Save and close
conn.commit()
conn.close()

print("Full relational schema successfully initialized!")