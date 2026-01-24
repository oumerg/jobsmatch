#!/usr/bin/env python3
"""
Database Migration Script
Safely adds missing columns to existing database tables
"""

import asyncio
import asyncpg
import logging
import sys
from bot.config import Config

async def migrate_database():
    """Migrate existing database to new schema"""
    print("🔄 Starting database migration...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host=Config.POSTGRES_HOST,
            port=int(Config.POSTGRES_PORT),
            database=Config.POSTGRES_DB,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD
        )
        
        print("✅ Connected to database")
        
        # Fix existing subscription table constraint for payment_method
        print("🔧 Checking subscription table constraints...")
        try:
            # Drop the old constraint if it exists
            await conn.execute("ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_payment_method_check")
            print("✅ Dropped old payment_method constraint")
            
            # Add the new constraint with trial and free_trial options
            constraint_sql = """
                ALTER TABLE subscriptions 
                ADD CONSTRAINT subscriptions_payment_method_check 
                CHECK (payment_method IN ('telebirr', 'cbebirr', 'hello_cash', 'manual', 'trial', 'free_trial'))
            """
            await conn.execute(constraint_sql)
            print("✅ Added new payment_method constraint with trial options")
            
            # Add unique constraint on user_id if not exists
            try:
                await conn.execute("ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_user_id_unique UNIQUE (user_id)")
                print("✅ Added unique constraint on user_id")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("⏭️ Unique constraint on user_id already exists")
                else:
                    print(f"⚠️ Could not add unique constraint: {e}")
            
        except Exception as e:
            print(f"⚠️ Could not update payment_method constraint: {e}")
        
        # Check existing columns in monitor_channels table
        channels_columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'monitor_channels'
        """
        existing_channels_columns = {row['column_name'] for row in await conn.fetch(channels_columns_query)}
        
        # Add channel_id column if not exists
        if 'telegram_id' not in existing_channels_columns:
            print("➕ Adding telegram_id column to monitor_channels")
            try:
                await conn.execute("ALTER TABLE monitor_channels ADD COLUMN IF NOT EXISTS telegram_id BIGINT")
                print("✅ Added telegram_id to monitor_channels")
            except Exception as e:
                print(f"❌ Error adding telegram_id to monitor_channels: {e}")
        else:
            print("⏭️ telegram_id column already exists in monitor_channels")
        
        # Check existing columns in monitor_groups table
        groups_columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'monitor_groups'
        """
        existing_groups_columns = {row['column_name'] for row in await conn.fetch(groups_columns_query)}
        
        # Add group_id column if not exists
        if 'telegram_id' not in existing_groups_columns:
            print("➕ Adding telegram_id column to monitor_groups")
            try:
                await conn.execute("ALTER TABLE monitor_groups ADD COLUMN IF NOT EXISTS telegram_id BIGINT")
                print("✅ Added telegram_id to monitor_groups")
            except Exception as e:
                print(f"❌ Error adding telegram_id to monitor_groups: {e}")
        else:
            print("⏭️ telegram_id column already exists in monitor_groups")
        
        # Check existing columns in users table
        columns_query = """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """
        existing_columns = {row['column_name'] for row in await conn.fetch(columns_query)}
        print(f"📋 Existing columns: {list(existing_columns)}")
        
        # Add missing columns one by one
        migrations = [
            ('telegram_id', 'BIGINT', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id BIGINT UNIQUE'),
            ('full_name', 'VARCHAR(100)', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100)'),
            ('email', 'VARCHAR(100)', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(100)'),
            ('role', 'VARCHAR(20)', "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'seeker' CHECK (role IN ('seeker', 'employer', 'admin'))"),
            ('last_active', 'TIMESTAMP', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active TIMESTAMP'),
            ('language', 'VARCHAR(10)', "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'am' CHECK (language IN ('am', 'en', 'et'))"),
            ('referral_code', 'VARCHAR(20)', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20) UNIQUE'),
            ('referral_data', 'JSONB', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_data JSONB'),
            ('total_earnings', 'DECIMAL(10,2)', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS total_earnings DECIMAL(10,2) DEFAULT 0.00'),
            ('available_balance', 'DECIMAL(10,2)', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS available_balance DECIMAL(10,2) DEFAULT 0.00'),
            ('referred_by', 'BIGINT', 'ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT REFERENCES users(user_id)')
        ]
        
        for column_name, data_type, alter_sql in migrations:
            if column_name not in existing_columns:
                print(f"➕ Adding column: {column_name}")
                try:
                    await conn.execute(alter_sql)
                    print(f"✅ Added {column_name} successfully")

                    # Set default values for newly added columns
                    if column_name == 'referral_data':
                        await conn.execute("UPDATE users SET referral_data = '{}' WHERE referral_data IS NULL")
                        print(f"✅ Set default value for {column_name}")

                except Exception as e:
                    print(f"❌ Error adding {column_name}: {e}")
            else:
                print(f"⏭️ Column {column_name} already exists")
        
        # Create new tables if they don't exist
        new_tables = [
            ('subscriptions', '''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    subscription_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    status VARCHAR(20) DEFAULT 'trial' CHECK (status IN ('active', 'expired', 'canceled', 'trial')),
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    payment_method VARCHAR(20) CHECK (payment_method IN ('telebirr', 'cbebirr', 'hello_cash', 'manual', 'trial', 'free_trial')),
                    transaction_ref VARCHAR(100),
                    amount_birr DECIMAL(10,2) DEFAULT 50.00,
                    renewal_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''),
            ('job_seekers', '''
                CREATE TABLE IF NOT EXISTS job_seekers (
                    seeker_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    education_level VARCHAR(20) CHECK (education_level IN ('highschool', 'diploma', 'bachelor', 'master', 'phd', 'other')),
                    field_of_study VARCHAR(100),
                    years_experience SMALLINT DEFAULT 0,
                    current_job_title VARCHAR(100),
                    preferred_location VARCHAR(100),
                    expected_salary DECIMAL(10,2),
                    resume_text TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''),
            ('user_preferences', '''
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
            '''),
            ('pending_payments', '''
                CREATE TABLE IF NOT EXISTS pending_payments (
                    payment_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    payment_method VARCHAR(20) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    reference VARCHAR(100) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by BIGINT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''),
            ('monitor_channels', '''
                CREATE TABLE IF NOT EXISTS monitor_channels (
                    channel_id BIGSERIAL PRIMARY KEY,
                    channel_username VARCHAR(100) UNIQUE NOT NULL,
                    channel_title VARCHAR(200),
                    channel_type VARCHAR(20) DEFAULT 'channel' CHECK (channel_type IN ('channel', 'group', 'private')),
                    telegram_id BIGINT,
                    is_active BOOLEAN DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP,
                    total_messages_scraped INTEGER DEFAULT 0,
                    total_jobs_found INTEGER DEFAULT 0,
                    notes TEXT
                )
            '''),
            ('monitor_groups', '''
                CREATE TABLE IF NOT EXISTS monitor_groups (
                    group_id BIGSERIAL PRIMARY KEY,
                    group_username VARCHAR(100) UNIQUE,
                    group_title VARCHAR(200),
                    group_type VARCHAR(20) DEFAULT 'public' CHECK (group_type IN ('public', 'private', 'supergroup')),
                    telegram_id BIGINT,
                    is_active BOOLEAN DEFAULT TRUE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_checked TIMESTAMP,
                    total_messages_scraped INTEGER DEFAULT 0,
                    total_jobs_found INTEGER DEFAULT 0,
                    invite_link TEXT,
                    notes TEXT
                )
            '''),
            ('skills', '''
                CREATE TABLE IF NOT EXISTS skills (
                    skill_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL
                )
            '''),
            ('seeker_skills', '''
                CREATE TABLE IF NOT EXISTS seeker_skills (
                    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    skill_id INTEGER NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
                    level VARCHAR(20) CHECK (level IN ('beginner', 'intermediate', 'expert')),
                    years_experience SMALLINT,
                    PRIMARY KEY (user_id, skill_id)
                )
            '''),
            ('job_posts', '''
                CREATE TABLE IF NOT EXISTS job_posts (
                    post_id BIGSERIAL PRIMARY KEY,
                    telegram_message_id BIGINT UNIQUE,
                    telegram_channel VARCHAR(200),
                    post_link TEXT,
                    title VARCHAR(200),
                    company_name VARCHAR(200),
                    location VARCHAR(100),
                    posted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
        ]
        
        tables_created = []
        for table_name, create_sql in new_tables:
            try:
                # Check if table exists first
                table_check = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table_name
                )
                
                if not table_check:
                    await conn.execute(create_sql)
                    tables_created.append(table_name)
                    print(f"✅ Created {table_name} successfully")
                else:
                    print(f"⏭️ Table {table_name} already exists")
                    
            except Exception as e:
                print(f"❌ Error with {table_name}: {e}")
        
        if not tables_created:
            print("✅ All tables already exist - no schema changes needed")
        
        print("✅ Database schema migration completed!")
        print("💡 Use admin commands to add channels/groups: /addchannel @username, /addgroup @username")
        
        await conn.close()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(migrate_database())
