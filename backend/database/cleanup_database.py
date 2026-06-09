import sys
import sqlite3
import os

# Add parent directory of database directory (i.e. 'backend') to system path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from database.db_manager import is_old_or_invalid_lead, DB_PATH

def cleanup():
    print(f"Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, platform, original_link, original_date, content FROM leads")
    rows = cursor.fetchall()
    
    total_checked = len(rows)
    deleted_count = 0
    
    print(f"Checking {total_checked} leads for outdated or invalid content...")
    print("=" * 80)
    
    for row in rows:
        lead_id = row['id']
        platform = row['platform']
        url = row['original_link'] or ""
        date_str = row['original_date'] or ""
        content = row['content']
        
        if is_old_or_invalid_lead(content, url, date_str):
            print(f"❌ DELETING (Old/Invalid): [{platform}] {content[:60]}... (Link: {url[:40]})")
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted_count += 1
        else:
            print(f"✅ KEEPING (Valid): [{platform}] {content[:60]}...")
            
    conn.commit()
    conn.close()
    
    print("=" * 80)
    print(f"Cleanup finished. Checked: {total_checked}, Deleted: {deleted_count}, Remaining: {total_checked - deleted_count}")

if __name__ == "__main__":
    cleanup()
