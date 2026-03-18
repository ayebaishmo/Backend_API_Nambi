"""
Voice API Routes
Handles speech-to-text using Whisper
"""

from flask import Blueprint, request, jsonify
from services.voice_service import VoiceService
from middleware.rate_limit import rate_limit
from werkzeug.utils import secure_filename
import os

voice_bp = Blueprint("voice", __name__)

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'ogg', 'flac', 'webm'}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@voice_bp.route("/voice/transcribe", methods=["POST"])
@rate_limit
def transcribe_audio():
    """
    Transcribe audio to text using Whisper
    ---
    tags:
      - Voice
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: audio
        type: file
        required: true
        description: Audio file (wav, mp3, m4a, ogg, flac, webm)
      - in: formData
        name: language
        type: string
        required: false
        description: Language code (e.g., 'en', 'sw', 'fr')
      - in: formData
        name: session_id
        type: string
        required: false
        description: Session ID to link transcription to conversation
    responses:
      200:
        description: Transcription successful
        schema:
          type: object
          properties:
            success:
              type: boolean
            text:
              type: string
            language:
              type: string
            confidence:
              type: number
            duration:
              type: number
      400:
        description: Bad request (no file, invalid format)
      413:
        description: File too large
      500:
        description: Transcription failed
    """
    try:
        # Check if file is present
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        file = request.files['audio']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Invalid file format. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Get optional parameters
        language = request.form.get('language')
        session_id = request.form.get('session_id')
        
        # Read file bytes
        audio_bytes = file.read()
        
        # Check file size
        if len(audio_bytes) > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024)} MB'
            }), 413
        
        # Transcribe
        result = VoiceService.transcribe_audio_bytes(
            audio_bytes,
            filename=secure_filename(file.filename),
            language=language
        )
        
        if not result['success']:
            return jsonify(result), 500
        
        # Add session info if provided
        if session_id:
            result['session_id'] = session_id
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Transcription failed: {str(e)}'
        }), 500


@voice_bp.route("/voice/detect-language", methods=["POST"])
@rate_limit
def detect_language():
    """
    Detect language from audio
    ---
    tags:
      - Voice
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: audio
        type: file
        required: true
        description: Audio file
    responses:
      200:
        description: Language detected
        schema:
          type: object
          properties:
            success:
              type: boolean
            language:
              type: string
            confidence:
              type: number
            all_probabilities:
              type: object
    """
    try:
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        file = request.files['audio']
        
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': 'Invalid file'
            }), 400
        
        # Save temporarily
        import tempfile
        from pathlib import Path
        
        suffix = Path(file.filename).suffix or '.wav'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        # Detect language
        result = VoiceService.detect_language(temp_path)
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@voice_bp.route("/voice/supported-languages", methods=["GET"])
def get_supported_languages():
    """
    Get list of supported languages
    ---
    tags:
      - Voice
    responses:
      200:
        description: List of supported languages
        schema:
          type: object
    """
    return jsonify(VoiceService.get_supported_languages()), 200


@voice_bp.route("/voice/models", methods=["GET"])
def get_models():
    """
    Get information about available Whisper models
    ---
    tags:
      - Voice
    responses:
      200:
        description: Model information
        schema:
          type: object
    """
    return jsonify(VoiceService.get_model_info()), 200


@voice_bp.route("/voice/speak", methods=["POST"])
def text_to_speech():
    """
    Convert text to speech (for welcome message narration)
    ---
    tags:
      - Voice
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            text:
              type: string
              example: "Hello! I'm Nambi, your Virtual Travel Assistant"
            language:
              type: string
              example: "en"
    responses:
      200:
        description: Audio file (mp3)
      400:
        description: Bad request
    """
    try:
        data = request.get_json()
        if not data or not data.get('text'):
            return jsonify({'error': 'text is required'}), 400

        text = data.get('text')
        language = data.get('language', 'en')

        # Use gTTS (Google Text-to-Speech) - free
        from gtts import gTTS
        import io

        tts = gTTS(text=text, lang=language, slow=False)

        # Save to bytes buffer
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)

        from flask import send_file
        return send_file(
            audio_buffer,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name='speech.mp3'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@voice_bp.route("/voice/chat", methods=["POST"])
@rate_limit
def voice_chat():
    """
    Voice chat - transcribe audio and get chatbot response
    ---
    tags:
      - Voice
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: audio
        type: file
        required: true
        description: Audio file with user's question
      - in: formData
        name: session_id
        type: string
        required: true
        description: Session ID
      - in: formData
        name: language
        type: string
        required: false
        description: Language code
    responses:
      200:
        description: Transcription and chat response
        schema:
          type: object
          properties:
            transcription:
              type: object
            answer:
              type: string
            suggested_questions:
              type: array
    """
    try:
        print("\n" + "=" * 80)
        print("VOICE CHAT REQUEST RECEIVED")
        print("=" * 80)
        
        # Transcribe audio
        if 'audio' not in request.files:
            print("ERROR: No audio file in request")
            return jsonify({'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        session_id = request.form.get('session_id')
        language_hint = request.form.get('language')  # Optional language hint from frontend
        
        print(f"File: {file.filename}")
        print(f"Session ID: {session_id}")
        print(f"Language hint from frontend: {language_hint or 'None (auto-detect)'}")
        
        if not session_id:
            print("ERROR: No session_id provided")
            return jsonify({'error': 'session_id is required'}), 400
        
        # Transcribe with language hint if provided
        print("Reading audio bytes...")
        audio_bytes = file.read()
        print(f"Audio size: {len(audio_bytes)} bytes")
        
        # Use language hint only if it's a valid 2-letter code (not 'en' default)
        whisper_language = None
        if language_hint and language_hint != 'en' and len(language_hint) == 2:
            whisper_language = language_hint
            print(f"Using language hint for Whisper: {whisper_language}")
        else:
            print("Auto-detecting language...")
        
        print("Starting transcription...")
        transcription = VoiceService.transcribe_audio_bytes(
            audio_bytes,
            filename=secure_filename(file.filename),
            language=whisper_language  # Use auto-detect or hint from frontend
        )
        
        print(f"Transcription result: {transcription}")
        
        if not transcription['success']:
            print(f"ERROR: Transcription failed - {transcription.get('error')}")
            return jsonify({
                'error': 'Transcription failed',
                'details': transcription.get('error', 'Unknown error')
            }), 500
        
        # Import chat processing logic
        from gemini import get_gemini_model
        from services.multilingual_chat_service import MultilingualChatService
        from services.session_manager import SessionManager
        from models.message import Message
        from extensions import db
        
        question = transcription['text']
        detected_language = transcription.get('language', 'en')
        
        print(f"=" * 80)
        print(f"TRANSCRIPTION RESULT:")
        print(f"Text: '{question}'")
        print(f"Detected Language: {detected_language}")
        print(f"Language Name: {VoiceService.get_supported_languages().get(detected_language, 'Unknown')}")
        print(f"=" * 80)
        
        # Use Whisper's detected language for voice (more reliable than googletrans)
        # Accept any language Whisper detects
        user_lang = detected_language
        
        print(f"Using Whisper detected language: {user_lang}")
        print(f"Language name: {VoiceService.get_supported_languages().get(user_lang, 'Unknown')}")
        
        # Translate to English if needed
        if user_lang != 'en':
            from services.translation_service import get_translation_service
            translation_service = get_translation_service()
            try:
                english_question = translation_service.translate_to_english(question, source_lang=user_lang)
                print(f"Translated '{question}' -> '{english_question}'")
            except Exception as e:
                print(f"Translation failed: {e}, using original text")
                english_question = question
        else:
            english_question = question
        
        # Check if this is first message in session
        conversation = SessionManager.get_or_create_session(session_id)
        
        # Update conversation language
        if not conversation.language or conversation.language == 'en':
            conversation.language = user_lang
            db.session.commit()
        
        existing_messages = Message.query.filter_by(
            conversation_id=conversation.id
        ).count()
        
        is_first_message = existing_messages == 0
        
        # Handle greetings ONLY for first message
        simple_greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings", 
                           "habari", "jambo", "mambo"]  # Added Swahili greetings
        is_greeting = english_question.lower().strip() in simple_greetings or question.lower().strip() in simple_greetings
        
        if is_greeting and is_first_message:
            from services.multilingual_chat_service import MultilingualChatService
            welcome_message = MultilingualChatService.get_welcome_message(user_lang)
            return jsonify({
                "transcription": {
                    "text": transcription['text'],
                    "language": detected_language
                },
                "answer": welcome_message,
                "suggested_questions": [
                    "What are the top tourist destinations in Uganda?",
                    "Tell me about accommodation options",
                    "What cultural experiences are available?"
                ]
            }), 200
        
        # Skip greeting for subsequent messages - proceed with normal chat
        
        # Get Gemini model and site content
        model = get_gemini_model()
        
        # Load site content
        from routes.chat import get_site_content
        site_content = get_site_content()
        
        # System prompt
        system_prompt = f"""You are Nambi, Virtual Consultant for Everything Uganda.

CRITICAL RULES:
- Answer ONLY using the company content below
- Be conversational, friendly, and natural
- Keep responses concise (2-3 paragraphs max)

COMPANY CONTENT:
{site_content}
"""
        
        # Call Gemini
        full_prompt = system_prompt + f"\n\nUser Question:\n{english_question}"
        response = model.generate_content(full_prompt)
        
        # Translate response to user's language
        if user_lang != 'en':
            from services.translation_service import get_translation_service
            translation_service = get_translation_service()
            translated_response = translation_service.translate_from_english(response.text, target_lang=user_lang)
            print(f"Translated response to {user_lang}")
        else:
            translated_response = response.text
        
        # Store conversation
        if session_id:
            try:
                conversation = SessionManager.get_or_create_session(session_id)
                
                user_message = Message(
                    conversation_id=conversation.id,
                    role='user',
                    content=question
                )
                db.session.add(user_message)
                
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
        
        return jsonify({
            'transcription': {
                'text': transcription['text'],
                'language': detected_language
            },
            'answer': translated_response,
            'suggested_questions': [],
            'action_buttons': [],
            'booking_buttons': [],
            'show_booking_prompt': False,
            'images': [],
            'quick_replies': []
        }), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("=" * 80)
        print("VOICE CHAT ERROR:")
        print(error_trace)
        print("=" * 80)
        return jsonify({
            'error': 'Voice chat failed',
            'details': str(e),
            'type': type(e).__name__
        }), 500
