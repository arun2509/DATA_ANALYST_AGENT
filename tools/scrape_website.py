from playwright.async_api import async_playwright
import asyncio
async def scrape_website(url: str, output_file: str = "scraped_content.html"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            content = await page.content()
            with open(output_file, "w", encoding="utf-8") as f:
                await f.write(content)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
        await browser.close()
