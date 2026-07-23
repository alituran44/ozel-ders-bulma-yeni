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

def is_old_or_invalid_lead(content, url="", date_str=""):
    import re
    text = (str(content) + " " + str(url) + " " + str(date_str)).lower()
    
    # 1. Obsolete Exam systems
    obsolete_exams = ["ygs", "lys", "sbs", "teog", "oks", "öss", "öys"]
    for exam in obsolete_exams:
        if re.search(r'\b' + exam + r'\b', text):
            return True
            
    # 2. Outdated Years (any year from 2010 to 2025)
    years = re.findall(r'\b(201\d|202[0-5])\b', text)
    if years:
        if "2026" not in text and "2027" not in text:
            return True

    # 3. Explicit old date formats (e.g. DD.MM.YY or DD.MM.YYYY for 2010-2025, or 2026 before May)
    old_date_pattern = r'\b\d{1,2}[./-]\d{1,2}[./-](?:20)?(?:1\d|2[0-5])\b'
    if re.search(old_date_pattern, text):
        if "2026" not in text and "2027" not in text:
            return True
            
    # Check if text contains a date in 2026 before May (Month < 5)
    # DD.MM.2026 or DD.MM.26
    date_2026_pattern = r'\b(\d{1,2})[./-](\d{1,2})[./-](?:20)?26\b'
    date_matches = re.findall(date_2026_pattern, text)
    for _, month in date_matches:
        if int(month) < 5:
            return True
            
    # YYYY-MM-DD format: 2026-MM-DD
    date_2026_iso = r'\b(?:20)?26[./-](\d{1,2})[./-]\d{1,2}\b'
    iso_matches = re.findall(date_2026_iso, text)
    for month in iso_matches:
        if int(month) < 5:
            return True

    # 4. Turkish/English Month + Old Year (e.g., "Nov 17, 2024", "Eylül 2023")
    months = ("ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık|"
              "january|february|march|april|may|june|july|august|september|october|november|december|"
              "jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec")
    month_year_pattern = r'\b(?:' + months + r')\s*(?:[,\s\d]*)\s*(?:20)?(?:1\d|2[0-5])\b'
    if re.search(month_year_pattern, text):
        if "2026" not in text and "2027" not in text:
            return True
            
    # Reject 2026 months before May
    early_months = "ocak|şubat|mart|nisan|january|february|march|april|jan|feb|mar|apr"
    early_month_pattern = r'\b(?:' + early_months + r')\s*(?:[,\s\d]*)\s*(?:20)?26\b'
    if re.search(early_month_pattern, text):
        return True

    # 5. Outdated Forum Thread IDs (to filter years-old pages indexed by search engines)
    # DonanımHaber: thread ID < 161000000 is 2025/older
    dh_match = re.search(r'--(\d+)', url)
    if dh_match and "donanimhaber.com" in url:
        if int(dh_match.group(1)) < 161000000:
            return True

    # Memurlar.net: konu ID < 2400000 is 2025/older
    mem_match = re.search(r'konu/(\d+)', url)
    if mem_match and "memurlar.net" in url:
        if int(mem_match.group(1)) < 2400000:
            return True

    # R10.net: thread ID < 3000000
    r10_match = re.search(r'/(\d+)-', url)
    if r10_match and "r10.net" in url:
        if int(r10_match.group(1)) < 3000000:
            return True

    # Ekşi Duyuru: ID < 1300000
    eksi_match = re.search(r'duyuru/(\d+)', url)
    if eksi_match and "eksiduyuru.com" in url:
        if int(eksi_match.group(1)) < 1300000:
            return True

    # Technopat: ID < 3100000
    tp_match = re.search(r'konu/[^/]+\.(\d+)/?', url) or re.search(r'\.(\d+)/?$', url)
    if tp_match and "technopat.net" in url:
        if int(tp_match.group(1)) < 3100000:
            return True

    # ShiftDelete: ID < 500000
    sd_match = re.search(r'konular/[^/]+\.(\d+)/?', url)
    if sd_match and "shiftdelete.net" in url:
        if int(sd_match.group(1)) < 500000:
            return True

    # 6. Invalid Sources / Landing Pages / Teacher Ads
    invalid_patterns = [
        "youtube.com/shorts", "tiktok.com/discover", "instagram.com/reel",
        "armut.com", "bionluk.com", "preply.com", "superprof.com.tr",
        "ozeldersimiz.com.tr", "almakistiyorum.net", "matematikozelders.com",
        "ozelders.com", "sahibinden.com/ozel-ders-verenler"
    ]
    for pattern in invalid_patterns:
        if pattern in text:
            return True
            
    # 7. Content length check
    if len(str(content).strip()) < 25:
        return True
        
    return False

def is_duplicate_lead(content, url=""):
    """Checks if the lead content is similar to recently saved leads to avoid duplicates."""
    from difflib import SequenceMatcher
    
    new_content_clean = str(content).strip().lower()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Exact URL check if link exists
        if url:
            cursor.execute("SELECT id FROM leads WHERE original_link = ?", (url,))
            if cursor.fetchone():
                return True
                
        # 2. Fetch recent 50 leads for similarity check
        cursor.execute("SELECT content FROM leads ORDER BY created_at DESC LIMIT 50")
        recent_leads = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching recent leads for deduplication: {e}")
        recent_leads = []
    finally:
        conn.close()
        
    for row in recent_leads:
        old_content_clean = str(row[0]).strip().lower()
        if new_content_clean == old_content_clean:
            return True
            
        # Calculate similarity ratio (threshold set to 0.95 for template-heavy sites)
        ratio = SequenceMatcher(None, new_content_clean, old_content_clean).ratio()
        if ratio > 0.95:
            return True
            
    return False

def save_lead(lead_data):
    """Saves a lead dictionary to the database."""
    content = lead_data.get("content", "")
    url = lead_data.get("original_link", "")
    date_str = lead_data.get("original_date", "")
    
    if is_old_or_invalid_lead(content, url, date_str):
        # Skip saving outdated or invalid leads
        return
        
    if is_duplicate_lead(content, url):
        # Skip duplicate leads
        print(f"   ℹ️ Yinelenen (Duplicate) ilan elendi (Benzerlik > 95%)")
        return
        
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
        
        # Trigger Telegram notification for new unique leads
        try:
            from core.notifications import send_telegram_notification
            send_telegram_notification(lead_data)
        except Exception as e:
            print(f"Failed to trigger Telegram notification: {e}")
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
