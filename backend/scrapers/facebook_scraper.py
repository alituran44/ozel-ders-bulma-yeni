import urllib.request
import urllib.parse
import uuid
import hashlib
import json
import asyncio
import re
import html as html_lib
import time
from datetime import datetime

class FacebookScraper:
    def __init__(self, keywords=None):
        if keywords is None:
            keywords = [
                'site:facebook.com/groups ("özel ders arıyorum" OR "özel ders lazım" OR "hoca arıyorum" OR "öğretmen arıyorum" OR "matematik özel ders" OR "ingilizce özel ders" OR "lgs özel ders" OR "yks özel ders" OR "kpss özel ders" OR "ales özel ders")'
            ]
        self.keywords = keywords
        
        # Specific Facebook group search queries
        self.group_searches = [
            'site:facebook.com/groups ("lgs anneleri" OR "lgs velileri" OR "yks" OR "tyt ayt" OR "kpss" OR "ales" OR "istanbul" OR "ankara") ("özel ders" OR "hoca")'
        ]

    async def scrape(self, max_posts=100):
        """Ultra-comprehensive browserless HTTP scraper for Facebook Groups via DuckDuckGo HTML"""
        leads = []
        seen_hashes = set()
        
        print(f"   📘 Facebook Ultra Scan: {len(self.keywords)} keyword + {len(self.group_searches)} group query")
        
        # Phase 1: Keyword-based search
        for i, kw in enumerate(self.keywords):
            if len(leads) >= max_posts:
                break
            try:
                if "site:" in kw or "OR" in kw:
                    query = kw
                else:
                    query = f'site:facebook.com/groups "{kw}"'
                new_leads = self._fetch_ddg(query, seen_hashes)
                leads.extend(new_leads)
                if new_leads:
                    print(f"      ✓ [{kw[:30]}...] -> {len(new_leads)} yeni sonuç")
                # Rate limiting - wait between requests
                time.sleep(2.5)
            except Exception as e:
                print(f"   ⚠️ FB keyword error ({kw}): {e}")
                time.sleep(3)
                continue
                
        # Phase 2: Direct group queries
        for i, gq in enumerate(self.group_searches):
            if len(leads) >= max_posts:
                break
            try:
                new_leads = self._fetch_ddg(gq, seen_hashes)
                leads.extend(new_leads)
                if new_leads:
                    print(f"      ✓ [group query {i+1}] -> {len(new_leads)} yeni sonuç")
                time.sleep(2.5)
            except Exception as e:
                print(f"   ⚠️ FB group query error: {e}")
                time.sleep(3)
                continue
        
        print(f"   📘 Facebook scan complete: {len(leads)} leads found")
        return leads[:max_posts]

    def _fetch_ddg(self, query, seen_hashes):
        """Fetch results from DuckDuckGo HTML for a single query"""
        results = []
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}&df=m"
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        
        html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8')
        
        # Parse using result blocks
        # DuckDuckGo HTML structure: <div class="result"> with <a class="result__snippet"> and <a class="result__url">
        result_blocks = html.split('<div class="result ')
        
        for block in result_blocks[1:]:
            try:
                # Extract snippet text
                snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
                snippet = ""
                if snippet_match:
                    snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                    snippet = html_lib.unescape(snippet)
                
                # Extract URL
                href = ""
                url_match = re.search(r'class="result__a"[^>]*href="([^"]*)"', block)
                if url_match:
                    raw_href = url_match.group(1)
                    if "uddg=" in raw_href:
                        href = urllib.parse.unquote(raw_href.split("uddg=")[1].split("&")[0])
                    else:
                        href = raw_href

                # Extract title
                title = ""
                title_match = re.search(r'class="result__a"[^>]*>([^<]+)', block)
                if title_match:
                    title = html_lib.unescape(title_match.group(1).strip())
                
                # Must have some content
                content = snippet if snippet else title
                if not content or len(content) < 15:
                    continue
                
                # Prefer Facebook group URLs
                clean_url = href.split('?')[0] if href else ""
                
                text_hash = hashlib.md5(content.encode()).hexdigest()
                if text_hash in seen_hashes:
                    continue
                seen_hashes.add(text_hash)
                
                platform = "Facebook Group" if "facebook.com/groups/" in href else "Facebook"
                
                results.append({
                    "id": str(uuid.uuid4()),
                    "platform": platform,
                    "content": content[:500],
                    "subject": "Özel Ders",
                    "location": "Türkiye Geneli",
                    "original_link": clean_url,
                    "text_hash": text_hash,
                    "is_qualified": 1,
                    "original_date": "Anlık"
                })
            except Exception:
                continue
                
        return results

if __name__ == "__main__":
    scraper = FacebookScraper()
    results = asyncio.run(scraper.scrape(10))
    print(f"Found {len(results)} results")
    print(json.dumps(results, indent=2, ensure_ascii=False))
