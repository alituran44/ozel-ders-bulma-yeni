import asyncio
from playwright.async_api import async_playwright
import json
import uuid
import hashlib

class SahibindenScraper:
    def __init__(self, base_url="https://www.sahibinden.com/ozel-ders-arayanlar"):
        self.base_url = base_url

    async def scrape(self, max_posts=10):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Sahibinden is very strict. We use some evasive measures.
                await page.goto(self.base_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                leads = []
                # Sahibinden rows are usually in a table or list
                rows = await page.query_selector_all(".searchResultsItem")
                
                for row in rows[:max_posts]:
                    try:
                        title_elem = await row.query_selector(".searchResultsTitleValue a")
                        if not title_elem: continue
                        
                        title = await title_elem.inner_text()
                        link = await title_elem.get_attribute("href")
                        if not link.startswith("http"):
                            link = "https://www.sahibinden.com" + link
                            
                        # Extract location
                        loc_elem = await row.query_selector(".searchResultsLocationValue")
                        location = await loc_elem.inner_text() if loc_elem else "Belirtilmemiş"
                        
                        content = title.strip()
                        text_hash = hashlib.md5(content.encode()).hexdigest()
                        
                        leads.append({
                            "id": str(uuid.uuid4()),
                            "platform": "Sahibinden",
                            "content": content,
                            "subject": "Özel Ders",
                            "location": location.strip().replace("\n", " "),
                            "original_link": link,
                            "text_hash": text_hash,
                            "is_qualified": 1,
                            "original_date": "Güncel"
                        })
                    except Exception:
                        continue
                        
                return leads
            except Exception as e:
                print(f"Sahibinden Scraper Error: {e}")
                return []
            finally:
                await browser.close()

if __name__ == "__main__":
    scraper = SahibindenScraper()
    results = asyncio.run(scraper.scrape(5))
    print(json.dumps(results, indent=2, ensure_ascii=False))
