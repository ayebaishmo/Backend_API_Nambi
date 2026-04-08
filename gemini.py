import os
from google import genai

# Cached client — created once at import time
_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment variables")
        _client = genai.Client(api_key=api_key)
        print("Gemini client initialised")
    return _client

# Pre-warm on import so first request has zero init overhead
try:
    _get_client()
except Exception:
    pass  # Will retry on first request

def get_gemini_model():
    return _GeminiWrapper()

class _GeminiWrapper:
    def generate_content(self, prompt):
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return _ResponseWrapper(response.text)

class _ResponseWrapper:
    def __init__(self, text):
        self.text = text
