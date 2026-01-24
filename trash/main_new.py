"""
Ethiopian Job Bot - Main Entry Point
Streamlined main.py with modular structure
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from bot.config import Config
from bot.database import DatabaseManager
from bot.channel_manager import register_channel_handlers

# Import all command handlers
from bot.commands import *
# Import all message and callback handlers
from bot.handlers import *

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

async def main() -> None:
    """Start the bot."""
    
    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed")
        return
    
    # Create the Application
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("preferences", preferences_command))
    application.add_handler(CommandHandler("jobs", jobs_command))
    application.add_handler(CommandHandler("apply", apply_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("confirm_subscribe", confirm_subscribe_command))
    application.add_handler(CommandHandler("admin_payments", admin_payments_command))
    application.add_handler(CommandHandler("education", education_command))
    
    # Register message handlers
    application.add_handler(MessageHandler(filters.CONTACT, contact_received))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Register callback query handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Register channel handlers
    await register_channel_handlers(application)
    
    # Log bot startup
    logger.info("Starting Ethiopian Job Bot...")
    
    # Start the bot
    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
