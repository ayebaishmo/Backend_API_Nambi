import os
from google import genai
from google.genai import types

def get_gemini_model():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment variables")
    return _GeminiWrapper(api_key)


class _GeminiWrapper:
    """Thin wrapper so existing code calling model.generate_content(prompt) keeps working."""
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def generate_content(self, prompt):
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return _ResponseWrapper(response.text)


class _ResponseWrapper:
    """Mimics the old GenerativeModel response so response.text still works."""
    def __init__(self, text):
        self.text = text
