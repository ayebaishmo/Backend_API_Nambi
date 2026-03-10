"""
AI-powered Dynamic Itinerary Builder
Generates personalized itineraries through natural conversation
"""

from gemini import get_gemini_model
from services.itinerary_validator import ItineraryValidator
from models.itinerary import Itinerary
from extensions import db
import json
import re


class ItineraryBuilder:
    """Build personalized itineraries using AI"""
    
    # Required information to build an itinerary
    REQUIRED_INFO = {
        'duration': 'How many days will you be traveling?',
        'budget': 'What is your approximate budget per person (in USD)?',
        'interests': 'What are you most interested in? (e.g., wildlife, culture, adventure, relaxation)',
        'pace': 'Do you prefer a relaxed or packed schedule?',
        'accommodation': 'What type of accommodation do you prefer? (budget, mid-range, luxury)',
    }
    
    @staticmethod
    def extract_itinerary_info(conversation_history):
        """
        Extract itinerary information from conversation history
        Returns dict with extracted info and list of missing fields
        """
        info = {
            'duration': None,
            'budget': None,
            'interests': None,
            'pace': None,
            'accommodation': None,
            'start_date': None,
            'group_size': None
        }
        
        # Combine all user messages
        user_text = ' '.join([
            msg['content'] for msg in conversation_history 
            if msg['role'] == 'user'
        ]).lower()
        
        # Extract duration (days)
        duration_patterns = [
            r'(\d+)\s*days?',
            r'(\d+)\s*day\s+trip',
            r'for\s+(\d+)\s+days?'
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, user_text)
            if match:
                info['duration'] = int(match.group(1))
                break
        
        # Extract budget
        budget_patterns = [
            r'\$?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:usd|dollars?)?',
            r'budget\s+(?:of\s+)?(?:around\s+)?\$?(\d+)',
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, user_text)
            if match:
                budget_str = match.group(1).replace(',', '')
                info['budget'] = float(budget_str)
                break
        
        # Extract interests (keywords)
        interest_keywords = {
            'wildlife': ['safari', 'wildlife', 'animals', 'gorilla', 'chimpanzee', 'game drive'],
            'culture': ['culture', 'cultural', 'traditional', 'history', 'heritage', 'local'],
            'adventure': ['adventure', 'hiking', 'rafting', 'climbing', 'trekking'],
            'relaxation': ['relax', 'relaxation', 'peaceful', 'calm', 'leisure'],
            'nature': ['nature', 'scenery', 'landscape', 'mountains', 'lakes']
        }
        
        detected_interests = []
        for interest, keywords in interest_keywords.items():
            if any(keyword in user_text for keyword in keywords):
                detected_interests.append(interest)
        
        if detected_interests:
            info['interests'] = ', '.join(detected_interests)
        
        # Extract pace
        if any(word in user_text for word in ['relaxed', 'slow', 'leisure', 'easy']):
            info['pace'] = 'relaxed'
        elif any(word in user_text for word in ['packed', 'busy', 'full', 'action']):
            info['pace'] = 'packed'
        
        # Extract accommodation preference
        if any(word in user_text for word in ['budget', 'cheap', 'affordable', 'backpack']):
            info['accommodation'] = 'budget'
        elif any(word in user_text for word in ['luxury', 'upscale', 'premium', 'high-end']):
            info['accommodation'] = 'luxury'
        elif any(word in user_text for word in ['mid-range', 'moderate', 'standard']):
            info['accommodation'] = 'mid-range'
        
        # Extract group size
        group_patterns = [
            r'(\d+)\s+(?:people|persons|travelers|pax)',
            r'group\s+of\s+(\d+)',
            r'(\d+)\s+of\s+us'
        ]
        for pattern in group_patterns:
            match = re.search(pattern, user_text)
            if match:
                info['group_size'] = int(match.group(1))
                break
        
        # Determine missing required fields
        missing = []
        for field in ['duration', 'budget', 'interests', 'accommodation']:
            if not info[field]:
                missing.append(field)
        
        return info, missing
    
    @staticmethod
    def generate_clarification_question(missing_fields):
        """Generate a natural question to gather missing information"""
        if not missing_fields:
            return None
        
        field = missing_fields[0]
        return ItineraryBuilder.REQUIRED_INFO.get(field)
    
    @staticmethod
    def generate_itinerary(info, site_content):
        """
        Generate a detailed itinerary using AI
        """
        model = get_gemini_model()
        
        # Build the prompt
        prompt = f"""You are an expert Uganda travel planner. Create a detailed, day-by-day itinerary based on these requirements:

TRAVELER REQUIREMENTS:
- Duration: {info['duration']} days
- Budget: ${info['budget']} per person
- Interests: {info['interests']}
- Pace: {info.get('pace', 'moderate')}
- Accommodation: {info['accommodation']}
- Group size: {info.get('group_size', 1)} person(s)

INSTRUCTIONS:
1. Create a realistic day-by-day itinerary
2. Include specific destinations from Uganda
3. Suggest appropriate accommodations for each location
4. Include estimated costs
5. Consider travel time between destinations
6. Match the pace preference (relaxed = fewer activities, packed = more activities)
7. Focus on the traveler's interests

UGANDA CONTEXT (use this information):
{site_content[:3000]}

OUTPUT FORMAT (JSON):
{{
  "title": "Descriptive title",
  "days": {info['duration']},
  "budget": "{info['budget']}",
  "places": "Comma-separated list of destinations",
  "accommodation": "Accommodation recommendations",
  "transport": "Transportation details",
  "details": "Day-by-day breakdown with activities",
  "package_name": "Budget/Silver/Gold/Platinum based on budget level"
}}

Generate the itinerary now:"""
        
        try:
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                itinerary_data = json.loads(json_match.group())
                return itinerary_data, None
            else:
                # If no JSON, parse the text response
                return ItineraryBuilder._parse_text_response(response_text, info), None
                
        except Exception as e:
            return None, f"Failed to generate itinerary: {str(e)}"
    
    @staticmethod
    def _parse_text_response(text, info):
        """Parse a text response into itinerary format"""
        # Extract destinations
        places = []
        for line in text.split('\n'):
            if any(keyword in line.lower() for keyword in ['day', 'visit', 'destination']):
                # Extract location names (simple heuristic)
                words = line.split()
                for word in words:
                    if word[0].isupper() and len(word) > 3:
                        places.append(word)
        
        return {
            'title': f"{info['duration']} Days Uganda Adventure",
            'days': info['duration'],
            'budget': str(info['budget']),
            'places': ', '.join(places[:5]) if places else 'Kampala, Entebbe',
            'accommodation': f"{info['accommodation']} accommodations",
            'transport': 'Private vehicle with driver-guide',
            'details': text,
            'package_name': ItineraryBuilder._determine_package(info['budget'])
        }
    
    @staticmethod
    def _determine_package(budget):
        """Determine package tier based on budget"""
        if budget < 100:
            return 'Budget'
        elif budget < 250:
            return 'Silver'
        elif budget < 500:
            return 'Gold'
        else:
            return 'Platinum'
    
    @staticmethod
    def save_itinerary(itinerary_data, session_id=None):
        """
        Save generated itinerary to database with validation
        """
        # Convert details to string if it's a dict/list
        details = itinerary_data['details']
        if isinstance(details, (dict, list)):
            import json
            details = json.dumps(details, indent=2)
        
        # Validate the itinerary
        validation_result = ItineraryValidator.validate_complete_itinerary(itinerary_data)
        
        # Create itinerary object
        itinerary = Itinerary(
            title=itinerary_data['title'],
            days=itinerary_data['days'],
            budget=itinerary_data['budget'],
            places=itinerary_data['places'],
            accommodation=itinerary_data['accommodation'],
            transport=itinerary_data['transport'],
            details=details,  # Use converted string
            package_name=itinerary_data['package_name']
        )
        
        db.session.add(itinerary)
        db.session.commit()
        
        return {
            'itinerary_id': itinerary.id,
            'validation': validation_result,
            'itinerary': itinerary_data
        }
