
"""
Content Fetcher — tries three methods in order:
1. Scrapy full site crawl (recursive, gets everything)
2. Playwright (JS-rendered pages)
3. Requests + BeautifulSoup (plain HTTP, always works)
"""

import json
import os
import tempfile
from urllib.parse import urlparse, urljoin


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
    """
    Try Scrapy first, fall back to Playwright, then requests+BS4.
    """
    print("Attempting Scrapy full site crawl...")
    result = _scrapy_crawl(start_url)
    if result:
        return result

    print("Scrapy failed, trying Playwright...")
    result = _playwright_fetch(SITE_URLS)
    if result:
        return result

    print("Playwright failed, using requests+BeautifulSoup...")
    return _requests_fetch(SITE_URLS)


# ── METHOD 1: Scrapy ──────────────────────────────────────────────────────────

def _scrapy_crawl(start_url):
    try:
        import scrapy
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.log import configure_logging

        # Use a fixed path with forward slashes — Windows-safe for Scrapy
        output_file = os.path.join(tempfile.gettempdir(), "nambi_scrapy_out.json")
        output_file_uri = output_file.replace("\\", "/")

        # Remove stale output file
        if os.path.exists(output_file):
            os.unlink(output_file)

        configure_logging(install_root_handler=False)
        domain = urlparse(start_url).netloc

        class FullSiteSpider(scrapy.Spider):
            name = "fullsite"
            start_urls = [start_url]
            allowed_domains = [domain]
            custom_settings = {
                "FEEDS": {output_file_uri: {"format": "json", "overwrite": True}},
                "LOG_ENABLED": False,
                "ROBOTSTXT_OBEY": True,
                "CONCURRENT_REQUESTS": 8,
                "DOWNLOAD_DELAY": 0.3,
                "DEPTH_LIMIT": 4,
                "CLOSESPIDER_PAGECOUNT": 150,
                "USER_AGENT": "Mozilla/5.0 (compatible; NambiBot/1.0)",
                "HTTPERROR_ALLOW_ALL": True,
            }

            def parse(self, response):
                text = " ".join(response.css(
                    "p::text, h1::text, h2::text, h3::text, h4::text, "
                    "li::text, td::text, th::text, span::text, a::text"
                ).getall()).strip()

                if text and len(text) > 50:
                    yield {"url": response.url, "text": text}

                for link in response.css("a::attr(href)").getall():
                    yield response.follow(link, self.parse)

        process = CrawlerProcess()
        process.crawl(FullSiteSpider)
        process.start()

        if not os.path.exists(output_file):
            print("Scrapy: output file not created")
            return None

        with open(output_file, "r", encoding="utf-8") as f:
            pages = json.load(f)

        os.unlink(output_file)

        if not pages:
            print("Scrapy: crawled but extracted no text")
            return None

        all_text = []
        for page in pages:
            all_text.append(f"\n--- CONTENT FROM {page['url']} ---\n")
            all_text.append(page.get("text", ""))

        result = "\n".join(all_text)
        print(f"Scrapy crawl complete: {len(pages)} pages, {len(result):,} chars")
        return result

    except Exception as e:
        print(f"Scrapy error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ── METHOD 2: Playwright ──────────────────────────────────────────────────────

def _playwright_fetch(urls):
    """Run Playwright in a separate thread with ProactorEventLoop (Windows-safe)."""
    import concurrent.futures

    def run():
        import asyncio
        # ProactorEventLoop is required on Windows for subprocess (Playwright)
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_playwright_async(urls))
        finally:
            loop.close()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(run).result(timeout=300)  # 5 min for all URLs
        return result
    except Exception as e:
        print(f"Playwright thread error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def _playwright_async(urls):
    """Async Playwright fetch — runs inside ProactorEventLoop thread."""
    try:
        from playwright.async_api import async_playwright
        all_text = []

        async with async_playwright() as p:
            for url in urls:
                # Launch a fresh browser per URL — avoids crash cascade
                browser = None
                try:
                    print(f"Playwright fetching: {url}")
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-dev-shm-usage",
                              "--disable-gpu", "--disable-extensions"]
                    )
                    page = await browser.new_page()
                    # domcontentloaded is faster than networkidle for JS sites
                    await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    # Give JS a moment to render
                    await page.wait_for_timeout(3000)
                    content = await page.inner_text("body")
                    await browser.close()

                    if content and len(content) > 100:
                        all_text.append(f"\n--- CONTENT FROM {url} ---\n")
                        all_text.append(content)
                        print(f"  Got {len(content):,} chars")
                    else:
                        print(f"  Got {len(content) if content else 0} chars (skipped)")

                except Exception as e:
                    print(f"Playwright failed for {url}: {e}")
                    if browser:
                        try:
                            await browser.close()
                        except Exception:
                            pass

        if not all_text:
            return None

        result = "\n".join(all_text)
        print(f"Playwright complete: {len(urls)} URLs, {len(result):,} chars")
        return result

    except Exception as e:
        print(f"Playwright async error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ── METHOD 3: Requests + BeautifulSoup (always works) ────────────────────────

def _requests_fetch(urls):
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Mozilla/5.0 (compatible; NambiBot/1.0)"}
        all_text = []

        for url in urls:
            try:
                print(f"Requests fetching: {url}")
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Remove scripts and styles
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()

                text = soup.get_text(separator=" ", strip=True)
                if text:
                    all_text.append(f"\n--- CONTENT FROM {url} ---\n")
                    all_text.append(text)
                    print(f"  Got {len(text):,} chars")
            except Exception as e:
                print(f"Requests failed for {url}: {e}")

        result = "\n".join(all_text)
        print(f"Requests complete: {len(result):,} chars total")
        return result

    except Exception as e:
        print(f"Requests+BS4 error: {e}")
        return ""


# ── Legacy helpers (kept for compatibility) ───────────────────────────────────

def fetch_page(url):
    return _requests_fetch([url])


def fetch_multiple_pages(urls):
    return _requests_fetch(urls)
