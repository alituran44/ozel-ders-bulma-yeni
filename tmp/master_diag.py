import asyncio
import urllib.request
import urllib.parse
from playwright.async_api import async_playwright
import re

async def diag():
    query = 'site:facebook.com/groups "lgs anneleri" özel ders'
    encoded = urllib.parse.quote(query)
    
    print(f"--- Diag for: {query} ---")
    
    # 1. DuckDuckGo HTML
    try:
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            matches = re.findall(r'class=\"result__a\"', html)
            print(f"DDG HTML (urllib): Found {len(matches)} results")
    except Exception as e:
        print(f"DDG HTML (urllib) Error: {e}")

    # 2. Yandex (Playwright)
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0")
            page = await context.new_page()
            
            print("Testing Yandex (Playwright)...")
            await page.goto(f"https://yandex.com/search/?text={encoded}", timeout=20000)
            await asyncio.sleep(2)
            results = await page.query_selector_all("li.serp-item")
            print(f"Yandex: Found {len(results)} results")
            
            # Check Bing again
            print("Testing Bing (Playwright)...")
            await page.goto(f"https://www.bing.com/search?q={encoded}", timeout=20000)
            await asyncio.sleep(2)
            results = await page.query_selector_all("li.b_algo")
            print(f"Bing: Found {len(results)} results")
            
            await browser.close()
        except Exception as e:
            print(f"Playwright Diag Error: {e}")

if __name__ == "__main__":
    asyncio.run(diag())
