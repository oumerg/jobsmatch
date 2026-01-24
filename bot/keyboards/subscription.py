"""
Subscription Keyboards
Contains subscription-related keyboard layouts
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

def get_subscription_keyboard(status_info):
    """Get subscription management keyboard based on status"""
    if status_info['status'] == 'trial':
        # User has trial - show upgrade options
        keyboard = [
            ["Check Status", "Upgrade to Premium"],
            ["Back to Main Menu"]
        ]
    elif status_info['is_active'] and status_info['status'] == 'active':
        # User has active paid subscription - show management options
        keyboard = [
            ["Check Status", "Back to Main Menu"],
            ["Cancel Subscription"]
        ]
    else:
        # User has no subscription or expired - show subscribe options
        keyboard = [
            ["Check Status", "Subscribe Now"],
            ["Back to Main Menu"]
        ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_payment_keyboard():
    """Get payment method selection keyboard"""
    keyboard = [
        ["Telebirr", "CBE Birr"],
        ["Hello Cash", "Manual Payment"],
        ["Cancel"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_payment_approval_keyboard(payment_id):
    """Get payment approval keyboard for admins"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{payment_id}")
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_payments")]
    ]
    return InlineKeyboardMarkup(keyboard)
