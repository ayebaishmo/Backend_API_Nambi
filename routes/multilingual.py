"""
Multilingual Support Routes
Handle language detection, switching, and translation
"""

from flask import Blueprint, request, jsonify
from services.translation_service import get_translation_service
from models.conversation import Conversation
from extensions import db

multilingual_bp = Blueprint("multilingual", __name__)

translation_service = get_translation_service()


@multilingual_bp.route("/languages", methods=["GET"])
def get_supported_languages():
    """
    Get list of supported languages
    ---
    tags:
      - Multilingual
    responses:
      200:
        description: List of supported languages
        schema:
          type: object
          properties:
            languages:
              type: object
              example:
                en: English
                fr: French
                de: German
    """
    return jsonify({
        "languages": translation_service.get_supported_languages()
    }), 200


@multilingual_bp.route("/detect-language", methods=["POST"])
def detect_language():
    """
    Detect language of text
    ---
    tags:
      - Multilingual
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - text
          properties:
            text:
              type: string
              example: "Bonjour, je veux visiter l'Ouganda"
    responses:
      200:
        description: Detected language
        schema:
          type: object
          properties:
            detected_language:
              type: string
              example: "fr"
            language_name:
              type: string
              example: "French"
            confidence:
              type: string
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "text is required"}), 400
        
        text = data['text']
        
        # Detect language
        detected_lang = translation_service.detect_language(text)
        language_name = translation_service.get_language_name(detected_lang)
        
        return jsonify({
            "detected_language": detected_lang,
            "language_name": language_name,
            "is_supported": translation_service.is_language_supported(detected_lang)
        }), 200
        
    except Exception as e:
        print(f"Error in detect_language: {str(e)}")
        return jsonify({"error": str(e)}), 500


@multilingual_bp.route("/translate", methods=["POST"])
def translate_text():
    """
    Translate text between languages
    ---
    tags:
      - Multilingual
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - text
            - target_lang
          properties:
            text:
              type: string
              example: "Hello, I want to visit Uganda"
            target_lang:
              type: string
              example: "fr"
            source_lang:
              type: string
              example: "en"
              default: "auto"
    responses:
      200:
        description: Translated text
        schema:
          type: object
          properties:
            translated_text:
              type: string
              example: "Bonjour, je veux visiter l'Ouganda"
            source_lang:
              type: string
            target_lang:
              type: string
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data or 'target_lang' not in data:
            return jsonify({"error": "text and target_lang are required"}), 400
        
        text = data['text']
        target_lang = data['target_lang']
        source_lang = data.get('source_lang', 'auto')
        
        # Validate target language
        if not translation_service.is_language_supported(target_lang):
            return jsonify({"error": f"Language '{target_lang}' is not supported"}), 400
        
        # Translate
        translated_text = translation_service.translate(
            text,
            target_lang=target_lang,
            source_lang=source_lang
        )
        
        return jsonify({
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }), 200
        
    except Exception as e:
        print(f"Error in translate_text: {str(e)}")
        return jsonify({"error": str(e)}), 500


@multilingual_bp.route("/set-language", methods=["POST"])
def set_language():
    """
    Set user's preferred language for a session
    ---
    tags:
      - Multilingual
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - session_id
            - language
          properties:
            session_id:
              type: string
              example: "user_session_123"
            language:
              type: string
              example: "fr"
    responses:
      200:
        description: Language preference saved
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            language:
              type: string
    """
    try:
        data = request.get_json()
        if not data or 'session_id' not in data or 'language' not in data:
            return jsonify({"error": "session_id and language are required"}), 400
        
        session_id = data['session_id']
        language = data['language']
        
        # Validate language
        if not translation_service.is_language_supported(language):
            return jsonify({"error": f"Language '{language}' is not supported"}), 400
        
        # Get or create conversation
        conversation = Conversation.query.filter_by(session_id=session_id).first()
        
        if not conversation:
            conversation = Conversation(session_id=session_id, language=language)
            db.session.add(conversation)
        else:
            conversation.language = language
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Language set to {translation_service.get_language_name(language)}",
            "language": language,
            "language_name": translation_service.get_language_name(language)
        }), 200
        
    except Exception as e:
        print(f"Error in set_language: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@multilingual_bp.route("/get-language/<session_id>", methods=["GET"])
def get_language(session_id):
    """
    Get user's preferred language for a session
    ---
    tags:
      - Multilingual
    parameters:
      - name: session_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: User's language preference
        schema:
          type: object
          properties:
            language:
              type: string
              example: "fr"
            language_name:
              type: string
              example: "French"
    """
    try:
        conversation = Conversation.query.filter_by(session_id=session_id).first()
        
        if conversation and conversation.language:
            language = conversation.language
        else:
            language = 'en'  # Default to English
        
        return jsonify({
            "language": language,
            "language_name": translation_service.get_language_name(language)
        }), 200
        
    except Exception as e:
        print(f"Error in get_language: {str(e)}")
        return jsonify({"error": str(e)}), 500
