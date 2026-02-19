"""
Menu Utilities
Handles main menu and navigation utilities
"""

import logging
from telegram import Update
from telegram.constants import ParseMode
from bot.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def show_main_menu(update: Update, user) -> None:
    """
    Show the main menu with reply buttons.
    
    Args:
        update (Update): Telegram update object
        user: Telegram user object
    """

    reply_markup = get_main_menu_keyboard()

    message = (
        f"Welcome back {user.first_name}!\n\n"
        "*Main Menu:*\n\n"
        "Choose an option below:"
    )

    effective_message = update.effective_message

    if effective_message:
        await effective_message.reply_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        logger.warning(
            "show_main_menu() called but no effective_message found in update."
        )
