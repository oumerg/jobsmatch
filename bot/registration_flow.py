"""
Complete User Registration Flow with 1-Day Free Trial
Handles user registration, preference collection, and subscription management
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.user_preferences import PreferenceCollector

logger = logging.getLogger(__name__)

class RegistrationFlow:
    """Manages complete user registration process"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.registration_states = {}  # Track user registration progress
        self.preference_collector = PreferenceCollector(db_manager)
    
    async def start_registration(self, user_id: int, user_data: Dict[str, Any]) -> str:
        """Start the registration process for new user"""
        
        # Create 1-day free trial subscription
        trial_end = datetime.now() + timedelta(days=1)
        
        try:
            # Create trial subscription
            subscription_query = """
                INSERT INTO subscriptions (user_id, status, start_date, end_date, payment_method, transaction_ref, amount_birr)
                VALUES ($1, 'trial', CURRENT_DATE, $2, 'trial', 'free_trial', 0.00)
            """
            await self.db.connection.execute(subscription_query, user_id, trial_end.date())
            
            # Initialize registration state
            self.registration_states[user_id] = {
                'step': 'welcome',
                'user_data': user_data,
                'preferences': {},
                'trial_end': trial_end
            }
            
            logger.info(f"Started registration for user {user_id} with 1-day trial ending {trial_end}")
            
            return self._get_welcome_message(user_id)
            
        except Exception as e:
            logger.error(f"Error starting registration for user {user_id}: {e}")
            return "Error starting registration. Please try again."
    
    def _get_welcome_message(self, user_id: int) -> str:
        """Get welcome message for new user"""
        trial_end = self.registration_states[user_id]['trial_end']
        
        message = (
            f"*Welcome to Ethiopian Job Bot!*\n\n"
            f"Name: {self.registration_states[user_id]['user_data'].get('first_name', '')}\n"
            f"Phone: {self.registration_states[user_id]['user_data'].get('phone_number', '')}\n\n"
            f"*1-Day Free Trial Activated!*\n"
            f"Trial ends: {trial_end.strftime('%B %d, %Y')}\n"
            f"After trial: 50 Birr/month\n\n"
            f"Let's set up your job preferences to find perfect opportunities!\n\n"
            f"*Step 1: Industry/Sector*\n\n"
            f"Select your preferred industry:"
        )
        
        return message
    
    def get_career_level_keyboard(self) -> InlineKeyboardMarkup:
        """Get career level options keyboard as inline buttons"""
        keyboard = [
            [
                InlineKeyboardButton("Student / Intern", callback_data="reg_experience_student"),
                InlineKeyboardButton("Entry Level (0-2)", callback_data="reg_experience_entry")
            ],
            [
                InlineKeyboardButton("Junior (2-5)", callback_data="reg_experience_junior"),
                InlineKeyboardButton("Mid-Level (5-10)", callback_data="reg_experience_mid")
            ],
            [
                InlineKeyboardButton("Senior (10+)", callback_data="reg_experience_senior"),
                InlineKeyboardButton("Manager / Lead", callback_data="reg_experience_manager")
            ],
            [
                InlineKeyboardButton("Director / Executive", callback_data="reg_experience_director"),
                InlineKeyboardButton("Other", callback_data="reg_experience_other")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_job_type_keyboard(self) -> List[List[str]]:
        """Get job type options keyboard"""
        return [
            ["Full Time", "Part Time"],
            ["Remote", "Freelance"],
            ["Contract", "Internship"]
        ]
    
    def get_industry_keyboard(self) -> InlineKeyboardMarkup:
        """Get industry/sector options keyboard as inline buttons"""
        keyboard = [
            [
                InlineKeyboardButton("Technology / IT", callback_data="reg_industry_technology"),
                InlineKeyboardButton("Banking / Finance", callback_data="reg_industry_finance")
            ],
            [
                InlineKeyboardButton("Healthcare", callback_data="reg_industry_healthcare"),
                InlineKeyboardButton("Education", callback_data="reg_industry_education")
            ],
            [
                InlineKeyboardButton("Manufacturing", callback_data="reg_industry_manufacturing"),
                InlineKeyboardButton("Retail / Sales", callback_data="reg_industry_retail")
            ],
            [
                InlineKeyboardButton("Marketing / Media", callback_data="reg_industry_marketing"),
                InlineKeyboardButton("Government", callback_data="reg_industry_government")
            ],
            [
                InlineKeyboardButton("Construction", callback_data="reg_industry_construction"),
                InlineKeyboardButton("Transportation", callback_data="reg_industry_transportation")
            ],
            [
                InlineKeyboardButton("Agriculture", callback_data="reg_industry_agriculture"),
                InlineKeyboardButton("Hospitality", callback_data="reg_industry_hospitality")
            ],
            [
                InlineKeyboardButton("Legal", callback_data="reg_industry_legal"),
                InlineKeyboardButton("Research", callback_data="reg_industry_research")
            ],
            [
                InlineKeyboardButton("HR / Recruitment", callback_data="reg_industry_hr"),
                InlineKeyboardButton("Consulting", callback_data="reg_industry_consulting")
            ],
            [
                InlineKeyboardButton("Creative / Design", callback_data="reg_industry_creative"),
                InlineKeyboardButton("Other", callback_data="reg_industry_other")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_location_keyboard(self) -> InlineKeyboardMarkup:
        """Get Ethiopian location options keyboard as inline buttons"""
        keyboard = [
            [
                InlineKeyboardButton("Addis Ababa", callback_data="reg_location_addis"),
                InlineKeyboardButton("Dire Dawa", callback_data="reg_location_dire")
            ],
            [
                InlineKeyboardButton("Remote", callback_data="reg_location_remote")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_education_keyboard(self) -> InlineKeyboardMarkup:
        """Get education level options keyboard as inline buttons"""
        keyboard = [
            [
                InlineKeyboardButton("High School", callback_data="reg_education_highschool"),
                InlineKeyboardButton("Diploma", callback_data="reg_education_diploma")
            ],
            [
                InlineKeyboardButton("Bachelor's Degree", callback_data="reg_education_bachelor"),
                InlineKeyboardButton("Master's Degree", callback_data="reg_education_master")
            ],
            [
                InlineKeyboardButton("PhD / Doctorate", callback_data="reg_education_phd"),
                InlineKeyboardButton("Other / Professional", callback_data="reg_education_other")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_salary_keyboard(self) -> InlineKeyboardMarkup:
        """Get salary range options keyboard as inline buttons"""
        keyboard = [
            [
                InlineKeyboardButton("< 5,000 Birr", callback_data="reg_salary_5000"),
                InlineKeyboardButton("5,000 - 10,000", callback_data="reg_salary_10000")
            ],
            [
                InlineKeyboardButton("10,000 - 15,000", callback_data="reg_salary_15000"),
                InlineKeyboardButton("15,000 - 25,000", callback_data="reg_salary_25000")
            ],
            [
                InlineKeyboardButton("25,000 - 40,000", callback_data="reg_salary_40000"),
                InlineKeyboardButton("40,000 - 60,000", callback_data="reg_salary_60000")
            ],
            [
                InlineKeyboardButton("> 60,000 Birr", callback_data="reg_salary_60000plus"),
                InlineKeyboardButton("Negotiable", callback_data="reg_salary_negotiable")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_skills_keyboard(self) -> List[List[str]]:
        """Get skills options keyboard"""
        return [
            ["Python", "JavaScript", "HTML/CSS"],
            ["React", "Node.js", "Java"],
            ["C#", "SQL", "Excel"],
            ["Accounting", "Marketing", "Sales"],
            ["Customer Service", "Project Management", "Data Analysis"],
            ["Graphic Design", "Content Writing", "Social Media"],
            ["Add Custom Skill", "Done with Skills"]
        ]
    
    async def handle_registration_response(self, user_id: int, response: str) -> Optional[str]:
        """Handle user response during registration flow"""
        
        if user_id not in self.registration_states:
            return "Please start registration with /start"
        
        state = self.registration_states[user_id]
        step = state['step']
        
        # Process response based on current step
        if step == 'welcome':
            return await self._handle_industry(user_id, response)
        elif step == 'industry':
            return await self._handle_location(user_id, response)
        elif step == 'location':
            return await self._handle_education(user_id, response)
        elif step == 'education':
            return await self._handle_salary(user_id, response)
        elif step == 'salary':
            return await self._handle_experience(user_id, response)
        elif step == 'skills':
            return await self._handle_skills(user_id, response)
        elif step == 'experience':
            return await self._handle_field_of_study(user_id, response)
        elif step == 'field_of_study':
            return await self._complete_registration(user_id)
        else:
            return None
    
    async def _handle_industry(self, user_id: int, response: str) -> str:
        """Handle industry selection"""
        self.registration_states[user_id]['step'] = 'industry'
        self.registration_states[user_id]['preferences']['industry'] = response
        
        message = (
            f"Industry: {response}\n\n"
            f"*Step 2: Location*\n\n"
            f"Select your preferred work location:"
        )
        
        return message
    
    async def _handle_location(self, user_id: int, response: str) -> str:
        """Handle location selection"""
        self.registration_states[user_id]['step'] = 'location'
        self.registration_states[user_id]['preferences']['locations'] = [response]
        
        message = (
            f"Location: {response}\n\n"
            f"*Step 3: Education Level*\n\n"
            f"Select your highest education level:"
        )
        
        return message
    
    async def _handle_education(self, user_id: int, response: str) -> str:
        """Handle education level selection"""
        self.registration_states[user_id]['step'] = 'education'
        self.registration_states[user_id]['preferences']['education'] = response
        
        message = (
            f"Education: {response}\n\n"
            f"*Step 4: Experience Level*\n\n"
            f"Select your experience level:"
        )
        
        return message
    
    async def _handle_salary(self, user_id: int, response: str) -> str:
        """Handle salary selection"""
        self.registration_states[user_id]['step'] = 'salary'
        self.registration_states[user_id]['preferences']['salary'] = response
        
        message = (
            f"Salary: {response}\n\n"
            f"*Step 5: Experience Level*\n\n"
            f"Select your experience level:"
        )
        
        return message
    
    async def _handle_experience_level(self, user_id: int, response: str) -> str:
        """Handle experience level selection"""
        self.registration_states[user_id]['step'] = 'experience'
        self.registration_states[user_id]['preferences']['max_experience'] = response
        
        message = (
            f"Experience Level: {response}\n\n"
            f"*Step 6: Field of Study*\n\n"
            f"What is your field of study?"
        )
        
        return message
    
    async def _handle_skills(self, user_id: int, response: str) -> str:
        """Handle skills selection"""
        if 'skills' not in self.registration_states[user_id]['preferences']:
            self.registration_states[user_id]['preferences']['skills'] = []
        
        if response not in ["Add Custom Skill", "Done with Skills"]:
            self.registration_states[user_id]['preferences']['skills'].append(response)
            message = (
                f"Added skill: {response}\n\n"
                f"*Skills selected:*\n"
                f"• {', '.join(self.registration_states[user_id]['preferences']['skills'])}\n\n"
                f"Select more skills or click 'Done with Skills':"
            )
            return message
        
        elif response == "Done with Skills":
            self.registration_states[user_id]['step'] = 'skills'
            message = (
                f"Skills completed!\n\n"
                f"*Step 6: Years of Experience*\n\n"
                f"How many years of work experience do you have?"
            )
            return message
        
        else:  # Add custom skill
            return "Please type your custom skill:"
    
    async def _handle_experience(self, user_id: int, response: str) -> str:
        """Handle experience years"""
        try:
            years = int(response)
            if years < 0 or years > 50:
                return "Please enter a valid number of years (0-50):"
            
            self.registration_states[user_id]['step'] = 'experience'
            self.registration_states[user_id]['preferences']['years_experience'] = years
            
            message = (
                f"Experience: {years} years\n\n"
                f"*Step 7: Field of Study*\n\n"
                f"What is your field of study? (e.g., Computer Science, Business, Engineering)"
            )
            
            return message
            
        except ValueError:
            return "Please enter a valid number of years:"
    
    async def _handle_field_of_study(self, user_id: int, response: str) -> str:
        """Handle field of study"""
        self.registration_states[user_id]['step'] = 'field_of_study'
        self.registration_states[user_id]['preferences']['field_of_study'] = response
        
        message = (
            f"Field of Study: {response}\n\n"
            f"*Registration Almost Complete!*\n\n"
            f"Review your preferences:\n"
            f"Industry: {self.registration_states[user_id]['preferences'].get('industry', 'Not set')}\n"
            f"Location: {', '.join(self.registration_states[user_id]['preferences'].get('locations', []))}\n"
            f"Education: {self.registration_states[user_id]['preferences'].get('education', 'Not set')}\n"
            f"Salary: {self.registration_states[user_id]['preferences'].get('salary', 'Not set')}\n"
            f"Skills: {', '.join(self.registration_states[user_id]['preferences'].get('skills', []))}\n"
            f"Experience: {self.registration_states[user_id]['preferences'].get('years_experience', 0)} years\n"
            f"Field: {self.registration_states[user_id]['preferences'].get('field_of_study', 'Not set')}\n\n"
            f"*Click 'Complete Registration' to finish!*"
        )
        
        return message
    
    async def _complete_registration(self, user_id: int) -> str:
        """Complete the registration process"""
        try:
            preferences = self.registration_states[user_id]['preferences']
            user_data = self.registration_states[user_id]['user_data']
            
            # Save job seeker profile
            seeker_query = """
                INSERT INTO job_seekers (user_id, education_level, field_of_study, years_experience, 
                                      current_job_title, preferred_location, expected_salary)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            await self.db.connection.execute(
                seeker_query,
                user_id,
                preferences.get('education', ''),
                preferences.get('field_of_study', ''),
                preferences.get('years_experience', 0),
                '',  # No career level needed
                ', '.join(preferences.get('locations', [])),
                preferences.get('salary', '')
            )
            
            # Save user preferences
            pref_query = """
                INSERT INTO user_preferences (user_id, preferred_job_types, preferred_locations, 
                                          preferred_categories, min_salary, education_level, keywords)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            
            await self.db.connection.execute(
                pref_query,
                user_id,
                [],  # No job types in registration
                preferences.get('locations', []),
                [preferences.get('industry', '')],
                0,  # Will be calculated from salary preference
                preferences.get('education', ''),
                preferences.get('skills', [])
            )
            
            # Save skills
            for skill in preferences.get('skills', []):
                # Check if skill exists
                skill_check = await self.db.connection.fetchval(
                    "SELECT skill_id FROM skills WHERE name = $1", skill
                )
                
                if not skill_check:
                    # Add new skill
                    skill_id = await self.db.connection.fetchval(
                        "INSERT INTO skills (name) VALUES ($1) RETURNING skill_id", skill
                    )
                else:
                    skill_id = skill_check
                
                # Link skill to user
                await self.db.connection.execute(
                    "INSERT INTO seeker_skills (user_id, skill_id, level) VALUES ($1, $2, 'intermediate')",
                    user_id, skill_id
                )
            
            # Get trial end date before cleaning up state
            trial_end = self.registration_states[user_id].get('trial_end', datetime.now() + timedelta(days=1))
            
            # Clean up registration state
            del self.registration_states[user_id]
            
            success_message = (
                f"*Registration Complete!*\n\n"
                f"Your 1-day free trial is active!\n"
                f"Trial ends: {trial_end.strftime('%B %d, %Y')}\n\n"
                f"*What happens now?*\n"
                f"We'll find jobs matching your preferences\n"
                f"You'll receive job notifications\n"
                f"You can apply for jobs immediately\n\n"
                f"*Start exploring:*\n"
                f"/jobs - Browse available jobs\n"
                f"/preferences - Update your preferences\n"
                f"/profile - View your profile\n"
                f"/subscribe - Upgrade to premium\n\n"
                f"Welcome to Ethiopian Job Bot!"
            )
            
            logger.info(f"Registration completed for user {user_id}")
            return success_message
            
        except Exception as e:
            logger.error(f"Error completing registration for user {user_id}: {e}")
            return "Error completing registration. Please try again or contact support."
    
    def get_keyboard_for_step(self, user_id: int) -> Optional[InlineKeyboardMarkup]:
        """Get appropriate keyboard for current registration step as inline buttons"""
        if user_id not in self.registration_states:
            logger.warning(f"No registration state found for user {user_id}")
            return None
        
        step = self.registration_states[user_id]['step']
        logger.info(f"Getting keyboard for step: {step}")
        
        keyboard_map = {
            'welcome': self.get_industry_keyboard(),
            'industry': self.get_location_keyboard(),
            'location': self.get_education_keyboard(),
            'education': self.get_career_level_keyboard(),
            'salary': self.get_salary_keyboard(),
            'skills': None,  # No keyboard for skills step - user types text
            'experience': self.get_career_level_keyboard(),  # Experience selection uses buttons
            'field_of_study': None  # No keyboard for field of study step - user types text
        }
        
        if step in keyboard_map and keyboard_map[step] is not None:
            keyboard = keyboard_map[step]
            logger.info(f"Returning inline keyboard for step {step}")
            return keyboard
        else:
            logger.warning(f"No keyboard available for step: {step}")
            return None
    
    async def check_trial_status(self, user_id: int) -> Dict[str, Any]:
        """Check user's trial/subscription status"""
        try:
            query = """
                SELECT status, start_date, end_date, payment_method
                FROM subscriptions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """

            result = await self.db.connection.fetchrow(query, user_id)
            
            if not result:
                return {'status': 'no_subscription', 'days_remaining': 0}
            
            days_remaining = (result['end_date'] - datetime.now().date()).days
            
            return {
                'status': result['status'],
                'start_date': result['start_date'],
                'end_date': result['end_date'],
                'days_remaining': days_remaining,
                'payment_method': result['payment_method']
            }
            
        except Exception as e:
            logger.error(f"Error checking trial status for user {user_id}: {e}")
            return {'status': 'error', 'days_remaining': 0}
