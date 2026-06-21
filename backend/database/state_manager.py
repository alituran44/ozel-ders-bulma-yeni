# State Manager for Delta Scraping
# Manages last-scraped timestamps per site to avoid re-scraping old content

import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = "backend/database/leads.db"

class ScrapingStateManager:
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_last_scraped(self, site_key: str) -> str | None:
        """Returns the ISO timestamp of the last successful scrape for a site."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT last_scraped_at FROM scraping_states WHERE site_key = ?", (site_key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def update_state(self, site_key: str, items_found: int = 0, error: str = None):
        """Updates the scraping state for a site after a scrape run."""
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if error:
            cursor.execute("""
                INSERT INTO scraping_states (site_key, last_scraped_at, items_found, status, error_message, updated_at)
                VALUES (?, ?, ?, 'ERROR', ?, ?)
                ON CONFLICT(site_key) DO UPDATE SET
                    last_scraped_at = excluded.last_scraped_at,
                    items_found = excluded.items_found,
                    status = 'ERROR',
                    error_message = excluded.error_message,
                    updated_at = excluded.updated_at
            """, (site_key, now, items_found, error, now))
        else:
            cursor.execute("""
                INSERT INTO scraping_states (site_key, last_scraped_at, items_found, status, updated_at)
                VALUES (?, ?, ?, 'ACTIVE', ?)
                ON CONFLICT(site_key) DO UPDATE SET
                    last_scraped_at = excluded.last_scraped_at,
                    items_found = excluded.items_found,
                    status = 'ACTIVE',
                    error_message = NULL,
                    updated_at = excluded.updated_at
            """, (site_key, now, items_found, now))
        
        conn.commit()
        conn.close()
    
    def get_all_states(self) -> list:
        """Returns all scraping states as a list of dicts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scraping_states ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    def start_scan(self, scan_type: str, platforms: list) -> int:
        """Records a new scan session. Returns the scan ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scan_history (scan_type, platforms_scanned, status)
            VALUES (?, ?, 'RUNNING')
        """, (scan_type, ','.join(platforms)))
        scan_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return scan_id
    
    def end_scan(self, scan_id: int, total_raw: int, total_qualified: int, error: str = None):
        """Marks a scan session as completed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        status = 'ERROR' if error else 'COMPLETED'
        cursor.execute("""
            UPDATE scan_history SET
                completed_at = CURRENT_TIMESTAMP,
                total_raw = ?,
                total_qualified = ?,
                status = ?,
                error_log = ?
            WHERE id = ?
        """, (total_raw, total_qualified, status, error, scan_id))
        conn.commit()
        conn.close()
    
    def get_scan_history(self, limit: int = 20) -> list:
        """Returns recent scan history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scan_history ORDER BY started_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
