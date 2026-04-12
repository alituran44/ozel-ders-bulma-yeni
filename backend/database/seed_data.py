import sqlite3
import uuid
import hashlib
import os

DB_PATH = 'backend/database/leads.db'
SCHEMA_PATH = 'backend/database/schema.sql'

def seed():
    # Remove old DB for a clean start
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Old database removed.")

    # Create new DB and apply schema
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, 'r') as f:
        cursor.executescript(f.read())
    
    # Recreate the Database completely ORGANIC. No fake data!
    print(f"Sucessfully generated empty organic database at {DB_PATH}")

if __name__ == "__main__":
    seed()
