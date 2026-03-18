"""
Multilingual Chat Service
Handles translation in chat conversations
"""

from services.translation_service import get_translation_service
from models.conversation import Conversation
from extensions import db

translation_service = get_translation_service()


class MultilingualChatService:
    """Service for handling multilingual chat"""
    
    @staticmethod
    def process_user_message(session_id, user_message):
        """
        Process user message with translation support
        
        Args:
            session_id: User's session ID
            user_message: User's message in their language
            
        Returns:
            dict with:
                - original_message: User's original message
                - english_message: Translated to English (for AI)
                - detected_language: Detected language code
                - user_language: User's preferred language
        """
        # Get or create conversation
        conversation = Conversation.query.filter_by(session_id=session_id).first()
        
        # Check for common greetings to improve detection
        greeting_map = {
            'mambo': 'sw',
            'habari': 'sw',
            'jambo': 'sw',
            'bonjour': 'fr',
            'salut': 'fr',
            'hola': 'es',
            'buenos dias': 'es',
            'hallo': 'de',
            'guten tag': 'de',
            'ciao': 'it',
            'buongiorno': 'it',
            'olá': 'pt',
            'привет': 'ru',
            '你好': 'zh-cn',
            'مرحبا': 'ar'
        }
        
        # Check if message matches a known greeting
        message_lower = user_message.lower().strip()
        detected_lang = None
        
        print(f"DEBUG: Checking greeting for: '{message_lower}'")
        
        for greeting, lang in greeting_map.items():
            if message_lower == greeting or message_lower.startswith(greeting + ' '):
                detected_lang = lang
                print(f"DEBUG: Matched greeting '{greeting}' → language '{lang}'")
                break
        
        # If not a known greeting, use translation service
        if not detected_lang:
            print(f"DEBUG: No greeting match, using translation service")
            detected_lang = translation_service.detect_language(user_message)
            print(f"DEBUG: Translation service detected: '{detected_lang}'")
        
        # Determine user's language
        if conversation and conversation.language and conversation.language != 'en':
            # Use existing language preference (but only if it's not default English)
            user_lang = conversation.language
            print(f"DEBUG: Using existing language preference: {user_lang}")
        else:
            # First message OR default English - use detected language
            user_lang = detected_lang
            print(f"DEBUG: Setting new language: {user_lang}")
            
            # Create or update conversation with detected language
            if not conversation:
                conversation = Conversation(session_id=session_id, language=user_lang)
                db.session.add(conversation)
            else:
                conversation.language = user_lang
            
            try:
                db.session.commit()
            except Exception as e:
                print(f"Error saving language preference: {e}")
                db.session.rollback()
        
        # Translate to English for AI processing
        if user_lang != 'en':
            english_message = translation_service.translate_to_english(
                user_message,
                source_lang=user_lang
            )
        else:
            english_message = user_message
        
        return {
            'original_message': user_message,
            'english_message': english_message,
            'detected_language': detected_lang,
            'user_language': user_lang
        }
    
    @staticmethod
    def process_ai_response(session_id, ai_response_english):
        """
        Process AI response with translation support
        
        Args:
            session_id: User's session ID
            ai_response_english: AI response in English
            
        Returns:
            dict with:
                - english_response: Original English response
                - translated_response: Translated to user's language
                - user_language: User's preferred language
        """
        # Get conversation to find user's language
        conversation = Conversation.query.filter_by(session_id=session_id).first()
        
        if conversation and conversation.language:
            user_lang = conversation.language
        else:
            user_lang = 'en'  # Default to English
        
        # Translate response to user's language
        if user_lang != 'en':
            translated_response = translation_service.translate_from_english(
                ai_response_english,
                target_lang=user_lang
            )
        else:
            translated_response = ai_response_english
        
        return {
            'english_response': ai_response_english,
            'translated_response': translated_response,
            'user_language': user_lang
        }
    
    @staticmethod
    def get_welcome_message(language='en'):
        """
        Get welcome message in user's language
        
        Args:
            language: Language code
            
        Returns:
            Welcome message in specified language
        """
        welcome_messages = {
            'en': "Hello! I'm Nambi, your Virtual Travel Assistant for Everything Uganda. I'm here to help you discover the Pearl of Africa through curated travel experiences, cultural insights, and essential services.",
            'fr': "Bonjour! Je suis Nambi, votre Assistante Virtuelle de Voyage pour Everything Uganda. Je suis là pour vous aider à découvrir la Perle de l'Afrique.",
            'de': "Hallo! Ich bin Nambi, Ihre virtuelle Reiseassistentin für Everything Uganda. Ich bin hier, um Ihnen zu helfen, die Perle Afrikas zu entdecken.",
            'es': "¡Hola! Soy Nambi, tu Asistente Virtual de Viajes para Everything Uganda. Estoy aquí para ayudarte a descubrir la Perla de África.",
            'sw': "Habari! Mimi ni Nambi, Msaidizi wako wa Usafiri wa Mtandao wa Everything Uganda. Niko hapa kukusaidia kugundua Lulu ya Afrika.",
            'zh-cn': "你好！我是Nambi，您的Everything Uganda虚拟旅行助手。我在这里帮助您发现非洲明珠。",
            'ar': "مرحبا! أنا نامبي، مساعدتك الافتراضية للسفر لـ Everything Uganda. أنا هنا لمساعدتك في اكتشاف لؤلؤة أفريقيا.",
            'pt': "Olá! Sou Nambi, sua Assistente Virtual de Viagens para Everything Uganda. Estou aqui para ajudá-lo a descobrir a Pérola da África.",
            'it': "Ciao! Sono Nambi, la tua Assistente Virtuale di Viaggio per Everything Uganda. Sono qui per aiutarti a scoprire la Perla d'Africa.",
            'ru': "Здравствуйте! Я Намби, ваш виртуальный помощник по путешествиям для Everything Uganda. Я здесь, чтобы помочь вам открыть Жемчужину Африки.",
            'ko': "안녕하세요! 저는 Nambi입니다, Everything Uganda의 가상 여행 도우미입니다. 아프리카의 진주를 발견하도록 도와드리겠습니다.",
            'ja': "こんにちは！私はNambi、Everything Ugandaのバーチャル旅行アシスタントです。アフリカの真珠を発見するお手伝いをします。"
        }
        
        return welcome_messages.get(language, welcome_messages['en'])
