"""
Preference Utilities
Handles preference-related utilities and helpers
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.user_preferences import PreferenceCollector

logger = logging.getLogger(__name__)

def get_preference_keyboard(collector, user_id):
    """Get appropriate keyboard for current preference step"""
    state = collector.user_states.get(user_id, {})
    step = state.get('step', 'categories')
    
    if step == 'categories':
        keyboard = collector.manager.get_categories_keyboard()
    elif step == 'locations':
        keyboard = collector.manager.get_locations_keyboard()
    elif step == 'job_types':
        keyboard = collector.manager.get_job_types_keyboard()
    elif step == 'salary':
        keyboard = collector.manager.get_salary_keyboard()
    elif step == 'education':
        keyboard = collector.manager.get_education_keyboard()
    elif step == 'experience':
        keyboard = collector.manager.get_experience_keyboard()
    else:
        return None, None
    
    # Convert InlineKeyboardMarkup to list for ReplyKeyboardMarkup
    if hasattr(keyboard, 'inline_keyboard'):
        keyboard_list = []
        for row in keyboard.inline_keyboard:
            keyboard_list.append([button.text for button in row])
        return keyboard_list, keyboard  # Return both list and original
    elif isinstance(keyboard, list):
        return keyboard, None
    else:
        return None, None

async def start_education_preference(update: Update, user, db):
    """Start education preference collection"""
    from bot.user_preferences import PreferenceCollector
    
    collector = PreferenceCollector(db)
    response = collector.start_preference_collection(user.id)
    
    # Set to education step directly
    if user.id in collector.user_states:
        collector.user_states[user.id]['step'] = 'education'
    
    keyboard = collector.manager.get_education_keyboard()
    if keyboard:
        keyboard_list = []
        for row in keyboard.inline_keyboard:
            keyboard_list.append([button.text for button in row])
        keyboard_list.append(["Back to Main Menu"])
        reply_markup = ReplyKeyboardMarkup(keyboard_list, resize_keyboard=True)
        await update.message.reply_text("*Select Your Education Level:*\n\nChoose your highest educational qualification:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(response)
