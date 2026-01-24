-- PostgreSQL Database Setup for Job Matching Bot
-- Run this script to create the database and user

-- Create database (run as postgres user)
-- CREATE DATABASE jobbot;

-- Create user (run as postgres user)
-- CREATE USER jobbot_user WITH PASSWORD 'your_password_here';

-- Grant privileges
-- GRANT ALL PRIVILEGES ON DATABASE jobbot TO jobbot_user;

-- Connect to the jobbot database and run these commands:
-- \c jobbot

-- Grant schema privileges
-- GRANT ALL ON SCHEMA public TO jobbot_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO jobbot_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO jobbot_user;

-- Set default permissions for future tables
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO jobbot_user;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO jobbot_user;
