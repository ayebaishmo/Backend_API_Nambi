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
    DEFAULT_TIMEOUT = int(os.getenv("WHISPER_TIMEOUT", "120"))
    
    _model = None
    
    @classmethod
    def load_model(cls, model_size=None):
        """Load Whisper model (lazy loading)"""
        if cls._model is None:
            model_size = model_size or cls.DEFAULT_MODEL
            print(f"Loading Whisper model: {model_size}...")
            cls._model = whisper.load_model(model_size)
            print(f"✓ Whisper model loaded: {model_size}")
        return cls._model
    
    @staticmethod
    def transcribe_audio(audio_file_path, language=None, timeout=None):
        """
        Transcribe audio file to text with timeout protection
        
        Args:
            audio_file_path: Path to audio file (mp3, wav, m4a, etc.)
            language: Optional language code (e.g., 'en', 'sw' for Swahili)
            timeout: Maximum seconds to wait (default from env or 120s)
        
        Returns:
            dict with 'text', 'language', 'confidence'
        """
        if timeout is None:
            timeout = VoiceService.DEFAULT_TIMEOUT
        try:
            # Verify file exists
            if not os.path.exists(audio_file_path):
                return {
                    'success': False,
                    'text': None,
                    'language': None,
                    'segments': [],
                    'error': f'Audio file not found: {audio_file_path}'
                }
            
            file_size = os.path.getsize(audio_file_path)
            print(f"Transcribing file: {audio_file_path} (size: {file_size} bytes)")
            
            model = VoiceService.load_model()
            
            # Transcribe with optimized settings for CPU
            options = {
                'fp16': False,  # Explicitly disable FP16 on CPU
                'verbose': False  # Reduce console output
            }
            if language:
                options['language'] = language
            
            # Use threading with timeout to prevent hanging
            result_queue = queue.Queue()
            error_queue = queue.Queue()
            
            def transcribe_worker():
                try:
                    print("Starting Whisper transcription (this may take 10-60 seconds on CPU)...")
                    result = model.transcribe(audio_file_path, **options)
                    result_queue.put(result)
                except Exception as e:
                    error_queue.put(e)
            
            # Start transcription in separate thread
            worker_thread = threading.Thread(target=transcribe_worker, daemon=True)
            worker_thread.start()
            
            # Wait for result with timeout
            worker_thread.join(timeout=timeout)
            
            if worker_thread.is_alive():
                # Timeout occurred
                print(f"ERROR: Transcription timed out after {timeout} seconds")
                return {
                    'success': False,
                    'text': None,
                    'language': None,
                    'segments': [],
                    'error': f'Transcription timed out after {timeout} seconds. Try using a shorter audio clip or switch to "tiny" or "base" model.'
                }
            
            # Check for errors
            if not error_queue.empty():
                error = error_queue.get()
                raise error
            
            # Get result
            if result_queue.empty():
                return {
                    'success': False,
                    'text': None,
                    'language': None,
                    'segments': [],
                    'error': 'Transcription completed but no result was returned'
                }
            
            result = result_queue.get()
            print(f"Transcription successful: '{result['text'][:100]}...'")
            
            return {
                'success': True,
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'segments': result.get('segments', []),
                'error': None
            }
            
        except Exception as e:
            import traceback
            print("Transcription error:")
            traceback.print_exc()
            return {
                'success': False,
                'text': None,
                'language': None,
                'segments': [],
                'error': str(e)
            }
    
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
