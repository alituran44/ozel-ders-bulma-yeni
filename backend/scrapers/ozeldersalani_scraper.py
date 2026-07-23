import asyncio
import sys
from playwright.async_api import async_playwright
import json
import uuid
import hashlib

sys.stdout.reconfigure(encoding='utf-8')

class OzelDersAlaniScraper:
    def __init__(self, base_url="https://www.ozeldersalani.com/ders-almak-isteyenler"):
        self.base_url = base_url

    async def scrape(self, max_posts=20):
        """Scrapes tutoring requests from ozeldersalani.com/ders-almak-isteyenler"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="tr-TR"
            )
            page = await context.new_page()
            
            try:
                print(f"   📡 Özel Ders Alanı taranıyor: {self.base_url}")
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(1000)
                
                leads = []
                cards = await page.query_selector_all(".dlistbox")
                
                for card in cards[:max_posts]:
                    try:
                        # Extract Branch
                        branch_el = await card.query_selector(".dlistbrans")
                        subject = await branch_el.inner_text() if branch_el else "Özel Ders"
                        subject = subject.strip()
                        
                        # Extract Name and Date
                        name_el = await card.query_selector(".dlistname")
                        name_date_text = await name_el.inner_text() if name_el else ""
                        name_date_parts = [p.strip() for p in name_date_text.split("\n") if p.strip()]
                        
                        author = "Anonim"
                        original_date = "Güncel"
                        if name_date_parts:
                            author_part = name_date_parts[0]
                            # Clean author name
                            author = author_part
                            if "saat" in author_part or "gün" in author_part or "dakika" in author_part:
                                words = author_part.split()
                                if len(words) >= 3:
                                    author = " ".join(words[:2])
                                    original_date = " ".join(words[2:])
                                else:
                                    original_date = author_part
                        
                        # Extract Location
                        location_el = await card.query_selector(".dlistw")
                        location_text = await location_el.inner_text() if location_el else "Belirtilmemiş"
                        location = location_text.split("-")[0].strip() if "-" in location_text else location_text.strip()
                        
                        # Extract Content / Note
                        text_el = await card.query_selector(".dlisttext")
                        content = await text_el.inner_text() if text_el else ""
                        content = content.strip()
                        
                        # Skip empty content
                        if not content or len(content) < 20:
                            continue
                            
                        text_hash = hashlib.md5(content.encode()).hexdigest()
                        
                        leads.append({
                            "id": str(uuid.uuid4()),
                            "platform": "Özel Ders Alanı",
                            "content": content,
                            "subject": subject,
                            "location": location,
                            "original_link": f"{self.base_url}#{text_hash[:10]}",
                            "original_date": original_date,
                            "text_hash": text_hash,
                            "is_qualified": 1
                        })
                    except Exception as e:
                        print(f"      Card parsing warning: {e}")
                        continue
                        
                return leads
            except Exception as e:
                print(f"   ❌ Özel Ders Alanı Scraper Error: {e}")
                return []
            finally:
                await browser.close()

if __name__ == "__main__":
    scraper = OzelDersAlaniScraper()
    results = asyncio.run(scraper.scrape(5))
    print(json.dumps(results, indent=2, ensure_ascii=False))
