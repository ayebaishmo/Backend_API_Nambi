"""
Translation Service for Multilingual Support
Uses Google Translate API for translation
"""

from googletrans import Translator, LANGUAGES
import os
from functools import lru_cache

class TranslationService:
    """Handle translation between languages"""
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'fr': 'French',
        'de': 'German',
        'es': 'Spanish',
        'sw': 'Swahili',
        'zh-cn': 'Chinese (Simplified)',
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
    
    def __init__(self):
        self.translator = Translator()
    
    def detect_language(self, text):
        """
        Detect the language of the text
        
        Args:
            text: Text to detect language from
            
        Returns:
            Language code (e.g., 'en', 'fr', 'sw')
        """
        try:
            # Add timeout to prevent hanging
            from googletrans import Translator
            translator = Translator()
            
            detection = translator.detect(text)
            detected_lang = detection.lang
            
            # If detected language is supported, return it
            if detected_lang in self.SUPPORTED_LANGUAGES:
                return detected_lang
            
            # Default to English if not supported
            return 'en'
            
        except Exception as e:
            print(f"Language detection error: {str(e)}")
            return 'en'  # Default to English
    
    def translate(self, text, target_lang='en', source_lang='auto'):
        """
        Translate text to target language
        
        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'fr', 'sw')
            source_lang: Source language code ('auto' for auto-detect)
            
        Returns:
            Translated text
        """
        try:
            # Don't translate if target is English and source is auto/English
            if target_lang == 'en' and source_lang in ['auto', 'en']:
                return text
            
            # Create new translator instance to avoid timeout
            from googletrans import Translator
            translator = Translator()
            
            # Translate
            translation = translator.translate(
                text,
                dest=target_lang,
                src=source_lang
            )
            
            return translation.text
            
        except Exception as e:
            print(f"Translation error: {str(e)}")
            # Return original text if translation fails
            return text
    
    def translate_to_english(self, text, source_lang='auto'):
        """
        Translate text to English (for AI processing)
        
        Args:
            text: Text to translate
            source_lang: Source language code ('auto' for auto-detect)
            
        Returns:
            English translation
        """
        return self.translate(text, target_lang='en', source_lang=source_lang)
    
    def translate_from_english(self, text, target_lang):
        """
        Translate English text to target language (for user response)
        
        Args:
            text: English text to translate
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        if target_lang == 'en':
            return text
        
        return self.translate(text, target_lang=target_lang, source_lang='en')
    
    @staticmethod
    def get_supported_languages():
        """Get list of supported languages"""
        return TranslationService.SUPPORTED_LANGUAGES
    
    @staticmethod
    def is_language_supported(lang_code):
        """Check if language is supported"""
        return lang_code in TranslationService.SUPPORTED_LANGUAGES
    
    def get_language_name(self, lang_code):
        """Get language name from code"""
        return self.SUPPORTED_LANGUAGES.get(lang_code, 'Unknown')


# Singleton instance
_translation_service = None

def get_translation_service():
    """Get or create translation service instance"""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service
