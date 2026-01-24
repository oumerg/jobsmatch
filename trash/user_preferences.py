"""
User Preference Management for Job Matching
Handles user selections for job categories, locations, and types
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager

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

    class Config:
        from_attributes = True

class PreferenceManager:
    """Manages user job preferences"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._db_connection = None  # Store connection reference
        
        # Initialize table on first use
        self._table_initialized = False
        
        # Job categories (Ethiopian context)
        self.job_categories = {
            'technology': [
                'Software Developer', 'IT Support', 'Network Engineer', 'Data Analyst',
                'Web Developer', 'Mobile Developer', 'Database Administrator',
                'የሶፍትዌር ዲቨሎፐር', 'የቴክ ስራ'
            ],
            'finance': [
                'Accountant', 'Financial Analyst', 'Bank Teller', 'Cashier',
                'Bookkeeper', 'Finance Manager', 'Auditor',
                'አካውንታንት', 'ባንክ ሰራተኛ'
            ],
            'healthcare': [
                'Doctor', 'Nurse', 'Pharmacist', 'Lab Technician',
                'Medical Assistant', 'Healthcare Worker',
                'ዶክተር', 'ነርስ', 'ፋርማሲስት'
            ],
            'education': [
                'Teacher', 'Lecturer', 'Academic Advisor', 'Librarian',
                'School Administrator', 'Tutor',
                'አስተማማኝ', 'መምህራት'
            ],
            'sales_marketing': [
                'Sales Representative', 'Marketing Manager', 'Sales Executive',
                'Digital Marketer', 'Brand Manager', 'Customer Service',
                'ሽዋጥ', 'ማርኬቲንግ'
            ],
            'engineering': [
                'Civil Engineer', 'Mechanical Engineer', 'Electrical Engineer',
                'Construction Manager', 'Project Engineer', 'Technical Support',
                'ኢንጂነር', 'ስራ አስኪያጅ'
            ],
            'hospitality': [
                'Hotel Manager', 'Chef', 'Waiter', 'Housekeeping',
                'Tour Guide', 'Receptionist', 'Customer Service',
                'ሆቴል ሰራተኛ', 'ሽፍራፍ'
            ],
            'government': [
                'Civil Servant', 'Government Officer', 'Administrative Assistant',
                'Public Service Worker', 'Municipal Worker',
                'የመንግስትዊ ሰራተኛ'
            ],
            'ngo': [
                'Program Officer', 'Project Coordinator', 'Field Officer',
                'NGO Worker', 'Development Worker', 'Community Worker',
                'የኤንጂኦ ሰራተኛ'
            ],
            'other': [
                'Driver', 'Security Guard', 'Cleaner', 'Laborer',
                'General Worker', 'Assistant', 'Helper',
                'ሰራተኛ', 'እርዳታ'
            ]
        }
        
        # Ethiopian locations
        self.ethiopian_locations = [
            'Addis Ababa', 'Adama', 'Dire Dawa', 'Mekelle', 'Gondar',
            'Bahir Dar', 'Hawassa', 'Jimma', 'Dessie', 'Shashemene',
            'Nekemte', 'Debre Markos', 'Kombolcha', 'Weldiya',
            'አዲስ አበባ', 'አዳማ', 'ድሬዳዋ', 'መቀሌ', 'ጎንደር'
        ]
        
        # Job types
        self.job_types = {
            'full_time': 'Full Time',
            'part_time': 'Part Time', 
            'contract': 'Contract',
            'remote': 'Remote/Work from Home',
            'hybrid': 'Hybrid',
            'internship': 'Internship',
            'full_time_am': 'ሙሉ ጊዜ',
            'part_time_am': 'ከፊል ጊዜ',
            'remote_am': 'ከቤት ስራ'
        }
    
    async def _ensure_connection_and_table(self):
        """Ensure database connection and table exist"""
        if not self._db_connection:
            await self.db.connect()
            self._db_connection = self.db.connection
            
        if not self._table_initialized:
            try:
                await self.create_user_preferences_table()
                self._table_initialized = True
            except Exception as e:
                logger.warning(f"Table initialization warning: {e}")
                # Still mark as initialized to avoid repeated attempts
                self._table_initialized = True

    async def get_user_preferences(self, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences from database"""
        try:
            # Query preferences table
            query = "SELECT * FROM user_preferences WHERE user_id = $1"
            result = await self.db.connection.fetchrow(query, user_id)
            
            if result:
                return UserPreferences(**dict(result))
            return None
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return None
    
    async def save_user_preferences_data(self, preferences: UserPreferences) -> bool:
        """Save complete user preferences object to database"""
        try:
            # Ensure we have a connection
            if not self._db_connection:
                await self.db.connect()
                self._db_connection = self.db.connection

            # Convert string timestamps to datetime objects for PostgreSQL
            created_at = datetime.fromisoformat(preferences.created_at)
            updated_at = datetime.fromisoformat(preferences.updated_at)

            await self._db_connection.execute('''
                INSERT INTO user_preferences
                (user_id, preferred_job_types, preferred_locations, preferred_categories,
                 min_salary, max_experience, education_level, keywords, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (user_id) DO UPDATE SET
                preferred_job_types = EXCLUDED.preferred_job_types,
                preferred_locations = EXCLUDED.preferred_locations,
                preferred_categories = EXCLUDED.preferred_categories,
                min_salary = EXCLUDED.min_salary,
                max_experience = EXCLUDED.max_experience,
                education_level = EXCLUDED.education_level,
                keywords = EXCLUDED.keywords,
                updated_at = EXCLUDED.updated_at
            ''',
                preferences.user_id,
                preferences.preferred_job_types,
                preferences.preferred_locations,
                preferences.preferred_categories,
                preferences.min_salary,
                preferences.max_experience,
                preferences.education_level,
                preferences.keywords,
                created_at,
                updated_at
            )

            logger.info(f"Saved preferences for user {preferences.user_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
            return False

    async def save_preference_field(self, user_id: int, field_name: str, value: Any) -> bool:
        """Save individual preference field to database incrementally"""
        try:
            # Ensure connection and table exist
            await self._ensure_connection_and_table()

            # Map field names to column names
            column_mapping = {
                'preferred_job_types': 'preferred_job_types',
                'preferred_locations': 'preferred_locations',
                'preferred_categories': 'preferred_categories',
                'min_salary': 'min_salary',
                'max_experience': 'max_experience',
                'education_level': 'education_level',
                'keywords': 'keywords'
            }

            if field_name not in column_mapping:
                logger.error(f"Unknown preference field: {field_name}")
                return False

            column = column_mapping[field_name]

            # Use UPSERT to handle both insert and update cases
            now = datetime.now()
            query = f'''
                INSERT INTO user_preferences (user_id, {column}, created_at, updated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE SET
                {column} = EXCLUDED.{column},
                updated_at = EXCLUDED.updated_at
            '''
            
            # Log values being saved for debugging
            logger.info(f"Attempting to save {field_name} for user {user_id}: {value} (type: {type(value)})")
            
            await self._db_connection.execute(query, user_id, value, now, now)
            
            # Verify save by querying back the data
            verify_query = f"SELECT {column} FROM user_preferences WHERE user_id = $1"
            saved_value = await self._db_connection.fetchval(verify_query, user_id)
            logger.info(f"Successfully saved {field_name} for user {user_id}. Verified value: {saved_value}")
            
            return True

        except Exception as e:
            logger.error(f"Error saving preference field {field_name} for user {user_id}: {e}")
            logger.error(f"Value being saved: {value} (type: {type(value)})")
            # Note: asyncpg connections don't have rollback method for individual statements
            # Transactions are handled at a higher level
            return False

    async def save_user_preferences(self, user_id: int, response: str) -> bool:
        """Save or update user preferences"""
        try:
            # Get current preference state
            current_step = await self.get_user_preference_step(user_id)
            
            if not current_step:
                # No active preference collection, start new one
                return await self.start_preference_collection(user_id)
            
            # Handle response based on current step
            if current_step == 'categories':
                # Handle category selection
                await self.save_preference(user_id, 'categories', [response])
                return await self.start_job_type_collection(user_id)
                
            elif current_step == 'job_types':
                # Handle job type selection
                await self.save_preference(user_id, 'job_types', [response])
                return await self.start_location_collection(user_id)
                
            elif current_step == 'locations':
                # Handle location selection
                await self.save_preference(user_id, 'locations', [response])
                return await self.start_salary_collection(user_id)
                
            elif current_step == 'salary':
                # Handle salary selection
                await self.save_preference(user_id, 'salary_range', response)
                return await self.start_skills_collection(user_id)
                
            elif current_step == 'skills':
                # Handle skills selection
                if response == "✅ Done with Skills":
                    return await self.complete_preference_collection(user_id)
                else:
                    # Add skill
                    await self.add_user_skill(user_id, response)
                    return f"✅ Added skill: {response}\n\nSelect more skills or click 'Done with Skills':"
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling preference response: {e}")
            return "❌ Error updating preferences. Please try again."
    
    def get_categories_keyboard(self):
        """Generate inline keyboard for job category selection"""
        keyboard = []
        
        # Simplified categories for testing
        test_categories = ['technology', 'finance', 'healthcare']
        
        # Create rows of 2 buttons each
        for i in range(0, len(test_categories), 2):
            row = []
            for category in test_categories[i:i+2]:
                if category in self.job_categories:
                    row.append(InlineKeyboardButton(
                        f"• {category.replace('_', ' ').title()}", 
                        callback_data=f"category_{category}"
                    ))
            if row:
                keyboard.append(row)
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("⚙️ Custom Preferences", callback_data="custom_categories"),
            InlineKeyboardButton("🔍 Search Jobs", callback_data="search_jobs")
        ])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_locations_keyboard(self):
        """Generate inline keyboard for location selection"""
        keyboard = []
        
        # Simplified locations for testing
        test_locations = ['Addis Ababa', 'Dire Dawa', 'Remote/Work from Home']
        
        # Create rows of 2 buttons each
        for i in range(0, len(test_locations), 2):
            row = []
            for location in test_locations[i:i+2]:
                if location == "Remote/Work from Home":
                    row.append(InlineKeyboardButton("🌍 Remote", callback_data="location_remote"))
                elif location == "Any Location":
                    row.append(InlineKeyboardButton("🇪🇹 Any Location", callback_data="location_any"))
                else:
                    row.append(InlineKeyboardButton(f"📍 {location}", callback_data=f"location_{location}"))
            if row:
                keyboard.append(row)
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_categories"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_job_types_keyboard(self):
        """Generate inline keyboard for job type selection"""
        keyboard = []
        
        # Job types including hybrid
        test_job_types = ['Full Time', 'Part Time', 'Remote', 'Hybrid']
        
        # Create rows of 2 buttons each
        for i in range(0, len(test_job_types), 2):
            row = []
            for job_type in test_job_types[i:i+2]:
                # Map to callback data
                callback_type = job_type.lower().replace(' ', '_')
                row.append(InlineKeyboardButton(f"• {job_type}", callback_data=f"jobtype_{callback_type}"))
            if row:
                keyboard.append(row)
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_locations"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_categories_message(self):
        """Format categories selection message"""
        return "🎯 *Select Job Categories You're Interested In:*\n\n🔹 Choose from the options below:"
    
    def format_locations_message(self):
        """Format locations selection message"""
        return "📍 *Select Your Preferred Work Locations:*\n\n🔹 Choose from the options below:"
    
    def get_salary_keyboard(self):
        """Generate inline keyboard for salary selection"""
        keyboard = []
        
        # Salary options in Birr (reasonable Ethiopian salary ranges)
        salary_options = [
            ('5,000 Birr', '5000'),
            ('10,000 Birr', '10000'), 
            ('15,000 Birr', '15000'),
            ('20,000 Birr', '20000'),
            ('25,000 Birr', '25000'),
            ('30,000 Birr', '30000'),
            ('Above 30,000 Birr', 'above_30000')
        ]
        
        # Create rows of 2 buttons each
        for i in range(0, len(salary_options), 2):
            row = []
            for display, value in salary_options[i:i+2]:
                row.append(InlineKeyboardButton(f"💵 {display}", callback_data=value))
            if row:
                keyboard.append(row)
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_job_types"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ])
        
        return InlineKeyboardMarkup(keyboard)

    def format_job_types_message(self):
        """Format job types selection message"""
        return "⏰ *Select Your Preferred Job Types:*\n\n🔹 Choose from the options below:"

    def format_salary_message(self):
        """Format salary selection message"""
        return "💰 *Select Your Minimum Expected Salary:*\n\nChoose from the options below or type a custom amount:"
    
    async def create_user_preferences_table(self):
        """Create user preferences table if not exists"""
        try:
            # Connection should already be established by _ensure_connection_and_table
            if not self._db_connection:
                raise Exception("Database connection not established")
                
            await self._db_connection.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id BIGINT PRIMARY KEY,
                    preferred_job_types TEXT[],
                    preferred_locations TEXT[],
                    preferred_categories TEXT[],
                    min_salary INTEGER,
                    max_experience INTEGER,
                    education_level VARCHAR(50),
                    keywords TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create trigger for updated_at (use IF NOT EXISTS approach)
            try:
                await self._db_connection.execute('''
                    CREATE OR REPLACE FUNCTION update_preferences_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                ''')
                
                # Drop trigger if exists and recreate it
                await self._db_connection.execute('DROP TRIGGER IF EXISTS update_user_preferences_updated_at ON user_preferences')
                
                await self._db_connection.execute('''
                    CREATE TRIGGER update_user_preferences_updated_at 
                        BEFORE UPDATE ON user_preferences 
                        FOR EACH ROW EXECUTE FUNCTION update_preferences_updated_at()
                ''')
            except Exception as trigger_error:
                logger.warning(f"Trigger creation warning (may already exist): {trigger_error}")
            
            logger.info("User preferences table created/verified successfully")
            
        except Exception as e:
            logger.error(f"Error creating preferences table: {e}")
            # Don't raise here - table may already exist and that's okay

# Preference collection handlers
class PreferenceCollector:
    """Collects user preferences step by step"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.manager = PreferenceManager(db_manager)
        self.user_states = {}  # Track user collection progress
        # Share the same connection as the manager
        self._db_connection = None  # Will use manager's connection
    
    async def start_preference_collection(self, user_id: int) -> str:
        """Start collecting user preferences"""
        self.user_states[user_id] = {
            'step': 'categories',
            'data': {}
        }
        
        return self.manager.format_categories_message()
    
    async def handle_preference_response(self, user_id: int, response: str) -> Optional[str]:
        """Handle user preference response and return next step message"""
        state = self.user_states.get(user_id)
        if not state:
            return None
        
        step = state['step']
        
        if step == 'categories':
            return await self.handle_category_selection(user_id, response)
        elif step == 'locations':
            return await self.handle_location_selection(user_id, response)
        elif step == 'job_types':
            return await self.handle_job_type_selection(user_id, response)
        elif step == 'salary':
            return await self.handle_salary_selection(user_id, response)
        else:
            return await self.finish_collection(user_id)
    
    async def handle_category_selection(self, user_id: int, response: str) -> str:
        """Handle category selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'categories',
                'data': {}
            }
        
        state = self.user_states[user_id]

        if "cancel" in response.lower():
            del self.user_states[user_id]
            return "Preference collection cancelled."
        elif "back" in response.lower():
            state['step'] = 'categories'
            return self.manager.format_categories_message()

        # Extract category from response and normalize
        category_clean = response.replace("📂 ", "").replace("🔹 ", "").strip().lower()
        
        # Check if it matches any category (case-insensitive partial match)
        for cat_key in self.manager.job_categories.keys():
            cat_key_lower = cat_key.lower()
            if category_clean in cat_key_lower or cat_key_lower in category_clean:
                # Save category incrementally (single selection)
                success = await self.manager.save_preference_field(user_id, 'preferred_categories', [cat_key])
                if success:
                    state['step'] = 'locations'
                    return self.manager.format_locations_message()
                else:
                    return "❌ Error saving category preference. Please try again."

        if "custom" in response.lower():
            state['step'] = 'custom_categories'
            return "Please type the job categories you're interested in (separate with commas):"
        else:
            return "Please select a valid category from the options above."
    
    async def handle_location_selection(self, user_id: int, response: str) -> str:
        """Handle location selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'locations',
                'data': {}
            }
        
        state = self.user_states[user_id]
        
        logger.info(f"Handling location selection for user {user_id}: {response.replace('📍', '').replace('🌍', '').replace('🇪🇹', '')}")

        if "cancel" in response.lower():
            del self.user_states[user_id]
            return "Preference collection cancelled."
        elif "back" in response.lower():
            state['step'] = 'categories'
            return self.manager.format_categories_message()

        # Extract location from response and normalize
        location_clean = response.replace("📍 ", "").replace("🌍 ", "").replace("🇪🇹 ", "").strip().lower()
        logger.info(f"Cleaned location: '{location_clean}'")

        locations_list = []
        if "remote" in location_clean or "work from home" in location_clean:
            locations_list = ['remote']
        elif "any" in location_clean:
            locations_list = ['any']
        else:
            # Check if it matches any Ethiopian location (case-insensitive partial match)
            for eth_loc in self.manager.ethiopian_locations:
                eth_loc_lower = eth_loc.lower()
                if location_clean in eth_loc_lower or eth_loc_lower in location_clean:
                    locations_list = [eth_loc]
                    break
            else:
                # Allow free text entry for locations not in the list
                if location_clean and len(location_clean) > 1:
                    locations_list = [location_clean.title()]
                else:
                    logger.warning(f"Invalid location entered: '{location_clean}'")
                    return "Please select a valid location from the options above."

        logger.info(f"Final locations list to save: {locations_list}")

        # Save location incrementally
        try:
            success = await self.manager.save_preference_field(user_id, 'preferred_locations', locations_list)
            logger.info(f"Location save result for user {user_id}: {success}")
            
            if success:
                state['step'] = 'job_types'
                return self.manager.format_job_types_message()
            else:
                logger.error(f"Failed to save location for user {user_id}")
                return "❌ Error saving location preference. Please try again."
        except Exception as e:
            logger.error(f"Exception during location save for user {user_id}: {e}")
            return "❌ Error saving location preference. Please try again."
    
    async def handle_job_type_selection(self, user_id: int, response: str) -> str:
        """Handle job type selection"""
        # Check if user state exists
        if user_id not in self.user_states:
            logger.warning(f"User {user_id} not found in user_states, reinitializing")
            self.user_states[user_id] = {
                'step': 'job_types',
                'data': {}
            }
        
        state = self.user_states[user_id]

        if "cancel" in response.lower():
            del self.user_states[user_id]
            return "Preference collection cancelled."
        elif "back" in response.lower():
            state['step'] = 'locations'
            return self.manager.format_locations_message()

        # Extract job type from response
        original_response = response
        job_type = response.replace("⏰ ", "").replace("🏢 ", "").replace("⏱️ ", "").replace("🏠 ", "").replace("📝 ", "").replace("🔹 ", "").lower().strip()
        logger.info(f"Original response: '{original_response}'")
        logger.info(f"Cleaned job type: '{job_type}'")
        logger.info(f"Job type mapping keys: {list(job_type_mapping.keys())}")

        # Map display names to internal values
        job_type_mapping = {
            'full time': 'full_time',
            'part time': 'part_time', 
            'remote': 'remote',
            'hybrid': 'hybrid',
            'contract': 'contract',
            'internship': 'internship'
        }

        # Check if the cleaned job type matches any mapping
        if job_type in job_type_mapping:
            mapped_type = job_type_mapping[job_type]
            logger.info(f"Job type matched: '{job_type}' -> '{mapped_type}'")
            # Save job type incrementally
            success = await self.manager.save_preference_field(user_id, 'preferred_job_types', [mapped_type])
            logger.info(f"Save result: {success}")
            if success:
                state['step'] = 'salary'
                logger.info(f"State before advancement: {state}")
                logger.info(f"Advanced to salary step for user {user_id}")
                return self.manager.format_salary_message()
            else:
                logger.error(f"Failed to save job type for user {user_id}")
                return "❌ Error saving job type preference. Please try again."
        else:
            logger.warning(f"Job type not matched: '{job_type}'")
            return "Please select a valid job type from the options above."
    
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
            return "Preference collection cancelled."
        
        # Check if response matches a salary button
        salary_mapping = {
            '5000': 5000,
            '10000': 10000,
            '15000': 15000,
            '20000': 20000,
            '25000': 25000,
            '30000': 30000,
            'above_30000': None  # Custom amount
        }
        
        if response in salary_mapping:
            salary = salary_mapping[response]
            if salary is not None:
                # Save salary incrementally
                success = await self.manager.save_preference_field(user_id, 'min_salary', salary)
                if success:
                    return await self.finish_collection(user_id)
                else:
                    return "❌ Error saving salary preference. Please try again."
            else:
                # Custom amount requested
                return "💰 *Enter your custom minimum salary amount:* (Enter amount in Birr, e.g., 35000)"
        
        # Try to parse as custom number
        try:
            salary = int(response.replace(",", "").replace("birr", "").replace("etb", "").strip())
            if salary > 0:
                # Save salary incrementally
                success = await self.manager.save_preference_field(user_id, 'min_salary', salary)
                if success:
                    return await self.finish_collection(user_id)
                else:
                    return "❌ Error saving salary preference. Please try again."
            else:
                return "Please enter a valid positive number."
        except ValueError:
            return "Please enter a valid number (e.g., 5000) or select from the options below."
    
    async def finish_collection(self, user_id: int) -> str:
        """Finish preference collection - all data already saved incrementally"""
        try:
            # Clean up user state
            del self.user_states[user_id]
            return "✅ *Preferences saved successfully!*\n\nI'll now send you matching jobs based on your preferences.\n\nUse /profile to view your preferences or /preferences to update them."

        except Exception as e:
            logger.error(f"Error finishing preference collection: {e}")
            return "❌ An error occurred. Please try again."
