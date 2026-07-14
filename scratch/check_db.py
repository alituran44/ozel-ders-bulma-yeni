import sqlite3
import json

DB_PATH = "backend/database/leads.db"

def check_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=== SCRAPING STATES ===")
    cursor.execute("SELECT * FROM scraping_states ORDER BY updated_at DESC")
    for r in cursor.fetchall():
        print(dict(r))
        
    print("\n=== RECENT SCAN HISTORY ===")
    cursor.execute("SELECT * FROM scan_history ORDER BY started_at DESC LIMIT 5")
    for r in cursor.fetchall():
        print(dict(r))
        
    conn.close()

if __name__ == "__main__":
    check_db()
