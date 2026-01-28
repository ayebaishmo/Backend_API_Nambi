import requests
from bs4 import BeatifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CompanyChatbot/1.0)"
}

def extract_visible_text(html: str) -> str:
    soup = BeatifulSoup(html, "html.parser")

    # Remove scripts 
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompse()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

