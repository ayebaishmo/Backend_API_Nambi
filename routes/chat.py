from flask import Blueprint, request, jsonify
from gemini import get_gemini_model
from services.content_fetcher import fetch_full_site
from services.session_manager import SessionManager
from services.cache_manager import CacheManager, cached
from services.multilingual_chat_service import MultilingualChatService
from middleware.rate_limit import rate_limit
from extensions import db
from models.conversation import Conversation
from models.message import Message
from models.feedback import Feedback
import threading

chat_bp = Blueprint("chat", __name__)

# Global variable to store site content
_site_content = None
_content_loaded = False
_loading_lock = threading.Lock()



def load_site_content():
    """Load site content at startup"""
    global _site_content, _content_loaded
    
    with _loading_lock:
        if _content_loaded:
            return _site_content
            
        try:
            _site_content = fetch_full_site("https://www.everythinguganda.com/")
            _content_loaded = True
        except Exception as e:
            print(f"ERROR: Failed to fetch site content - {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            _site_content = ""
            _content_loaded = True
    
    return _site_content

def get_site_content():
    """Get cached site content"""
    global _site_content, _content_loaded
    if not _content_loaded:
        return load_site_content()
    return _site_content if _site_content else ""

@chat_bp.route("/chat", methods=["POST", "OPTIONS"])
@rate_limit
def chat():
    """
    Chat with Nambi (Everything Uganda Virtual Consultant)
    ---
    tags:
      - Chatbot
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            question:
              type: string
              example: "Tell me about Kampala"
            session_id:
              type: string
              example: "abc123"
    responses:
      200:
        description: Bot response
      500:
        description: Server error
    """
    # Handle OPTIONS request for CORS
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request body"}), 400
        
        question = data.get("question", "").strip()
        session_id = data.get("session_id")
        is_first_message = data.get("is_first_message", False)
        
        # Process message with translation support
        translation_result = MultilingualChatService.process_user_message(session_id, question)
        user_language = translation_result['user_language']
        english_question = translation_result['english_message']
        
        print(f"User language: {user_language}, Original: '{question}', English: '{english_question}'")

        # Multilingual static responses
        _suggested_questions = {
            'en': ["What are the top tourist destinations in Uganda?", "Tell me about accommodation options", "What cultural experiences are available?"],
            'sw': ["Ni vivutio gani vya utalii nchini Uganda?", "Niambie kuhusu malazi", "Ni uzoefu gani wa kitamaduni unapatikana?"],
            'fr': ["Quelles sont les meilleures destinations en Ouganda?", "Parlez-moi des options d'hébergement", "Quelles expériences culturelles sont disponibles?"],
            'de': ["Was sind die besten Reiseziele in Uganda?", "Erzähl mir von Unterkunftsmöglichkeiten", "Welche kulturellen Erlebnisse gibt es?"],
            'es': ["¿Cuáles son los mejores destinos turísticos en Uganda?", "Háblame de las opciones de alojamiento", "¿Qué experiencias culturales están disponibles?"],
            'pt': ["Quais são os melhores destinos turísticos em Uganda?", "Fale-me sobre opções de acomodação", "Que experiências culturais estão disponíveis?"],
            'ar': ["ما هي أفضل الوجهات السياحية في أوغندا؟", "أخبرني عن خيارات الإقامة", "ما هي التجارب الثقافية المتاحة؟"],
            'it': ["Quali sono le migliori destinazioni turistiche in Uganda?", "Parlami delle opzioni di alloggio", "Quali esperienze culturali sono disponibili?"],
            'ru': ["Каковы лучшие туристические направления в Уганде?", "Расскажи мне о вариантах проживания", "Какие культурные мероприятия доступны?"],
            'ko': ["우간다의 최고 관광지는 어디인가요?", "숙박 옵션에 대해 알려주세요", "어떤 문화 체험이 가능한가요?"],
            'ja': ["ウガンダのトップ観光地はどこですか？", "宿泊オプションについて教えてください", "どんな文化体験ができますか？"],
            'zh': ["乌干达最好的旅游目的地是哪里？", "告诉我住宿选择", "有哪些文化体验？"],
            'zh-cn': ["乌干达最好的旅游目的地是哪里？", "告诉我住宿选择", "有哪些文化体验？"],
            'hi': ["युगांडा में शीर्ष पर्यटन स्थल कौन से हैं?", "आवास विकल्पों के बारे में बताएं", "कौन से सांस्कृतिक अनुभव उपलब्ध हैं?"],
        }

        _booking_answers = {
            'en': "Wonderful! To book your Uganda experience, please visit https://www.everythinguganda.com/holiday-booking or contact us directly. Our team will craft the perfect trip for you.",
            'sw': "Vizuri sana! Ili kuhifadhi uzoefu wako wa Uganda, tafadhali tembelea https://www.everythinguganda.com/holiday-booking au wasiliana nasi moja kwa moja. Timu yetu itakutengenezea safari nzuri.",
            'fr': "Parfait! Pour réserver votre expérience en Ouganda, visitez https://www.everythinguganda.com/holiday-booking ou contactez-nous directement. Notre équipe créera le voyage parfait pour vous.",
            'de': "Wunderbar! Um Ihr Uganda-Erlebnis zu buchen, besuchen Sie https://www.everythinguganda.com/holiday-booking oder kontaktieren Sie uns direkt. Unser Team plant die perfekte Reise für Sie.",
            'es': "¡Maravilloso! Para reservar tu experiencia en Uganda, visita https://www.everythinguganda.com/holiday-booking o contáctanos directamente. Nuestro equipo creará el viaje perfecto para ti.",
            'pt': "Maravilhoso! Para reservar sua experiência em Uganda, visite https://www.everythinguganda.com/holiday-booking ou entre em contato conosco diretamente.",
            'ar': "رائع! لحجز تجربتك في أوغندا، يرجى زيارة https://www.everythinguganda.com/holiday-booking أو التواصل معنا مباشرة.",
            'it': "Meraviglioso! Per prenotare la tua esperienza in Uganda, visita https://www.everythinguganda.com/holiday-booking o contattaci direttamente.",
            'ru': "Замечательно! Чтобы забронировать ваш опыт в Уганде, посетите https://www.everythinguganda.com/holiday-booking или свяжитесь с нами напрямую.",
            'ko': "훌륭합니다! 우간다 여행을 예약하려면 https://www.everythinguganda.com/holiday-booking 을 방문하거나 직접 문의하세요.",
            'ja': "素晴らしい！ウガンダ体験を予約するには、https://www.everythinguganda.com/holiday-booking をご覧いただくか、直接お問い合わせください。",
            'zh': "太好了！要预订您的乌干达体验，请访问 https://www.everythinguganda.com/holiday-booking 或直接联系我们。",
            'zh-cn': "太好了！要预订您的乌干达体验，请访问 https://www.everythinguganda.com/holiday-booking 或直接联系我们。",
            'hi': "बहुत अच्छा! अपना युगांडा अनुभव बुक करने के लिए, कृपया https://www.everythinguganda.com/holiday-booking पर जाएं या हमसे सीधे संपर्क करें।",
        }

        _booking_questions = {
            'en': ["What destinations can I visit?", "Tell me about accommodation options", "What activities are available?"],
            'sw': ["Ni maeneo gani ninaweza kutembelea?", "Niambie kuhusu malazi", "Ni shughuli gani zinapatikana?"],
            'fr': ["Quelles destinations puis-je visiter?", "Parlez-moi des options d'hébergement", "Quelles activités sont disponibles?"],
            'de': ["Welche Reiseziele kann ich besuchen?", "Erzähl mir von Unterkunftsmöglichkeiten", "Welche Aktivitäten gibt es?"],
            'es': ["¿Qué destinos puedo visitar?", "Háblame de las opciones de alojamiento", "¿Qué actividades están disponibles?"],
            'pt': ["Que destinos posso visitar?", "Fale-me sobre opções de acomodação", "Que atividades estão disponíveis?"],
            'ar': ["ما هي الوجهات التي يمكنني زيارتها؟", "أخبرني عن خيارات الإقامة", "ما هي الأنشطة المتاحة؟"],
            'it': ["Quali destinazioni posso visitare?", "Parlami delle opzioni di alloggio", "Quali attività sono disponibili?"],
            'ru': ["Какие направления я могу посетить?", "Расскажи о вариантах проживания", "Какие мероприятия доступны?"],
            'ko': ["어떤 목적지를 방문할 수 있나요?", "숙박 옵션에 대해 알려주세요", "어떤 활동이 가능한가요?"],
            'ja': ["どんな目的地を訪れることができますか？", "宿泊オプションについて教えてください", "どんなアクティビティがありますか？"],
            'zh': ["我可以参观哪些目的地？", "告诉我住宿选择", "有哪些活动？"],
            'zh-cn': ["我可以参观哪些目的地？", "告诉我住宿选择", "有哪些活动？"],
            'hi': ["मैं कौन से गंतव्य देख सकता हूं?", "आवास विकल्पों के बारे में बताएं", "कौन सी गतिविधियां उपलब्ध हैं?"],
        }

        def get_lang_response(mapping, lang):
            return mapping.get(lang, mapping['en'])

        # Handle initial greeting (check both original and translated)
        simple_greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings",
                           "habari", "jambo", "mambo", "bonjour", "hola", "hallo", "ciao", "olá", "привет", "你好", "مرحبا"]

        is_greeting = (not english_question or
                      english_question.lower().strip() in simple_greetings or
                      question.lower().strip() in simple_greetings)

        if is_greeting:
            welcome_message = MultilingualChatService.get_welcome_message(user_language)
            return jsonify({
                "answer": welcome_message,
                "suggested_questions": get_lang_response(_suggested_questions, user_language),
                "action_buttons": [],
                "booking_buttons": [],
                "show_booking_prompt": False,
                "images": [],
                "quick_replies": []
            })

        # Handle booking intent
        booking_keywords = ["yes please", "yes", "book", "booking", "reserve", "reservation", "i want to book", "how do i book", "book now",
                            "hifadhi", "weka", "ninataka kuhifadhi", "réserver", "reservar", "buchen", "prenotare"]
        if any(keyword in question.lower() for keyword in booking_keywords):
            return jsonify({
                "answer": get_lang_response(_booking_answers, user_language),
                "suggested_questions": get_lang_response(_booking_questions, user_language),
                "action_buttons": [],
                "booking_buttons": [],
                "show_booking_prompt": True,
                "images": [],
                "quick_replies": []
            })

        # Get Gemini model
        model = get_gemini_model()

        # Load site content (from URLs or fallback to file)
        site_content = get_site_content()
        
        # Debug: Check if content is loaded
        if not site_content or len(site_content) < 100:
            print(f"WARNING: Site content is empty or too short. Length: {len(site_content) if site_content else 0}")
        else:
            print(f"Site content loaded successfully. Length: {len(site_content)} characters")
            # Check if accommodation info is in content
            if "accommodation" in site_content.lower() or "where to stay" in site_content.lower():
                print("✓ Accommodation content found in site_content")
            else:
                print("✗ Accommodation content NOT found in site_content")
        
        # If site content is empty, try loading from file
        if not site_content:
            try:
                with open("company_content.txt", "r", encoding="utf-8") as f:
                    site_content = f.read()
                    print(f"Loaded content from file. Length: {len(site_content)}")
            except FileNotFoundError:
                return jsonify({
                    "error": "Content not available. Please try again later."
                }), 503

        # System prompt - more natural and conversational
        system_prompt = f"""You are Nambi, Virtual Travel Assistant for Everything Uganda. You are warm, charming, and knowledgeable.

LANGUAGE RULE — THIS IS THE MOST IMPORTANT RULE:
The user is communicating in: {user_language}
You MUST respond in that exact language. If the user writes in Swahili, respond fully in Swahili.
If they switch to French, respond in French. Never refuse to use the user's language.
Never say "I don't speak [language]" — you always respond in whatever language the user uses.

CONVERSATION STRUCTURE RULES:
- Always open your reply by directly acknowledging what the user asked — never start with a generic filler phrase
- Structure longer answers with clear short paragraphs, each covering one point
- Use natural transitions between paragraphs ("Beyond that...", "What makes this special is...", "On top of that...")
- End every response with one engaging follow-up question or a gentle nudge toward the next step
- Never use bullet point lists — write in flowing, conversational prose
- Keep responses to 2-3 focused paragraphs maximum
- Use "in summary" instead of "in short"
- Refer to business collaborations as "partnerships"

CONTENT RULES:
- Answer ONLY using the company content below
- Search thoroughly through ALL the content before saying you don't have information
- After answering, subtly encourage the next step with phrases like "Would you like to explore this further?" or "Shall I help you plan a visit?"

ACTIVITIES YOU KNOW ABOUT:
Wildlife & Nature, Gorilla Trekking, Chimpanzee Tracking, Game Drives, Bird Watching,
White Water Rafting, Hiking, Mountain Climbing, Cultural Village Visits, Craft Markets,
Agrofarming Tours, Coffee Plantation Visits, Vanilla Farm Tours, Tea Estate Walks,
Fishing on Lake Victoria, Lake Albert Fishing, Nile Perch Angling, Boat Cruises,
Sunset Cruises, Spa Retreats

IMPORTANT: The content below includes sections marked with "--- CONTENT FROM [URL] ---". Look through ALL sections.

If after searching ALL the content you truly cannot find the answer, respond in {user_language}:
"I don't have specific details on that right now, but I'd be happy to help you with other aspects of your Uganda journey. You can also visit https://www.everythinguganda.com/where-to-stay or contact us directly."

COMPANY CONTENT:
{site_content}
"""

        # Build full prompt
        full_prompt = system_prompt + f"\n\nUser Question:\n{english_question}"

        # Call Gemini
        response = model.generate_content(full_prompt)
        
        # Translate response to user's language
        response_result = MultilingualChatService.process_ai_response(session_id, response.text)
        translated_response = response_result['translated_response']
        
        print(f"AI response (English): '{response.text[:100]}...'")
        print(f"Translated to {user_language}: '{translated_response[:100]}...'")

        # Store conversation in database with session management
        if session_id:
            try:
                # Use session manager to handle session lifecycle
                conversation = SessionManager.get_or_create_session(session_id)
                
                # Store user message (original language)
                user_message = Message(
                    conversation_id=conversation.id,
                    role='user',
                    content=question
                )
                db.session.add(user_message)
                
                # Store bot response (translated)
                bot_message = Message(
                    conversation_id=conversation.id,
                    role='bot',
                    content=translated_response
                )
                db.session.add(bot_message)
                
                db.session.commit()
            except Exception as e:
                print(f"Failed to store conversation: {str(e)}")
                db.session.rollback()

        # Return response with all required fields
        return jsonify({
            "answer": translated_response,
            "suggested_questions": [],
            "action_buttons": [],
            "booking_buttons": [],
            "show_booking_prompt": False,
            "images": [],
            "quick_replies": []
        })

    except ValueError as e:
        return jsonify({"error": "Invalid input data"}), 400
    except ConnectionError as e:
        return jsonify({"error": "Failed to connect to AI service"}), 503
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred. Please try again later."
        }), 500


@chat_bp.route("/debug/content", methods=["GET"])
def debug_content():
    """Debug endpoint to check if content is loaded"""
    site_content = get_site_content()
    
    return jsonify({
        "content_loaded": _content_loaded,
        "content_length": len(site_content) if site_content else 0,
        "has_accommodation": "accommodation" in site_content.lower() if site_content else False,
        "has_where_to_stay": "where to stay" in site_content.lower() if site_content else False,
        "content_preview": site_content[:500] if site_content else "No content",
    })


@chat_bp.route("/history/<session_id>", methods=["GET"])
def get_chat_history(session_id):
    """
    Get chat history for a session
    ---
    tags:
      - Chatbot
    parameters:
      - name: session_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Chat history
      404:
        description: Conversation not found
    """
    conversation = Conversation.query.filter_by(session_id=session_id).first()
    
    if not conversation:
        return jsonify({"messages": []}), 200
    
    messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.created_at).all()
    
    return jsonify({
        "session_id": session_id,
        "messages": [{
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at
        } for m in messages]
    }), 200


@chat_bp.route("/feedback", methods=["POST"])
def submit_feedback():
    """
    Submit feedback on a message
    ---
    tags:
      - Chatbot
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - message_id
            - rating
          properties:
            message_id:
              type: integer
              example: 5
            rating:
              type: string
              enum: [positive, negative]
              example: "positive"
            comment:
              type: string
              example: "Very helpful response"
    responses:
      201:
        description: Feedback submitted
      400:
        description: Validation error
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Invalid request body"}), 400
        
        message_id = data.get("message_id")
        rating = data.get("rating")
        
        if not message_id or not rating:
            return jsonify({"error": "message_id and rating are required"}), 400
        
        if rating not in ["positive", "negative"]:
            return jsonify({"error": "rating must be 'positive' or 'negative'"}), 400
        
        # Check if message exists
        message = Message.query.get(message_id)
        if not message:
            return jsonify({"error": "Message not found"}), 404
        
        feedback = Feedback(
            message_id=message_id,
            rating=rating,
            comment=data.get("comment")
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({"message": "Feedback submitted successfully"}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to submit feedback: {str(e)}"}), 500


@chat_bp.route("/content/refresh", methods=["POST"])
def refresh_content():
    """
    Refresh website content
    ---
    tags:
      - Chatbot
    responses:
      200:
        description: Content refreshed
    """
    global _site_content, _content_loaded
    
    try:
        with _loading_lock:
            _content_loaded = False
            _site_content = None
            load_site_content()
        
        # Clear cache when content is refreshed
        CacheManager.clear()
        
        return jsonify({
            "message": "Content refreshed successfully",
            "content_length": len(_site_content) if _site_content else 0
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to refresh content: {str(e)}"}), 500


@chat_bp.route("/sessions/cleanup", methods=["POST"])
def cleanup_sessions():
    """
    Cleanup old and expired sessions (Admin endpoint)
    ---
    tags:
      - Chatbot
    responses:
      200:
        description: Sessions cleaned up
    """
    try:
        result = SessionManager.cleanup_old_sessions()
        return jsonify({
            "message": "Session cleanup completed",
            "expired_marked": result['expired_marked'],
            "old_deleted": result['old_deleted']
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to cleanup sessions: {str(e)}"}), 500


@chat_bp.route("/sessions/stats", methods=["GET"])
def session_stats():
    """
    Get session statistics
    ---
    tags:
      - Chatbot
    responses:
      200:
        description: Session statistics
    """
    try:
        active_count = SessionManager.get_active_sessions_count()
        total_count = Conversation.query.count()
        
        return jsonify({
            "active_sessions": active_count,
            "total_sessions": total_count,
            "inactive_sessions": total_count - active_count
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to get session stats: {str(e)}"}), 500
