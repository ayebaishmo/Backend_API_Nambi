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

# Language to neural voice map
# Note: sw-KE-ZuriNeural exists in edge-tts; fallback to en-GB-SoniaNeural if it fails
VOICE_MAP = {
    'en': 'en-GB-SoniaNeural',
    'sw': 'sw-KE-ZuriNeural',
    'fr': 'fr-FR-DeniseNeural',
    'de': 'de-DE-KatjaNeural',
    'es': 'es-ES-ElviraNeural',
    'pt': 'pt-BR-FranciscaNeural',
    'it': 'it-IT-ElsaNeural',
    'ar': 'ar-EG-SalmaNeural',
    'zh': 'zh-CN-XiaoxiaoNeural',
    'zh-cn': 'zh-CN-XiaoxiaoNeural',
    'ru': 'ru-RU-SvetlanaNeural',
    'ko': 'ko-KR-SunHiNeural',
    'ja': 'ja-JP-NanamiNeural',
    'hi': 'hi-IN-SwaraNeural',
}


def _strip_markdown(text):
    """Remove markdown formatting so TTS reads clean text."""
    import re
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)   # bold/italic
    text = re.sub(r'#{1,6}\s*', '', text)                  # headers
    text = re.sub(r'`{1,3}.*?`{1,3}', '', text, flags=re.DOTALL)  # code
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # links
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)   # bullets
    text = re.sub(r'\n{2,}', '. ', text)                   # double newlines → pause
    text = re.sub(r'\n', ' ', text)                        # single newlines
    return text.strip()


def _run_async(coro):
    """Run an async coroutine safely on Windows — always uses a fresh thread with its own event loop."""
    import asyncio
    import concurrent.futures

    def run_in_thread(c):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(c)
        finally:
            loop.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_in_thread, coro)
        return future.result(timeout=30)  # 30s max for TTS


def _generate_audio_b64(text, language='en'):
    """Generate audio from text and return as base64 string"""
    try:
        import edge_tts
        import base64

        clean_text = _strip_markdown(text)
        if not clean_text:
            print("Audio generation skipped: empty text after stripping")
            return None

        voice = VOICE_MAP.get(language, 'en-GB-SoniaNeural')
        print(f"Generating audio: voice={voice}, lang={language}, chars={len(clean_text)}")

        async def generate(v):
            communicate = edge_tts.Communicate(clean_text, v)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        # Try the mapped voice; fall back to Sonia if it fails (e.g. sw-KE-ZuriNeural unavailable)
        try:
            audio_bytes = _run_async(generate(voice))
        except Exception as voice_err:
            print(f"Voice {voice} failed ({voice_err}), falling back to en-GB-SoniaNeural")
            audio_bytes = _run_async(generate('en-GB-SoniaNeural'))

        if not audio_bytes:
            print("Audio generation returned empty bytes")
            return None

        print(f"Audio generated: {len(audio_bytes)} bytes")
        return base64.b64encode(audio_bytes).decode('utf-8')

    except Exception as e:
        import traceback
        print(f"Audio generation failed: {e}")
        traceback.print_exc()
        return None


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
    Convert text to speech using Microsoft Edge Neural TTS
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
            voice:
              type: string
              example: "en-US-JennyNeural"
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
        requested_voice = data.get('voice')

        # Strip markdown so TTS reads clean text
        text = _strip_markdown(text)
        if not text:
            return jsonify({'error': 'text is empty after processing'}), 400

        # Map language codes to best neural voices
        language_voice_map = {
            'en': 'en-GB-SoniaNeural',      # warm, elegant British female - Nambi's voice
            'sw': 'sw-KE-ZuriNeural',
            'fr': 'fr-FR-DeniseNeural',
            'de': 'de-DE-KatjaNeural',
            'es': 'es-ES-ElviraNeural',
            'pt': 'pt-BR-FranciscaNeural',
            'it': 'it-IT-ElsaNeural',
            'ar': 'ar-EG-SalmaNeural',
            'zh': 'zh-CN-XiaoxiaoNeural',
            'zh-cn': 'zh-CN-XiaoxiaoNeural',
            'ru': 'ru-RU-SvetlanaNeural',
            'ko': 'ko-KR-SunHiNeural',
            'ja': 'ja-JP-NanamiNeural',
            'hi': 'hi-IN-SwaraNeural',
        }

        # Use requested voice, or pick best for language, or default to Sonia
        voice = requested_voice or language_voice_map.get(language, 'en-GB-SoniaNeural')

        import edge_tts
        from flask import Response

        async def generate(v):
            communicate = edge_tts.Communicate(text, v)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

        try:
            audio_bytes = _run_async(generate(voice))
        except Exception:
            audio_bytes = _run_async(generate('en-GB-SoniaNeural'))

        return Response(
            audio_bytes,
            mimetype="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
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
        
        # Use language hint if explicitly provided by frontend (not the default 'en')
        # If no hint or default 'en', let Whisper auto-detect
        whisper_language = None
        if language_hint and language_hint not in ('en', 'auto') and len(language_hint) <= 5:
            whisper_language = language_hint
            print(f"Using language hint for Whisper: {whisper_language}")
        else:
            print("Auto-detecting language (no explicit hint)...")
        
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

        # Fix: low confidence on unlikely language → fall back to Swahili
        segments = transcription.get('segments', [])
        if segments:
            avg_no_speech = sum(s.get('no_speech_prob', 0) for s in segments) / len(segments)
            unlikely_langs = {'ko', 'ja', 'zh', 'ru', 'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'nl'}
            if avg_no_speech > 0.4 and detected_language in unlikely_langs:
                print(f"Low confidence ({avg_no_speech:.2f}) for {detected_language}, falling back to sw")
                detected_language = 'sw'

        user_lang = detected_language
        english_question = question  # Gemini handles all languages natively

        # Check greeting without blocking DB call
        simple_greetings = {"hi", "hello", "hey", "good morning", "good afternoon",
                            "good evening", "greetings", "habari", "jambo", "mambo"}
        is_greeting = question.lower().strip() in simple_greetings

        if is_greeting:
            from services.multilingual_chat_service import MultilingualChatService
            welcome_message = MultilingualChatService.get_welcome_message(user_lang)
            audio_b64 = _generate_audio_b64(welcome_message, user_lang)
            return jsonify({
                "transcription": {"text": transcription['text'], "language": detected_language},
                "answer": welcome_message,
                "audio_base64": audio_b64,
                "suggested_questions": []
            }), 200
        
        # Get Gemini model and site content
        model = get_gemini_model()
        
        # Load site content
        from routes.chat import get_site_content
        site_content = get_site_content()
        
        # System prompt
        system_prompt = f"""You are Nambi, Virtual Travel Assistant for Everything Uganda. You are warm, fun and quick.

LANGUAGE: Respond in {user_lang} only.

RESPONSE RULES:
- ONE short paragraph only — 2-3 sentences max
- Be direct, warm and conversational — like texting a friend
- End with a quick follow-up question to keep the chat going
- No bullet points, no headers, no long explanations
- Use the company content below to answer accurately

If you can't find the answer: "I don't have that detail right now, but visit https://www.everythinguganda.com or ask me something else about Uganda!"

COMPANY CONTENT:
{site_content[:4000]}
"""
        
        # Call Gemini — responds in user's language directly, no translation needed
        full_prompt = system_prompt + f"\n\nUser Question:\n{english_question}"
        response = model.generate_content(full_prompt)
        translated_response = response.text
        
        # Store in background — never block the audio response
        if session_id:
            from flask import current_app
            _app = current_app._get_current_object()
            _q, _r = question, translated_response
            def _store_voice():
                try:
                    with _app.app_context():
                        conv = Conversation.query.filter_by(session_id=session_id).first()
                        if not conv:
                            conv = Conversation(session_id=session_id, language=user_lang, is_active=True)
                            db.session.add(conv)
                            try:
                                db.session.flush()
                            except Exception:
                                db.session.rollback()
                                conv = Conversation.query.filter_by(session_id=session_id).first()
                        db.session.add(Message(conversation_id=conv.id, role='user', content=_q))
                        db.session.add(Message(conversation_id=conv.id, role='bot', content=_r))
                        db.session.commit()
                except Exception as e:
                    print(f"Voice store failed: {e}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
            import threading
            threading.Thread(target=_store_voice, daemon=True).start()
        
        return jsonify({
            'transcription': {
                'text': transcription['text'],
                'language': detected_language
            },
            'answer': translated_response,
            'audio_base64': _generate_audio_b64(translated_response, user_lang),
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
