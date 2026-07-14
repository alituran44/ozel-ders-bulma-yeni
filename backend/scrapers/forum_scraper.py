import asyncio
from playwright.async_api import async_playwright
import json
import uuid
import hashlib

class ForumScraper:
    def __init__(self, base_url="https://forum.donanimhaber.com/tyt-ayt-ydt--f615"):
        self.base_url = base_url

    async def scrape(self, max_posts=25):
        async with async_playwright() as p:
            # Using a user agent to avoid common blocks
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(self.base_url, wait_until="domcontentloaded", timeout=15000)
                # Wait for thread list - verified row selector
                await page.wait_for_selector(".kl-icerik-satir", timeout=8000)
                
                leads = []
                # Verified selector for the thread row in the new DH layout
                rows = await page.query_selector_all(".kl-icerik-satir")
                
                for row in rows[:max_posts]:
                    try:
                        # Verified selector for title and link
                        title_elem = await row.query_selector(".kl-konu a")
                        if title_elem:
                            title = await title_elem.inner_text()
                            link = await title_elem.get_attribute("href")
                            if not link.startswith("http"):
                                link = "https://forum.donanimhaber.com" + link
                            
                            # Grab author for more 'real' feel
                            author_elem = await row.query_selector(".kl-uye-ad")
                            author = await author_elem.inner_text() if author_elem else "Anonim"
                            
                            leads.append({
                                "id": str(uuid.uuid4()),
                                "platform": "DonanımHaber",
                                "content": f"{title} (Yazar: {author})",
                                "subject": "Özel Ders / Koçluk",
                                "location": "Türkiye Geneli / Online",
                                "original_link": link,
                                "original_date": "Bugün",
                                "text_hash": hashlib.md5(title.encode()).hexdigest(),
                                "is_qualified": 1
                            })
                    except Exception: continue
                        
                return leads
            except Exception as e:
                print(f"Forum Scraper Error: {e}")
                return []
            finally:
                await browser.close()

if __name__ == "__main__":
    scraper = ForumScraper()
    results = asyncio.run(scraper.scrape(5))
    print(json.dumps(results, indent=2, ensure_ascii=False))
