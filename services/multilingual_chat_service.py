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
        Process user message with translation support.
        Always re-detects language so switching mid-conversation works instantly.
        """
        conversation = Conversation.query.filter_by(session_id=session_id).first()

        greeting_map = {
            'mambo': 'sw', 'habari': 'sw', 'jambo': 'sw',
            'bonjour': 'fr', 'salut': 'fr',
            'hola': 'es', 'buenos dias': 'es',
            'hallo': 'de', 'guten tag': 'de',
            'ciao': 'it', 'buongiorno': 'it',
            'olá': 'pt',
            'привет': 'ru',
            '你好': 'zh-cn',
            'مرحبا': 'ar'
        }

        message_lower = user_message.lower().strip()
        detected_lang = None

        print(f"DEBUG: Checking greeting for: '{message_lower}'")

        for greeting, lang in greeting_map.items():
            if message_lower == greeting or message_lower.startswith(greeting + ' '):
                detected_lang = lang
                print(f"DEBUG: Matched greeting '{greeting}' → language '{lang}'")
                break

        if not detected_lang:
            print(f"DEBUG: No greeting match, using translation service")
            detected_lang = translation_service.detect_language(user_message)
            print(f"DEBUG: Translation service detected: '{detected_lang}'")

        # Always update the session language to whatever is detected NOW
        # This allows instant language switching mid-conversation
        user_lang = detected_lang
        print(f"DEBUG: Setting language to: {user_lang}")

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

        if user_lang != 'en':
            english_message = translation_service.translate_to_english(
                user_message, source_lang=user_lang
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
        """
        conversation = Conversation.query.filter_by(session_id=session_id).first()
        
        if conversation and conversation.language:
            user_lang = conversation.language
        else:
            user_lang = 'en'
        
        if user_lang != 'en':
            translated_response = translation_service.translate_from_english(
                ai_response_english, target_lang=user_lang
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
        """Get brief, charming welcome message in user's language"""
        welcome_messages = {
            'en':    "Hey there! I'm Nambi, your Virtual Travel Assistant for Everything Uganda — your gateway to the Pearl of Africa. Ready to discover Uganda?",
            'sw':    "Habari! Mimi ni Nambi, Msaidizi wako wa Usafiri wa Everything Uganda — lango lako la Lulu ya Afrika. Uko tayari kugundua Uganda?",
            'fr':    "Bonjour! Je suis Nambi, votre Assistante de Voyage pour Everything Uganda — votre porte vers la Perle de l'Afrique. Prêt à découvrir l'Ouganda?",
            'de':    "Hallo! Ich bin Nambi, Ihre Reiseassistentin für Everything Uganda — Ihr Tor zur Perle Afrikas. Bereit, Uganda zu entdecken?",
            'es':    "¡Hola! Soy Nambi, tu Asistente de Viajes para Everything Uganda — tu puerta hacia la Perla de África. ¿Listo para descubrir Uganda?",
            'pt':    "Olá! Sou Nambi, sua Assistente de Viagens para Everything Uganda — sua porta para a Pérola de África. Pronto para descobrir Uganda?",
            'ar':    "مرحبا! أنا نامبي، مساعدتك للسفر في Everything Uganda — بوابتك إلى جوهرة أفريقيا. هل أنت مستعد لاكتشاف أوغندا؟",
            'zh-cn': "你好！我是Nambi，您的Everything Uganda旅行助手——您通往非洲明珠的大门。准备好探索乌干达了吗？",
            'it':    "Ciao! Sono Nambi, la tua Assistente di Viaggio per Everything Uganda — il tuo portale verso la Perla d'Africa. Pronto a scoprire l'Uganda?",
            'ru':    "Привет! Я Намби, ваш помощник по путешествиям для Everything Uganda — ваши ворота в Жемчужину Африки. Готовы открыть Уганду?",
            'ko':    "안녕하세요! 저는 Nambi, Everything Uganda의 여행 도우미입니다 — 아프리카의 진주로 가는 관문. 우간다를 탐험할 준비됐나요?",
            'ja':    "こんにちは！私はNambi、Everything Ugandaの旅行アシスタントです — アフリカの真珠への入り口。ウガンダを探検する準備はできていますか？",
            'hi':    "नमस्ते! मैं Nambi हूं, Everything Uganda की आपकी Virtual Travel Assistant — अफ्रीका के मोती का आपका प्रवेश द्वार। युगांडा खोजने के लिए तैयार हैं?",
        }
        return welcome_messages.get(language, welcome_messages['en'])
