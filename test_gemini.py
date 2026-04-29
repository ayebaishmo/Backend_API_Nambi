"""Quick test to verify Gemini API key works."""
from dotenv import load_dotenv
load_dotenv()

from google import genai
import os

api_key = os.environ.get("GEMINI_API_KEY")
print(f"Testing key: {api_key[:20]}...")

client = genai.Client(api_key=api_key)

for model in ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.0-flash-lite"]:
    try:
        response = client.models.generate_content(
            model=model,
            contents="Say hello in one sentence."
        )
        print(f"✓ {model} WORKS: {response.text.strip()[:80]}")
        break
    except Exception as e:
        print(f"✗ {model} FAILED: {str(e)[:120]}")
