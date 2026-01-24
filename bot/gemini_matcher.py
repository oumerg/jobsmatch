"""
Gemini AI Job Matcher
Uses Google Gemini API for intelligent job matching based on user preferences
"""

import logging
import asyncio
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from bot.config import Config

logger = logging.getLogger(__name__)

class GeminiJobMatcher:
    """AI-powered job matcher using Google Gemini"""
    
    def __init__(self):
        self.model = None
        self.api_key = Config.GEMINI_API_KEY
        self.model_name = Config.GEMINI_MODEL
        self.temperature = Config.GEMINI_TEMPERATURE
        self.max_tokens = Config.GEMINI_MAX_TOKENS
        
    async def initialize(self) -> bool:
        """Initialize Gemini AI model"""
        try:
            if not self.api_key:
                logger.error("GEMINI_API_KEY not configured!")
                return False
                
            # Configure Gemini API
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            
            logger.info(f"✅ Gemini AI initialized with model: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            return False
    
    async def match_job_to_user(self, job_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Gemini AI to determine if a job matches user preferences
        
        Returns:
        {
            'match_score': float (0.0-1.0),
            'match_reason': str,
            'recommendation': str,
            'is_match': bool
        }
        """
        try:
            # Create matching prompt
            prompt = self._create_matching_prompt(job_data, user_preferences)
            
            # Get AI response with timeout
            response = await asyncio.wait_for(
                self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=self.temperature,
                        max_output_tokens=self.max_tokens
                    )
                ),
                timeout=15.0  # 15 second timeout
            )
            
            # Parse AI response
            result = self._parse_ai_response(response.text)
            return result
            
        except asyncio.TimeoutError:
            logger.error("⏰ Gemini AI timeout during job matching")
            return {
                'match_score': 0.0,
                'match_reason': 'AI matching timeout',
                'recommendation': 'Unable to process job match due to timeout',
                'is_match': False
            }
        except Exception as e:
            logger.error(f"❌ Error in Gemini matching: {e}")
            return {
                'match_score': 0.0,
                'match_reason': 'Error in AI matching process',
                'recommendation': 'Unable to process job match',
                'is_match': False
            }
    
    def _create_matching_prompt(self, job_data: Dict[str, Any], user_preferences: Dict[str, Any]) -> str:
        """Create a comprehensive prompt for job matching"""
        
        job_info = f"""
Job Details:
- Title: {job_data.get('title', 'N/A')}
- Company: {job_data.get('company_name', 'N/A')}
- Location: {job_data.get('location', 'N/A')}
- Job Type: {job_data.get('job_type', 'N/A')}
- Salary: {job_data.get('salary_range', 'N/A')}
- Description: {job_data.get('description', 'N/A')[:500]}...
"""
        
        user_info = f"""
User Preferences:
- Preferred Job Types: {', '.join(user_preferences.get('preferred_job_types', []))}
- Preferred Locations: {', '.join(user_preferences.get('preferred_locations', []))}
- Preferred Categories: {', '.join(user_preferences.get('preferred_categories', []))}
- Min Salary: {user_preferences.get('min_salary', 'Not specified')}
- Max Experience: {user_preferences.get('max_experience', 'Not specified')} years
- Education Level: {user_preferences.get('education_level', 'Not specified')}
- Keywords: {', '.join(user_preferences.get('keywords', []))}
"""
        
        prompt = f"""
You are an expert job matching AI for the Ethiopian job market. Analyze the job and user preferences below and provide a detailed matching analysis.

{job_info}

{user_info}

Please analyze this job against the user's preferences and provide:

1. Match Score (0.0-1.0): How well this job matches the user
2. Match Reason: Brief explanation of why it matches or doesn't match
3. Recommendation: Personalized message to the user about this opportunity
4. Is Match: true/false - whether to forward this job to the user

Consider Ethiopian job market context, cultural factors, and realistic expectations. Be fair and encouraging.

Respond in JSON format:
{{
    "match_score": 0.0,
    "match_reason": "Brief explanation",
    "recommendation": "Personalized message",
    "is_match": false
}}
"""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response to extract structured data"""
        try:
            # Try to extract JSON from response
            # Look for JSON pattern in the response
            import re
            
            # Find JSON object in the response
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Fallback: create structured response from text
            return self._create_fallback_response(response_text)
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return {
                'match_score': 0.0,
                'match_reason': 'Error parsing AI response',
                'recommendation': 'Unable to process job match',
                'is_match': False
            }
    
    def _create_fallback_response(self, response_text: str) -> Dict[str, Any]:
        """Create structured response from text when JSON parsing fails"""
        text_lower = response_text.lower()
        
        # Simple keyword-based matching as fallback
        match_score = 0.0
        is_match = False
        
        # Check for positive indicators
        positive_words = ['match', 'suitable', 'good fit', 'excellent', 'perfect', 'highly recommended']
        negative_words = ['not match', 'unsuitable', 'poor fit', 'not recommended', 'inappropriate']
        
        for word in positive_words:
            if word in text_lower:
                match_score = max(match_score, 0.7)
                is_match = True
        
        for word in negative_words:
            if word in text_lower:
                match_score = min(match_score, 0.3)
                is_match = False
        
        # Extract recommendation (first paragraph or line)
        lines = response_text.split('\n')
        recommendation = lines[0] if lines else "Job opportunity available"
        
        # Extract reasoning (look for reasoning keywords)
        reasoning = "AI analysis completed"
        for line in lines:
            if any(keyword in line.lower() for keyword in ['because', 'due to', 'since', 'based on']):
                reasoning = line.strip()
                break
        
        return {
            'match_score': match_score,
            'match_reason': reasoning,
            'recommendation': recommendation,
            'is_match': is_match
        }
    
    async def get_user_preferences(self, user_id: int, db_manager) -> Dict[str, Any]:
        """Get user preferences from database"""
        try:
            if db_manager:
                query = """
                    SELECT up.* 
                    FROM user_preferences up
                    WHERE up.user_id = $1
                """
                
                result = await db_manager.execute_query(query, (user_id,))
                
                if result:
                    return result[0]
            
            # Return default preferences if no DB or no result
            return {
                'preferred_job_types': [],
                'preferred_locations': [],
                'preferred_categories': [],
                'min_salary': None,
                'max_experience': None,
                'education_level': None,
                'keywords': []
            }
                    
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return {
                'preferred_job_types': [],
                'preferred_locations': [],
                'preferred_categories': [],
                'min_salary': None,
                'max_experience': None,
                'education_level': None,
                'keywords': []
            }
    
    async def batch_match_jobs(self, jobs: List[Dict[str, Any]], users: List[Dict[str, Any]], db_manager=None) -> List[Dict[str, Any]]:
        """Match multiple jobs to multiple users efficiently"""
        matches = []
        
        for job in jobs:
            for user in users:
                try:
                    # Add timeout for individual user matching
                    user_prefs = await asyncio.wait_for(
                        self.get_user_preferences(user['user_id'], db_manager),
                        timeout=5.0  # 5 second timeout
                    )
                    
                    match_result = await asyncio.wait_for(
                        self.match_job_to_user(job, user_prefs),
                        timeout=20.0  # 20 second timeout per match
                    )
                    
                    if match_result['is_match']:
                        matches.append({
                            'user_id': user['user_id'],
                            'user_telegram_id': user['telegram_id'],
                            'job_data': job,
                            'match_score': match_result['match_score'],
                            'match_reason': match_result['match_reason'],
                            'recommendation': match_result['recommendation']
                        })
                        
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ Timeout matching job {job.get('title')} to user {user['user_id']}")
                    continue
                except Exception as e:
                    logger.error(f"Error matching job {job.get('title')} to user {user['user_id']}: {e}")
                    continue
        
        return matches
