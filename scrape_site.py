"""
Manual site scraper — run this once to save content to company_content.txt
Then the backend loads from that file instantly on every startup.
"""

import asyncio
from playwright.async_api import async_playwright

URLS = [
    "https://www.everythinguganda.com/",
    "https://www.everythinguganda.com/facts",
    "https://www.everythinguganda.com/culture",
    "https://www.everythinguganda.com/top-cities/kampala",
    "https://www.everythinguganda.com/religion",
    "https://www.everythinguganda.com/travel-tips",
    "https://www.everythinguganda.com/destinations",
    "https://www.everythinguganda.com/holiday-types?type=birding-holidays",
    "https://www.everythinguganda.com/about",
    "https://www.everythinguganda.com/where-to-stay",
    "https://www.everythinguganda.com/insights",
    "https://www.everythinguganda.com/impact",
]


async def scrape():
    all_text = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # visible so you can see progress
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080}
        )

        for url in URLS:
            try:
                print(f"Scraping: {url}")
                page = await context.new_page()
                await page.goto(url, timeout=120000, wait_until="load")
                await page.wait_for_timeout(8000)  # wait for React

                content = await page.evaluate("""() => {
                    ['script','style','noscript','nav','footer','header','iframe','svg'].forEach(t => {
                        document.querySelectorAll(t).forEach(e => e.remove());
                    });
                    return document.body.innerText;
                }""")

                await page.close()

                if content and len(content) > 100:
                    all_text.append(f"\n{'='*80}\nCONTENT FROM {url}\n{'='*80}\n{content}")
                    print(f"  ✓ Got {len(content):,} chars")
                else:
                    print(f"  ✗ Only {len(content) if content else 0} chars")

            except Exception as e:
                print(f"  ✗ Failed: {e}")

        await browser.close()

    return "\n".join(all_text)


if __name__ == "__main__":
    print("Starting manual scrape...")
    print("A browser window will open — wait for all pages to load")
    print("This may take 2-3 minutes\n")

    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    content = loop.run_until_complete(scrape())
    loop.close()

    if content and len(content) > 1000:
        with open("company_content.txt", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✓ SUCCESS: Saved {len(content):,} chars to company_content.txt")
        print("The backend will now load from this file on every startup")
    else:
        print(f"\n✗ FAILED: Only got {len(content) if content else 0} chars")
