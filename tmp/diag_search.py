import asyncio
from playwright.async_api import async_playwright
import urllib.parse

async def test_search():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        query = 'site:facebook.com/groups "lgs anneleri" özel ders'
        encoded = urllib.parse.quote(query)
        
        # Test Google
        print(f"Testing Google for: {query}")
        await page.goto(f"https://www.google.com/search?q={encoded}", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        body = await page.inner_text("body")
        print(f"Google Body Length: {len(body)}")
        if "unusual traffic" in body.lower() or "captcha" in body.lower():
            print("Google: CAPTCHA detected")
        else:
            results = await page.query_selector_all("div.g")
            print(f"Google: Found {len(results)} search results")
            for i, res in enumerate(results[:3]):
                text = await res.inner_text()
                print(f"Result {i+1}: {text[:100]}...")

        # Test Bing
        print(f"\nTesting Bing for: {query}")
        await page.goto(f"https://www.bing.com/search?q={encoded}", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        results = await page.query_selector_all("li.b_algo")
        print(f"Bing: Found {len(results)} search results")
        for i, res in enumerate(results[:3]):
            text = await res.inner_text()
            print(f"Result {i+1}: {text[:100]}...")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_search())
