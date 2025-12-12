import requests
from agrosphere import settings
import logging

logger = logging.getLogger(__name__)

class YarnGPTService:
    """
    Service for converting text to speech using YarnGPT (Nigerian Languages)
    """
    def __init__(self):
        # Hugging Face API Token
        self.api_url = "https://yarngpt.ai/api/v1/tts"  # Example Endpoint
        self.api_key = settings.YARNGPT_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def generate_audio(self, text, language_code='pcm'):
        """
        Convert text to audio in Nigerian languages.
        
        Args:
            text (str): The text to speak
            language_code (str): 'yo'(Yoruba), 'ig'(Igbo), 'ha'(Hausa), 'pcm'(Pidgin)
            
        Returns:
            bytes: Audio content (MP3/WAV)
        """
        try:
            # Prompt engineering for YarnGPT usually involves prefixing the language
            # Example prompt: "yoruba: Bawo ni, se daadaa ni?"
            
            payload = {
                "inputs": f"{language_code}: {text}",
                "options": {"wait_for_model": True}
            }
            
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"YarnGPT API Error: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"TTS Service Error: {str(e)}")
            return None

# Singleton instance
tts_service = YarnGPTService()