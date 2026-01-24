-- Referral System Setup for Ethiopian Job Bot

-- Create referrals table to track referral relationships and earnings
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id INTEGER NOT NULL REFERENCES job_seekers(user_id),
    referred_id INTEGER NOT NULL REFERENCES job_seekers(user_id),
    referral_code VARCHAR(20) NOT NULL,
    earnings DECIMAL(10, 2) DEFAULT 1.00, -- 1 ETB per referral
    status VARCHAR(20) DEFAULT 'pending', -- pending, confirmed, paid
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    UNIQUE(referrer_id, referred_id),
    UNIQUE(referral_code)
);

-- Create referral_codes table to manage unique referral codes
CREATE TABLE IF NOT EXISTS referral_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES job_seekers(user_id),
    referral_code VARCHAR(20) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    uses_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create referral_earnings table to track user earnings and withdrawals
CREATE TABLE IF NOT EXISTS referral_earnings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES job_seekers(user_id),
    referral_id INTEGER REFERENCES referrals(id),
    amount DECIMAL(10, 2) NOT NULL DEFAULT 1.00,
    type VARCHAR(20) DEFAULT 'referral', -- referral, bonus, withdrawal
    status VARCHAR(20) DEFAULT 'available', -- available, withdrawn, pending
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Add referral columns to job_seekers table if they don't exist
ALTER TABLE job_seekers 
ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20) UNIQUE,
ADD COLUMN IF NOT EXISTS total_earnings DECIMAL(10, 2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS available_balance DECIMAL(10, 2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS referred_by INTEGER REFERENCES job_seekers(user_id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_code ON referrals(referral_code);
CREATE INDEX IF NOT EXISTS idx_referral_codes_user_id ON referral_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_referral_codes_code ON referral_codes(referral_code);
CREATE INDEX IF NOT EXISTS idx_referral_earnings_user_id ON referral_earnings(user_id);

-- Create function to generate unique referral codes
CREATE OR REPLACE FUNCTION generate_referral_code(user_id_param INTEGER)
RETURNS TEXT AS $$
DECLARE
    new_code TEXT;
    code_exists BOOLEAN;
BEGIN
    LOOP
        -- Generate code: REF + first 4 chars of user_id + random 4 digits
        new_code := 'REF' || LPAD(user_id_param::TEXT, 4, '0') || LPAD(FLOOR(RANDOM() * 10000)::TEXT, 4, '0');
        
        -- Check if code already exists
        SELECT EXISTS(SELECT 1 FROM referral_codes WHERE referral_code = new_code) INTO code_exists;
        
        IF NOT code_exists THEN
            EXIT;
        END IF;
    END LOOP;
    
    RETURN new_code;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically generate referral code for new users
CREATE OR REPLACE FUNCTION auto_generate_referral_code()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.referral_code IS NULL THEN
        NEW.referral_code := generate_referral_code(NEW.user_id);
        
        -- Insert into referral_codes table
        INSERT INTO referral_codes (user_id, referral_code)
        VALUES (NEW.user_id, NEW.referral_code);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_generate_referral_code ON job_seekers;
CREATE TRIGGER trigger_generate_referral_code
    BEFORE INSERT ON job_seekers
    FOR EACH ROW
    EXECUTE FUNCTION auto_generate_referral_code();

-- Create function to process referral earnings
CREATE OR REPLACE FUNCTION process_referral_earning(referrer_id_param INTEGER, referred_id_param INTEGER, referral_code_param TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    referral_id INTEGER;
    earning_id INTEGER;
BEGIN
    -- Check if referral already processed
    IF EXISTS(SELECT 1 FROM referrals WHERE referred_id = referred_id_param) THEN
        RETURN FALSE;
    END IF;
    
    -- Create referral record
    INSERT INTO referrals (referrer_id, referred_id, referral_code, status, confirmed_at)
    VALUES (referrer_id_param, referred_id_param, referral_code_param, 'confirmed', CURRENT_TIMESTAMP)
    RETURNING id INTO referral_id;
    
    -- Add earnings to referrer
    INSERT INTO referral_earnings (user_id, referral_id, amount, type, status, description)
    VALUES (referrer_id_param, referral_id, 1.00, 'referral', 'available', 'Referral bonus for user ' || referred_id_param)
    RETURNING id INTO earning_id;
    
    -- Update referrer's total earnings and balance
    UPDATE job_seekers 
    SET 
        total_earnings = total_earnings + 1.00,
        available_balance = available_balance + 1.00
    WHERE user_id = referrer_id_param;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
