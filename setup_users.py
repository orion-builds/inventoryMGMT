import sqlite3
from auth_utils import get_password_hash

def create_user_db():
    # This creates a separate master database just for login info [cite: 2026-03-05]
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Create the user table [cite: 2026-03-05]
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            hashed_password TEXT
        )
    """)

    # --- ADD YOUR FAMILY MEMBERS HERE ---
    # format: (user_id, username, plain_text_password)
    family_members = [
        ("user_01", "Orion", "password1"),
        ("user_02", "Papa", "password2")
    ]

    for uid, name, pwd in family_members:
        # Use auth_utils to scramble the password before saving [cite: 2026-03-05]
        h_pwd = get_password_hash(pwd)
        try:
            cursor.execute(
                "INSERT INTO users (user_id, username, hashed_password) VALUES (?, ?, ?)",
                (uid, name, h_pwd)
            )
            print(f"✅ Created account for: {name}")
        except sqlite3.IntegrityError:
            print(f"⚠️  User {name} already exists. Skipping.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_user_db()