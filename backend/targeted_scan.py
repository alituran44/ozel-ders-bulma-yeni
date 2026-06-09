"""
Targeted Scan - Ozel Ders / Grup Ders / Online Ders
Facebook Groups, Instagram ve genel web'den ilan toplama
"""
import sys
import os

# Fix encoding for Windows terminals / background tasks
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import asyncio
from datetime import datetime
import csv
import hashlib
import uuid
import re
import urllib.parse
import json
import time

import warnings
warnings.filterwarnings("ignore")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import save_lead, get_leads, init_db
from core.classifier import LeadClassifier

# ============================================================
# HEDEFLI SORGULAR - "özel ders" / "grup ders" / "online ders"
# ============================================================

# Facebook Group sorguları
fb_queries = [
    # Özel Ders - Talep/Arayış
    'site:facebook.com/groups "özel ders arıyorum"',
    'site:facebook.com/groups "özel ders lazım"',
    'site:facebook.com/groups "özel ders arayışı"',
    'site:facebook.com/groups "özel ders tavsiye"',
    'site:facebook.com/groups "hoca arıyorum" özel ders',
    # Grup Ders - Talep/Arayış
    'site:facebook.com/groups "grup ders arıyorum"',
    'site:facebook.com/groups "grup ders lazım"',
    'site:facebook.com/groups "grup dersi"',
    'site:facebook.com/groups "grup dersi arıyorum"',
    # Online Ders - Talep/Arayış
    'site:facebook.com/groups "online ders arıyorum"',
    'site:facebook.com/groups "online ders lazım"',
    'site:facebook.com/groups "online ders tavsiye"',
    'site:facebook.com/groups "online hoca"',
    'site:facebook.com/groups "online özel ders"',
    # LGS / YKS / KPSS + ders türü
    'site:facebook.com/groups "lgs" "özel ders"',
    'site:facebook.com/groups "yks" "özel ders"',
    'site:facebook.com/groups "kpss" "özel ders"',
    'site:facebook.com/groups "tyt" "özel ders"',
    # Konu bazlı Facebook
    'site:facebook.com/groups "matematik" "özel ders arıyorum"',
    'site:facebook.com/groups "ingilizce" "özel ders arıyorum"',
    'site:facebook.com/groups "fizik" "özel ders arıyorum"',
]

# Instagram sorguları
ig_queries = [
    'site:instagram.com "özel ders arıyorum"',
    'site:instagram.com "özel ders lazım"',
    'site:instagram.com "grup ders arıyorum"',
    'site:instagram.com "online ders arıyorum"',
    'site:instagram.com "online özel ders" arıyorum',
    'site:instagram.com "hoca arıyorum" özel ders',
    'site:instagram.com "özel ders tavsiye"',
    'site:instagram.com "online ders lazım"',
]

# Genel Web Sorguları
web_queries = [
    '"özel ders arıyorum" 2025 OR 2026',
    '"grup ders arıyorum" 2025 OR 2026',
    '"online ders arıyorum" 2025 OR 2026',
    '"özel ders lazım" 2025 OR 2026',
    '"grup dersi lazım" 2025 OR 2026',
    '"online ders lazım" 2025 OR 2026',
    '"özel ders arıyorum" matematik',
    '"özel ders arıyorum" ingilizce',
    '"grup ders" arıyorum lgs',
    '"grup ders" arıyorum yks',
    '"online ders" arıyorum tyt ayt',
    '"online özel ders" arıyorum kpss',
    'özel ders arıyorum türkçe',
    'özel ders arıyorum kimya',
    'grup ders arıyorum istanbul',
    'online ders arıyorum ankara',
    'özel ders lazım izmir',
    'çocuğuma özel ders arıyorum',
    'lgs özel ders arıyorum 2026',
    'yks özel ders arıyorum 2026',
]

# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def _detect_platform(href, default):
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

def _make_lead(content, href, platform, text_hash, query_tag=""):
    """Lead dict oluştur"""
    return {
        "id": str(uuid.uuid4()),
        "platform": platform,
        "content": (content[:500]).strip(),
        "subject": _detect_subject(content, query_tag),
        "location": _detect_location(content),
        "original_link": href.split('?')[0] if href else "",
        "text_hash": text_hash,
        "is_qualified": 1,
        "original_date": datetime.now().strftime("%d.%m.%Y")
    }

def _detect_subject(text, tag=""):
    """Konu tespiti"""
    text_l = text.lower()
    if "matematik" in text_l: return "Matematik"
    if "ingilizce" in text_l or "english" in text_l: return "İngilizce"
    if "fizik" in text_l: return "Fizik"
    if "kimya" in text_l: return "Kimya"
    if "biyoloji" in text_l: return "Biyoloji"
    if "türkçe" in text_l: return "Türkçe"
    if "tarih" in text_l: return "Tarih"
    if "kpss" in text_l: return "KPSS"
    if "lgs" in text_l: return "LGS"
    if "yks" in text_l or "tyt" in text_l or "ayt" in text_l: return "YKS/TYT"
    if "ales" in text_l: return "ALES"
    if "dgs" in text_l: return "DGS"
    if "grup" in text_l and "ders" in text_l: return "Grup Ders"
    if "online" in text_l and "ders" in text_l: return "Online Ders"
    return "Özel Ders"

def _detect_location(text):
    """Şehir tespiti"""
    cities = [
        "istanbul", "ankara", "izmir", "bursa", "antalya", "adana", "konya",
        "gaziantep", "şanlıurfa", "mersin", "kayseri", "eskişehir", "diyarbakır",
        "samsun", "denizli", "malatya", "trabzon", "erzurum", "van", "manisa",
        "pendik", "kadıköy", "üsküdar", "beşiktaş", "fatih", "bağcılar",
        "karşıyaka", "bornova", "nilüfer", "osmangazi", "çankaya", "keçiören",
        "mamak"
    ]
    text_l = text.lower()
    for city in cities:
        if city in text_l:
            return city.title()
    if "online" in text_l:
        return "Online"
    return "Türkiye Geneli"

async def _scrape_google(page, query, seen_hashes, default_platform):
    """Google arama sonuçlarını çek"""
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}&hl=tr&num=20"
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        
        body = await page.inner_text("body")
        if "unusual traffic" in body.lower() or "captcha" in body.lower():
            print(f"   ⚠️  Google CAPTCHA, Bing'e geçiliyor...")
            return []
        
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
                results.append(_make_lead(content, href, platform, text_hash, query))
            except Exception:
                continue
    except Exception as e:
        print(f"   ⚠️  Google hata: {e}")
    
    return results

async def _scrape_bing(page, query, seen_hashes, default_platform):
    """Bing arama sonuçlarını çek"""
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded}&setlang=tr&cc=TR"
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
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
                results.append(_make_lead(content, href, platform, text_hash, query))
            except Exception:
                continue
    except Exception as e:
        print(f"   ⚠️  Bing hata: {e}")
    
    return results

async def _scrape_yandex(page, query, seen_hashes, default_platform):
    """Yandex arama - Türkçe içerik için iyi"""
    results = []
    encoded = urllib.parse.quote(query)
    url = f"https://yandex.com.tr/search/?text={encoded}&lr=983"
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        
        elements = await page.query_selector_all("li.serp-item")
        for el in elements:
            try:
                title_el = await el.query_selector("a.OrganicTitle-Link, a.Link")
                if not title_el:
                    continue
                
                title_text_el = await el.query_selector(".OrganicTitle-LinkText, h2")
                title = await title_text_el.inner_text() if title_text_el else await title_el.inner_text()
                href = await title_el.get_attribute("href") or ""
                
                snippet_el = await el.query_selector(".OrganicTextContentSpan, .Organic-ContentText")
                snippet = await snippet_el.inner_text() if snippet_el else ""
                
                content = f"{title}: {snippet}" if snippet else title
                if len(content) < 20:
                    continue
                
                text_hash = hashlib.md5(content.encode()).hexdigest()
                if text_hash in seen_hashes:
                    continue
                seen_hashes.add(text_hash)
                
                platform = _detect_platform(href, default_platform)
                results.append(_make_lead(content, href, platform, text_hash, query))
            except Exception:
                continue
    except Exception as e:
        print(f"   ⚠️  Yandex hata: {e}")
    
    return results

async def _try_all_engines(page, query, seen_hashes, default_platform):
    """Google -> Bing -> Yandex sırasıyla dene"""
    results = await _scrape_google(page, query, seen_hashes, default_platform)
    if results:
        return results
    
    results = await _scrape_bing(page, query, seen_hashes, default_platform)
    if results:
        return results
    
    results = await _scrape_yandex(page, query, seen_hashes, default_platform)
    return results

# ============================================================
# ANA TARAMA FONKSİYONU
# ============================================================

async def run_targeted_scan():
    start_time = datetime.now()
    total_queries = len(fb_queries) + len(ig_queries) + len(web_queries)
    
    print(f"\n{'='*72}")
    print(f"🎯 HEDEFLI ÖZEL DERS / GRUP DERS / ONLINE DERS TARAMASI")
    print(f"⏰ Başlangıç: {start_time.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"📘 Facebook Sorgu: {len(fb_queries)}")
    print(f"📸 Instagram Sorgu: {len(ig_queries)}")
    print(f"🌐 Web Sorgu: {len(web_queries)}")
    print(f"📊 Toplam: {total_queries} sorgu | Motor: Google → Bing → Yandex")
    print(f"{'='*72}")
    
    # DB başlat
    init_db()
    
    classifier = LeadClassifier()
    seen_hashes = set()
    total_qualified = 0
    total_raw = 0
    
    def process_and_save(leads, phase_label):
        nonlocal total_raw, total_qualified
        for lead in leads:
            total_raw += 1
            analysis = classifier.classify(lead["content"])
            if analysis.get("is_lead"):
                lead.update({
                    "subject": analysis.get("subject") or lead.get("subject", "Özel Ders"),
                    "location": analysis.get("location") or lead.get("location", "Türkiye"),
                    "contact_info": analysis.get("contact_info"),
                    "whatsapp_link": analysis.get("whatsapp_link"),
                    "is_qualified": 1
                })
                save_lead(lead)
                total_qualified += 1
                print(f"      ✅ [{lead['platform']}] {lead['subject']} | {lead['location']} | {lead['content'][:60]}...")
    
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--lang=tr-TR",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="tr-TR",
            timezone_id="Europe/Istanbul"
        )
        page = await context.new_page()
        
        # ============================================================
        # PHASE 1: FACEBOOK GROUPS
        # ============================================================
        print(f"\n{'─'*72}")
        print(f"📘 PHASE 1: FACEBOOK GROUP İLANLARI ({len(fb_queries)} sorgu)")
        print(f"{'─'*72}")
        
        fb_before = total_qualified
        for i, query in enumerate(fb_queries):
            print(f"\n  [{i+1:02}/{len(fb_queries)}] {query[:65]}")
            leads = await _try_all_engines(page, query, seen_hashes, "Facebook Group")
            process_and_save(leads, "Facebook")
            raw_count = len(leads)
            print(f"   → {raw_count} sonuç bulundu")
            await asyncio.sleep(4)  # Rate limit koruması
        
        fb_total = total_qualified - fb_before
        print(f"\n  📘 Facebook Özet: {fb_total} nitelikli ilan kaydedildi")
        
        # ============================================================
        # PHASE 2: INSTAGRAM
        # ============================================================
        print(f"\n{'─'*72}")
        print(f"📸 PHASE 2: INSTAGRAM İLANLARI ({len(ig_queries)} sorgu)")
        print(f"{'─'*72}")
        
        ig_before = total_qualified
        for i, query in enumerate(ig_queries):
            print(f"\n  [{i+1:02}/{len(ig_queries)}] {query[:65]}")
            leads = await _try_all_engines(page, query, seen_hashes, "Instagram")
            process_and_save(leads, "Instagram")
            print(f"   → {len(leads)} sonuç bulundu")
            await asyncio.sleep(4)
        
        ig_total = total_qualified - ig_before
        print(f"\n  📸 Instagram Özet: {ig_total} nitelikli ilan kaydedildi")
        
        # ============================================================
        # PHASE 3: GENEL WEB
        # ============================================================
        print(f"\n{'─'*72}")
        print(f"🌐 PHASE 3: GENEL WEB İLANLARI ({len(web_queries)} sorgu)")
        print(f"{'─'*72}")
        
        web_before = total_qualified
        for i, query in enumerate(web_queries):
            print(f"\n  [{i+1:02}/{len(web_queries)}] {query[:65]}")
            leads = await _try_all_engines(page, query, seen_hashes, "Google / Web")
            process_and_save(leads, "Web")
            print(f"   → {len(leads)} sonuç bulundu")
            await asyncio.sleep(4)
        
        web_total = total_qualified - web_before
        print(f"\n  🌐 Web Özet: {web_total} nitelikli ilan kaydedildi")
        
        await browser.close()
    
    # ============================================================
    # ÖZET
    # ============================================================
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*72}")
    print(f"🏆 TARAMA TAMAMLANDI!")
    print(f"  📘 Facebook:  {fb_total} ilan")
    print(f"  📸 Instagram: {ig_total} ilan")
    print(f"  🌐 Web:       {web_total} ilan")
    print(f"  ─────────────────────────")
    print(f"  🎯 Toplam Nitelikli: {total_qualified} ilan")
    print(f"  ⏱️  Süre: {elapsed:.0f} sn ({elapsed/60:.1f} dk)")
    print(f"  💡 Panel: http://localhost:8081")
    print(f"{'='*72}")
    
    # CSV Dışa aktar
    _export_csv()
    
    return total_qualified


def _export_csv():
    """Tüm veritabanını CSV'ye aktar"""
    all_leads = get_leads(limit=2000)
    
    csv_path = os.path.join(os.path.dirname(__file__), "nitelikli_talepler_listesi.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Platform', 'Ders Türü', 'Konum', 'İletişim', 'İçerik', 'Link', 'Tarih'])
        for l in all_leads:
            writer.writerow([
                l['platform'],
                l.get('subject', ''),
                l.get('location', ''),
                l.get('contact_info') or '',
                (l.get('content', '')[:200]).replace('\n', ' '),
                l.get('original_link', ''),
                l.get('original_date', '')
            ])
    
    print(f"\n  📁 CSV dışa aktarıldı: {csv_path}")
    print(f"  📊 Toplam kayıt: {len(all_leads)}")


if __name__ == "__main__":
    asyncio.run(run_targeted_scan())
