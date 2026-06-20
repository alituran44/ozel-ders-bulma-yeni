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
    classifier = LeadClassifier()
    total_found = 0
    total_qualified = 0
    
    for name, scraper in scrapers:
        print(f"\n📡 [{name}] ağına sızılıyor ve güncel talepler çekiliyor...")
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
                    
        except Exception as e:
            print(f"   ❌ {name} tarama motorunda hata oluştu: {str(e)}")
            import traceback
            traceback.print_exc()
            
    print("\n" + "="*60)
    print(f"🏆 DERİN TARAMA ÖZETİ")
    print(f"   Çekilen Ham Gönderi: {total_found}")
    print(f"   Elenen (Reklam vs.): {total_found - total_qualified}")
    print(f"   Yakalanan Lead   :   {total_qualified}")
    print(f"   Tüm yeni talepler paneldeki veritabanına eklendi. Paneli yenileyerek görebilirsiniz!")

if __name__ == "__main__":
    asyncio.run(run_all())
