# --- Windows Loop Policy Initialization (CRITICAL: MUST BE FIRST) ---
import sys
import os
import asyncio

if os.name == 'nt':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception as e:
        print(f"Asyncio policy setting warning: {e}")
# -------------------------------------------------------------------

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlite3
import uuid
import hashlib
from datetime import datetime

# Add the 'backend' directory to the path to enable direct imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import components
from database.db_manager import init_db, save_lead, get_leads
from scrapers.forum_scraper import ForumScraper
from scrapers.twitter_scraper import TwitterScraper
from scrapers.sahibinden_scraper import SahibindenScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.instagram_scraper import InstagramScraper
from core.classifier import LeadClassifier

app = FastAPI(title="Özel Ders Lead Aggregator API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background Task for Automatic Scraping (Every 4 Hours)
async def automated_scraper_task():
    """Task that runs every 4 hours to fetch new leads."""
    scrapers = [
        ForumScraper(),
        TwitterScraper(),
        SahibindenScraper(),
        FacebookScraper(),
        InstagramScraper()
    ]
    classifier = LeadClassifier()
    
    while True:
        print(f"[{datetime.now()}] Automated deep scraping started...")
        raw_leads = []
        for scraper in scrapers:
            try:
                found = await scraper.scrape(max_posts=8)
                print(f"[{datetime.now()}] Scraper ({scraper.__class__.__name__}) found {len(found)} raw items.")
                raw_leads.extend(found)
            except Exception as e:
                print(f"[{datetime.now()}] Scraper Error ({scraper.__class__.__name__}): {str(e)}")
                # Log to a file if possible or just continue to next scraper
                continue
        
        # Process and Classify
        qualified_count = 0
        for lead in raw_leads:
            try:
                analysis = classifier.classify(lead["content"])
                if analysis.get("is_lead"):
                    lead.update({
                        "subject": analysis.get("subject", "Özel Ders"),
                        "location": analysis.get("location", lead.get("location", "Belirtilmemiş")),
                        "contact_info": analysis.get("contact_info", lead.get("contact_info")),
                        "whatsapp_link": analysis.get("whatsapp_link"),
                        "is_qualified": 1
                    })
                    save_lead(lead)
                    qualified_count += 1
            except Exception as classify_err:
                print(f"Classification skipped for one lead: {classify_err}")
                continue
            
        print(f"[{datetime.now()}] Cycle finished. Processed {len(raw_leads)}, Saved {qualified_count} qualified leads.")
        try:
            await asyncio.sleep(14400)
        except asyncio.CancelledError:
            print(f"[{datetime.now()}] Automated scraper task cancelled.")
            break
        except Exception as sleep_err:
            print(f"[{datetime.now()}] Unexpected error in sleeper: {sleep_err}")
            await asyncio.sleep(60) # Short wait before retry

# Initialize database and background task on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    # Store the task to avoid it being garbage collected prematurely and to track it
    app.state.scraper_task = asyncio.create_task(automated_scraper_task())
    
    # Catch unhandled exceptions in the background task
    def handle_task_result(task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass # Task was cancelled
        except Exception as e:
            print(f"CRITICAL: Background scraper task failed with error: {e}")
            # Optionally restart the task here if needed
            
    app.state.scraper_task.add_done_callback(handle_task_result)

# API Endpoint to fetch leads
@app.get("/api/leads")
async def fetch_leads_api():
    try:
        leads = get_leads(limit=100)
        return {"status": "success", "data": leads}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Global status for scannning
is_scanning = False

@app.post("/api/scan")
async def trigger_scan():
    global is_scanning
    if is_scanning:
        return {"status": "error", "message": "Tarama zaten devam ediyor."}
    
    is_scanning = True
    try:
        scrapers = [ForumScraper(), TwitterScraper(), SahibindenScraper(), FacebookScraper(), InstagramScraper()]
        classifier = LeadClassifier()
        total_found = 0
        
        for scraper in scrapers:
            try:
                found = await scraper.scrape(max_posts=20)
                for lead in found:
                    analysis = classifier.classify(lead["content"])
                    if analysis.get("is_lead"):
                        lead.update({
                            "subject": analysis.get("subject", "Özel Ders"),
                            "location": analysis.get("location", lead.get("location", "Belirtilmemiş")),
                            "contact_info": analysis.get("contact_info", lead.get("contact_info")),
                            "whatsapp_link": analysis.get("whatsapp_link"),
                        })
                        save_lead(lead)
                        total_found += 1
            except Exception as scraper_err:
                print(f"Manual Scan Error for {scraper.__class__.__name__}: {scraper_err}")
                continue 
            
        return {"status": "success", "message": f"Tarama bitti. {total_found} yeni nitelikli talep eklendi."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        is_scanning = False

@app.get("/api/status")
async def get_status():
    return {"is_scanning": is_scanning}

# Serve Dashboard
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    with open("backend/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False, loop="asyncio")
