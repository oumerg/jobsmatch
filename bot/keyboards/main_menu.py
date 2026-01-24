"""
Main Menu Keyboards
Contains main menu keyboard layouts
"""

from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard():
    """Get main menu keyboard with reply buttons"""
    keyboard = [
        ["View Profile", "Update Preferences"],
        ["Search Jobs", "Manage Subscription"],
        ["Referral Program", "Help"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_jobs_keyboard():
    """Get jobs listing keyboard"""
    keyboard = [
        ["1️⃣ Apply for Job 1", "2️⃣ Apply for Job 2"],
        ["3️⃣ Apply for Job 3", "4️⃣ Apply for Job 4"],
        ["⬅️ Back to Main Menu"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_contact_keyboard():
    """Get contact sharing keyboard"""
    keyboard = [
        [KeyboardButton("Share Contact", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
