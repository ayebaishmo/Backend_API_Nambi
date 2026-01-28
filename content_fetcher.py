import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CompanyChatbot/1.0)"
}

def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts 
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompse()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return extract_visible_text(response.text)

def fetch_multiple_pages(urls: list[str]) -> str:
    all_text = []

    for url in urls:
        try:
            print(f"fetching: {url}")
            page_text = fetch_page(url)
            all_text.append(f"\n---CONTENT FROM {url} ---\n")
            all_text.append(page_text)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    return "\n".join(all_text)