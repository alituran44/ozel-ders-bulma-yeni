import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
sys.stdout.reconfigure(encoding='utf-8')

from scrapers.ozeldersalani_scraper import OzelDersAlaniScraper
from scrapers.forum_scraper import ForumScraper
from database.db_manager import is_old_or_invalid_lead, is_duplicate_lead

async def test_filter():
    print("Testing OzelDersAlani scraper leads...")
    oda = OzelDersAlaniScraper()
    oda_leads = await oda.scrape(5)
    for l in oda_leads:
        content = l.get("content", "")
        url = l.get("original_link", "")
        date_str = l.get("original_date", "")
        is_invalid = is_old_or_invalid_lead(content, url, date_str)
        is_dup = is_duplicate_lead(content)
        print(f"Content snippet: {content[:60]}...")
        print(f"  -> is_old_or_invalid_lead: {is_invalid}")
        print(f"  -> is_duplicate_lead: {is_dup}")
        print("-" * 50)
        
    print("\nTesting ForumScraper leads...")
    forum = ForumScraper()
    forum_leads = await forum.scrape(5)
    for l in forum_leads:
        content = l.get("content", "")
        url = l.get("original_link", "")
        date_str = l.get("original_date", "")
        is_invalid = is_old_or_invalid_lead(content, url, date_str)
        is_dup = is_duplicate_lead(content)
        print(f"Content snippet: {content[:60]}...")
        print(f"  -> URL: {url}")
        print(f"  -> is_old_or_invalid_lead: {is_invalid}")
        print(f"  -> is_duplicate_lead: {is_dup}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_filter())
