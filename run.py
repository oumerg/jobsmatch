import warnings
import asyncio
import logging
import sys
from bot.config import Config
from bot.database import DatabaseManager

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning, module='apscheduler')

async def initialize_database():
    """Initialize database connection and tables"""
    try:
        # Run migration script instead of full schema
        from migrate_database import migrate_database
        await migrate_database()
        print(f"✅ Database migration completed ({Config.DB_TYPE})")
        return True
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False

def setup_logging():
    """Setup logging configuration"""
    # Suppress all warnings
    warnings.filterwarnings("ignore")
    
    # Disable httpx logging to reduce console spam
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.ERROR)
    logging.getLogger('telegram.ext').setLevel(logging.WARNING)
    logging.getLogger('telethon').setLevel(logging.WARNING)
    
    # Configure logging with UTF-8 encoding for console output
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

# Global bot instance for scraper
bot_instance = None

async def run_bot():
    """Run the main Telegram bot"""
    try:
        from bot.main import main as bot_main
        
        # Start bot - this will set the bot instance globally
        await bot_main()
        
        print("✅ Bot started and instance set globally")
        
    except Exception as e:
        print(f"❌ Bot error: {e}")
        # Don't exit on timeout, let the system handle it gracefully
        if "TimedOut" not in str(e):
            print("⚠️ Bot timed out, but continuing...")

async def run_scraper():
    """Run the job scraper"""
    try:
        from bot.telethon_scraper import JobScraper
        from bot.shared_bot import get_bot_instance
        global bot_instance
        
        db = DatabaseManager()
        await db.connect()
        
        scraper = JobScraper(db)
        
        # Get bot instance from shared module
        bot_instance = get_bot_instance()
        
        # Pass bot instance to scraper for forwarding messages
        if bot_instance:
            scraper.bot_instance = bot_instance
            print("✅ Bot instance connected to scraper")
        else:
            print("⚠️ No bot instance available - scraper will run but won't send messages")
            scraper.bot_instance = None
        
        if await scraper.initialize():
            print("✅ Job scraper initialized")
            
            # Load channels from database
            channels = await db.get_active_channels()
            groups = await db.get_active_groups()
            
            if not channels and not groups:
                print("⚠️ No channels or groups found in database - scraper will not run")
                print("💡 Add channels/groups to the monitor_channels and monitor_groups tables")
                return
            
            # Add channels to scraper
            for channel in channels:
                # Use telegram_id if available, otherwise use username
                identifier = channel.get('telegram_id') or channel['channel_username']
                await scraper.add_source_channel(identifier)
                print(f"📺 Added channel: {channel['channel_username']} ({channel.get('channel_title', 'No title')}) -> ID: {channel.get('telegram_id', 'N/A')}")
            
            # Add groups to scraper
            for group in groups:
                # Use telegram_id if available, otherwise use username
                identifier = group.get('telegram_id') or group['group_username']
                await scraper.add_source_channel(identifier)
                print(f"👥 Added group: {group['group_username']} ({group.get('group_title', 'No title')}) -> ID: {group.get('telegram_id', 'N/A')}")
            
            print(f"🔍 Starting job monitoring... ({len(channels)} channels, {len(groups)} groups)")
            print("📤 Job scraper will broadcast jobs to all users")
            await scraper.start_monitoring()
        else:
            print("⚠️  Scraper not configured - bot will run without job scraping")
            
        await db.close()
        
    except Exception as e:
        print(f"⚠️  Scraper error: {e}")

async def main():
    """Main entry point - runs both bot and scraper"""
    print("🤖 Starting Ethiopian Job Bot System...")
    
    # Validate configuration
    if not Config.validate():
        print("❌ Configuration validation failed!")
        sys.exit(1)
    
    print("✅ Configuration validated")
    
    # Setup logging
    setup_logging()
    print(f"✅ Logging configured (Level: {Config.LOG_LEVEL})")
    
    # Initialize database
    try:
        db_initialized = await initialize_database()
        if not db_initialized:
            print("⚠️  Database initialization failed, but continuing...")
    except Exception as e:
        print(f"⚠️  Database initialization error: {e}")
    
    print("🚀 Starting services...")
    
    # Run both bot and scraper concurrently
    try:
        await asyncio.gather(
            run_bot(),
            run_scraper(),
            return_exceptions=True
        )
    except KeyboardInterrupt:
        print("\n👋 System stopped by user")
    except Exception as e:
        print(f"❌ System error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
