import re
from datetime import datetime, timedelta, timezone

# Turkish month mappings
MONTH_MAP = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
    "oca": 1, "şub": 2, "mar": 3, "nis": 4, "may": 5, "haz": 6,
    "tem": 7, "ağu": 8, "eyl": 9, "eki": 10, "kas": 11, "ara": 12
}

def parse_turkish_date(date_str: str) -> str:
    """
    Standardizes a Turkish date string into ISO 8601 UTC format (YYYY-MM-DDTHH:MM:SSZ).
    Handles relative times ('3 saat önce', '10 dk önce'), absolute times ('Bugün 14:30', 'Dün'),
    and standard date formats ('20.06.2026', '20 Haz 2026').
    """
    if not date_str:
        return datetime.now(timezone.utc).isoformat() + "Z"
        
    now = datetime.now(timezone.utc)
    date_clean = date_str.strip().lower()
    
    # 1. Handle relative minutes: "15 dakika önce" / "15 dk önce"
    min_match = re.search(r'(\d+)\s*(?:dakika|dk)\s*önce', date_clean)
    if min_match:
        minutes = int(min_match.group(1))
        target_time = now - timedelta(minutes=minutes)
        return target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
    # 2. Handle relative hours: "3 saat önce"
    hour_match = re.search(r'(\d+)\s*saat\s*önce', date_clean)
    if hour_match:
        hours = int(hour_match.group(1))
        target_time = now - timedelta(hours=hours)
        return target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
    # 3. Handle relative days: "3 gün önce"
    day_match = re.search(r'(\d+)\s*gün\s*önce', date_clean)
    if day_match:
        days = int(day_match.group(1))
        target_time = now - timedelta(days=days)
        return target_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 4. Handle "Bugün" (Today) with optional time: "Bugün 14:20"
    if "bugün" in date_clean:
        time_match = re.search(r'(\d{2}):(\d{2})', date_clean)
        if time_match:
            hh, mm = map(int, time_match.groups())
            target_time = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            return target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 5. Handle "Dün" (Yesterday) with optional time: "Dün 23:10"
    if "dün" in date_clean:
        yesterday = now - timedelta(days=1)
        time_match = re.search(r'(\d{2}):(\d{2})', date_clean)
        if time_match:
            hh, mm = map(int, time_match.groups())
            target_time = yesterday.replace(hour=hh, minute=mm, second=0, microsecond=0)
            return target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return yesterday.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 6. Handle standard numeric formats: DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY (or YY)
    num_match = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})', date_clean)
    if num_match:
        day, month, year_str = num_match.groups()
        day = int(day)
        month = int(month)
        year = int(year_str)
        if year < 100:
            year += 2000 # convert 26 to 2026
        
        # Check for optional time
        time_match = re.search(r'(\d{2}):(\d{2})', date_clean)
        hh, mm = (12, 0) # default noon
        if time_match:
            hh, mm = map(int, time_match.groups())
            
        try:
            target_time = datetime(year, month, day, hh, mm, tzinfo=timezone.utc)
            return target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    # 7. Handle text month formats: "20 haziran 2026", "5 mayıs 26", "12 eyl 2026 14:30"
    for m_name, m_val in MONTH_MAP.items():
        if m_name in date_clean:
            # Match pattern: Day Month Year (optionally Time)
            pattern = rf'(\d{{1,2}})\s+{m_name}\s*(\d{{2,4}})?'
            match = re.search(pattern, date_clean)
            if match:
                day = int(match.group(1))
                year_val = match.group(2)
                year = int(year_val) if year_val else now.year
                if year < 100:
                    year += 2000
                
                # Check for time
                time_match = re.search(r'(\d{2}):(\d{2})', date_clean)
                hh, mm = (12, 0)
                if time_match:
                    hh, mm = map(int, time_match.groups())
                
                try:
                    target_time = datetime(year, m_val, day, hh, mm, tzinfo=timezone.utc)
                    return target_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    pass

    # Fallback to now if no match
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")

if __name__ == "__main__":
    # Test cases
    tests = [
        "3 saat önce",
        "15 dk önce",
        "Bugün 14:20",
        "Dün 23:10",
        "20.06.2026",
        "20 Haz 2026 18:45",
        "5 mayıs 2026"
    ]
    print("Testing date parser:")
    for t in tests:
        print(f"'{t}' -> '{parse_turkish_date(t)}'")
