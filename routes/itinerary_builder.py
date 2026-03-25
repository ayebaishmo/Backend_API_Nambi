"""
Dynamic Itinerary Builder Routes
Conversational itinerary building using Gemini AI
"""

from flask import Blueprint, request, jsonify
from extensions import db
from models.conversation import Conversation
from models.message import Message
from services.itinerary_builder import ItineraryBuilder
from services.session_manager import SessionManager
from routes.chat import get_site_content
from middleware.rate_limit import rate_limit
from gemini import get_gemini_model
import json
import re

itinerary_builder_bp = Blueprint("itinerary_builder", __name__)


def _get_conversation_history(conversation_id):
    messages = Message.query.filter_by(
        conversation_id=conversation_id
    ).order_by(Message.created_at).all()
    return [{'role': m.role, 'content': m.content} for m in messages]


def _build_history_text(history):
    """Format conversation history for Gemini context."""
    lines = []
    for m in history:
        role = "User" if m['role'] == 'user' else "Nambi"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


def _gemini_itinerary_conversation(history, new_message, site_content):
    """
    Use Gemini to drive the itinerary conversation naturally.
    Returns dict with: status, reply, extracted_info (if ready)
    """
    model = get_gemini_model()

    history_text = _build_history_text(history)

    prompt = f"""You are Nambi, a warm and knowledgeable Uganda travel assistant building a personalised itinerary.

CONVERSATION SO FAR:
{history_text}

USER JUST SAID: {new_message}

YOUR TASK:
1. Read the FULL conversation above carefully — extract everything the user has already told you.
2. Determine what information you still need to build the itinerary:
   - Duration (how many days)
   - Budget (in British Pounds £)
   - Interests/activities (e.g. hiking, wildlife, culture, fishing, agrofarming)
   - Accommodation preference (budget / mid-range / luxury)
3. If you have ALL four pieces of information, respond with status "ready" and summarise what you'll build.
4. If you are MISSING information, ask for ONLY the next missing piece in a natural, conversational way — acknowledge what they already told you, do NOT repeat questions already answered.
5. Never ask for information the user already provided in this conversation.
6. Keep your reply warm, brief, and natural — 1-2 sentences max.

RESPOND IN THIS EXACT JSON FORMAT:
{{
  "status": "gathering" or "ready",
  "reply": "Your conversational response here",
  "extracted": {{
    "duration": null or number,
    "budget": null or number,
    "interests": null or "comma separated string",
    "accommodation": null or "budget/mid-range/luxury",
    "pace": null or "relaxed/moderate/packed"
  }}
}}

IMPORTANT: Return ONLY the JSON, no markdown, no extra text."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Strip markdown code blocks if present
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text)
    except Exception as e:
        print(f"Gemini itinerary conversation error: {e}")
        return {
            "status": "gathering",
            "reply": "I'd love to help plan your Uganda adventure! Could you tell me how many days you're thinking and what activities excite you most?",
            "extracted": {"duration": None, "budget": None, "interests": None, "accommodation": None, "pace": None}
        }


@itinerary_builder_bp.route("/build-itinerary", methods=["POST"])
@rate_limit
def build_itinerary():
    """
    Build personalised itinerary through natural conversation
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
              example: "I want mountain hiking for a week"
            session_id:
              type: string
              example: "session_123"
            generate_now:
              type: boolean
              example: false
    responses:
      200:
        description: Conversational response or generated itinerary
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

        conversation = SessionManager.get_or_create_session(session_id)

        # Store user message
        if user_message:
            db.session.add(Message(
                conversation_id=conversation.id,
                role='user',
                content=user_message
            ))
            db.session.commit()

        # Get full conversation history
        history = _get_conversation_history(conversation.id)

        # Let Gemini drive the conversation
        site_content = get_site_content()
        result = _gemini_itinerary_conversation(history, user_message, site_content)

        status = result.get("status", "gathering")
        reply = result.get("reply", "")
        extracted = result.get("extracted", {})

        # Store Nambi's reply
        db.session.add(Message(
            conversation_id=conversation.id,
            role='bot',
            content=reply
        ))
        db.session.commit()

        # If still gathering info, return the conversational reply
        if status == "gathering" and not generate_now:
            return jsonify({
                "status": "gathering_info",
                "message": reply,
                "question": reply,
                "extracted_info": extracted,
            }), 200

        # Ready to generate — build the itinerary
        # Fill any gaps with sensible defaults
        info = {
            'duration': extracted.get('duration') or 7,
            'budget': extracted.get('budget') or 500,
            'interests': extracted.get('interests') or 'general tourism',
            'accommodation': extracted.get('accommodation') or 'mid-range',
            'pace': extracted.get('pace') or 'moderate',
            'group_size': 1
        }

        itinerary_data, error = ItineraryBuilder.generate_itinerary(info, site_content)

        if error:
            return jsonify({"status": "error", "message": error}), 500

        save_result = ItineraryBuilder.save_itinerary(itinerary_data, session_id)

        response_message = (
            f"Your {itinerary_data['days']}-day Uganda itinerary is ready! "
            f"Here's a preview of {itinerary_data['title']}. "
            "Would you like to view the full details, make any changes, or go ahead and book?"
        )

        db.session.add(Message(
            conversation_id=conversation.id,
            role='bot',
            content=response_message
        ))
        db.session.commit()

        return jsonify({
            "status": "generated",
            "message": response_message,
            "itinerary_id": save_result['itinerary_id'],
            "itinerary": save_result['itinerary'],
            "validation": save_result['validation'],
            "actions": [
                {"label": "View Full Itinerary", "action": "view_itinerary"},
                {"label": "Modify Itinerary", "action": "modify"},
                {"label": "Proceed to Booking", "action": "book"}
            ]
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


@itinerary_builder_bp.route("/itinerary/<int:itinerary_id>", methods=["GET"])
def get_generated_itinerary(itinerary_id):
    """
    Get a generated itinerary by ID
    ---
    tags:
      - Itinerary Builder
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
    """
    from models.itinerary import Itinerary
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    data = request.get_json() or {}

    try:
        budget_val = float(re.sub(r'[^\d.]', '', str(itinerary.budget)))
    except Exception:
        budget_val = 500

    info = {
        'duration': itinerary.days,
        'budget': budget_val,
        'interests': data.get("modifications") or 'general tourism',
        'accommodation': itinerary.package_name.lower() if itinerary.package_name else 'mid-range',
        'pace': 'moderate',
        'group_size': 1
    }

    site_content = get_site_content()
    itinerary_data, error = ItineraryBuilder.generate_itinerary(info, site_content)

    if error:
        return jsonify({"error": error}), 500

    result = ItineraryBuilder.save_itinerary(itinerary_data, data.get("session_id"))

    return jsonify({
        "message": "Itinerary regenerated successfully",
        "old_itinerary_id": itinerary_id,
        "new_itinerary_id": result['itinerary_id'],
        "itinerary": result['itinerary'],
        "validation": result['validation']
    }), 200
