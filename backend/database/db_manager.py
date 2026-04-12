import sqlite3
import os

DB_PATH = "backend/database/leads.db"

def init_db():
    # Ensure the directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Read and execute the schema
    with open("backend/database/schema.sql", "r") as f:
        schema = f.read()
        cursor.executescript(schema)
        
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

def save_lead(lead_data):
    """Saves a lead dictionary to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO leads (id, platform, original_date, content, subject, location, contact_info, whatsapp_link, original_link, text_hash, is_qualified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_data.get("id"),
            lead_data.get("platform"),
            lead_data.get("original_date"),
            lead_data.get("content"),
            lead_data.get("subject"),
            lead_data.get("location"),
            lead_data.get("contact_info"),
            lead_data.get("whatsapp_link"),
            lead_data.get("original_link"),
            lead_data.get("text_hash"),
            lead_data.get("is_qualified", 1)
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        # Avoid logging common duplicates
        pass
    finally:
        conn.close()

def get_leads(limit=50):
    """Retrieves qualified leads from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Return as dict-like rows
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM leads WHERE is_qualified = 1 ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    
    conn.close()
    return [dict(row) for row in rows]

if __name__ == "__main__":
    init_db()
