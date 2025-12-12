import logging
from agrosphere import settings
from deepgram import DeepgramClient, PrerecordedOptions
from .ai_service import gemini_service # Import Gemini AI service
from .tts_service import tts_service # Import TTS dependency by YarnGPT 

logger = logging.getLogger(__name__)

class SpeechToSpeechService:
    """
    Orchestrator for the Voice-to-Voice pipeline:
    1. Transcribe Audio (Deepgram)
    2. Get AI Answer (Gemini)
    3. Generate Speech (YarnGPT/TTS Service)
    """
    def __init__(self):
        # Initialize Deepgram with API Key from settings
        api_key = getattr(settings, 'DEEPGRAM_API_KEY', '')
        self.deepgram = DeepgramClient(api_key)

    def process_voice_query(self, audio_file, language_code='ha'):
        """
        Full pipeline: Voice -> Text -> AI Answer -> Audio
        """
        try:
            # -------------------------------------------------------
            # STEP 1: SPEECH-TO-TEXT (Transcribe)
            # -------------------------------------------------------
            # Deepgram v3 expects a specific payload structure for raw files
            # mimetype is optional but helps accuracy
            payload = {
                "buffer": audio_file.read(),
            }
            
            # Options for Deepgram
            options = PrerecordedOptions(
                model="nova-2", 
                smart_format=True,
                language="en" # Detects accents well even if set to English
            )

            # Call Deepgram API
            # FIX: Add # type: ignore because 'prerecorded' is generated dynamically
            response = self.deepgram.listen.prerecorded.v("1").transcribe_file(payload, options) # type: ignore
            
            # Extract the text
            # Deepgram v3 response object access
            farmer_query_text = response.results.channels[0].alternatives[0].transcript
            
            if not farmer_query_text:
                logger.warning("Deepgram returned empty transcription")
                return None

            logger.info(f"Transcribed Text: {farmer_query_text}")

            # -------------------------------------------------------
            # STEP 2: AI PROCESSING (Think)
            # -------------------------------------------------------
            lang_name = self._get_language_name(language_code)
            context = f"Reply strictly in {lang_name}. Keep the answer short, simple, and spoken-style for a rural farmer."
            
            ai_text_response = gemini_service.answer_farming_question(farmer_query_text, context=context)
            
            logger.info(f"AI Response ({lang_name}): {ai_text_response}")

            # -------------------------------------------------------
            # STEP 3: TEXT-TO-SPEECH (Speak)
            # -------------------------------------------------------
            audio_content = tts_service.generate_audio(ai_text_response, language_code)

            if not audio_content:
                logger.error("TTS Service failed to generate audio")
                return {
                    "transcription": farmer_query_text,
                    "text_response": ai_text_response,
                    "audio_content": None
                }

            return {
                "transcription": farmer_query_text,
                "text_response": ai_text_response,
                "audio_content": audio_content
            }

        except Exception as e:
            logger.error(f"STS Pipeline Error: {str(e)}")
            return None

    def _get_language_name(self, code):
        """Helper to map code to full language name for Gemini prompt"""
        mapping = {
            'ha': 'Hausa',
            'yo': 'Yoruba',
            'ig': 'Igbo',
            'pcm': 'Nigerian Pidgin English',
            'en': 'English'
        }
        return mapping.get(code, 'English')

# Singleton instance
sts_service = SpeechToSpeechService()