# --- Windows Loop Policy Initialization (CRITICAL: MUST BE FIRST) ---
import sys
import os
import asyncio

sys.stdout.reconfigure(encoding='utf-8')

if os.name == 'nt':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception as e:
        print(f"Asyncio policy setting warning: {e}")
# -------------------------------------------------------------------

from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sqlite3
import uuid
import hashlib
import json
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

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")), name="static")


# Background Task for Automatic Scraping (Every 4 Hours)
async def automated_scraper_task():
    """Task that runs every 4 hours to fetch new leads via an isolated subprocess."""
    # Delay first run by 30 seconds to allow clean server boot and UI load
    await asyncio.sleep(30)
    
    import sys
    cmd = [sys.executable, "backend/run_deep_scan.py"]
    
    while True:
        print(f"[{datetime.now()}] Starting background scraper subprocess...")
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                print(f"[{datetime.now()}] Background scraper completed successfully.")
            else:
                err_msg = stderr.decode(errors='ignore')
                print(f"[{datetime.now()}] Background scraper failed with code {process.returncode}. Error: {err_msg}")
        except Exception as e:
            print(f"[{datetime.now()}] Failed to launch background scraper: {e}")
            
        try:
            await asyncio.sleep(14400)
        except asyncio.CancelledError:
            print(f"[{datetime.now()}] Automated scraper task cancelled.")
            break
        except Exception as sleep_err:
            print(f"[{datetime.now()}] Unexpected error in sleeper: {sleep_err}")
            await asyncio.sleep(60)

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
async def trigger_scan(background_tasks: BackgroundTasks):
    global is_scanning
    if is_scanning:
        return {"status": "error", "message": "Tarama zaten devam ediyor."}
    
    is_scanning = True
    
    async def run_scan_in_bg():
        global is_scanning
        import sys
        try:
            cmd = [sys.executable, "backend/ultra_deep_scan.py"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                print("Deep scan subprocess completed successfully.")
            else:
                err_msg = stderr.decode(errors='ignore')
                print(f"Deep scan subprocess failed with code {process.returncode}. Error: {err_msg}")
        except Exception as e:
            print(f"Failed to launch deep scan subprocess: {e}")
        finally:
            is_scanning = False
            
    background_tasks.add_task(run_scan_in_bg)
    return {"status": "success", "message": "Derin tarama arka planda başlatıldı."}

@app.get("/api/status")
async def get_status():
    return {"is_scanning": is_scanning}

class SettingsRequest(BaseModel):
    platform: str
    cookies: str

@app.get("/api/settings")
async def get_settings():
    fb_path = "backend/auth/facebook_cookies.json"
    ig_path = "backend/auth/instagram_cookies.json"
    li_path = "backend/auth/linkedin_cookies.json"
    
    fb_connected = False
    if os.path.exists(fb_path):
        try:
            with open(fb_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    val = str(data[0].get("value", ""))
                    if "BURAYA_" not in val:
                        fb_connected = True
        except:
            pass
            
    ig_connected = False
    if os.path.exists(ig_path):
        try:
            with open(ig_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    val = str(data[0].get("value", ""))
                    if "BURAYA_" not in val:
                        ig_connected = True
        except:
            pass
            
    li_connected = False
    if os.path.exists(li_path):
        try:
            with open(li_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    val = str(data[0].get("value", ""))
                    if "BURAYA_" not in val:
                        li_connected = True
        except:
            pass
            
    return {
        "status": "success",
        "data": {
            "facebook": {"connected": fb_connected},
            "instagram": {"connected": ig_connected},
            "linkedin": {"connected": li_connected}
        }
    }

@app.post("/api/settings")
async def save_settings(req: SettingsRequest):
    platform = req.platform.lower()
    if platform not in ["facebook", "instagram", "linkedin"]:
        return {"status": "error", "message": "Geçersiz platform. Sadece 'facebook', 'instagram' veya 'linkedin' destekleniyor."}
        
    os.makedirs("backend/auth", exist_ok=True)
    file_path = f"backend/auth/{platform}_cookies.json"
    
    try:
        cookies_list = json.loads(req.cookies)
        if not isinstance(cookies_list, list):
            return {"status": "error", "message": "Çerezler bir JSON dizisi (array) olmalıdır."}
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(cookies_list, f, indent=2, ensure_ascii=False)
            
        return {"status": "success", "message": f"{req.platform.capitalize()} çerezleri başarıyla kaydedildi."}
    except json.JSONDecodeError:
        return {"status": "error", "message": "Geçersiz JSON formatı. Lütfen kopyaladığınız çerezleri kontrol edin."}
    except Exception as e:
        return {"status": "error", "message": f"Kaydedilirken hata oluştu: {str(e)}"}

# Serve Dashboard
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    with open("backend/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=False, loop="asyncio")
