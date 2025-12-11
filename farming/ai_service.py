"""
AgroMentor 360 - Gemini AI Service
Crop recommendations, disease detection, and farming guidance using Google Gemini
"""

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from django.conf import settings
from PIL import Image
import io
import logging
import json

logger = logging.getLogger(__name__)


class GeminiAIService:
    """
    Service class for Google Gemini AI integrations
    """
    def __init__(self):
        """
        Initialize Gemini AI with API key from settings
        """
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_CONFIG['MODEL'],
            api_key=settings.GEMINI_CONFIG['API_KEY']
        )
        self.generation_config = GenerationConfig(
            temperature=settings.GEMINI_CONFIG['TEMPERATURE'],
            max_output_tokens=settings.GEMINI_CONFIG['MAX_OUTPUT_TOKENS'],
        )
    
    def get_crop_recommendations(self, user_data):
        """
        Get AI-powered crop recommendations based on location, season, soil, experience
        
        Args:
            user_data (dict): Contains location, season, soil_type, experience_level, farm_size
            
        Returns:
            dict: Recommendations with crop suggestions, tips, and timeline
        """
        try:
            # Build context-rich prompt
            prompt = f"""
            You are an expert agricultural advisor in Nigeria. Provide crop recommendations for a farmer with these details:
            
            Location: {user_data.get('city', 'Nigeria')}, {user_data.get('state', '')}
            Season: {user_data.get('season', 'Current season')}
            Soil Type: {user_data.get('soil_type', 'Unknown')}
            Soil pH: {user_data.get('soil_ph', 'Unknown')}
            Experience Level: {user_data.get('experience_level', 'beginner')}
            Farm Size: {user_data.get('farm_size', 'small')}
            Farm Type: {user_data.get('farm_type', 'traditional')}
            
            Provide:
            1. Top 5 recommended crops suitable for this location and conditions
            2. For each crop:
               - Why it's suitable
               - Expected planting season
               - Growing duration
               - Expected yield
               - Difficulty level
               - Market demand
            3. General farming tips for this location
            4. Climate considerations
            
            Format response as JSON with this structure:
            {{
                "recommendations": [
                    {{
                        "crop_name": "name",
                        "category": "vegetables/fruits/grains/etc",
                        "suitability_score": 85,
                        "reasons": ["reason1", "reason2"],
                        "planting_season": "March-April",
                        "growing_duration_days": 90,
                        "expected_yield_per_hectare": "5-8 tons",
                        "difficulty": "easy/medium/hard",
                        "market_demand": "high/medium/low",
                        "tips": ["tip1", "tip2"]
                    }}
                ],
                "general_tips": ["tip1", "tip2"],
                "climate_notes": "Climate information"
            }}
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            # Parse JSON response
            result = self._parse_json_response(response.text)
            
            logger.info(f"Generated crop recommendations for {user_data.get('city')}")
            return result
        
        except Exception as e:
            logger.error(f"Error generating crop recommendations: {str(e)}")
            return self._fallback_crop_recommendations(user_data)
    
    def detect_disease(self, image_file, crop_name=None):
        """
        Detect crop diseases from image using Gemini Vision
        
        Args:
            image_file: Image file object
            crop_name: Optional crop name for better context
            
        Returns:
            dict: Disease detection results with treatment recommendations
        """
        try:
            # Load and process image
            image = Image.open(image_file)
            
            # Build prompt for disease detection
            crop_context = f"This is a {crop_name} plant. " if crop_name else "This is a crop plant. "
            
            prompt = f"""
            {crop_context}Analyze this image for any plant diseases, pests, or health issues.
            
            Provide a detailed analysis including:
            1. Disease/problem identification (if any)
            2. Confidence level (0-100%)
            3. Severity assessment (low/medium/high/critical)
            4. Detailed symptoms observed
            5. Treatment recommendations (3-5 specific treatments)
            6. Preventive measures for future
            7. When to seek expert help
            
            Format as JSON:
            {{
                "disease_detected": true/false,
                "disease_name": "disease name or 'Healthy'",
                "confidence_score": 85,
                "severity": "low/medium/high/critical",
                "symptoms": ["symptom1", "symptom2"],
                "analysis": "Detailed analysis text",
                "treatment_recommendations": [
                    {{
                        "treatment": "treatment description",
                        "application": "how to apply",
                        "frequency": "application frequency"
                    }}
                ],
                "preventive_measures": ["measure1", "measure2"],
                "expert_consultation_needed": true/false,
                "additional_notes": "Any other important information"
            }}
            
            If the image is not clear or not a plant, indicate that clearly.
            """
            
            # Generate response with image
            response = self.model.generate_content(
                [prompt, image],
                generation_config=self.generation_config
            )
            
            # Parse JSON response
            result = self._parse_json_response(response.text)
            
            logger.info(f"Disease detection completed: {result.get('disease_name', 'N/A')}")
            return result
        
        except Exception as e:
            logger.error(f"Error in disease detection: {str(e)}")
            return {
                'disease_detected': False,
                'disease_name': 'Analysis Error',
                'confidence_score': 0,
                'analysis': f'Failed to analyze image: {str(e)}',
                'treatment_recommendations': [],
                'preventive_measures': [],
                'expert_consultation_needed': True
            }
    
    def generate_farming_tips(self, crop_name, growth_stage, location):
        """
        Generate stage-specific farming tips
        
        Args:
            crop_name: Name of the crop
            growth_stage: Current growth stage (planted, growing, flowering, etc.)
            location: Farm location
            
        Returns:
            dict: Stage-specific tips and care instructions
        """
        try:
            prompt = f"""
            Provide detailed farming tips for {crop_name} currently in the '{growth_stage}' stage, 
            located in {location}, Nigeria.
            
            Include:
            1. Current stage care instructions
            2. What to watch for (problems, pests, diseases)
            3. Watering requirements
            4. Fertilizer recommendations
            5. Expected duration of this stage
            6. Signs of healthy growth
            7. Common problems at this stage
            
            Format as JSON with clear, actionable tips.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            result = self._parse_json_response(response.text)
            return result
        
        except Exception as e:
            logger.error(f"Error generating farming tips: {str(e)}")
            return {'error': str(e)}
    
    def analyze_yield_prediction(self, crop_data):
        """
        Predict expected yield based on crop and farm data
        
        Args:
            crop_data: Dictionary containing crop information
            
        Returns:
            dict: Yield prediction with factors affecting yield
        """
        try:
            prompt = f"""
            Analyze and predict yield for this crop:
            
            Crop: {crop_data.get('crop_name')}
            Location: {crop_data.get('location')}
            Area: {crop_data.get('area_planted')} square meters
            Plant Date: {crop_data.get('plant_date')}
            Soil Type: {crop_data.get('soil_type')}
            Farming Method: {crop_data.get('farming_method', 'traditional')}
            
            Provide:
            1. Expected yield range (min-max in kg)
            2. Factors affecting yield
            3. Tips to maximize yield
            4. Best harvest timing
            
            Format as JSON.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            result = self._parse_json_response(response.text)
            return result
        
        except Exception as e:
            logger.error(f"Error in yield prediction: {str(e)}")
            return {'error': str(e)}
    
    def answer_farming_question(self, question, context=None):
        """
        Answer farmer's questions using AI
        
        Args:
            question: Farmer's question
            context: Optional context (crop, location, etc.)
            
        Returns:
            str: AI-generated answer
        """
        try:
            context_str = f"\nContext: {context}" if context else ""
            
            prompt = f"""
            You are an expert agricultural advisor in Nigeria. Answer this farmer's question 
            with practical, actionable advice suitable for Nigerian farming conditions.
            
            Question: {question}{context_str}
            
            Provide a clear, concise answer with:
            1. Direct answer to the question
            2. Practical steps if applicable
            3. Important considerations
            4. Additional tips
            
            Keep the language simple and accessible.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            return response.text
        
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return "I apologize, but I'm unable to answer that question right now. Please try again or consult with an expert."
    
    def _parse_json_response(self, text):
        """
        Parse JSON from AI response, handling markdown code blocks
        
        Args:
            text: Response text from Gemini
            
        Returns:
            dict: Parsed JSON data
        """
        try:
            # Remove markdown code blocks if present
            text = text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            return json.loads(text.strip())
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            # Return text as-is in analysis field if JSON parsing fails
            return {
                'analysis': text,
                'error': 'Failed to parse structured response'
            }
    
    def _fallback_crop_recommendations(self, user_data):
        """
        Provide basic fallback recommendations if AI fails
        
        Args:
            user_data: User's location and farm data
            
        Returns:
            dict: Basic recommendations
        """
        # Basic recommendations for common Nigerian crops
        return {
            'recommendations': [
                {
                    'crop_name': 'Tomatoes',
                    'category': 'vegetables',
                    'suitability_score': 80,
                    'reasons': ['Grows well in most Nigerian climates', 'High market demand'],
                    'planting_season': 'March-April or September-October',
                    'growing_duration_days': 90,
                    'expected_yield_per_hectare': '15-25 tons',
                    'difficulty': 'medium',
                    'market_demand': 'high',
                    'tips': ['Requires good drainage', 'Regular watering needed']
                },
                {
                    'crop_name': 'Maize',
                    'category': 'grains',
                    'suitability_score': 85,
                    'reasons': ['Adaptable to various conditions', 'Staple crop'],
                    'planting_season': 'April-May',
                    'growing_duration_days': 120,
                    'expected_yield_per_hectare': '3-5 tons',
                    'difficulty': 'easy',
                    'market_demand': 'high',
                    'tips': ['Plant in rows', 'Weed regularly']
                }
            ],
            'general_tips': [
                'Start with crops you are familiar with',
                'Consider market demand in your area',
                'Ensure good water supply'
            ],
            'climate_notes': 'Nigerian climate suitable for diverse crops'
        }


# Singleton instance
gemini_service = GeminiAIService()