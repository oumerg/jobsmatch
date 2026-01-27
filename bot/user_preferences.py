"""
User Preference Management for Job Matching
Handles user selections for job categories, locations, and types
Refactored to use separate preference modules
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, field_validator
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.preference import JobCategoriesManager, JobTypesManager, LocationManager, SalaryManager, EducationManager
from bot.preference.experience import ExperienceManager

logger = logging.getLogger(__name__)

class UserPreferences(BaseModel):
    """User job preferences"""
    user_id: int
    preferred_job_types: Optional[List[str]] = []
    preferred_locations: Optional[List[str]] = []
    preferred_categories: Optional[List[str]] = []
    min_salary: Optional[int] = None
    max_experience: Optional[int] = None
    education_level: Optional[str] = None
    keywords: Optional[List[str]] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def convert_datetime_to_string(cls, v):
        """Convert datetime objects to strings"""
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True

class PreferenceManager:
    """Manages user job preferences using modular approach"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._table_initialized = False  # Initialize table flag

        # Initialize preference managers WITH database connection
        self.categories_manager = JobCategoriesManager(db_manager)  # Pass db connection
        self.job_types_manager = JobTypesManager(db_manager)      # Pass db connection
        self.location_manager = LocationManager(db_manager)      # Pass db connection
        self.salary_manager = SalaryManager(db_manager)        # Pass db connection
        self.experience_manager = ExperienceManager(db_manager)  # Pass db connection
        self.education_manager = EducationManager(db_manager)  # Pass db connection
        
        # Column mapping for database
        self.column_mapping = {
            'preferred_job_types': 'preferred_job_types',
            'preferred_locations': 'preferred_locations',
            'preferred_categories': 'preferred_categories',
            'min_salary': 'min_salary',
            'max_experience': 'max_experience',
            'education_level': 'education_level',
            'keywords': 'keywords'
        }
    
    async def _ensure_connection(self):
        """Ensure database connection is open"""
        try:
            # Check if connection exists and is open
            if not self.db.connection:
                logger.info("Database connection is None, connecting...")
                await self.db.connect()
            elif hasattr(self.db.connection, 'is_closed'):
                if callable(self.db.connection.is_closed):
                    if self.db.connection.is_closed():
                        logger.warning("Database connection was closed, reconnecting...")
                        await self.db.connect()
        except Exception as e:
            logger.warning(f"Connection check failed, reconnecting: {e}")
            try:
                await self.db.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect: {reconnect_error}")
                raise
    
    async def _ensure_connection_and_table(self):
        """Ensure database connection and table exist"""
        # Always check connection status before operations
        await self._ensure_connection()
        
        if not self._table_initialized:
            await self.create_user_preferences_table()
            self._table_initialized = True
    
    async def create_user_preferences_table(self):
        """Create user preferences table if it doesn't exist"""
        try:
            create_table_query = """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id BIGINT PRIMARY KEY,
                    preferred_job_types TEXT[],
                    preferred_locations TEXT[],
                    preferred_categories TEXT[],
                    min_salary INTEGER,
                    max_experience INTEGER,
                    education_level VARCHAR(100),
                    keywords TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            await self.db.connection.execute(create_table_query)
            
            # Create trigger for updated_at
            try:
                await self.db.connection.execute("""
                    CREATE OR REPLACE FUNCTION update_preferences_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                """)
                
                await self.db.connection.execute("""
                    DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON user_preferences
                """)
                
                await self.db.connection.execute("""
                    CREATE TRIGGER update_user_preferences_updated_at
                        BEFORE UPDATE ON user_preferences
                        FOR EACH ROW
                        EXECUTE FUNCTION update_preferences_updated_at();
                """)
            except Exception as trigger_error:
                logger.warning(f"Trigger creation warning: {trigger_error}")
            
            logger.info("User preferences table created/verified successfully")
            
        except Exception as e:
            logger.error(f"Error creating preferences table: {e}")
            raise
    
    async def save_preference_field(self, user_id: int, field_name: str, value: Any) -> bool:
        """Save individual preference field with UPSERT logic"""
        try:
            # Ensure connection is open before saving
            await self._ensure_connection_and_table()
            
            # Double-check connection is still valid before executing query
            await self._ensure_connection()
            
            column = self.column_mapping.get(field_name)
            if not column:
                logger.error(f"Unknown preference field: {field_name}")
                return False
            
            now = datetime.now()
            
            # UPSERT query - update if exists, insert if not
            query = f"""
                INSERT INTO user_preferences (user_id, {column}, created_at, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    {column} = EXCLUDED.{column},
                    updated_at = EXCLUDED.updated_at
            """
            
            await self.db.connection.execute(query, user_id, value, now, now)
            
            # Verify the save
            saved_value = await self.db.connection.fetchval(
                f"SELECT {column} FROM user_preferences WHERE user_id = $1", 
                user_id
            )
            
            logger.info(f"Successfully saved {field_name} for user {user_id}. Verified value: {saved_value}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving {field_name} for user {user_id}: {e}")
            return False
    
    # Delegate methods to preference managers
    def get_experience_keyboard(self):
        """Get experience keyboard"""
        return self.experience_manager.get_experience_keyboard()
    
    def get_education_keyboard(self):
        """Get education keyboard"""
        return self.education_manager.get_education_keyboard()
    
    def get_job_types_keyboard(self):
        """Get job types keyboard"""
        return self.job_types_manager.get_job_types_keyboard()
    
    def get_locations_keyboard(self):
        """Get locations keyboard"""
        return self.location_manager.get_locations_keyboard()
    
    def get_salary_keyboard(self):
        """Get salary keyboard"""
        return self.salary_manager.get_salary_keyboard()
    
    def format_categories_message(self):
        """Format categories message"""
        return self.categories_manager.format_categories_message()
    
    def format_job_types_message(self):
        """Format job types message"""
        return self.job_types_manager.format_job_types_message()
    
    def format_locations_message(self):
        """Format locations message"""
        return self.location_manager.format_locations_message()
    
    def format_salary_message(self):
        """Format salary message"""
        return self.salary_manager.format_salary_message()
    
    def format_experience_message(self):
        """Format experience message"""
        return self.experience_manager.format_experience_message()
    
    def format_education_message(self):
        """Format education message"""
        return self.education_manager.format_education_message()
    
    def get_job_type_mapping(self):
        """Get job type mapping"""
        return self.job_types_manager.get_job_type_mapping()

    def get_categories_keyboard(self):
        """Get categories keyboard"""
        return self.categories_manager.get_categories_keyboard()

    async def get_user_preferences(self, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences from database"""
        try:
            await self._ensure_connection_and_table()

            query = """
                SELECT user_id, preferred_job_types, preferred_locations, preferred_categories,
                       min_salary, max_experience, education_level, keywords, created_at, updated_at
                FROM user_preferences
                WHERE user_id = $1
            """

            result = await self.db.connection.fetchrow(query, user_id)

            if result:
                return UserPreferences(**result)
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting preferences for user {user_id}: {e}")
            return None

class PreferenceCollector:
    """Collects user preferences through interactive flow"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.manager = PreferenceManager(db_manager)
        self.user_states = {}  # Track user progress
    
    
    def start_preference_collection(self, user_id: int) -> str:
        """Start collecting user preferences"""
        # Initialize state with empty selections lists
        self.user_states[user_id] = {
            'step': 'categories',
            'data': {
                'selected_categories': [],
                'selected_locations': [],
                'selected_job_types': []
            }
        }
        return self.manager.format_categories_message()
    
    async def handle_category_selection(self, user_id: int, response: str) -> str:
        """Handle category selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'categories',
                'data': {'selected_categories': [], 'selected_locations': [], 'selected_job_types': []}
            }
        
        state = self.user_states[user_id]
        current_selections = state['data'].get('selected_categories', [])
        
        if "cancel" in response.lower():
            del self.user_states[user_id]
            # Close database connection on cancellation
            try:
                if self.manager.db.connection:
                    await self.manager.db.close()
            except Exception as e:
                logger.warning(f"Error closing database connection on cancel: {e}")
            return "Preference collection cancelled."
        
        # specific handling for "Done"
        if response == "category_done" or response.lower() == "done":
            if not current_selections:
                return "⚠️ Please select at least one category before proceeding."
            
            # Save all selected categories
            success = await self.manager.save_preference_field(user_id, 'preferred_categories', current_selections)
            if success:
                state['step'] = 'education'
                return self.manager.format_education_message()
            else:
                return "❌ Error saving category preferences. Please try again."

        # Handle "All Categories" toggle
        if response == "category_all":
            all_categories = list(self.manager.categories_manager.job_categories.keys())
            if len(current_selections) == len(all_categories):
                # If all selected, deselect all
                state['data']['selected_categories'] = []
            else:
                # Select all
                state['data']['selected_categories'] = all_categories
            return self.manager.format_categories_message()

        # Handle individual toggles
        category = response.replace("category_", "")
        if category in current_selections:
            current_selections.remove(category)
        else:
            current_selections.append(category)
        
        state['data']['selected_categories'] = current_selections
        
        # Return the same message to refresh keyboard with new state
        return self.manager.format_categories_message()
    
    async def handle_education_selection(self, user_id: int, response: str) -> str:
        """Handle education level selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'education',
                'data': {}
            }

        state = self.user_states[user_id]

        if "cancel" in response.lower():
            del self.user_states[user_id]
            # Close database connection on cancellation
            try:
                if self.manager.db.connection:
                    await self.manager.db.close()
            except Exception as e:
                logger.warning(f"Error closing database connection on cancel: {e}")
            return "Preference collection cancelled."
        elif "back" in response.lower():
            state['step'] = 'categories'
            return self.manager.format_categories_message()

        # Handle both callback data format (education_key) and display text
        education_key = None
        valid_education_levels = ['no_formal', 'high_school', 'diploma', 'bachelor', 'master', 'phd']
        
        # First, check if it's callback data format (education_xxx)
        if response.startswith("education_"):
            education_key = response.replace("education_", "")
        elif response in valid_education_levels:
            education_key = response
        else:
            # Clean the response to remove bullet points and emojis
            clean_response = response.replace("• ", "").replace(" ", "").replace(" ", "").replace(" ", "").strip()

            # Map display text back to education key
            education_display_to_key = {
                'No Formal Education': 'no_formal',
                'High School': 'high_school',
                'Diploma/Certificate': 'diploma',
                'Diploma': 'diploma',
                'Bachelor\'s Degree': 'bachelor',
                'Bachelor': 'bachelor',
                'Master\'s Degree': 'master',
                'Master': 'master',
                'PhD/Doctorate': 'phd',
                'PhD': 'phd'
            }

            education_key = education_display_to_key.get(clean_response)

        # Validate education key
        if not education_key or education_key not in valid_education_levels:
            logger.error(f"Unknown education level: '{response}' (extracted key: '{education_key}')")
            logger.error(f"Valid keys: {valid_education_levels}")
            return "❌ Invalid education selection. Please try again."

        # Save education preference
        success = await self.manager.save_preference_field(user_id, 'education_level', education_key)
        if success:
            state['step'] = 'locations'
            return self.manager.format_locations_message()
        else:
            return "❌ Error saving education preference. Please try again."
    
    async def handle_location_selection(self, user_id: int, response: str) -> str:
        """Handle location selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'locations',
                'data': {'selected_categories': [], 'selected_locations': [], 'selected_job_types': []}
            }
        
        state = self.user_states[user_id]
        current_selections = state['data'].get('selected_locations', [])
        
        if "cancel" in response.lower():
            del self.user_states[user_id]
            # Close database connection on cancellation
            try:
                if self.manager.db.connection:
                    await self.manager.db.close()
            except Exception as e:
                logger.warning(f"Error closing database connection on cancel: {e}")
            return "Preference collection cancelled."
        elif "back" in response.lower():
            state['step'] = 'education'
            return self.manager.format_education_message()
        
        # specific handling for "Done"
        if response == "location_done" or response.lower() == "done":
            if not current_selections:
                return "⚠️ Please select at least one location before proceeding."
            
            # Save selections
            success = await self.manager.save_preference_field(user_id, 'preferred_locations', current_selections)
            if success:
                state['step'] = 'job_types'
                return self.manager.format_job_types_message()
            else:
                return "❌ Error saving location preferences. Please try again."

        # Handle "Any Location" / "All"
        location = response.replace("location_", "")
        
        if location == "any":
            if "Any Location" in current_selections:
                current_selections.remove("Any Location")
            else:
                # If Any is selected, maybe clear others? Or just add it.
                # User asked for "inclusive". Let's just add it.
                current_selections.append("Any Location")
        elif location == "remote":
             if "Remote" in current_selections:
                 current_selections.remove("Remote")
             else:
                 current_selections.append("Remote")
        else:
             if location in current_selections:
                 current_selections.remove(location)
             else:
                 current_selections.append(location)
        
        state['data']['selected_locations'] = current_selections
        
        # Return same message to refresh keyboard
        return self.manager.format_locations_message()
    
    async def handle_job_type_selection(self, user_id: int, response: str) -> str:
        """Handle job type selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'job_types',
                'data': {'selected_categories': [], 'selected_locations': [], 'selected_job_types': []}
            }
        
        state = self.user_states[user_id]
        current_selections = state['data'].get('selected_job_types', [])
        
        if "cancel" in response.lower():
            del self.user_states[user_id]
            # Close database connection on cancellation
            try:
                if self.manager.db.connection:
                    await self.manager.db.close()
            except Exception as e:
                logger.warning(f"Error closing database connection on cancel: {e}")
            return "Preference collection cancelled."
        elif "back" in response.lower():
            state['step'] = 'locations'
            return self.manager.format_locations_message()
        
        # specific handling for "Done"
        if response == "jobtype_done" or response.lower() == "done":
            if not current_selections:
                return "⚠️ Please select at least one job type before proceeding."
            
            # Save selections
            success = await self.manager.save_preference_field(user_id, 'preferred_job_types', current_selections)
            logger.info(f"Save job types result: {success}")
            if success:
                state['step'] = 'salary'
                return self.manager.format_salary_message()
            else:
                logger.error(f"Failed to save job type for user {user_id}")
                return "❌ Error saving job type preferences. Please try again."

        # Handle "All Job Types"
        if response == "jobtype_all":
            all_types = list(self.manager.job_types_manager.job_types_display.keys())
            if len(current_selections) == len(all_types):
                state['data']['selected_job_types'] = []
            else:
                state['data']['selected_job_types'] = all_types
            return self.manager.format_job_types_message()
            
        # Extract job type
        job_type = response.replace("jobtype_", "")
        
        # Original logic was complex because of text input, but with inline buttons we primarily get callbacks
        # If it's a direct text input (fallback), we might need the mapping logic, but let's assume callback for multi-select flow
        
        if job_type in current_selections:
            current_selections.remove(job_type)
        else:
            current_selections.append(job_type)
            
        state['data']['selected_job_types'] = current_selections
        return self.manager.format_job_types_message()
    
    async def handle_salary_selection(self, user_id: int, response: str) -> str:
        """Handle salary selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'salary',
                'data': {}
            }
        
        state = self.user_states[user_id]
        
        if "cancel" in response.lower():
            del self.user_states[user_id]
            # Close database connection on cancellation
            try:
                if self.manager.db.connection:
                    await self.manager.db.close()
            except Exception as e:
                logger.warning(f"Error closing database connection on cancel: {e}")
            return "Preference collection cancelled."
        elif "back" in response.lower():
            state['step'] = 'job_types'
            return self.manager.format_job_types_message()
        
        # Parse salary
        try:
            if response == "custom":
                return "Please enter your custom minimum salary amount:"
            
            # Check if response is a raw number (from callback) or formatted display
            try:
                # Try to parse as integer first (for callback data)
                salary = int(response)
            except ValueError:
                # If that fails, clean formatted display text
                clean_salary = response.replace(" ", "").replace(",", "").replace(" Birr", "").strip()
                if clean_salary == "above_30000":
                    # Handle "Above 30,000" special case
                    salary = 35000  # Default to 35,000 Birr
                else:
                    salary = int(clean_salary)
            
            if salary <= 0:
                return "Please enter a valid positive salary amount."
            
            # Save salary preference
            success = await self.manager.save_preference_field(user_id, 'min_salary', salary)
            if success:
                state['step'] = 'experience'
                return self.manager.format_experience_message()
            else:
                return "❌ Error saving salary preference. Please try again."
                
        except ValueError:
            return "Please enter a valid number for salary."
    
    async def finish_collection(self, user_id: int) -> str:
        """Finish preference collection"""
        # Clean up user state
        if user_id in self.user_states:
            del self.user_states[user_id]
            logger.info(f"Cleaned up user state for {user_id}")
        
        message = (
            "✅ *Preferences Saved Successfully!*\n\n"
            "Your job preferences have been updated. You will now receive "
            "job notifications based on your selections.\n\n"
            "Use /profile to view your preferences or /preferences to update them."
        )
        return message
    
    async def handle_experience_selection(self, user_id: int, response: str) -> str:
        """Handle experience level selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'experience',
                'data': {}
            }

        state = self.user_states[user_id]

        if "cancel" in response.lower():
            del self.user_states[user_id]
            # Close database connection on cancellation
            try:
                if self.manager.db.connection:
                    await self.manager.db.close()
            except Exception as e:
                logger.warning(f"Error closing database connection on cancel: {e}")
            return "Preference collection cancelled."
        elif "back" in response.lower():
            state['step'] = 'salary'
            return self.manager.format_salary_message()

        # Clean the response to remove bullet points, emojis, and whitespace
        clean_response = response.replace("•", "").replace("", "").replace("", "").replace("", "").strip()
        
        # Convert experience level to years
        experience_mapping = {
            '0_years': 0,
            '3_years': 3,
            '5_years': 5,
            'above_5_years': 6  # Use 6 to represent "above 5 years"
        }
        
        # Map display text to experience keys
        display_to_key = {
            'entry level (0 years)': '0_years',
            'entry level': '0_years',
            '0 years': '0_years',
            '3 years experience': '3_years',
            '3 years': '3_years',
            '5 years experience': '5_years',
            '5 years': '5_years',
            'above 5 years': 'above_5_years',
            'above 5': 'above_5_years',
            'more than 5 years': 'above_5_years'
        }
        
        # Try to extract experience key from response
        experience_key = None
        valid_experience_keys = set(experience_mapping.keys())
        
        # First, check if it's a callback data format (experience_xxx)
        if response.startswith("experience_"):
            experience_key = response.replace("experience_", "")
        elif response in valid_experience_keys:
            experience_key = response
        else:
            # Try to match cleaned response to display text
            clean_lower = clean_response.lower()
            experience_key = display_to_key.get(clean_lower)
            
            # If not found, try partial matching
            if not experience_key:
                for display_text, key in display_to_key.items():
                    if display_text in clean_lower or clean_lower in display_text:
                        experience_key = key
                        break
        
        # Get years from mapping
        years = experience_mapping.get(experience_key) if experience_key else None
        
        if years is None:
            logger.error(f"Unknown experience level: '{response}' (cleaned: '{clean_response}')")
            logger.error(f"Available keys: {list(experience_mapping.keys())}")
            logger.error(f"Available display texts: {list(display_to_key.keys())}")
            return "❌ Invalid experience selection. Please try again."
        
        # Save experience preference as integer years
        success = await self.manager.save_preference_field(user_id, 'max_experience', years)
        if success:
            del self.user_states[user_id]
            return await self.finish_collection(user_id)
        else:
            return "❌ Error saving experience preference. Please try again."

    async def handle_preference_response(self, user_id: int, response: str) -> Optional[str]:
        """Handle user preference responses by step"""
        state = self.user_states.get(user_id)
        if not state:
            return None

        step = state['step']

        if step == 'categories':
            return await self.handle_category_selection(user_id, response)
        elif step == 'education':
            return await self.handle_education_selection(user_id, response)
        elif step == 'locations':
            return await self.handle_location_selection(user_id, response)
        elif step == 'job_types':
            return await self.handle_job_type_selection(user_id, response)
        elif step == 'salary':
            return await self.handle_salary_selection(user_id, response)
        elif step == 'experience':
            return await self.handle_experience_selection(user_id, response)
        else:
            return await self.finish_collection(user_id)
