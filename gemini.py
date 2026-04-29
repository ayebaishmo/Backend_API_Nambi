import os
from google import genai
from logger import get_logger

log = get_logger("gemini")

_client = None
_model_name = "gemini-2.5-flash"  # confirmed working on this key

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=api_key)
        log.info(f"Gemini client ready — model: {_model_name}")
    return _client

try:
    _get_client()
except Exception as e:
    log.warning(f"Gemini pre-warm failed: {e}")

def get_gemini_model():
    return _GeminiWrapper()

class _GeminiWrapper:
    def generate_content(self, prompt):
        client = _get_client()
        # Try primary model, fall back to gemini-2.5-flash if needed
        for model in [_model_name, "gemini-2.5-flash", "gemini-2.0-flash-lite"]:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return _ResponseWrapper(response.text)
            except Exception as e:
                err = str(e)
                if '429' in err or 'RESOURCE_EXHAUSTED' in err:
                    raise  # Let caller handle rate limits
                log.warning(f"Model {model} failed: {err}, trying next...")
                continue
        raise RuntimeError("All Gemini models failed")

class _ResponseWrapper:
    def __init__(self, text):
        self.text = text
