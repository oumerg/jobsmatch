"""
Menu Utilities
Handles main menu and navigation utilities
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from bot.database import DatabaseManager
from bot.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)

async def show_main_menu(update: Update, user):
    """Show main menu with reply buttons"""
    reply_markup = get_main_menu_keyboard()
    
    message = (
        f"Welcome back {user.first_name}!\n\n"
        "*Main Menu:*\n\n"
        "Choose an option below:"
    )
    
    effective_message = update.effective_message
    if effective_message:
        await effective_message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    else:
