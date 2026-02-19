import os
import asyncpg
import pymongo
import sqlite3
import aiosqlite
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class User(BaseModel):
    user_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class DatabaseManager:
    def __init__(self):
        self.db_type = os.getenv('DB_TYPE', 'sqlite').lower()
        self.connection = None
        
    async def connect(self):
        """Connect to the database based on DB_TYPE"""
        if self.db_type == 'postgresql':
            await self._connect_postgresql()
        elif self.db_type == 'mongodb':
            await self._connect_mongodb()
        else:
            await self._connect_sqlite()
    
    async def _connect_postgresql(self):
        """Connect to PostgreSQL database"""
        self.connection = await asyncpg.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'jobbot'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'postgres')
        )
        # Don't create tables here - migration will handle it
    
    async def _connect_mongodb(self):
        """Connect to MongoDB"""
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        self.connection = pymongo.MongoClient(mongo_uri)
        self.db = self.connection[os.getenv('MONGODB_DB', 'jobbot')]
    
    async def _connect_sqlite(self):
        """Connect to SQLite database"""
        self.connection = await aiosqlite.connect('jobbot.db')
        await self._create_sqlite_tables()
    
    async def _create_sqlite_tables(self):
        """Create SQLite tables"""
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT,
                username TEXT,
                phone_number TEXT,
                referral_code TEXT UNIQUE,
                referral_data TEXT,
                total_earnings REAL DEFAULT 0.00,
                available_balance REAL DEFAULT 0.00,
                referred_by INTEGER,
                telegram_id INTEGER UNIQUE,
                full_name TEXT,
                email TEXT,
                role TEXT DEFAULT 'seeker',
                language TEXT DEFAULT 'am',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS job_posts (
                post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_message_id INTEGER UNIQUE,
                telegram_channel TEXT,
                post_link TEXT,
                title TEXT,
                company_name TEXT,
                location TEXT,
                posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                preferred_job_types TEXT, -- Stored as comma-separated string or JSON
                preferred_locations TEXT,
                preferred_categories TEXT,
                min_salary INTEGER,
                max_experience INTEGER,
                education_level TEXT,
                keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS monitor_channels (
                channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username TEXT UNIQUE NOT NULL,
                channel_title TEXT,
                channel_type TEXT DEFAULT 'channel',
                telegram_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP,
                total_messages_scraped INTEGER DEFAULT 0,
                total_jobs_found INTEGER DEFAULT 0,
                notes TEXT
            )
        ''')
        
        await self.connection.execute('''
            CREATE TABLE IF NOT EXISTS monitor_groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_username TEXT UNIQUE,
                group_title TEXT,
                group_type TEXT DEFAULT 'public',
                telegram_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP,
                total_messages_scraped INTEGER DEFAULT 0,
                total_jobs_found INTEGER DEFAULT 0,
                invite_link TEXT,
                notes TEXT
            )
        ''')
        
        await self.connection.execute('''
             CREATE TABLE IF NOT EXISTS subscriptions (
                subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                status TEXT DEFAULT 'trial',
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                payment_method TEXT,
                transaction_ref TEXT,
                amount_birr REAL DEFAULT 50.00,
                renewal_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
    
    async def save_user(self, user_data: Dict[str, Any]) -> bool:
        """Save or update user information"""
        try:
            if self.db_type == 'postgresql':
                await self._save_user_postgresql(user_data)
            elif self.db_type == 'mongodb':
                await self._save_user_mongodb(user_data)
            else:
                await self._save_user_sqlite(user_data)
            return True
        except Exception as e:
            print(f"Error saving user: {e}")
            return False
    
    async def _save_user_postgresql(self, user_data: Dict[str, Any]):
        """Save user to PostgreSQL"""
        await self.connection.execute('''
            INSERT INTO users (user_id, first_name, last_name, username, phone_number)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                username = EXCLUDED.username,
                phone_number = EXCLUDED.phone_number,
                updated_at = CURRENT_TIMESTAMP
        ''', user_data['user_id'], user_data['first_name'], 
            user_data.get('last_name'), user_data.get('username'), 
            user_data.get('phone_number'))
    
    async def _save_user_mongodb(self, user_data: Dict[str, Any]):
        """Save user to MongoDB"""
        user_data['updated_at'] = datetime.now()
        self.db.users.update_one(
            {'user_id': user_data['user_id']},
            {'$set': user_data, '$setOnInsert': {'created_at': datetime.now()}},
            upsert=True
        )
    
    async def _save_user_sqlite(self, user_data: Dict[str, Any]):
        """Save user to SQLite"""
        await self.connection.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, first_name, last_name, username, phone_number, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_data['user_id'], user_data['first_name'], 
            user_data.get('last_name'), user_data.get('username'), 
            user_data.get('phone_number')))
        
        # Handle referral data separately to avoid overwriting
        if 'referral_code' in user_data:
            await self.connection.execute('''
                UPDATE users SET referral_code = ? WHERE user_id = ?
            ''', (user_data['referral_code'], user_data['user_id']))
        
        if 'referral_data' in user_data:
            await self.connection.execute('''
                UPDATE users SET referral_data = ? WHERE user_id = ?
            ''', (user_data['referral_data'], user_data['user_id']))
            
        if 'total_earnings' in user_data:
            await self.connection.execute('''
                UPDATE users SET total_earnings = ? WHERE user_id = ?
            ''', (user_data['total_earnings'], user_data['user_id']))
            
        if 'available_balance' in user_data:
            await self.connection.execute('''
                UPDATE users SET available_balance = ? WHERE user_id = ?
            ''', (user_data['available_balance'], user_data['user_id']))
            
        if 'referred_by' in user_data:
            await self.connection.execute('''
                UPDATE users SET referred_by = ? WHERE user_id = ?
            ''', (user_data['referred_by'], user_data['user_id']))
        
        await self.connection.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by user_id"""
        try:
            if self.db_type == 'postgresql':
                row = await self.connection.fetchrow(
                    'SELECT * FROM users WHERE user_id = $1', user_id
                )
                return dict(row) if row else None
            elif self.db_type == 'mongodb':
                user = self.db.users.find_one({'user_id': user_id})
                return user
            else:
                cursor = await self.connection.execute(
                    'SELECT * FROM users WHERE user_id = ?', (user_id,)
                )
                row = await cursor.fetchone()
                if row:
                    # Convert SQLite row to dict
                    columns = [description[0] for description in cursor.description] if cursor.description else []
                    if columns:
                        return dict(zip(columns, row))
                    # Fallback: use row keys if available
                    return dict(row) if hasattr(row, 'keys') else None
                return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            if self.db_type == 'postgresql':
                await self.connection.close()
            elif self.db_type == 'mongodb':
                self.connection.close()
            else:
                await self.connection.close()
    
    async def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute a query and return results"""
        try:
            if self.db_type == 'postgresql':
                if params:
                    result = await self.connection.fetch(query, *params)
                else:
                    result = await self.connection.fetch(query)
                # Convert asyncpg Record objects to dictionaries
                return [dict(row) for row in result] if result else []
            elif self.db_type == 'mongodb':
                # MongoDB queries would need different handling
                return []
            else:
                cursor = await self.connection.execute(query, params or ())
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = await cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows] if rows else []
                return []
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
    
    async def get_active_channels(self) -> list:
        """Get all active channels to monitor"""
        query = """
            SELECT channel_id, channel_username, channel_title, channel_type, telegram_id
            FROM monitor_channels 
            WHERE is_active = TRUE
            ORDER BY channel_username
        """
        return await self.execute_query(query)
    
    async def get_active_groups(self) -> list:
        """Get all active groups to monitor"""
        query = """
            SELECT group_id, group_username, group_title, group_type, telegram_id
            FROM monitor_groups 
            WHERE is_active = TRUE
            ORDER BY group_username
        """
        return await self.execute_query(query)
    
    async def add_monitor_channel(self, username: str, title: str = None, channel_type: str = 'channel', notes: str = None, telegram_id: int = None) -> bool:
        """Add a new channel to monitor"""
        try:
            if self.db_type == 'postgresql':
                # First try to insert, if conflict then update
                try:
                    query = "INSERT INTO monitor_channels (channel_username, channel_title, channel_type, notes, telegram_id) VALUES ($1, $2, $3, $4, $5)"
                    await self.connection.execute(query, username, title, channel_type, notes, telegram_id)
                except Exception:
                    # If conflict, update existing record
                    query = "UPDATE monitor_channels SET channel_title = $1, channel_type = $2, notes = $3, telegram_id = $4, is_active = TRUE WHERE channel_username = $5"
                    await self.connection.execute(query, title, channel_type, notes, telegram_id, username)
            else:
                await self.connection.execute('''
                    INSERT OR REPLACE INTO monitor_channels 
                    (channel_username, channel_title, channel_type, notes, telegram_id, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (username, title, channel_type, notes, telegram_id))
                await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error adding channel: {e}")
            return False
    
    async def add_monitor_group(self, username: str, title: str = None, group_type: str = 'public', notes: str = None, telegram_id: int = None) -> bool:
        """Add a new group to monitor"""
        try:
            if self.db_type == 'postgresql':
                await self.connection.execute('''
                    INSERT INTO monitor_groups (group_username, group_title, group_type, notes, telegram_id)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (group_username) DO UPDATE SET
                        group_title = EXCLUDED.group_title,
                        group_type = EXCLUDED.group_type,
                        notes = EXCLUDED.notes,
                        telegram_id = EXCLUDED.telegram_id,
                        is_active = TRUE
                ''', username, title, group_type, notes, telegram_id)
            else:
                await self.connection.execute('''
                    INSERT OR REPLACE INTO monitor_groups 
                    (group_username, group_title, group_type, notes, telegram_id, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (username, title, group_type, notes, telegram_id))
                await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error adding group: {e}")
            return False
    
    async def update_channel_telegram_id(self, username: str, telegram_id: int) -> bool:
        """Update the telegram_id for an existing channel"""
        try:
            if self.db_type == 'postgresql':
                await self.connection.execute('''
                    UPDATE monitor_channels SET telegram_id = $1 WHERE channel_username = $2
                ''', telegram_id, username)
            else:
                await self.connection.execute('''
                    UPDATE monitor_channels SET telegram_id = ? WHERE channel_username = ?
                ''', (telegram_id, username))
                await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error updating channel telegram_id: {e}")
            return False
    
    async def update_group_telegram_id(self, username: str, telegram_id: int) -> bool:
        """Update the telegram_id for an existing group"""
        try:
            if self.db_type == 'postgresql':
                await self.connection.execute('''
                    UPDATE monitor_groups SET telegram_id = $1 WHERE group_username = $2
                ''', telegram_id, username)
            else:
                await self.connection.execute('''
                    UPDATE monitor_groups SET telegram_id = ? WHERE group_username = ?
                ''', (telegram_id, username))
                await self.connection.commit()
            return True
        except Exception as e:
            print(f"Error updating group telegram_id: {e}")
            return False
