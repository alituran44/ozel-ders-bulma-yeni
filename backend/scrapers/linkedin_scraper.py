import asyncio
import os
import json
import uuid
import hashlib
import re
import urllib.parse
import urllib.request
import html as html_lib
from datetime import datetime

class LinkedInScraper:
    def __init__(self, keywords=None):
        if keywords is None:
            keywords = [
                "özel ders arıyorum",
                "özel ders lazım",
                "matematik öğretmen arıyoruz",
                "ingilizce hoca arıyorum",
                "lgs ders hoca"
            ]
        self.keywords = keywords
        self.cookie_path = "backend/auth/linkedin_cookies.json"

    def load_cookies(self):
        """Load and sanitize LinkedIn session cookies from file if exists"""
        if os.path.exists(self.cookie_path):
            try:
                with open(self.cookie_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    sanitized = []
                    for c in cookies:
                        if "BURAYA_" in str(c.get("value", "")):
                            continue
                        
                        # Playwright expects sameSite as 'Strict', 'Lax', or 'None'
                        ss = c.get("sameSite", "None")
                        if ss.lower() in ["no_restriction", "unspecified"]:
                            c["sameSite"] = "None"
                        elif ss[0].upper() + ss[1:].lower() in ["Strict", "Lax", "None"]:
                            c["sameSite"] = ss[0].upper() + ss[1:].lower()
                        else:
                            c["sameSite"] = "None"
                        
                        # Remove fields Playwright doesn't want
                        for key in ["hostOnly", "session", "storeId", "expirationDate"]:
                            if key in c:
                                if key == "expirationDate":
                                    c["expires"] = c.pop(key)
                                else:
                                    c.pop(key)
                        sanitized.append(c)
                    return sanitized
            except Exception as e:
                print(f"⚠️ LinkedIn cookie sanitizing error: {e}")
        return None

    async def scrape(self, max_posts=25):
        """Scrapes LinkedIn tutoring requests. Authenticated Playwright (Primary) or DDG Fallback (Secondary)."""
        cookies = self.load_cookies()
        if cookies:
            return await self._scrape_authenticated(cookies, max_posts)
        else:
            return await self._scrape_public_fallback(max_posts)

    async def _scrape_authenticated(self, cookies, max_posts):
        print(f"   💼 LinkedIn Authenticated Scan: {len(self.keywords)} keywords")
        leads = []
        seen_hashes = set()
        
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="tr-TR"
            )
            await context.add_cookies(cookies)
            page = await context.new_page()
            
            for kw in self.keywords:
                if len(leads) >= max_posts:
                    break
                try:
                    encoded_query = urllib.parse.quote(kw)
                    # LinkedIn post search URL
                    url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_query}&origin=GLOBAL_SEARCH_HEADER"
                    
                    await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    await asyncio.sleep(4) # Let results load
                    
                    # Scroll to trigger lazy loading
                    await page.mouse.wheel(0, 800)
                    await asyncio.sleep(2)
                    
                    # Common selectors for search results / posts
                    posts = await page.query_selector_all("li.reusable-search__result-container, div.search-content__result, div.update-outlet, div[role='article']")
                    for post in posts:
                        if len(leads) >= max_posts:
                            break
                        try:
                            # Extract text
                            text = await post.inner_text()
                            if len(text) < 30:
                                continue
                            
                            # Clean text
                            clean_text = re.sub(r'\s+', ' ', text).strip()
                            
                            # Find links in the post
                            link_el = await post.query_selector("a.app-aware-link")
                            href = await link_el.get_attribute("href") if link_el else ""
                            if href and "?" in href:
                                href = href.split("?")[0]
                                
                            if not href.startswith("http"):
                                href = "https://www.linkedin.com" + href
                                
                            text_hash = hashlib.md5(clean_text.encode()).hexdigest()
                            if text_hash in seen_hashes:
                                continue
                            seen_hashes.add(text_hash)
                            
                            leads.append({
                                "id": str(uuid.uuid4()),
                                "platform": "LinkedIn",
                                "content": clean_text[:450],
                                "subject": "Özel Ders",
                                "location": "Türkiye",
                                "original_link": href or "https://www.linkedin.com/feed/",
                                "text_hash": text_hash,
                                "is_qualified": 1,
                                "original_date": "Anlık"
                            })
                        except Exception:
                            continue
                except Exception as e:
                    print(f"      ⚠️ LinkedIn Auth scan error for keyword '{kw}': {e}")
                    
            await browser.close()
        return leads

    async def _scrape_public_fallback(self, max_posts):
        print(f"   💼 LinkedIn Public Scan (Fallback): {len(self.keywords)} keywords")
        leads = []
        seen_hashes = set()
        
        for kw in self.keywords:
            if len(leads) >= max_posts:
                break
            try:
                # Target posts on LinkedIn indexable by search engines
                query = f'site:linkedin.com/posts/ "{kw}"'
                encoded_query = urllib.parse.quote(query)
                url = f"https://html.duckduckgo.com/html/?q={encoded_query}&df=m"
                
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                })
                
                html = urllib.request.urlopen(req, timeout=12).read().decode('utf-8')
                parts = html.split('class="result__snippet"')
                for part in parts[1:]:
                    if len(leads) >= max_posts:
                        break
                    try:
                        raw_text = part.split('>')[1].split('</')[0] if '>' in part else ''
                        clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()
                        clean_text = html_lib.unescape(clean_text)
                        
                        if len(clean_text) < 20:
                            continue
                            
                        text_hash = hashlib.md5(clean_text.encode()).hexdigest()
                        if text_hash in seen_hashes:
                            continue
                        seen_hashes.add(text_hash)
                        
                        # Find link
                        link = ""
                        href_match = re.search(r'href="([^"]*linkedin\.com/posts/[^"]*)"', part)
                        if href_match:
                            raw_href = href_match.group(1)
                            if "uddg=" in raw_href:
                                link = urllib.parse.unquote(raw_href.split("uddg=")[1].split("&")[0])
                            else:
                                link = raw_href
                                
                        leads.append({
                            "id": str(uuid.uuid4()),
                            "platform": "LinkedIn",
                            "content": clean_text[:400],
                            "subject": "Özel Ders",
                            "location": "Türkiye",
                            "original_link": link.split('?')[0] if link else "https://www.linkedin.com/",
                            "text_hash": text_hash,
                            "is_qualified": 1,
                            "original_date": "Bugün"
                        })
                    except Exception:
                        continue
            except Exception as e:
                print(f"      ⚠️ LinkedIn public scan error for keyword '{kw}': {e}")
                
        return leads

if __name__ == "__main__":
    scraper = LinkedInScraper()
    results = asyncio.run(scraper.scrape(5))
    print(f"Scraped {len(results)} items from LinkedIn.")
