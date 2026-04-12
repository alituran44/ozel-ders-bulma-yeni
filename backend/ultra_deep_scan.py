"""
Ultra Deep Scan v5 - Multi-Strategy Approach
Uses multiple search engines with fallback, plus direct site scraping.
"""
import sys
import os
import asyncio
from datetime import datetime
import csv
import hashlib
import uuid
import re
import urllib.parse
import urllib.request
import html as html_lib
import json
import time

if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import save_lead, get_leads
from core.classifier import LeadClassifier

# ============================================================
# SEARCH QUERIES
# ============================================================

# Facebook group specific queries
fb_group_queries = [
    'site:facebook.com/groups özel ders arıyorum',
    'site:facebook.com/groups hoca arıyorum',
    'site:facebook.com/groups özel ders lazım',
    'site:facebook.com/groups matematik özel ders',
    'site:facebook.com/groups ingilizce özel ders',
    'site:facebook.com/groups lgs anneleri',
    'site:facebook.com/groups lgs velileri',
    'site:facebook.com/groups lgs 2026',
    'site:facebook.com/groups yks hoca',
    'site:facebook.com/groups kpss özel ders',
    'site:facebook.com/groups kpss matematik',
    'site:facebook.com/groups ales hoca',
    'site:facebook.com/groups ales özel ders',
    'site:facebook.com/groups dgs matematik',
    'site:facebook.com/groups ilkokul özel ders',
]

# Web queries
web_queries = [
    'özel ders arıyorum 2026',
    'matematik hoca lazım 2026',
    'özel ders lazım 2026',
    'ingilizce hoca arıyorum',
    'lgs özel ders 2026',
    'yks özel ders 2026',
    'kpss özel ders arıyorum',
    'kpss matematik hoca',
    'ales özel ders lazım',
    'ales hoca arıyorum',
    'tyt matematik hoca',
    'ayt fizik hoca',
    'çocuğuma özel ders',
    'piyano özel ders',
    'ilkokul özel ders',
]

# Instagram specific fallback queries
ig_queries = [
    'site:instagram.com "özel ders arıyorum"',
    'site:instagram.com "hoca arıyorum"',
    'site:instagram.com "özel ders lazım"',
    'site:instagram.com matematik özel ders',
    'site:instagram.com ingilizce özel ders',
    'site:instagram.com lgs özel ders',
    'site:instagram.com yks özel ders',
]


async def _try_search_engines(page, query, seen_hashes, default_platform):
    """Try multiple search engines in order: Google -> Bing -> Yandex"""
    results = []
    
    # Strategy 1: Google
    try:
        results = await _scrape_google(page, query, seen_hashes, default_platform)
        if results:
            return results
    except Exception as e:
        pass
    
    # Strategy 2: Bing
    try:
        results = await _scrape_bing(page, query, seen_hashes, default_platform)
        if results:
            return results
    except Exception as e:
        pass
    
    # Strategy 3: Yandex (good for Turkish content)
    try:
        results = await _scrape_yandex(page, query, seen_hashes, default_platform)
        if results:
            return results
    except Exception as e:
        pass
    
    return results


async def _scrape_google(page, query, seen_hashes, default_platform):
    """Try Google search"""
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}&hl=tr&num=20"
    
    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(2)
    
    # Check for CAPTCHA
    body = await page.inner_text("body")
    if "unusual traffic" in body.lower() or "captcha" in body.lower():
        return []
    
    # Google result blocks
    elements = await page.query_selector_all("div.g")
    for el in elements:
        try:
            title_el = await el.query_selector("h3")
            link_el = await el.query_selector("a")
            snippet_el = await el.query_selector("div.VwiC3b, span.st, div[data-sncf]")
            
            if not title_el or not link_el:
                continue
            
            title = await title_el.inner_text()
            href = await link_el.get_attribute("href") or ""
            snippet = await snippet_el.inner_text() if snippet_el else ""
            
            if "google.com" in href:
                continue
            
            content = f"{title}: {snippet}" if snippet else title
            if len(content) < 20:
                continue
            
            text_hash = hashlib.md5(content.encode()).hexdigest()
            if text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)
            
            platform = _detect_platform(href, default_platform)
            
            results.append(_make_lead(content, href, platform, text_hash))
        except Exception:
            continue
    
    return results


async def _scrape_bing(page, query, seen_hashes, default_platform):
    """Bing search"""
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded}&setlang=tr"
    
    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(2)
    
    elements = await page.query_selector_all("li.b_algo")
    for el in elements:
        try:
            title_el = await el.query_selector("h2 a")
            if not title_el:
                continue
            title = await title_el.inner_text()
            href = await title_el.get_attribute("href") or ""
            
            snippet_el = await el.query_selector(".b_caption p")
            snippet = await snippet_el.inner_text() if snippet_el else ""
            
            content = f"{title}: {snippet}" if snippet else title
            if len(content) < 20:
                continue
            
            text_hash = hashlib.md5(content.encode()).hexdigest()
            if text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)
            
            platform = _detect_platform(href, default_platform)
            results.append(_make_lead(content, href, platform, text_hash))
        except Exception:
            continue
    
    return results


async def _scrape_yandex(page, query, seen_hashes, default_platform):
    """Yandex search - great for Turkish content"""
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://yandex.com/search/?text={encoded}&lr=983"
    
    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(2)
    
    # Yandex result blocks
    elements = await page.query_selector_all("li.serp-item")
    for el in elements:
        try:
            title_el = await el.query_selector("a.OrganicTitle-Link, a.Link")
            if not title_el:
                continue
            
            title_text_el = await el.query_selector(".OrganicTitle-LinkText, h2")
            title = await title_text_el.inner_text() if title_text_el else await title_el.inner_text()
            href = await title_el.get_attribute("href") or ""
            
            snippet_el = await el.query_selector(".OrganicTextContentSpan, .Organic-ContentText, .TextContainer")
            snippet = await snippet_el.inner_text() if snippet_el else ""
            
            content = f"{title}: {snippet}" if snippet else title
            if len(content) < 20:
                continue
            
            text_hash = hashlib.md5(content.encode()).hexdigest()
            if text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)
            
            platform = _detect_platform(href, default_platform)
            results.append(_make_lead(content, href, platform, text_hash))
        except Exception:
            continue
    
    return results


def load_fb_cookies():
    """Load and sanitize Facebook session cookies from file if exists"""
    cookie_path = os.path.join(os.path.dirname(__file__), "auth", "facebook_cookies.json")
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, 'r') as f:
                cookies = json.load(f)
                sanitized = []
                for c in cookies:
                    # Skip placeholders
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
            print(f"⚠️ Cookie sanitizing error: {e}")
    return None

async def _scrape_fb_feed(page, seen_hashes):
    """Scrape the authenticated Facebook Group Feed"""
    results = []
    print(f"   📡 Authed Feed: facebook.com/groups/feed")
    try:
        await page.goto("https://www.facebook.com/groups/feed", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(5) # Allow dynamic content to load
        
        # Scroll a bit to trigger lazy loading
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(2)
            
        # Select post containers
        # Common FB feed selector for posts: div[role="feed"] > div, or specific data-testid
        posts = await page.query_selector_all('div[role="article"]')
        for post in posts[:15]:
            try:
                # FB structure is complex, use innerText of the whole post first
                text = await post.inner_text()
                if len(text) < 30: continue
                
                # Try to find a link to the original post
                link_el = await post.query_selector('a[href*="/groups/"]')
                href = await link_el.get_attribute("href") if link_el else "https://www.facebook.com/groups/feed"
                
                text_hash = hashlib.md5(text.encode()).hexdigest()
                if text_hash in seen_hashes: continue
                seen_hashes.add(text_hash)
                
                results.append(_make_lead(text, href, "Facebook Group (Auth)", text_hash))
            except:
                continue
    except Exception as e:
        print(f"   ⚠️ Auth Feed Error: {e}")
    return results

def _detect_platform(href, default):
    """Detect platform from URL"""
    if "facebook.com/groups/" in href:
        return "Facebook Group"
    elif "facebook.com" in href:
        return "Facebook"
    elif "twitter.com" in href or "x.com" in href:
        return "Twitter (X)"
    elif "instagram.com" in href:
        return "Instagram"
    elif "sahibinden.com" in href:
        return "Sahibinden"
    elif "donanimhaber" in href.lower():
        return "DonanımHaber"
    elif "eksi" in href.lower():
        return "Ekşi Sözlük"
    elif "armut.com" in href:
        return "Armut"
    return default


def _make_lead(content, href, platform, text_hash):
    """Create a lead dictionary"""
    return {
        "id": str(uuid.uuid4()),
        "platform": platform,
        "content": content[:500],
        "subject": "Özel Ders",
        "location": "Türkiye Geneli",
        "original_link": href.split('?')[0] if href else "",
        "text_hash": text_hash,
        "is_qualified": 1,
        "original_date": "Anlık"
    }


async def run_ultra_deep_scan():
    start_time = datetime.now()
    total_queries = len(fb_group_queries) + len(web_queries)
    
    print(f"\n{'='*70}")
    print(f"🚀 ANTIGRAVITY ULTRA DERİN TARAMA v5.0 (Multi-Engine)")
    print(f"⏰ Başlangıç: {start_time.strftime('%H:%M:%S')}")
    print(f"🔍 Stratejiler: Google → Bing → Yandex (otomatik fallback)")
    print(f"📘 Facebook Grup Sorguları: {len(fb_group_queries)}")
    print(f"🌐 Web Sorguları: {len(web_queries)}")
    print(f"📊 Toplam: {total_queries} sorgu + DonanımHaber + Sahibinden")
    print(f"{'='*70}")
    
    classifier = LeadClassifier()
    seen_hashes = set()
    total_qualified = 0
    total_raw = 0
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="tr-TR"
        )
        fb_cookies = load_fb_cookies()
        if fb_cookies:
            print(f"   🔑 Facebook çerezleri yüklendi! ({len(fb_cookies)} cookie)")
            await context.add_cookies(fb_cookies)
        else:
            print(f"   ℹ️ Facebook çerezleri bulunamadı. Sadece halka açık gruplar taranacak.")
            
        page = await context.new_page()
        
        def process_leads(leads):
            nonlocal total_raw, total_qualified
            for lead in leads:
                total_raw += 1
                analysis = classifier.classify(lead["content"])
                if analysis.get("is_lead"):
                    lead.update({
                        "subject": analysis.get("subject", lead.get("subject", "Özel Ders")),
                        "location": analysis.get("location", lead.get("location", "Türkiye")),
                        "contact_info": analysis.get("contact_info"),
                        "whatsapp_link": analysis.get("whatsapp_link"),
                        "is_qualified": 1
                    })
                    save_lead(lead)
                    total_qualified += 1
        
        # ============================================================
        # PHASE 1: AUTHENTICATED FEED (If cookies present)
        # ============================================================
        if fb_cookies:
            print(f"\n🔑 PHASE 1: Facebook Oturumlu Akış (Private Groups)")
            print("-" * 50)
            feed_leads = await _scrape_fb_feed(page, seen_hashes)
            process_leads(feed_leads)
            print(f"      ✅ {len(feed_leads)} yeni sonuç akıştan çekildi")

        # ============================================================
        # PHASE 2: FACEBOOK GROUPS (Search)
        # ============================================================
        print(f"\n📘 PHASE 2: Facebook Aramaları ({len(fb_group_queries)} sorgu)")
        print("-" * 50)
        
        for i, query in enumerate(fb_group_queries):
            print(f"   [{i+1}/{len(fb_group_queries)}] {query[:55]}...")
            leads = await _try_search_engines(page, query, seen_hashes, "Facebook Group")
            process_leads(leads)
            if leads:
                print(f"      ✅ {len(leads)} sonuç")
            else:
                print(f"      ○ Sonuç yok")
            await asyncio.sleep(4)
        
        fb_count = total_qualified
        print(f"\n   📘 Facebook: {fb_count} nitelikli lead")
        
        # ============================================================
        # PHASE 2: WEB GENELI
        # ============================================================
        print(f"\n🌐 PHASE 2: Web Geneli ({len(web_queries)} sorgu)")
        print("-" * 50)
        
        for i, query in enumerate(web_queries):
            print(f"   [{i+1}/{len(web_queries)}] {query[:55]}...")
            leads = await _try_search_engines(page, query, seen_hashes, "Google / Web")
            process_leads(leads)
            if leads:
                print(f"      ✅ {len(leads)} sonuç")
            else:
                print(f"      ○ Sonuç yok")
            await asyncio.sleep(4)
        
        web_count = total_qualified - fb_count
        print(f"\n   🌐 Web: {web_count} nitelikli lead")
        
        # ============================================================
        # PHASE 3: DonanımHaber Forum (Direct)
        # ============================================================
        print(f"\n💬 PHASE 3: DonanımHaber Forum")
        print("-" * 50)
        
        before_forum = total_qualified
        forum_urls = [
            "https://forum.donanimhaber.com/tyt-ayt-ydt--f615",
            "https://forum.donanimhaber.com/lgs--f621",
        ]
        
        for forum_url in forum_urls:
            try:
                print(f"   Taranıyor: {forum_url}")
                await page.goto(forum_url, wait_until="load", timeout=20000)
                await asyncio.sleep(2)
                
                rows = await page.query_selector_all(".kl-icerik-satir")
                for row in rows[:25]:
                    try:
                        title_elem = await row.query_selector(".kl-konu a")
                        if not title_elem:
                            continue
                        title = await title_elem.inner_text()
                        link = await title_elem.get_attribute("href")
                        if not link.startswith("http"):
                            link = "https://forum.donanimhaber.com" + link
                        
                        author_elem = await row.query_selector(".kl-uye-ad")
                        author = await author_elem.inner_text() if author_elem else "Anonim"
                        
                        content = f"{title} (Yazar: {author})"
                        text_hash = hashlib.md5(content.encode()).hexdigest()
                        
                        if text_hash in seen_hashes:
                            continue
                        seen_hashes.add(text_hash)
                        
                        lead = _make_lead(content, link, "DonanımHaber", text_hash)
                        lead["original_date"] = "Bugün"
                        lead["location"] = "Türkiye Geneli / Online"
                        lead["subject"] = "Özel Ders / Koçluk"
                        process_leads([lead])
                    except Exception:
                        continue
                
                print(f"   ✅ Forum sayfası tamamlandı")
            except Exception as e:
                print(f"   ⚠️ Forum hatası: {e}")
        
        forum_count = total_qualified - before_forum
        print(f"   💬 Forum: {forum_count} nitelikli lead")
        
        # ============================================================
        # PHASE 4: Sahibinden (Direct)
        # ============================================================
        print(f"\n🏠 PHASE 4: Sahibinden")
        print("-" * 50)
        
        before_sahib = total_qualified
        try:
            await page.goto("https://www.sahibinden.com/kategori/ders-danismanlik-ozel-ders", wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)
            
            rows = await page.query_selector_all(".searchResultsItem")
            if not rows:
                # Try alternative selectors
                rows = await page.query_selector_all("[class*='searchResult']")
            
            for row in rows[:30]:
                try:
                    title_elem = await row.query_selector("a[title], a.classifiedTitle")
                    if not title_elem:
                        title_elem = await row.query_selector("a")
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    link = await title_elem.get_attribute("href")
                    if link and not link.startswith("http"):
                        link = "https://www.sahibinden.com" + link
                    
                    content = title.strip()
                    if len(content) < 10:
                        continue
                    
                    text_hash = hashlib.md5(content.encode()).hexdigest()
                    if text_hash in seen_hashes:
                        continue
                    seen_hashes.add(text_hash)
                    
                    lead = _make_lead(content, link or "", "Sahibinden", text_hash)
                    lead["original_date"] = "Güncel"
                    process_leads([lead])
                except Exception:
                    continue
            
            sahib_count = total_qualified - before_sahib
            print(f"   ✅ Sahibinden: {sahib_count} nitelikli lead")
        except Exception as e:
            print(f"   ⚠️ Sahibinden hatası: {e}")
        
        # ============================================================
        # PHASE 5: INSTAGRAM (via Search Fallback)
        # ============================================================
        print(f"\n📸 PHASE 5: Instagram ({len(ig_queries)} sorgu)")
        print("-" * 50)
        
        before_ig = total_qualified
        for i, query in enumerate(ig_queries):
            print(f"   [{i+1}/{len(ig_queries)}] {query[:55]}...")
            leads = await _try_search_engines(page, query, seen_hashes, "Instagram")
            process_leads(leads)
            if leads:
                print(f"      ✅ {len(leads)} sonuç")
            else:
                print(f"      ○ Sonuç yok")
            await asyncio.sleep(4)
        
        ig_count = total_qualified - before_ig
        print(f"   📸 Instagram: {ig_count} nitelikli lead")

        await browser.close()
    
    # ============================================================
    # SUMMARY
    # ============================================================
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*70}")
    print(f"🏆 ULTRA TARAMA TAMAMLANDI!")
    print(f"📊 İncelenen: {total_raw} -> Nitelikli: {total_qualified}")
    print(f"⏱️ Süre: {elapsed:.0f} saniye ({elapsed/60:.1f} dakika)")
    print(f"{'='*70}")
    
    export_results()


def export_results():
    """Exports database to CSV"""
    all_leads = get_leads(limit=1000)
    
    csv_path = "backend/nitelikli_talepler_listesi.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Platform', 'Ders', 'Konum', 'İletişim', 'İçerik', 'Link', 'Tarih'])
        for l in all_leads:
            writer.writerow([
                l['platform'], l['subject'], l['location'],
                l.get('contact_info') or 'Gizli',
                l['content'][:150].replace('\n', ' '),
                l['original_link'], l.get('original_date', '')
            ])
    
    print(f"\n📁 CSV: {csv_path}")
    print(f"📊 Toplam kayıt: {len(all_leads)}")
    print(f"💡 Panel: http://localhost:8080")


if __name__ == "__main__":
    asyncio.run(run_ultra_deep_scan())
