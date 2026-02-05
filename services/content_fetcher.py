from playwright.sync_api import sync_playwright


def fetch_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle")
        content = page.inner_text("body")
        browser.close()
        return content

def fetch_multiple_pages(urls):
    all_text = []

    for url in urls:
        try:
            print(f"fetching: {url}")
            page_text = fetch_page(url)
            all_text.append(f"\n--- CONTENT FROM {url} ---\n")
            all_text.append(page_text)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    return "\n".join(all_text)
