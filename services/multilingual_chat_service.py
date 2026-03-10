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
            'en': "Hello! I'm Nambi, your Virtual Consultant for Everything Uganda. I'm here to help you discover the Pearl of Africa through curated travel experiences, cultural insights, and essential services.",
            'fr': "Bonjour! Je suis Nambi, votre consultant virtuel pour Everything Uganda. Je suis là pour vous aider à découvrir la Perle de l'Afrique à travers des expériences de voyage organisées, des aperçus culturels et des services essentiels.",
            'de': "Hallo! Ich bin Nambi, Ihr virtueller Berater für Everything Uganda. Ich bin hier, um Ihnen zu helfen, die Perle Afrikas durch kuratierte Reiseerlebnisse, kulturelle Einblicke und wesentliche Dienstleistungen zu entdecken.",
            'es': "¡Hola! Soy Nambi, tu consultor virtual para Everything Uganda. Estoy aquí para ayudarte a descubrir la Perla de África a través de experiencias de viaje seleccionadas, conocimientos culturales y servicios esenciales.",
            'sw': "Habari! Mimi ni Nambi, mshauri wako wa mtandao wa Everything Uganda. Niko hapa kukusaidia kugundua Lulu ya Afrika kupitia uzoefu wa usafiri uliochaguliwa, maarifa ya kitamaduni, na huduma muhimu.",
            'zh-cn': "你好！我是Nambi，您的Everything Uganda虚拟顾问。我在这里帮助您通过精选的旅行体验、文化见解和基本服务发现非洲明珠。",
            'ar': "مرحبا! أنا نامبي، مستشارك الافتراضي لـ Everything Uganda. أنا هنا لمساعدتك في اكتشاف لؤلؤة أفريقيا من خلال تجارب السفر المنسقة والرؤى الثقافية والخدمات الأساسية.",
            'pt': "Olá! Sou Nambi, seu consultor virtual para Everything Uganda. Estou aqui para ajudá-lo a descobrir a Pérola da África através de experiências de viagem selecionadas, insights culturais e serviços essenciais.",
            'it': "Ciao! Sono Nambi, il tuo consulente virtuale per Everything Uganda. Sono qui per aiutarti a scoprire la Perla d'Africa attraverso esperienze di viaggio curate, approfondimenti culturali e servizi essenziali.",
            'ru': "Здравствуйте! Я Намби, ваш виртуальный консультант по Everything Uganda. Я здесь, чтобы помочь вам открыть для себя Жемчужину Африки через тщательно подобранные туристические впечатления, культурные идеи и основные услуги."
        }
        
        return welcome_messages.get(language, welcome_messages['en'])
