import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class for the Job Bot"""
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN')
    BOT_USER_NAME: str = os.getenv('BOT_USER_NAME', 'jobsmatchbot')
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')
    
    # Database Configuration
    DB_TYPE: str = os.getenv('DB_TYPE', 'sqlite')
    
    # PostgreSQL Configuration
    POSTGRES_HOST: str = os.getenv('POSTGRES_HOST',)
    POSTGRES_PORT: int = int(os.getenv('POSTGRES_PORT'))
    POSTGRES_DB: str = os.getenv('POSTGRES_DB', 'jobbot')
    POSTGRES_USER: str = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD: str = os.getenv('POSTGRES_PASSWORD', 'postgres')
    
    # MongoDB Configuration
    MONGODB_URI: str = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB: str = os.getenv('MONGODB_DB', 'jobbot')
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'WARNING')
    LOG_FILE: str = os.getenv('LOG_FILE', 'bot.log')
    
    # Bot Configuration
    JOBS_PER_PAGE: int = int(os.getenv('JOBS_PER_PAGE', 10))
    MATCH_THRESHOLD: float = float(os.getenv('MATCH_THRESHOLD', 0.6))
    SCAN_INTERVAL: int = int(os.getenv('SCAN_INTERVAL', 30))
    MAX_JOB_AGE_DAYS: int = int(os.getenv('MAX_JOB_AGE_DAYS', 30))
    
    # Admin Configuration
    ADMIN_IDS: list = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '7992535377').split(',') if id.strip()]
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL: str = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    GEMINI_TEMPERATURE: float = float(os.getenv('GEMINI_TEMPERATURE', '0.3'))
    GEMINI_MAX_TOKENS: int = int(os.getenv('GEMINI_MAX_TOKENS', '1000'))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.TELEGRAM_BOT_TOKEN:
            print("ERROR: TELEGRAM_BOT_TOKEN is required")
            return False
        
        if cls.DB_TYPE not in ['sqlite', 'postgresql', 'mongodb']:
            print(f"ERROR: Invalid DB_TYPE '{cls.DB_TYPE}'. Must be 'sqlite', 'postgresql', or 'mongodb'")
            return False
        
        return True
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database connection URL"""
        if cls.DB_TYPE == 'postgresql':
            return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
        elif cls.DB_TYPE == 'mongodb':
            return cls.MONGODB_URI
        else:
            return "sqlite:///jobbot.db"
