"""
Shared Bot Instance
Provides a global bot instance that can be accessed by both the main bot and scraper
"""

import logging

logger = logging.getLogger(__name__)

# Global bot instance
bot_instance = None

def get_bot_instance():
    """Get the global bot instance"""
    return bot_instance

def set_bot_instance(instance):
    """Set the global bot instance"""
    global bot_instance
    bot_instance = instance
    logger.info("✅ Bot instance set globally for scraper access")
