import sys
import os
import asyncio
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import save_lead
from scrapers.forum_scraper import ForumScraper
from scrapers.twitter_scraper import TwitterScraper
from scrapers.sahibinden_scraper import SahibindenScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.instagram_scraper import InstagramScraper
from scrapers.linkedin_scraper import LinkedInScraper
from core.classifier import LeadClassifier

async def run_all():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Antigravity Derin Tarama Motoru Başlatıldı\n" + "="*60)
    scrapers = [
        ("X (Twitter)", TwitterScraper()),
        ("Sahibinden", SahibindenScraper()),
        ("Facebook Group", FacebookScraper()),
        ("Instagram", InstagramScraper()),
        ("LinkedIn", LinkedInScraper()),
        ("DonanımHaber/Forum", ForumScraper())
    ]
    
    # Optional: Include Apify if configured
    try:
        from scrapers.apify_scraper import ApifyScraper
        apify_scraper = ApifyScraper()
        if apify_scraper.is_configured():
            scrapers.append(("Apify (Social)", apify_scraper))
            print("   📲 Apify modülü aktif olarak tarama listesine eklendi.")
    except Exception as e:
        print(f"   ⚠️ Apify modülü yükleme uyarısı: {e}")

    # Initialize ScrapingStateManager and start scan session
    state_manager = None
    scan_id = None
    try:
        from database.state_manager import ScrapingStateManager
        state_manager = ScrapingStateManager()
        platforms = [s[0] for s in scrapers]
        scan_id = state_manager.start_scan("Periodic Scan", platforms)
        print(f"   📊 Tarama oturumu başlatıldı (ID: {scan_id})")
    except Exception as e:
        print(f"   ⚠️ State Manager başlatma hatası: {e}")

    classifier = LeadClassifier()
    total_found = 0
    total_qualified = 0
    
    for name, scraper in scrapers:
        print(f"\n📡 [{name}] ağına sızılıyor ve güncel talepler çekiliyor...")
        state_key = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        try:
            found = await scraper.scrape(max_posts=25)
            print(f"   => {len(found)} adet ham veri toplandı. Yapay Zeka (Gemini) filtreden geçiriyor...")
            total_found += len(found)
            
            for lead in found:
                # Basic classification
                analysis = classifier.classify(lead["content"])
                if analysis.get("is_lead"):
                    lead.update({
                        "subject": analysis.get("subject", "Özel Ders"),
                        "location": analysis.get("location", lead.get("location", "Belirtilmemiş")),
                        "contact_info": analysis.get("contact_info", lead.get("contact_info")),
                        "whatsapp_link": analysis.get("whatsapp_link"),
                    })
                    save_lead(lead)
                    total_qualified += 1
                    contact = lead.get('contact_info') or 'İletişim gizli/yok'
                    print(f"      ✅ [NİTELİKLİ TALEP BULUNDU]")
                    print(f"         Ders: {lead['subject']} | Konum: {lead['location']} | {contact}")
                    
            if state_manager:
                state_manager.update_state(state_key, items_found=len(found))
        except Exception as e:
            print(f"   ❌ {name} tarama motorunda hata oluştu: {str(e)}")
            if state_manager:
                state_manager.update_state(state_key, error=str(e))
            import traceback
            traceback.print_exc()
            
    print("\n" + "="*60)
    print(f"🏆 DERİN TARAMA ÖZETİ")
    print(f"   Çekilen Ham Gönderi: {total_found}")
    print(f"   Elenen (Reklam vs.): {total_found - total_qualified}")
    print(f"   Yakalanan Lead   :   {total_qualified}")
    print(f"   Tüm yeni talepler paneldeki veritabanına eklendi. Paneli yenileyerek görebilirsiniz!")

    if state_manager and scan_id is not None:
        try:
            state_manager.end_scan(scan_id, total_raw=total_found, total_qualified=total_qualified)
            print("   📊 Tarama oturumu başarıyla kapatıldı.")
        except Exception as e:
            print(f"   ⚠️ Tarama oturumu kapatma hatası: {e}")

if __name__ == "__main__":
    asyncio.run(run_all())
