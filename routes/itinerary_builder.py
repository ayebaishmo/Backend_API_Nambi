"""
Dynamic Itinerary Builder Routes
Handles AI-powered itinerary generation through conversation
"""

from flask import Blueprint, request, jsonify
from extensions import db
from models.conversation import Conversation
from models.message import Message
from services.itinerary_builder import ItineraryBuilder
from services.session_manager import SessionManager
from services.content_fetcher import fetch_multiple_pages
from routes.chat import get_site_content
from middleware.rate_limit import rate_limit

itinerary_builder_bp = Blueprint("itinerary_builder", __name__)


@itinerary_builder_bp.route("/build-itinerary", methods=["POST"])
@rate_limit
def build_itinerary():
    """
    Build personalized itinerary through conversation
    ---
    tags:
      - Itinerary Builder
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - session_id
          properties:
            message:
              type: string
              example: "I want a 5 day safari with gorilla trekking"
            session_id:
              type: string
              example: "session_123"
            generate_now:
              type: boolean
              example: false
              description: "Set to true to force generation with current info"
    responses:
      200:
        description: Response with itinerary or clarification question
        schema:
          type: object
          properties:
            status:
              type: string
              enum: [gathering_info, ready_to_generate, generated]
            message:
              type: string
            question:
              type: string
            extracted_info:
              type: object
            missing_fields:
              type: array
              items:
                type: string
            itinerary:
              type: object
            itinerary_id:
              type: integer
      400:
        description: Bad request
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request body"}), 400
        
        session_id = data.get("session_id")
        user_message = data.get("message", "").strip()
        generate_now = data.get("generate_now", False)
        
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        
        # Get or create session
        conversation = SessionManager.get_or_create_session(session_id)
        
        # Store user message if provided
        if user_message:
            message = Message(
                conversation_id=conversation.id,
                role='user',
                content=user_message
            )
            db.session.add(message)
            db.session.commit()
        
        # Get conversation history
        messages = Message.query.filter_by(
            conversation_id=conversation.id
        ).order_by(Message.created_at).all()
        
        conversation_history = [
            {'role': m.role, 'content': m.content}
            for m in messages
        ]
        
        # Extract itinerary information from conversation
        info, missing_fields = ItineraryBuilder.extract_itinerary_info(conversation_history)
        
        # Check if we have enough information
        if missing_fields and not generate_now:
            # Ask clarification question
            question = ItineraryBuilder.generate_clarification_question(missing_fields)
            
            # Store bot question
            bot_message = Message(
                conversation_id=conversation.id,
                role='bot',
                content=question
            )
            db.session.add(bot_message)
            db.session.commit()
            
            return jsonify({
                "status": "gathering_info",
                "message": "I need a bit more information to create your perfect itinerary.",
                "question": question,
                "extracted_info": info,
                "missing_fields": missing_fields,
                "progress": f"{len([k for k, v in info.items() if v])} / {len(ItineraryBuilder.REQUIRED_INFO)} fields collected"
            }), 200
        
        # We have enough info or user forced generation
        if not missing_fields or generate_now:
            # Get site content for context
            site_content = get_site_content()
            
            # Generate itinerary
            itinerary_data, error = ItineraryBuilder.generate_itinerary(info, site_content)
            
            if error:
                return jsonify({
                    "status": "error",
                    "message": error
                }), 500
            
            # Save itinerary
            result = ItineraryBuilder.save_itinerary(itinerary_data, session_id)
            
            # Create response message
            response_message = f"""Great! I've created a personalized {itinerary_data['days']}-day itinerary for you.

**{itinerary_data['title']}**

{itinerary_data['details'][:500]}...

Would you like to:
1. View the full itinerary
2. Modify something
3. Proceed to booking
"""
            
            # Store bot response
            bot_message = Message(
                conversation_id=conversation.id,
                role='bot',
                content=response_message
            )
            db.session.add(bot_message)
            db.session.commit()
            
            return jsonify({
                "status": "generated",
                "message": response_message,
                "itinerary_id": result['itinerary_id'],
                "itinerary": result['itinerary'],
                "validation": result['validation'],
                "actions": [
                    {"label": "View Full Itinerary", "action": "view_itinerary"},
                    {"label": "Modify Itinerary", "action": "modify"},
                    {"label": "Proceed to Booking", "action": "book"}
                ]
            }), 200
        
        # Ready to generate
        return jsonify({
            "status": "ready_to_generate",
            "message": "I have all the information I need! Shall I create your itinerary now?",
            "extracted_info": info,
            "actions": [
                {"label": "Yes, create my itinerary!", "action": "generate"},
                {"label": "Let me add more details", "action": "continue"}
            ]
        }), 200
        
    except Exception as e:
        print(f"Error in build_itinerary: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500


@itinerary_builder_bp.route("/itinerary/<int:itinerary_id>", methods=["GET"])
def get_generated_itinerary(itinerary_id):
    """
    Get a generated itinerary by ID
    ---
    tags:
      - Itinerary Builder
    parameters:
      - name: itinerary_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Itinerary details
      404:
        description: Itinerary not found
    """
    from models.itinerary import Itinerary
    
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    
    return jsonify({
        "id": itinerary.id,
        "title": itinerary.title,
        "days": itinerary.days,
        "budget": itinerary.budget,
        "places": itinerary.places,
        "accommodation": itinerary.accommodation,
        "transport": itinerary.transport,
        "details": itinerary.details,
        "package_name": itinerary.package_name,
        "created_at": itinerary.created_at
    }), 200


@itinerary_builder_bp.route("/itinerary/<int:itinerary_id>/regenerate", methods=["POST"])
@rate_limit
def regenerate_itinerary(itinerary_id):
    """
    Regenerate an itinerary with modifications
    ---
    tags:
      - Itinerary Builder
    parameters:
      - name: itinerary_id
        in: path
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            modifications:
              type: string
              example: "Add more cultural activities"
            session_id:
              type: string
    responses:
      200:
        description: New itinerary generated
      404:
        description: Original itinerary not found
    """
    from models.itinerary import Itinerary
    
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    data = request.get_json() or {}
    
    modifications = data.get("modifications", "")
    session_id = data.get("session_id")
    
    # Extract info from existing itinerary
    info = {
        'duration': itinerary.days,
        'budget': float(itinerary.budget) if itinerary.budget.replace('.', '').isdigit() else 1000,
        'interests': modifications or 'general tourism',
        'accommodation': itinerary.package_name.lower(),
        'pace': 'moderate'
    }
    
    # Get site content
    site_content = get_site_content()
    
    # Generate new itinerary
    itinerary_data, error = ItineraryBuilder.generate_itinerary(info, site_content)
    
    if error:
        return jsonify({"error": error}), 500
    
    # Save new itinerary
    result = ItineraryBuilder.save_itinerary(itinerary_data, session_id)
    
    return jsonify({
        "message": "Itinerary regenerated successfully",
        "old_itinerary_id": itinerary_id,
        "new_itinerary_id": result['itinerary_id'],
        "itinerary": result['itinerary'],
        "validation": result['validation']
    }), 200
