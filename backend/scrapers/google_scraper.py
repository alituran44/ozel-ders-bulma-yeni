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

class GoogleScraper:
    """DuckDuckGo-based web scraper that searches the entire internet for tutoring leads."""
    
    def __init__(self, keywords=None):
        if keywords is None:
            keywords = [
                # === GENEL ===
                "özel ders arıyorum",
                "özel ders lazım",
                "hoca arıyorum acil",
                "çocuğuma özel ders lazım",
                "özel ders talebi",
                
                # === MATEMATİK ===
                "matematik özel ders arıyorum",
                "matematik hoca lazım",
                "geometri özel ders arıyorum",
                "matematik koçu arıyorum",
                
                # === FEN / FİZİK / KİMYA / BİYOLOJİ ===
                "fizik özel ders arıyorum",
                "kimya özel ders arıyorum",
                "biyoloji özel ders arıyorum",
                "fen bilimleri özel ders",
                
                # === İNGİLİZCE / DİL ===
                "ingilizce özel ders arıyorum",
                "ingilizce hoca lazım",
                "almanca özel ders arıyorum",
                
                # === TÜRKÇE / EDEBİYAT ===
                "türkçe özel ders arıyorum",
                "edebiyat özel ders",
                
                # === TARİH / COĞRAFYA ===
                "tarih özel ders arıyorum",
                "coğrafya özel ders arıyorum",
                
                # === LGS ===
                "lgs özel ders arıyorum",
                "lgs hazırlık hoca arıyorum",
                "8 sınıf özel ders lazım",
                
                # === YKS / TYT / AYT ===
                "yks özel ders arıyorum",
                "tyt matematik hoca lazım",
                "ayt fizik özel ders",
                "üniversite sınavı özel ders",
                
                # === MÜZİK ===
                "piyano özel ders arıyorum",
                "gitar dersi arıyorum",
                
                # === YAZILIM ===
                "programlama özel ders arıyorum",
                "python özel ders",
            ]
        self.keywords = keywords

    async def scrape(self, max_posts=100, pages=1):
        """Scrapes DuckDuckGo HTML for web-wide tutoring leads."""
        all_leads = []
        seen_hashes = set()
        
        print(f"   🌐 Google/Web Ultra Scan: {len(self.keywords)} keywords")
        
        for kw in self.keywords:
            if len(all_leads) >= max_posts:
                break
            try:
                # Search the entire web (not restricted to a specific site)
                query = f'"{kw}" 2026'
                encoded_query = urllib.parse.quote(query)
                url = f"https://html.duckduckgo.com/html/?q={encoded_query}&df=m"
                
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
                })
                
                html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8')
                
                # Parse results
                result_blocks = html.split('class="result__body"')
                
                for block in result_blocks[1:]:
                    if len(all_leads) >= max_posts:
                        break
                    try:
                        # Extract URL
                        href = ""
                        href_match = re.search(r'href="([^"]*uddg=[^"]*)"', block)
                        if href_match:
                            raw_href = href_match.group(1)
                            href = urllib.parse.unquote(raw_href.split("uddg=")[1].split("&")[0])
                        
                        if not href or "google.com" in href:
                            continue
                        
                        # Skip known teacher ad platforms
                        skip_domains = ["armut.com", "bionluk.com", "preply.com", "superprof.com.tr"]
                        if any(d in href for d in skip_domains):
                            continue
                        
                        # Extract title
                        title = ""
                        title_match = re.search(r'class="result__a"[^>]*>([^<]+)', block)
                        if title_match:
                            title = html_lib.unescape(title_match.group(1).strip())
                        
                        # Extract snippet
                        snippet = ""
                        snippet_match = re.search(r'class="result__snippet"[^>]*>(.+?)</a>', block, re.DOTALL)
                        if snippet_match:
                            snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                            snippet = html_lib.unescape(snippet)
                        
                        content = f"{title}: {snippet}" if title and snippet else title or snippet
                        
                        if len(content) < 20:
                            continue
                        
                        text_hash = hashlib.md5(content.encode()).hexdigest()
                        if text_hash in seen_hashes:
                            continue
                        seen_hashes.add(text_hash)
                        
                        clean_url = href.split('?')[0]
                        
                        # Detect platform from URL
                        platform = "Google / Web"
                        if "facebook.com" in href:
                            platform = "Facebook (via Web)"
                        elif "twitter.com" in href or "x.com" in href:
                            platform = "Twitter (via Web)"
                        elif "instagram.com" in href:
                            platform = "Instagram (via Web)"
                        elif "sahibinden.com" in href:
                            platform = "Sahibinden (via Web)"
                        elif "forum" in href.lower() or "donanimhaber" in href.lower():
                            platform = "Forum (via Web)"
                        elif "eksi" in href.lower():
                            platform = "Ekşi Sözlük"
                        
                        all_leads.append({
                            "id": str(uuid.uuid4()),
                            "platform": platform,
                            "content": content[:500],
                            "subject": "Genel Özel Ders",
                            "location": "Türkiye / Web",
                            "original_link": clean_url,
                            "original_date": "2026",
                            "text_hash": text_hash,
                            "is_qualified": 1
                        })
                    except Exception:
                        continue
                
                # Also parse result__snippet directly as fallback
                snippet_parts = html.split('class="result__snippet"')
                for sp in snippet_parts[1:]:
                    if len(all_leads) >= max_posts:
                        break
                    try:
                        text = sp.split('>')[1].split('</')[0] if '>' in sp else ''
                        text = re.sub(r'<[^>]+>', '', text).strip()
                        text = html_lib.unescape(text)
                        
                        if len(text) < 20:
                            continue
                        
                        text_hash = hashlib.md5(text.encode()).hexdigest()
                        if text_hash in seen_hashes:
                            continue
                        seen_hashes.add(text_hash)
                        
                        all_leads.append({
                            "id": str(uuid.uuid4()),
                            "platform": "Google / Web",
                            "content": text[:500],
                            "subject": "Genel Özel Ders",
                            "location": "Türkiye / Web",
                            "original_link": "",
                            "original_date": "2026",
                            "text_hash": text_hash,
                            "is_qualified": 1
                        })
                    except Exception:
                        continue
                        
            except Exception as e:
                print(f"   ⚠️ Web Scraper Error for '{kw}': {e}")
                time.sleep(3)
                continue
            
            # Rate limiting between requests
            time.sleep(2.5)
        
        print(f"   🌐 Web scan complete: {len(all_leads)} leads found")
        return all_leads

if __name__ == "__main__":
    scraper = GoogleScraper()
    results = asyncio.run(scraper.scrape(max_posts=10))
    print(f"Found {len(results)} results:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
