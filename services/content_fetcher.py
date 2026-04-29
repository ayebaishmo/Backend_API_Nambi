"""
Content Fetcher for everythinguganda.com (Next.js/React site)
Uses Playwright with a single persistent browser session.
"""

import os
import concurrent.futures

SITE_URLS = [
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


def fetch_full_site(start_url="https://www.everythinguganda.com/"):
    print("Starting Playwright site scrape...")
    result = _playwright_fetch(SITE_URLS)
    if result and len(result) > 1000:
        print(f"Scrape complete: {len(result):,} chars")
        return result
    print(f"Playwright got {len(result) if result else 0} chars — insufficient")
    return result or ""


def _playwright_fetch(urls):
    """Run Playwright in a dedicated ProactorEventLoop thread."""
    def run():
        import asyncio
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_scrape(urls))
        finally:
            loop.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(run).result(timeout=600)
    except Exception as e:
        print(f"Playwright fetch error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def _scrape(urls):
    from playwright.async_api import async_playwright

    all_text = []

    async with async_playwright() as p:
        # Single browser for all URLs — avoids repeated launch overhead
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-extensions",
                "--no-first-run",
            ]
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )

        for url in urls:
            page = None
            try:
                print(f"Fetching: {url}")
                page = await context.new_page()

                # Use 'load' — faster than networkidle, works on Next.js
                await page.goto(url, timeout=90000, wait_until="load")

                # Wait for React to hydrate
                await page.wait_for_timeout(5000)

                # Extract all meaningful text via JS
                content = await page.evaluate("""() => {
                    // Remove noise elements
                    ['script','style','noscript','nav','footer','header',
                     'iframe','svg','img'].forEach(tag => {
                        document.querySelectorAll(tag).forEach(el => el.remove());
                    });

                    // Collect text from content elements
                    const tags = ['h1','h2','h3','h4','h5','p','li',
                                  'td','th','span','div','article',
                                  'section','main','blockquote'];
                    const seen = new Set();
                    const lines = [];

                    tags.forEach(tag => {
                        document.querySelectorAll(tag).forEach(el => {
                            const t = (el.innerText || '').trim();
                            if (t.length > 15 && !seen.has(t)) {
                                seen.add(t);
                                lines.push(t);
                            }
                        });
                    });
                    return lines.join('\\n');
                }""")

                await page.close()

                if content and len(content) > 100:
                    all_text.append(f"\n--- CONTENT FROM {url} ---\n{content}")
                    print(f"  Got {len(content):,} chars")
                else:
                    print(f"  Only {len(content) if content else 0} chars")

            except Exception as e:
                print(f"  Failed {url}: {e}")
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass

        await browser.close()

    if not all_text:
        return None

    return "\n".join(all_text)


# Legacy compatibility
def fetch_page(url):
    return _playwright_fetch([url]) or ""

def fetch_multiple_pages(urls):
    return _playwright_fetch(urls) or ""
