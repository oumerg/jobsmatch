"""
Telethon-based Job Scraper for Ethiopian Job Market
Reads jobs from Telegram groups/channels and forwards to users based on preferences
"""

import os
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from telethon import TelegramClient, events
from telethon.tl.types import Message
from bot.config import Config
from bot.database import DatabaseManager
from bot.job_models import Job, JobSeeker, EducationLevel, JobType
from bot.gemini_matcher import GeminiJobMatcher

logger = logging.getLogger(__name__)

class JobScraper:
    """Scrapes jobs from Telegram groups/channels using Telethon"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.gemini_matcher = GeminiJobMatcher()
        self.client = None
        self.processed_messages = set()  # Avoid duplicates
        self.processed_content = set()  # Track processed content to avoid duplicates
        
        # Ethiopian job keywords (Amharic and English)
        self.job_keywords = {
            'amharic': [
                'ሥራ', 'ስራ', 'ምርጫዎች', 'የስራ አስፈለጊያ', 'ባለሙያ', 'ተማራች',
                'ስራ ይፈልጋል', 'የስራ ጥቅም', 'ስራ መፈለጊያ', 'ምርጫ ይፈለጋል'
            ],
            'english': [
                'job', 'vacancy', 'hiring', 'recruitment', 'position', 'career',
                'employment', 'opportunity', 'opening', 'role', 'work', 'apply'
            ]
        }
        
        # Job type indicators
        self.job_types = {
            'full_time': ['full time', 'full-time', 'permanent'],
            'part_time': ['part time', 'part-time', 'temporary'],
            'contract': ['contract', 'consultant', 'freelance'],
            'remote': ['remote', 'work from home', 'wfh', 'online'],
            'internship': ['internship', 'intern', 'trainee']
        }
        
        # Location indicators (Ethiopian cities)
        self.locations = [
            'addis ababa', 'addis', 'adama', 'dire dawa', 'mekelle',
            'gondar', 'bahir dar', 'hawassa', 'jimma', 'dessie',
            'አዲስ አበባ', 'አዲስ', 'አዳማ', 'ድሬዳዋ', 'መቀሌ', 'ጎንደር'
        ]
    
    async def initialize(self):
        """Initialize Telethon client and Gemini AI"""
        try:
            # Initialize Gemini AI first
            gemini_initialized = await self.gemini_matcher.initialize()
            if not gemini_initialized:
                logger.warning("Gemini AI not initialized - will use basic matching")
            
            # Initialize Telethon client
            api_id = int(os.getenv('TELETHON_API_ID', '0'))
            api_hash = os.getenv('TELETHON_API_HASH', '')
            phone = os.getenv('TELETHON_PHONE', '')
            
            if not api_id or not api_hash or not phone:
                logger.error("Telethon credentials not configured!")
                return False
            
            self.client = TelegramClient('job_scraper_session', api_id, api_hash)
            await self.client.start(phone)
            logger.info("✅ Telethon client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize scraper: {e}")
            return False
    
    async def setup_handlers(self):
        """Setup message handlers for job scraping"""
        
        @self.client.on(events.NewMessage)
        async def handle_job_post(event):
            """Handle new messages from monitored groups/channels"""
            message = event.message
            
            # Log ALL messages for debugging
            channel_name = getattr(message.chat, 'title', str(message.chat_id))
            logger.info(f"📨 RECEIVED: {channel_name} - {message.text[:100]}...")
            
            # Create unique identifier for message
            message_id = f"{message.chat_id}_{message.id}"
            
            # Skip if already processed (using chat_id + message_id combo)
            if message_id in self.processed_messages:
                logger.debug(f"🔄 Already processed message {message_id}")
                return
            
            # Skip messages from the bot itself (unless it looks like a job posting for testing)
            # We allow it for now to enable testing with own account
            try:
                me = await self.client.get_me()
                from_id = getattr(message, 'from_id', None)
                if message.out or from_id == me.id:
                    # Check if it looks like a job before skipping completely
                    if not self.is_job_posting(message.text):
                         logger.debug(f"ℹ️ Skipping own message (not a job)")
                         return
                    logger.info(f"ℹ️ Processing own message (detected as job)")
            except Exception as e:
                logger.error(f"Error getting bot info: {e}")
                # If we can't get bot info, don't filter out messages
                pass
            
            # Skip messages that are too short
            if not message.text or len(message.text.strip()) < 50:
                logger.debug(f"🚫 Skipping message - too short: {len(message.text.strip())} chars")
                return
            
            # Create content hash to detect duplicate content
            import hashlib
            content_hash = hashlib.md5(message.text.encode()).hexdigest()
            
            # Skip if content already processed
            if content_hash in self.processed_content:
                logger.debug(f"🔄 Already processed content (hash: {content_hash[:8]}...)")
                return
            
            # Mark as processed immediately to prevent duplicates
            self.processed_messages.add(message_id)
            self.processed_content.add(content_hash)
            
            # Check if message contains job posting
            is_job = self.is_job_posting(message.text)
            logger.info(f"🔍 Job posting check result: {is_job}")
            
            if is_job:
                logger.info(f"🔍 Job posting detected in {channel_name}")
                
                # Add timeout for job extraction
                job_data = await asyncio.wait_for(
                    self.extract_job_data(message), 
                    timeout=10.0  # 10 second timeout
                )
                
                if job_data:
                    logger.info(f"📋 Job extracted: {job_data['title']} at {job_data.get('company_name', 'Unknown')}")
                    
                    # Add timeout for job processing
                    await asyncio.wait_for(
                        self.process_and_forward_job(job_data),
                        timeout=30.0  # 30 second timeout
                    )
                else:
                    logger.warning(f"⚠️ Failed to extract job data from {channel_name}")
            else:
                logger.debug(f"📄 Regular message (not job) from {channel_name}")
            
            # Clear processed messages periodically to prevent memory issues
            if len(self.processed_messages) > 1000:
                self.processed_messages.clear()
                logger.info("🧹 Cleared processed messages cache")
            
            # Clear processed content periodically to prevent memory issues
            if len(self.processed_content) > 1000:
                self.processed_content.clear()
                logger.info("🧹 Cleared processed content cache")
        
        # Add a test handler to see if events are being triggered
        @self.client.on(events.NewMessage)
        async def test_handler(event):
            """Test handler to verify events are working"""
            logger.info(f"🧪 TEST: Event triggered from {getattr(event.message.chat, 'title', 'Unknown')}")
        
        logger.info("✅ Event handlers registered successfully")
    
    async def check_group_access(self):
        """Check if scraper has access to monitored groups/channels"""
        try:
            channels = await self.db.get_active_channels()
            groups = await self.db.get_active_groups()
            
            logger.info("🔍 Checking access to monitored channels/groups...")
            
            # Check channels
            for channel in channels:
                try:
                    identifier = channel.get('telegram_id') or channel['channel_username']
                    entity = await self.client.get_entity(identifier)
                    logger.info(f"✅ Channel access: {channel['channel_username']} -> {getattr(entity, 'title', 'Unknown')}")
                except Exception as e:
                    logger.error(f"❌ No access to channel {channel['channel_username']}: {e}")
            
            # Check groups
            for group in groups:
                try:
                    identifier = group.get('telegram_id') or group['group_username']
                    entity = await self.client.get_entity(identifier)
                    logger.info(f"✅ Group access: {group['group_username']} -> {getattr(entity, 'title', 'Unknown')}")
                except Exception as e:
                    logger.error(f"❌ No access to group {group['group_username']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking group access: {e}")
    
    def is_job_posting(self, text: str) -> bool:
        """Check if message text contains job posting indicators"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Skip bot messages and error messages
        skip_patterns = [
            'database error', 'error adding', 'failed to add', '❌', 'error:',
            'select job categories', 'update preferences', 'contact support',
            'main menu', 'back to', 'help', 'start', 'welcome', 'commands',
            'subscription', 'payment', 'apply', 'profile', 'settings',
            'admin', 'statistics', 'channels', 'groups', 'monitor',
            'forwarded job', 'ai-matched', 'matched job'
        ]
        
        for pattern in skip_patterns:
            if pattern in text_lower:
                logger.debug(f"🚫 Skipping message due to pattern: {pattern}")
                return False
        
        # Skip very short messages
        if len(text.strip()) < 50:
            logger.debug(f"🚫 Skipping message - too short: {len(text.strip())} chars")
            return False
        
        # Skip messages that are mostly buttons or menu options
        if text.count('/') > 2:  # Too many commands
            logger.debug(f"🚫 Skipping message - too many commands: {text.count('/')}")
            return False
        
        # TEMPORARY: For testing, treat any message with "job title:" as a job posting
        if 'job title:' in text_lower:
            logger.info(f"✅ Found 'job title:' - treating as job posting")
            return True
        
        # Check for job keywords with context
        job_keyword_found = False
        for keyword_list in self.job_keywords.values():
            for keyword in keyword_list:
                if keyword in text_lower:
                    job_keyword_found = True
                    logger.debug(f"✅ Found job keyword: {keyword}")
                    break
        
        if not job_keyword_found:
            logger.debug(f"🚫 No job keywords found in text")
            return False
        
        # Additional validation - look for job-specific patterns
        job_indicators = [
            'job title:', 'position:', 'vacancy:', 'hiring:', 'recruitment:',
            'salary:', 'compensation:', 'deadline:', 'work location:',
            'job type:', 'experience:', 'qualification:', 'requirements:',
            'ሥራ:', 'የስራ:', 'ደሞዓ:', 'ክፍያ:', 'ምርጫ:', 'ክፍት'
        ]
        
        has_job_indicator = any(indicator in text_lower for indicator in job_indicators)
        
        # For Afriwork format, check for structured job posting
        afriwork_pattern = any(pattern in text_lower for pattern in [
            'job title:', 'job type:', 'work location:', 'salary/compensation:', 'deadline:'
        ])
        
        result = has_job_indicator or afriwork_pattern
        logger.debug(f"🔍 Job indicators found: {has_job_indicator}, Afriwork pattern: {afriwork_pattern}, Result: {result}")
        
        return result
    
    async def extract_job_data(self, message: Message) -> Optional[Dict[str, Any]]:
        """Extract structured job data from message"""
        try:
            text = message.text or ""
            
            # Extract job title (look for common patterns)
            title = self.extract_title(text)
            
            # Extract company name
            company = self.extract_company(text)
            
            # Extract location
            location = self.extract_location(text)
            
            # Extract job type
            job_type = self.extract_job_type(text)
            
            # Extract salary information
            salary = self.extract_salary(text)
            
            # Extract deadline
            deadline = self.extract_deadline(text)
            
            # Extract application link
            application_link = self.extract_application_link(text)
            
            # Extract view details indicator
            view_details = self.extract_view_details_link(text)
            
            # Clean description
            description = self.clean_description(text)
            
            if not title or not description:
                return None
            
            return {
                'title': title,
                'company_name': company,
                'location': location,
                'job_type': job_type,
                'salary_range': salary,
                'deadline': deadline,
                'application_link': application_link,
                'view_details': view_details,
                'description': description,
                'source': f"telegram_{message.chat_id}",
                'posted_date': datetime.now().date(),
                'telegram_message_id': message.id,
                'telegram_channel': getattr(message.chat, 'title', None) or str(message.chat_id)
            }
            
        except Exception as e:
            logger.error(f"Error extracting job data: {e}")
            return None
    
    def extract_title(self, text: str) -> str:
        """Extract job title from text"""
        lines = text.split('\n')
        
        # Look for Afriwork specific pattern
        for line in lines:
            if line.strip().startswith('Job Title:'):
                return line.replace('Job Title:', '').strip()
        
        # Look for general title patterns
        title_patterns = [
            r'position:\s*(.+)',
            r'job title:\s*(.+)',
            r'role:\s*(.+)',
            r'vacancy:\s*(.+)',
            r'ሥራ:\s*(.+)',
            r'የስራ ስም:\s*(.+)'
        ]
        
        for line in lines:
            for pattern in title_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        # If no pattern found, use first line if it looks like a title
        if lines and len(lines[0]) < 100:
            return lines[0].strip()
        
        return "Job Position"
    
    def extract_job_type(self, text: str) -> str:
        """Extract job type from text"""
        lines = text.split('\n')
        
        # Look for Afriwork specific pattern
        for line in lines:
            if line.strip().startswith('Job Type:'):
                job_type = line.replace('Job Type:', '').strip()
                # Simplify job type
                if 'On-site' in job_type:
                    return 'onsite'
                elif 'Remote' in job_type:
                    return 'remote'
                elif 'Hybrid' in job_type:
                    return 'hybrid'
                return job_type.lower()
        
        # Fallback to original method
        text_lower = text.lower()
        for job_type, keywords in self.job_types.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return job_type
        
        return None
    
    def extract_salary(self, text: str) -> str:
        """Extract salary information from text"""
        lines = text.split('\n')
        
        # Look for Afriwork specific pattern
        for line in lines:
            if line.strip().startswith('Salary/Compensation:'):
                salary = line.replace('Salary/Compensation:', '').strip()
                if salary and salary != 'Monthly' and salary != 'Fixed (One-time)':
                    return salary
        
        # Fallback to original patterns
        salary_patterns = [
            r'salary:\s*([0-9,]+(?:\s*-\s*[0-9,]+)?)\s*(?:birr|etb|br)?',
            r'([0-9,]+(?:\s*-\s*[0-9,]+)?)\s*(?:birr|etb|br)',
            r'ደሞዓ:\s*([0-9,]+(?:\s*-\s*[0-9,]+)?)',
            r'የክፍያት:\s*([0-9,]+(?:\s*-\s*[0-9,]+)?)'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)} Birr"
        
        return None
    
    def extract_location(self, text: str) -> str:
        """Extract location from text"""
        lines = text.split('\n')
        
        # Look for Afriwork specific pattern
        for line in lines:
            if line.strip().startswith('Work Location:'):
                location = line.replace('Work Location:', '').strip()
                return location
        
        # Fallback to original method
        text_lower = text.lower()
        for location in self.locations:
            if location in text_lower:
                return location.title()
        
        return None
    
    def extract_deadline(self, text: str) -> str:
        """Extract application deadline from text"""
        lines = text.split('\n')
        
        # Look for Afriwork specific pattern
        for line in lines:
            if line.strip().startswith('Deadline:'):
                deadline = line.replace('Deadline:', '').strip()
                return deadline
        
        return None
    
    def extract_company(self, text: str) -> str:
        """Extract company name from text"""
        lines = text.split('\n')
        
        # Look for company patterns in Afriwork format
        # Company is usually the last line before the separator
        for i, line in enumerate(lines):
            if '__________________' in line and i > 0:
                # Check the line before separator
                company_line = lines[i-1].strip()
                if company_line and not company_line.startswith('From:') and not company_line.startswith('Verified Company'):
                    return company_line
        
        # Fallback to original patterns
        company_patterns = [
            r'company:\s*(.+)',
            r'organization:\s*(.+)',
            r'employer:\s*(.+)',
            r'ድርጅት:\s*(.+)',
            r'ድርጅታዊ:\s*(.+)'
        ]
        
        for pattern in company_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_application_link(self, text: str) -> str:
        """Extract application link from text"""
        # Look for application links
        link_patterns = [
            r'https://forms\.gle/[^\s]+',
            r'https://[^\s]+\.forms\.gle/[^\s]+',
            r'apply using this link:\s*(https://[^\s]+)',
            r'link:\s*(https://[^\s]+)'
        ]
        
        for pattern in link_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_view_details_link(self, text: str) -> str:
        """Extract 'view details below' link indicator"""
        if '[view details below]' in text:
            return 'View details available in original post'
        return None
    
    def clean_description(self, text: str) -> str:
        """Clean and format job description"""
        # Remove common spam/irrelevant content
        spam_patterns = [
            r'share this post',
            r'forward this message',
            r'join this channel',
            r'click here',
            r'link:\s*https?://\S+',
            r'@[\w]+'
        ]
        
        cleaned = text
        for pattern in spam_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    async def process_and_forward_job(self, job_data: Dict[str, Any]):
        """Process job and forward to MATCHING users (Inclusive)"""
        try:
            # Save minimal data to database
            post_id = await self.save_job_post_to_db(job_data)
            if not post_id:
                logger.error("Failed to save job post to database")
                return
            
            logger.info(f"✅ Saved job post to database: {job_data['title']} at {job_data.get('company_name', 'Unknown')} (Post ID: {post_id})")
            
            # Get MATCHING users (using inclusive preferences)
            users = await self.find_matching_users(job_data)
            
            if not users:
                logger.info("⚠️ No matching users found for job")
                return
            
            logger.info(f"📢 Broadcasting job to {len(users)} matching users")
            
            # Forward to matching users
            for user in users:
                logger.info(f"📤 Forwarding to user {user['user_id']} ({user.get('full_name') or user.get('username')})")
                await self.forward_job_to_user(user, job_data, post_id)
                
        except Exception as e:
            logger.error(f"Error processing job: {e}")

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all bot users for broadcasting"""
        try:
            # Get all users from the database who have a telegram_id
            query = """
                SELECT user_id, full_name, username, telegram_id, role
                FROM users
                WHERE telegram_id IS NOT NULL
                ORDER BY user_id
            """
            
            users = await self.db.execute_query(query)
            return users if users else []
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    async def save_job_post_to_db(self, job_data: Dict[str, Any]) -> Optional[int]:
        """Save minimal job post data to database (DB Agnostic)"""
        try:
            # Prepare values
            params = (
                job_data.get('telegram_message_id'),
                job_data.get('telegram_channel'),
                job_data.get('application_link') or job_data.get('view_details'),
                job_data['title'],
                job_data.get('company_name'),
                job_data.get('location')
            )
            
            if self.db.db_type == 'postgresql':
                query = """
                    INSERT INTO job_posts (
                        telegram_message_id, telegram_channel, post_link, 
                        title, company_name, location, posted_date
                    ) VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                    RETURNING post_id
                """
                result = await self.db.connection.fetchrow(query, *params)
                return result['post_id'] if result else None
            else:
                # SQLite
                query = """
                    INSERT INTO job_posts (
                        telegram_message_id, telegram_channel, post_link, 
                        title, company_name, location, posted_date
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """
                cursor = await self.db.connection.execute(query, params)
                await self.db.connection.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error saving job post: {e}")
            return None

    async def find_matching_users(self, job_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find users who match this job based on preferences (Keywords, Location, Job Type) - INCLUSIVE"""
        try:
            job_title = job_data.get('title', '').lower()
            job_desc = job_data.get('description', '').lower()
            job_location = job_data.get('location', '').lower() if job_data.get('location') else ''
            job_type = job_data.get('job_type', '').lower() if job_data.get('job_type') else ''
            
            # We need to fetch users and their preferences.
            query = """
                SELECT u.user_id, u.full_name, u.telegram_id, u.username, 
                       up.keywords, up.preferred_locations, up.preferred_job_types, up.preferred_categories
                FROM users u
                LEFT JOIN user_preferences up ON u.user_id = up.user_id
                WHERE u.telegram_id IS NOT NULL
            """
            
            users = await self.db.execute_query(query)
            if not users:
                return []
                
            matched_users = []
            
            for user in users:
                score = 0
                is_match = False
                
                # Helper to parse list-like strings from DB (simple parsing)
                def parse_pref_list(pref_value):
                    if not pref_value:
                        return []
                    if isinstance(pref_value, list):
                        return [str(p).lower().strip() for p in pref_value]
                    if isinstance(pref_value, str):
                        # Handle potential Python list string representation or comma separated
                        cleaned = pref_value.replace('[', '').replace(']', '').replace("'", "").replace('"', "")
                        return [p.strip().lower() for p in cleaned.split(',') if p.strip()]
                    return []

                # Parse preferences
                user_locs = parse_pref_list(user.get('preferred_locations'))
                user_types = parse_pref_list(user.get('preferred_job_types'))
                user_cats = parse_pref_list(user.get('preferred_categories'))
                
                # 1. No preferences set? -> Match everything (Broadcast behavior if user hasn't set prefs)
                if not user_locs and not user_types and not user_cats:
                    is_match = True
                    score += 1
                else:
                    # 2. Location Match (Inclusive OR)
                    # If user has "Remote" or "Any Location", they match "Remote" or any location respectively
                    location_match = False
                    if not user_locs or 'any' in user_locs or 'any location' in user_locs:
                        location_match = True
                    elif job_location:
                        if 'remote' in user_locs and ('remote' in job_location or 'work from home' in job_location):
                             location_match = True
                        else:
                            for loc in user_locs:
                                if loc in job_location or job_location in loc:
                                    location_match = True
                                    break
                    
                    if location_match:
                        score += 2
                    
                    # 3. Job Type Match (Inclusive OR)
                    type_match = False
                    if not user_types or 'all' in user_types or 'all job types' in user_types:
                        type_match = True
                    elif job_type:
                         for ut in user_types:
                             if ut in job_type or job_type in ut:
                                 type_match = True
                                 break
                    
                    if type_match:
                        score += 1
                    
                    # 4. Keyword/Category Match (Inclusive OR)
                    # Since we don't have job category extraction yet, rely on title/desc keywords
                    keyword_match = False
                    # Use categories as keywords
                    combined_keywords = user_cats
                    if user.get('keywords'):
                        combined_keywords.extend(parse_pref_list(user.get('keywords')))
                    
                    if not combined_keywords:
                        keyword_match = True # lenient if no keywords/categories
                    else:
                        for kw in combined_keywords:
                            if kw in job_title or kw in job_desc:
                                keyword_match = True
                                break
                    
                    if keyword_match:
                        score += 2

                    # Final Decision: inclusive matching
                    # If ANY criteria matched strongly, or if location matched and others didn't conflict
                    if location_match or type_match or keyword_match:
                        is_match = True
                
                if is_match:
                    user['match_score'] = score
                    matched_users.append(user)
            
            # Sort by score
            matched_users.sort(key=lambda x: x['match_score'], reverse=True)
            
            return matched_users
            
        except Exception as e:
            logger.error(f"Error finding matching users: {e}")
            return []
    
    async def forward_job_to_user(self, user: Dict[str, Any], job_data: Dict[str, Any], job_id: int):
        """Forward job to specific user via bot"""
        try:
            # Import bot here to avoid circular imports
            from bot.config import Config
            
            # Create formatted job message
            message = self.format_job_message(job_data, job_id)
            
            # Send via bot (this would integrate with your main bot)
            # For now, we'll use the bot instance if available
            if hasattr(self, 'bot_instance') and self.bot_instance:
                try:
                    await self.bot_instance.send_message(
                        chat_id=user['telegram_id'],
                        text=message,
                        parse_mode='Markdown'
                    )
                    logger.info(f"✅ Forwarded job to user {user['user_id']}: {job_data['title']}")
                except Exception as e:
                    logger.error(f"Error sending job to user {user['user_id']}: {e}")
            else:
                # Log that we would send the message
                logger.info(f"📤 Would forward job to user {user['user_id']} ({user['telegram_id']}): {job_data['title']}")
                
        except Exception as e:
            logger.error(f"Error forwarding job to user {user['user_id']}: {e}")
    
    def format_job_message(self, job_data: Dict[str, Any], job_id: int) -> str:
        """Format job message for forwarding"""
        message = f"*NEW JOB MATCH*\n\n"
        message += f"*{job_data['title']}*\n"
        
        if job_data.get('company_name'):
            message += f"Company: {job_data['company_name']}\n"
        
        if job_data.get('location'):
            message += f"Location: {job_data['location']}\n"
        
        if job_data.get('job_type'):
            message += f"Job Type: {job_data['job_type'].replace('_', ' ').title()}\n"
        
        if job_data.get('salary_range'):
            message += f"Salary: {job_data['salary_range']}\n"
        
        message += f"\n*Description:*\n{job_data['description'][:500]}...\n\n"
        message += f"Job ID: {job_id}\n"
        message += f"Posted: {job_data['posted_date']}\n\n"
        message += f"*Interested?* Use /apply {job_id} to apply"
        
        return message
    
    async def start_monitoring(self):
        """Start monitoring Telegram groups/channels"""
        if not self.client:
            logger.error("Telethon client not initialized!")
            return
        
        logger.info("🚀 Starting job monitoring...")
        
        # Check access to channels/groups first
        await self.check_group_access()
        
        # Setup handlers
        await self.setup_handlers()
        logger.info("✅ Event handlers setup complete")
        
        # Test if we're actually connected
        try:
            me = await self.client.get_me()
            logger.info(f"🤖 Connected as: {me.first_name} (@{me.username})")
        except Exception as e:
            logger.error(f"❌ Error getting bot info: {e}")
        
        # Show what channels we're monitoring
        try:
            channels = await self.db.get_active_channels()
            groups = await self.db.get_active_groups()
            
            logger.info(f"📺 Monitoring {len(channels)} channels:")
            for channel in channels:
                logger.info(f"   📺 {channel['channel_username']} ({channel.get('channel_title', 'No title')})")
            
            logger.info(f"👥 Monitoring {len(groups)} groups:")
            for group in groups:
                logger.info(f"   👥 {group['group_username']} ({group.get('group_title', 'No title')})")
                
            if not channels and not groups:
                logger.warning("⚠️ No channels or groups configured for monitoring!")
                logger.info("💡 Use admin commands to add channels: /addchannel @username")
                logger.info("💡 Use admin commands to add groups: /addgroup @username")
                return
            
        except Exception as e:
            logger.error(f"Error getting monitored channels: {e}")
        
        logger.info("👂 Listening for job postings... (Press Ctrl+C to stop)")
        logger.info("📨 All incoming messages will be logged for debugging")
        
        # Test message handler with a simple test
        logger.info("🧪 Testing message handler...")
        
        # Keep running
        try:
            await self.client.run_until_disconnected()
        except KeyboardInterrupt:
            logger.info("👋 Scraper stopped by user")
        except Exception as e:
            logger.error(f"❌ Scraper error: {e}")
    
    async def load_sources_from_db(self):
        """Load channels and groups to monitor from database"""
        try:
            channels = await self.db.get_active_channels()
            groups = await self.db.get_active_groups()
            
            sources_added = 0
            
            # Add channels
            for channel in channels:
                # Use telegram_id if available, otherwise use username
                identifier = channel.get('telegram_id') or channel['channel_username']
                if await self.add_source_channel(identifier):
                    sources_added += 1
                    logger.info(f"Loaded channel from DB: {channel['channel_username']} ({channel.get('channel_title', 'No title')}) -> ID: {channel.get('telegram_id', 'N/A')}")
            
            # Add groups
            for group in groups:
                # Use telegram_id if available, otherwise use username
                identifier = group.get('telegram_id') or group['group_username']
                if await self.add_source_channel(identifier):
                    sources_added += 1
                    logger.info(f"Loaded group from DB: {group['group_username']} ({group.get('group_title', 'No title')}) -> ID: {group.get('telegram_id', 'N/A')}")
            
            logger.info(f"Loaded {sources_added} sources from database")
            return sources_added
            
        except Exception as e:
            logger.error(f"Error loading sources from database: {e}")
            return 0
    
    async def add_source_channel(self, channel_username: str):
        """Add a new channel/group to monitor"""
        try:
            # Clean username - remove @ if present for database storage
            # Handle if channel_username is an int
            clean_username = str(channel_username).lstrip('@')
            
            # Try different ways to get the entity
            entity = None
            
            # Method 1: Try with @ prefix
            try:
                entity = await self.client.get_entity(f"@{clean_username}")
            except:
                pass
            
            # Method 2: Try without @ prefix
            if not entity:
                try:
                    entity = await self.client.get_entity(clean_username)
                except:
                    pass
            
            # Method 3: Try as numeric ID if it looks like a number
            if not entity and clean_username.isdigit():
                try:
                    entity = await self.client.get_entity(int(clean_username))
                except:
                    pass
            
            if not entity:
                logger.error(f"Could not find entity for: {channel_username}")
                return False
            
            # Extract the actual channel ID
            channel_id = entity.id
            logger.info(f"Added monitoring for: {getattr(entity, 'title', str(channel_id))} (ID: {channel_id})")
            
            # Store the actual channel ID for future reference
            await self.store_channel_id(clean_username, channel_id, getattr(entity, 'title', None))
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding channel {channel_username}: {e}")
            return False
    
    async def get_channel_info(self, channel_identifier: str):
        """Get detailed information about a channel/group"""
        try:
            # Try different ways to get the entity
            entity = None
            
            # Method 1: Try with @ prefix
            try:
                entity = await self.client.get_entity(f"@{channel_identifier.lstrip('@')}")
            except:
                pass
            
            # Method 2: Try without @ prefix
            if not entity:
                try:
                    entity = await self.client.get_entity(channel_identifier.lstrip('@'))
                except:
                    pass
            
            # Method 3: Try as numeric ID
            if not entity and channel_identifier.isdigit():
                try:
                    entity = await self.client.get_entity(int(channel_identifier))
                except:
                    pass
            
            if not entity:
                return None
            
            return {
                'id': entity.id,
                'username': getattr(entity, 'username', None),
                'title': getattr(entity, 'title', None),
                'type': type(entity).__name__,
                'access_hash': getattr(entity, 'access_hash', None)
            }
            
        except Exception as e:
            logger.error(f"Error getting channel info for {channel_identifier}: {e}")
            return None

    async def store_channel_id(self, username: str, channel_id: int, title: str = None):
        """Store the actual channel ID in database for future use"""
        try:
            # Update the database with the actual channel ID
            # This would require adding a channel_id column to your tables
            logger.info(f"Channel ID mapping: {username} -> {channel_id}")
        except Exception as e:
            logger.error(f"Error storing channel ID: {e}")

# Usage example
async def main():
    """Main function to run the job scraper"""
    from bot.database import DatabaseManager
    
    db = DatabaseManager()
    await db.connect()
    
    scraper = JobScraper(db)
    
    if await scraper.initialize():
        # Load channels and groups from database
        sources_loaded = await scraper.load_sources_from_db()
        
        if sources_loaded > 0:
            print(f"✅ Loaded {sources_loaded} sources from database")
            # Start monitoring
            await scraper.start_monitoring()
        else:
            print("⚠️ No sources found in database")
    
    await db.close()

if __name__ == '__main__':
    asyncio.run(main())
