import asyncio
import os
import json
import uuid
import hashlib
import re
import urllib.parse
from playwright.async_api import async_playwright
from core.date_parser import parse_turkish_date
from core.classifier import LeadClassifier

class GenericScraper:
    def __init__(self, site_name):
        self.site_name = site_name
        self.config = self._load_config(site_name)
        self.classifier = LeadClassifier()

    def _load_config(self, name):
        config_path = os.path.join(os.path.dirname(__file__), "site_configs.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for site in data.get("sites", []):
                    if site["name"].lower() == name.lower() or site["platform_key"].lower() == name.lower():
                        return site
        raise ValueError(f"Configuration for site '{name}' not found in site_configs.json.")

    async def scrape(self, max_posts=20, last_scraped_iso=None):
        """Scrapes listings based on JSON configuration and filters out older dates (delta scraping)."""
        if not self.config:
            print(f"⚠️ No configuration loaded for {self.site_name}.")
            return []

        leads = []
        url = self.config["base_url"]
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="tr-TR"
            )
            page = await context.new_page()
            
            try:
                print(f"📡 Config-driven scrape starting for: {self.config['name']} ({url})")
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)
                
                # Retrieve the row containers
                rows = await page.query_selector_all(self.config["list_selector"])
                print(f"   Found {len(rows)} matching containers.")
                
                for row in rows[:max_posts]:
                    try:
                        # Extract title & link
                        title_el = await row.query_selector(self.config["title_selector"])
                        if not title_el:
                            continue
                            
                        title = await title_el.inner_text()
                        href = await title_el.get_attribute("href") or ""
                        if href and not href.startswith("http"):
                            # Resolve relative URL
                            parsed_base = urllib.parse.urlparse(url)
                            href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"

                        # Extract author if selector present
                        author = "Anonim"
                        if self.config.get("author_selector"):
                            author_el = await row.query_selector(self.config["author_selector"])
                            if author_el:
                                author = await author_el.inner_text()

                        # Extract date
                        date_raw = "Bugün"
                        if self.config.get("date_selector"):
                            date_el = await row.query_selector(self.config["date_selector"])
                            if date_el:
                                date_raw = await date_el.inner_text()
                                
                        # Standardize date using the date-parser
                        date_iso = parse_turkish_date(date_raw)
                        
                        # Delta Scraping: If date_iso is older than last_scraped_iso, skip/break
                        if last_scraped_iso and date_iso < last_scraped_iso:
                            print(f"   Delta check: skipping older item (date: {date_iso})")
                            continue

                        # Build lead entry
                        clean_content = f"{title} (Yazar: {author})" if author != "Anonim" else title
                        text_hash = hashlib.md5(clean_content.encode()).hexdigest()
                        
                        leads.append({
                            "id": str(uuid.uuid4()),
                            "platform": self.config["platform_key"],
                            "content": clean_content,
                            "subject": self.config["default_subject"],
                            "location": self.config["default_location"],
                            "original_link": href,
                            "original_date": date_raw,
                            "date_iso": date_iso,
                            "text_hash": text_hash,
                            "is_qualified": 1
                        })
                    except Exception as row_err:
                        print(f"      Row processing error: {row_err}")
                        continue
                        
            except Exception as e:
                print(f"   ❌ Error scraping {self.config['name']}: {e}")
            finally:
                await browser.close()
                
        return leads

if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    async def test():
        # Scrape DonanımHaber Forum as a test
        scraper = GenericScraper("DonanımHaber Forum")
        results = await scraper.scrape(5)
        print(f"\nScraped results:\n{json.dumps(results[:2], indent=2, ensure_ascii=False)}")
        
    asyncio.run(test())
