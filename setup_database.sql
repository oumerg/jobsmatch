-- Job Bot Database Schema for Ethiopian Job Market
-- PostgreSQL Schema

-- Check if users table exists and add missing columns
DO $$
BEGIN
    -- Add new columns to existing users table if they don't exist
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'telegram_id') THEN
        -- Column exists, do nothing
    ELSE
        EXECUTE 'ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id BIGINT UNIQUE';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'full_name') THEN
        -- Column exists, do nothing
    ELSE
        EXECUTE 'ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100)';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'email') THEN
        -- Column exists, do nothing
    ELSE
        EXECUTE 'ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(100)';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'role') THEN
        -- Column exists, do nothing
    ELSE
        EXECUTE 'ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT ''seeker'' CHECK (role IN (''seeker'', ''employer'', ''admin''))';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_active') THEN
        -- Column exists, do nothing
    ELSE
        EXECUTE 'ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active TIMESTAMP';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'language') THEN
        -- Column exists, do nothing
    ELSE
        EXECUTE 'ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT ''am'' CHECK (language IN (''am'', ''en'', ''et''))';
    END IF;
END $$;

-- Subscriptions Table (50 Birr/month)
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'trial' CHECK (status IN ('active', 'expired', 'canceled', 'trial')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    payment_method VARCHAR(20) CHECK (payment_method IN ('telebirr', 'cbebirr', 'hello_cash', 'manual', 'trial', 'free_trial')),
    transaction_ref VARCHAR(100),
    amount_birr DECIMAL(10,2) DEFAULT 50.00,
    renewal_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job Seekers Profile Table
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
);

-- Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    job_id BIGSERIAL PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    company_name VARCHAR(100),
    location VARCHAR(100),
    job_type VARCHAR(20) CHECK (job_type IN ('full_time', 'part_time', 'contract', 'remote', 'internship')),
    salary_range VARCHAR(50),
    description TEXT NOT NULL,
    requirements TEXT,
    posted_by_user_id BIGINT REFERENCES users(user_id),
    source VARCHAR(50),
    posted_date DATE DEFAULT CURRENT_DATE,
    expires_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    views_count INTEGER DEFAULT 0,
    telegram_message_id BIGINT,
    telegram_channel VARCHAR(100)
);

-- Job Matches/Recommendations Table
CREATE TABLE IF NOT EXISTS job_matches (
    match_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    job_id BIGINT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    match_score DECIMAL(5,2),
    status VARCHAR(20) DEFAULT 'new' CHECK (status IN ('new', 'viewed', 'applied', 'rejected', 'saved')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, job_id)
);

-- Applications Table
CREATE TABLE IF NOT EXISTS applications (
    application_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    job_id BIGINT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'submitted' CHECK (status IN ('submitted', 'seen', 'interview', 'rejected', 'hired')),
    notes TEXT
);

-- User Preferences Table
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
);

-- Monitor Channels Table (for managing which channels/groups to scrape)
CREATE TABLE IF NOT EXISTS monitor_channels (
    channel_id BIGSERIAL PRIMARY KEY,
    channel_username VARCHAR(100) UNIQUE NOT NULL,
    channel_title VARCHAR(200),
    channel_type VARCHAR(20) DEFAULT 'channel' CHECK (channel_type IN ('channel', 'group', 'private')),
    is_active BOOLEAN DEFAULT TRUE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP,
    total_messages_scraped INTEGER DEFAULT 0,
    total_jobs_found INTEGER DEFAULT 0,
    notes TEXT
);

-- Monitor Groups Table (for managing which groups to scrape)
CREATE TABLE IF NOT EXISTS monitor_groups (
    group_id BIGSERIAL PRIMARY KEY,
    group_username VARCHAR(100) UNIQUE,
    group_title VARCHAR(200),
    group_type VARCHAR(20) DEFAULT 'public' CHECK (group_type IN ('public', 'private', 'supergroup')),
    is_active BOOLEAN DEFAULT TRUE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP,
    total_messages_scraped INTEGER DEFAULT 0,
    total_jobs_found INTEGER DEFAULT 0,
    invite_link TEXT,
    notes TEXT
);

-- Skills Table
CREATE TABLE IF NOT EXISTS skills (
    skill_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- Seeker Skills (Many-to-Many)
CREATE TABLE IF NOT EXISTS seeker_skills (
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    level VARCHAR(20) CHECK (level IN ('beginner', 'intermediate', 'expert')),
    years_experience SMALLINT,
    PRIMARY KEY (user_id, skill_id)
);

-- Job Skills (Many-to-Many)
CREATE TABLE IF NOT EXISTS job_skills (
    job_id BIGINT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    required_level VARCHAR(20) CHECK (required_level IN ('beginner', 'intermediate', 'expert')),
    PRIMARY KEY (job_id, skill_id)
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_job_seekers_user ON job_seekers(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date);
CREATE INDEX IF NOT EXISTS idx_job_matches_user ON job_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_job_matches_status ON job_matches(status);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_monitor_channels_active ON monitor_channels(is_active);
CREATE INDEX IF NOT EXISTS idx_monitor_groups_active ON monitor_groups(is_active);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_job_seekers_updated_at 
    BEFORE UPDATE ON job_seekers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at 
    BEFORE UPDATE ON user_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
