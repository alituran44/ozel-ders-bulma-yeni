import asyncio
import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding='utf-8')

from database.state_manager import ScrapingStateManager
from scrapers.ozeldersalani_scraper import OzelDersAlaniScraper
from scrapers.forum_scraper import ForumScraper
from scrapers.sahibinden_scraper import SahibindenScraper
from scrapers.twitter_scraper import TwitterScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.instagram_scraper import InstagramScraper
from scrapers.linkedin_scraper import LinkedInScraper

class ScraperHealthChecker:
    def __init__(self):
        self.state_manager = ScrapingStateManager()

    async def run_checks(self):
        print("🔍 Tarayıcı Sağlık Kontrolü Başlatıldı...\n" + "="*50)
        
        # List of scrapers to test: (site_key, instance, name)
        scrapers_to_test = [
            ("ozeldersalani", OzelDersAlaniScraper(), "Özel Ders Alanı"),
            ("donanimhaber", ForumScraper(), "DonanımHaber Forum"),
            ("sahibinden", SahibindenScraper(), "Sahibinden"),
            ("x_twitter", TwitterScraper(keywords=["özel ders"]), "X (Twitter)"),
            ("facebook_group", FacebookScraper(keywords=["özel ders"]), "Facebook Group"),
            ("instagram", InstagramScraper(keywords=["özel ders"]), "Instagram"),
            ("linkedin", LinkedInScraper(keywords=["özel ders"]), "LinkedIn")
        ]
        
        results = {}
        
        for site_key, scraper, name in scrapers_to_test:
            print(f"📡 Testing Scraper: {name} ({site_key})...")
            try:
                # Perform a minimal scrape test
                leads = await scraper.scrape(max_posts=2)
                count = len(leads) if leads else 0
                
                # Treat 0 leads on critical direct scrapers as a failure (timeout or block)
                if count == 0 and site_key in ["ozeldersalani", "donanimhaber"]:
                    raise ValueError("Scraper returned 0 leads. Platform is likely blocked, offline, or CSS selectors changed.")
                
                print(f"   ✅ Test Successful. Leads found: {count}")
                self.state_manager.update_state(site_key, items_found=count)
                results[site_key] = {"status": "ACTIVE", "leads": count, "error": None}
                
            except Exception as e:
                err_msg = str(e)
                tb = traceback.format_exc()
                print(f"   ❌ Test Failed: {err_msg}")
                self.state_manager.update_state(site_key, error=err_msg)
                results[site_key] = {"status": "ERROR", "leads": 0, "error": err_msg}
                
            print("-" * 50)
            
        print("\n📊 Sağlık Kontrolü Raporu:")
        for key, res in results.items():
            print(f" - {key}: {res['status']} (Leads: {res['leads']}) {f'Error: {res['error']}' if res['error'] else ''}")
            
        return results

if __name__ == "__main__":
    checker = ScraperHealthChecker()
    asyncio.run(checker.run_checks())
