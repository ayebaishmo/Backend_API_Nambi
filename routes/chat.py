from flask import Blueprint, request, jsonify
from gemini import get_gemini_model
from services.content_fetcher import fetch_multiple_pages
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

SITE_URLS = [
    "https://www.everythinguganda.com//",
    "https://www.everythinguganda.com/facts",
    "https://www.everythinguganda.com/culture",
    "https://www.everythinguganda.com/top-cities/kampala",
    "https://www.everythinguganda.com/religion",
    "https://www.everythinguganda.com/travel-tips",
    "https://www.everythinguganda.com/destinations",
    "https://www.everythinguganda.com/holiday-types?type=birding-holidays",
    "https://www.everythinguganda.com/about",
    "https://www.everythinguganda.com/where-to-stay",
    "https://www.everythinguganda.com/insights",
    "https://www.everythinguganda.com/impact",
]

def load_site_content():
    """Load site content at startup"""
    global _site_content, _content_loaded
    
    with _loading_lock:
        if _content_loaded:
            return _site_content
            
        try:
            _site_content = fetch_multiple_pages(SITE_URLS)
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
                "suggested_questions": [
                    "What are the top tourist destinations in Uganda?",
                    "Tell me about accommodation options",
                    "What cultural experiences are available?"
                ],
                "action_buttons": [],
                "booking_buttons": [],
                "show_booking_prompt": False,
                "images": [],
                "quick_replies": []
            })
        
        # Handle booking intent
        booking_keywords = ["yes please", "yes", "book", "booking", "reserve", "reservation", "i want to book", "how do i book", "book now"]
        if any(keyword in question.lower() for keyword in booking_keywords):
            return jsonify({
                "answer": "Great! To book your Uganda experience, please visit our booking page at https://everything-ug.netlify.app/holiday-booking or contact us directly. Our team will help you plan the perfect trip tailored to your interests and budget.",
                "suggested_questions": [
                    "What destinations can I visit?",
                    "Tell me about accommodation options",
                    "What activities are available?"
                ],
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
        system_prompt = f"""You are Nambi, Virtual Consultant for Everything Uganda.

CRITICAL RULES:
- Answer ONLY using the company content below
- The company content contains information from multiple pages including accommodation, destinations, culture, activities, etc.
- Search thoroughly through ALL the content before saying you don't have information
- Be conversational, friendly, and natural
- Use "in summary" instead of "in short"
- Refer to business collaborations as "partnerships"
- After answering informational questions, subtly encourage booking with phrases like "Would you like to explore this further?" or "Interested in experiencing this?"
- Keep responses concise (2-3 paragraphs max)

IMPORTANT: The content below includes sections marked with "--- CONTENT FROM [URL] ---". Look through ALL sections to find relevant information.

If after searching ALL the content you truly cannot find the answer, respond:
"I don't have specific details on that right now, but I'd be happy to help you with other information about Uganda. You can also visit https://everything-ug.netlify.app/where-to-stay for accommodation details or contact us directly."

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
        "urls_count": len(SITE_URLS)
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
