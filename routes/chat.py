from flask import Blueprint, request, jsonify
from gemini import get_gemini_model
from services.content_fetcher import fetch_multiple_pages
import threading

chat_bp = Blueprint("chat", __name__)

# Global variable to store site content
_site_content = None
_content_loaded = False
_loading_lock = threading.Lock()

SITE_URLS = [
    "https://everything-ug.netlify.app/",
    "https://everything-ug.netlify.app/facts",
    "https://everything-ug.netlify.app/culture",
    "https://everything-ug.netlify.app/top-cities/kampala",
    "https://everything-ug.netlify.app/religion",
    "https://everything-ug.netlify.app/travel-tips",
    "https://everything-ug.netlify.app/destinations",
    "https://everything-ug.netlify.app/activities",
    "https://everything-ug.netlify.app/about",
    "https://everything-ug.netlify.app/where-to-stay",
    "https://everything-ug.netlify.app/insights",
    "https://everything-ug.netlify.app/impact",
    "https://everything-ug.netlify.app/holiday-booking"
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
        question = data.get("question", "").strip()
        session_id = data.get("session_id")
        is_first_message = data.get("is_first_message", False)

        # Handle initial greeting (empty question OR simple greetings)
        simple_greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings"]
        if not question or question.lower() in simple_greetings:
            return jsonify({
                "answer": "Hello! I'm Nambi, your Virtual Consultant for Everything Uganda. I'm here to help you discover the Pearl of Africa through curated travel experiences, cultural insights, and essential services.",
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
        full_prompt = system_prompt + f"\n\nUser Question:\n{question}"

        # Call Gemini
        response = model.generate_content(full_prompt)

        # Return response with all required fields
        return jsonify({
            "answer": response.text,
            "suggested_questions": [],
            "action_buttons": [],
            "booking_buttons": [],
            "show_booking_prompt": False,
            "images": [],
            "quick_replies": []
        })

    except Exception as e:
        return jsonify({
            "error": f"Failed to generate response: {str(e)}"
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


# Load content when blueprint is registered (removed - using lazy loading on first request instead)
