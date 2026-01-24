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
from bot.shared_bot import set_bot_instance

# Import all command handlers
from bot.commands.start_commands import start, contact_received, help_command
from bot.commands.user_commands import profile_command, jobs_command, apply_command, preferences_command, education_command
from bot.commands.subscription_commands import subscribe_command, status_command, cancel_subscription_command, subscription_management_command
from bot.commands.admin_commands import admin_menu_command, admin_add_channel_command, admin_add_group_command, admin_channels_command, admin_groups_command, admin_stats_command, admin_payments_command
from bot.commands.referral_commands import referral_command, earnings_command, withdraw_command, leaderboard_command
from bot.handlers.message_handlers import message_handler
from bot.handlers.callback_handlers import callback_query_handler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception while processing update", exc_info=context.error)

async def main():
    """Main bot function"""
    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed")
        return
    
    # Create application instance
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    
    # Set the global bot instance for scraper access
    set_bot_instance(application.bot)
    
    # Register all command handlers
    # Basic commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # User commands
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("jobs", jobs_command))
    application.add_handler(CommandHandler("apply", apply_command))
    application.add_handler(CommandHandler("preferences", preferences_command))
    application.add_handler(CommandHandler("education", education_command))
    
    # Subscription commands
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("cancel_subscription", cancel_subscription_command))
    application.add_handler(CommandHandler("subscription_management", subscription_management_command))
    
    # Admin commands
    application.add_handler(CommandHandler("admin", admin_menu_command))
    application.add_handler(CommandHandler("addchannel", admin_add_channel_command))
    application.add_handler(CommandHandler("addgroup", admin_add_group_command))
    application.add_handler(CommandHandler("admin_channels", admin_channels_command))
    application.add_handler(CommandHandler("admin_groups", admin_groups_command))
    application.add_handler(CommandHandler("admin_stats", admin_stats_command))
    application.add_handler(CommandHandler("admin_payments", admin_payments_command))
    
    # Referral system commands
    application.add_handler(CommandHandler("referral", referral_command))
    application.add_handler(CommandHandler("earnings", earnings_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    
    # Register message handlers
    application.add_handler(MessageHandler(filters.CONTACT, contact_received))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Register callback query handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    # Global error handler
    application.add_error_handler(error_handler)
    
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
        logger.info("Bot stopped by user")
        await application.stop()
    except Exception as e:
        logger.error(f"Bot error: {e}")
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
