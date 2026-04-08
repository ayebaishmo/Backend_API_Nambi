"""
Voice Service using OpenAI Whisper (Free, Local)
Handles speech-to-text conversion
"""

import whisper
import os
import tempfile
from pathlib import Path
import threading
import queue


class VoiceService:
    """Handle voice-to-text conversion using Whisper"""
    
    # Model sizes: tiny, base, small, medium, large
    # tiny = fastest, least accurate (~32x realtime on CPU)
    # base = good balance (recommended) (~16x realtime on CPU)
    # small = better accuracy for non-English languages (~6x realtime on CPU)
    # large = most accurate, slowest (~1x realtime on CPU)
    DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "base")
    DEFAULT_TIMEOUT = int(os.getenv("WHISPER_TIMEOUT", "30"))

    # Pre-load model at import time so first request isn't slow
    _model = None
    _model_lock = threading.Lock()
    
    @classmethod
    def load_model(cls, model_size=None):
        """Load Whisper model (lazy loading, thread-safe)"""
        with cls._model_lock:
            if cls._model is None:
                model_size = model_size or cls.DEFAULT_MODEL
                print(f"Loading Whisper model: {model_size}...")
                cls._model = whisper.load_model(model_size)
                print(f"✓ Whisper model loaded: {model_size}")
        return cls._model

    @staticmethod
    def transcribe_audio(audio_file_path, language=None, timeout=None):
        if timeout is None:
            timeout = VoiceService.DEFAULT_TIMEOUT
        try:
            if not os.path.exists(audio_file_path):
                return {'success': False, 'text': None, 'language': None,
                        'segments': [], 'error': f'File not found: {audio_file_path}'}

            file_size = os.path.getsize(audio_file_path)
            print(f"Transcribing: {audio_file_path} ({file_size} bytes)")

            # Convert webm/ogg to wav for faster Whisper processing
            wav_path = audio_file_path
            converted = False
            if audio_file_path.endswith(('.webm', '.ogg', '.m4a')):
                try:
                    import subprocess
                    wav_path = audio_file_path.replace(
                        Path(audio_file_path).suffix, '.wav'
                    )
                    subprocess.run(
                        ['ffmpeg', '-y', '-i', audio_file_path,
                         '-ar', '16000', '-ac', '1', '-f', 'wav', wav_path],
                        capture_output=True, timeout=15
                    )
                    if os.path.exists(wav_path):
                        converted = True
                        print(f"Converted to WAV: {wav_path}")
                except Exception as e:
                    print(f"FFmpeg conversion skipped: {e}")
                    wav_path = audio_file_path

            model = VoiceService.load_model()

            # Speed-optimised options — fastest possible on CPU
            options = {
                'fp16': False,
                'verbose': False,
                'beam_size': 1,           # greedy decode — fastest
                'best_of': 1,             # no sampling candidates
                'temperature': 0,         # deterministic, no retries
                'condition_on_previous_text': False,  # no context window overhead
                'compression_ratio_threshold': 2.4,
                'no_speech_threshold': 0.6,
            }
            if language:
                options['language'] = language

            result_queue = queue.Queue()
            error_queue = queue.Queue()

            def transcribe_worker():
                try:
                    result = model.transcribe(wav_path, **options)
                    result_queue.put(result)
                except Exception as e:
                    error_queue.put(e)

            worker_thread = threading.Thread(target=transcribe_worker, daemon=True)
            worker_thread.start()
            worker_thread.join(timeout=timeout)

            # Cleanup converted wav
            if converted and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except Exception:
                    pass

            if worker_thread.is_alive():
                return {'success': False, 'text': None, 'language': None,
                        'segments': [], 'error': f'Timed out after {timeout}s'}

            if not error_queue.empty():
                raise error_queue.get()

            if result_queue.empty():
                return {'success': False, 'text': None, 'language': None,
                        'segments': [], 'error': 'No result returned'}

            result = result_queue.get()
            text = result['text'].strip()
            print(f"Transcription done: '{text[:80]}'")

            return {
                'success': True,
                'text': text,
                'language': result.get('language', 'unknown'),
                'segments': result.get('segments', []),
                'error': None
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'text': None, 'language': None,
                    'segments': [], 'error': str(e)}
    
    @staticmethod
    def transcribe_audio_bytes(audio_bytes, filename="audio.wav", language=None):
        """
        Transcribe audio from bytes (for API uploads)
        
        Args:
            audio_bytes: Audio file bytes
            filename: Original filename (for format detection)
            language: Optional language code
        
        Returns:
            dict with transcription results
        """
        temp_path = None
        try:
            # Create temporary file (don't auto-delete on Windows)
            suffix = Path(filename).suffix or '.wav'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            print(f"Temp file created: {temp_path}")
            
            # Transcribe
            result = VoiceService.transcribe_audio(temp_path, language)
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'text': None,
                'language': None,
                'segments': [],
                'error': str(e)
            }
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    print(f"Temp file deleted: {temp_path}")
                except Exception as e:
                    print(f"Warning: Could not delete temp file {temp_path}: {e}")
    
    @staticmethod
    def detect_language(audio_file_path):
        """
        Detect language from audio file
        
        Returns:
            dict with 'language' and 'confidence'
        """
        try:
            model = VoiceService.load_model()
            
            # Load audio and detect language
            audio = whisper.load_audio(audio_file_path)
            audio = whisper.pad_or_trim(audio)
            
            # Make log-Mel spectrogram
            mel = whisper.log_mel_spectrogram(audio).to(model.device)
            
            # Detect language
            _, probs = model.detect_language(mel)
            detected_language = max(probs, key=probs.get)
            
            return {
                'success': True,
                'language': detected_language,
                'confidence': probs[detected_language],
                'all_probabilities': dict(sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5])
            }
            
        except Exception as e:
            return {
                'success': False,
                'language': None,
                'confidence': 0,
                'error': str(e)
            }
    
    @staticmethod
    def get_supported_languages():
        """Get list of supported languages"""
        return {
            'en': 'English',
            'sw': 'Swahili',
            'fr': 'French',
            'de': 'German',
            'es': 'Spanish',
            'lg': 'Luganda',  # May not be well supported
            'ar': 'Arabic',
            'zh': 'Chinese',
            'hi': 'Hindi',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean'
        }
    
    @staticmethod
    def get_model_info():
        """Get information about available models"""
        return {
            'tiny': {
                'size': '39 MB',
                'speed': 'Very Fast',
                'accuracy': 'Low',
                'recommended_for': 'Quick testing'
            },
            'base': {
                'size': '74 MB',
                'speed': 'Fast',
                'accuracy': 'Good',
                'recommended_for': 'Production (default)'
            },
            'small': {
                'size': '244 MB',
                'speed': 'Medium',
                'accuracy': 'Better',
                'recommended_for': 'Higher accuracy needs'
            },
            'medium': {
                'size': '769 MB',
                'speed': 'Slow',
                'accuracy': 'Very Good',
                'recommended_for': 'Professional use'
            },
            'large': {
                'size': '1550 MB',
                'speed': 'Very Slow',
                'accuracy': 'Best',
                'recommended_for': 'Maximum accuracy'
            }
        }
