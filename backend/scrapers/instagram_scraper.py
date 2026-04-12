import asyncio
import urllib.request
import urllib.parse
import json
import uuid
import hashlib
import re
import html as html_lib
import time
from datetime import datetime

class InstagramScraper:
    def __init__(self, keywords=None):
        if keywords is None:
            keywords = [
                "özel ders arıyorum",
                "matematik özel ders arıyorum",
                "ingilizce özel ders arıyorum",
                "fizik özel ders arıyorum",
                "kimya özel ders arıyorum",
                "biyoloji özel ders arıyorum",
                "türkçe özel ders arıyorum",
                "lgs özel ders",
                "yks özel ders",
                "özel ders lazım",
                "hoca arıyorum",
                "öğretmen arıyorum",
                "çocuğuma özel ders",
                "piyano özel ders",
                "gitar özel ders",
                "programlama özel ders",
            ]
        self.keywords = keywords

    async def scrape(self, max_posts=50):
        """Uses DuckDuckGo HTML to find recent public Instagram posts without login or Playwright."""
        leads = []
        seen_hashes = set()
        
        print(f"   📸 Instagram Ultra Scan: {len(self.keywords)} keywords")
        
        for kw in self.keywords:
            if len(leads) >= max_posts:
                break
            try:
                query = f'site:instagram.com/p/ "{kw}"'
                encoded_query = urllib.parse.quote(query)
                url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
                })
                
                html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
                
                # Parse snippets
                parts = html.split('class="result__snippet"')
                for part in parts[1:]:
                    if len(leads) >= max_posts:
                        break
                    try:
                        raw_text = part.split('>')[1].split('</')[0] if '>' in part else ''
                        clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()
                        clean_text = html_lib.unescape(clean_text)
                        
                        if len(clean_text) < 15:
                            continue
                        
                        text_hash = hashlib.md5(clean_text.encode()).hexdigest()
                        if text_hash in seen_hashes:
                            continue
                        seen_hashes.add(text_hash)
                        
                        # Try to find IG URL
                        ig_url = ""
                        href_match = re.search(r'href="([^"]*instagram\.com/p/[^"]*)"', part)
                        if href_match:
                            raw_href = href_match.group(1)
                            if "uddg=" in raw_href:
                                ig_url = urllib.parse.unquote(raw_href.split("uddg=")[1].split("&")[0])
                            else:
                                ig_url = raw_href
                        
                        leads.append({
                            "id": str(uuid.uuid4()),
                            "platform": "Instagram",
                            "content": clean_text[:400],
                            "subject": "Özel Ders",
                            "location": "Türkiye",
                            "original_link": ig_url.split('?')[0] if ig_url else "",
                            "text_hash": text_hash,
                            "is_qualified": 1,
                            "original_date": "Anlık"
                        })
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f"   ⚠️ IG error ({kw}): {e}")
                time.sleep(3)
                continue
            
            # Rate limiting
            time.sleep(2.5)
        
        print(f"   📸 Instagram scan complete: {len(leads)} leads found")
        return leads

if __name__ == "__main__":
    scraper = InstagramScraper()
    results = asyncio.run(scraper.scrape(5))
    print(f"Found {len(results)} results")
    print(json.dumps(results, indent=2, ensure_ascii=False))
