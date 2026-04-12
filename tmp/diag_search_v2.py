import asyncio
from playwright.async_api import async_playwright
import urllib.parse

async def test_ddg():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        query = 'site:facebook.com/groups "lgs anneleri" özel ders'
        encoded = urllib.parse.quote(query)
        
        # Test DuckDuckGo
        print(f"Testing DuckDuckGo for: {query}")
        await page.goto(f"https://html.duckduckgo.com/html/?q={encoded}", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        results = await page.query_selector_all(".result")
        print(f"DuckDuckGo: Found {len(results)} search results")
        for i, res in enumerate(results[:3]):
            text = await res.inner_text()
            print(f"Result {i+1}: {text[:100]}...")

        # Test Yandex
        print(f"\nTesting Yandex for: {query}")
        await page.goto(f"https://yandex.com/search/?text={encoded}", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        results = await page.query_selector_all("li.serp-item")
        print(f"Yandex: Found {len(results)} search results")
        for i, res in enumerate(results[:3]):
            text = await res.inner_text()
            print(f"Result {i+1}: {text[:100]}...")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_ddg())
