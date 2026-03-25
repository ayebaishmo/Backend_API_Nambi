"""
Translation Service for Multilingual Support
Uses deep-translator (no httpx conflict, reliable, free)
"""

from deep_translator import GoogleTranslator, single_detection
import os


class TranslationService:
    """Handle translation between languages"""

    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'fr': 'French',
        'de': 'German',
        'es': 'Spanish',
        'sw': 'Swahili',
        'zh-CN': 'Chinese (Simplified)',
        'zh': 'Chinese',
        'ar': 'Arabic',
        'pt': 'Portuguese',
        'it': 'Italian',
        'ru': 'Russian',
        'ko': 'Korean',
        'ja': 'Japanese',
        'hi': 'Hindi',
        'id': 'Indonesian',
        'th': 'Thai',
        'vi': 'Vietnamese',
        'tr': 'Turkish',
        'pl': 'Polish',
        'nl': 'Dutch'
    }

    # deep-translator uses 'zh-CN' but we store 'zh-cn' — normalise on the way in
    _LANG_NORMALISE = {
        'zh-cn': 'zh-CN',
        'zh': 'zh-CN',
    }

    def _norm(self, lang):
        return self._LANG_NORMALISE.get(lang, lang)

    def detect_language(self, text):
        if not text or not text.strip():
            return 'en'
        try:
            # deep-translator single_detection needs a googletrans-compatible API key
            # Fall back to GoogleTranslator detect trick
            detected = GoogleTranslator(source='auto', target='en').translate(text)
            # We can't get the source lang directly from translate, so use a workaround
            from deep_translator import GoogleTranslator as GT
            t = GT(source='auto', target='en')
            t.translate(text[:100])
            lang = t.source  # after translate, .source is updated to detected lang
            lang = lang.lower()
            if lang in self.SUPPORTED_LANGUAGES:
                return lang
            # normalise zh-CN → zh-cn for internal use
            if lang == 'zh-cn':
                return 'zh-cn'
            return 'en'
        except Exception as e:
            print(f"Language detection error: {e}")
            return 'en'

    def translate(self, text, target_lang='en', source_lang='auto'):
        if not text or not text.strip():
            return text
        try:
            if target_lang == 'en' and source_lang in ('auto', 'en'):
                return text

            src = 'auto' if source_lang == 'auto' else self._norm(source_lang)
            tgt = self._norm(target_lang)

            translated = GoogleTranslator(source=src, target=tgt).translate(text)
            return translated or text
        except Exception as e:
            print(f"Translation error ({source_lang}→{target_lang}): {e}")
            return text

    def translate_to_english(self, text, source_lang='auto'):
        return self.translate(text, target_lang='en', source_lang=source_lang)

    def translate_from_english(self, text, target_lang):
        if target_lang == 'en':
            return text
        return self.translate(text, target_lang=target_lang, source_lang='en')

    @staticmethod
    def get_supported_languages():
        return TranslationService.SUPPORTED_LANGUAGES

    @staticmethod
    def is_language_supported(lang_code):
        return lang_code in TranslationService.SUPPORTED_LANGUAGES

    def get_language_name(self, lang_code):
        return self.SUPPORTED_LANGUAGES.get(lang_code, 'Unknown')


# Singleton
_translation_service = None

def get_translation_service():
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
