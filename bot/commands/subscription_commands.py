"""
Subscription Commands
Handles all subscription-related commands
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription process"""
    user = update.effective_user
    effective_message = update.effective_message
    
    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db, context.bot)
        
        # Check current subscription status
        status_info = await sub_manager.check_subscription_status(user.id)
        
        if status_info['is_active']:
            if effective_message:
                await effective_message.reply_text(
                    f"✅ You already have an active subscription!\n\n"
                    f"📊 Status: {status_info['message']}\n"
                    f"📅 Expires: {status_info.get('subscription', {}).get('end_date', 'Unknown')}\n\n"
                    f"Use /status to check your subscription details."
                )
            return
        
        # Start subscription process
        response = await sub_manager.start_subscription_process(user.id)
        
        # Store subscription manager for this user
        from bot.handlers.subscription_handlers import subscription_managers
        subscription_managers[user.id] = sub_manager
        
        # Get payment keyboard
        keyboard = sub_manager.get_payment_keyboard()
        if effective_message:
            await effective_message.reply_text(response, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in subscribe command: {e}")
        if effective_message:
            await effective_message.reply_text("❌ Error starting subscription. Please try again.")
    finally:
        await db.close()

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription status check"""
    user = update.effective_user
    effective_message = update.effective_message

    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db, context.bot)

        # Get subscription status
        status_info = await sub_manager.check_subscription_status(user.id)
        status_message = sub_manager.format_subscription_status(status_info)

        # Create appropriate inline keyboard based on status (same as subscription_management_command)
        if status_info['status'] == 'trial':
            # User has trial - show upgrade options
            keyboard = [
                [
                    InlineKeyboardButton("Check Status", callback_data="sub_status"),
                    InlineKeyboardButton("Upgrade to Premium", callback_data="sub_upgrade")
                ],
                [
                    InlineKeyboardButton("Back", callback_data="back_to_previous"),
                    InlineKeyboardButton("Main Menu", callback_data="back_to_main_menu")
                ]
            ]

        elif status_info['is_active'] and status_info['status'] == 'active':
            # User has active paid subscription - show management options
            keyboard = [
                [
                    InlineKeyboardButton("Check Status", callback_data="sub_status"),
                    InlineKeyboardButton("Back", callback_data="back_to_previous")
                ],
                [
                    InlineKeyboardButton("Cancel Subscription", callback_data="sub_cancel"),
                    InlineKeyboardButton("Main Menu", callback_data="back_to_main_menu")
                ]
            ]

        else:
            # User has no subscription or expired - show subscribe options
            keyboard = [
                [
                    InlineKeyboardButton("Check Status", callback_data="sub_status"),
                    InlineKeyboardButton("Subscribe Now", callback_data="sub_subscribe")
                ],
                [
                    InlineKeyboardButton("Back", callback_data="back_to_previous"),
                    InlineKeyboardButton("Main Menu", callback_data="back_to_main_menu")
                ]
            ]

        # Handle both callback queries and regular messages
        if update.callback_query:
            await update.callback_query.edit_message_text(status_message, reply_markup=InlineKeyboardMarkup(keyboard))
        elif effective_message:
            await effective_message.reply_text(status_message, reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logger.error(f"Error checking status: {e}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main_menu")]
        ])
        # Handle both callback queries and regular messages
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Error checking subscription status. Please try again.", reply_markup=keyboard)
        elif effective_message:
            await effective_message.reply_text("❌ Error checking subscription status. Please try again.", reply_markup=keyboard)
    finally:
        await db.close()

async def subscription_management_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription management with proper flow"""
    user = update.effective_user
    effective_message = update.effective_message
    
    # Check current subscription status first
    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db, context.bot)
        
        # Get current subscription status
        status_info = await sub_manager.check_subscription_status(user.id)
        status_message = sub_manager.format_subscription_status(status_info)
        
        # Create appropriate inline keyboard based on status
        if status_info['status'] == 'trial':
            # User has trial - show upgrade options
            keyboard = [
                [
                    InlineKeyboardButton("📊 Check Status", callback_data="sub_status"),
                    InlineKeyboardButton("💳 Upgrade to Premium", callback_data="sub_upgrade")
                ],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu")
                ]
            ]
            message = f"{status_message}\n\n💰 *Subscription Management:*\n\nChoose an option:"
            
        elif status_info['is_active'] and status_info['status'] == 'active':
            # User has active paid subscription - show management options
            keyboard = [
                [
                    InlineKeyboardButton("📊 Check Status", callback_data="sub_status"),
                    InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous")
                ],
                [
                    InlineKeyboardButton("❌ Cancel Subscription", callback_data="sub_cancel"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu")
                ]
            ]
            message = f"{status_message}\n\n💰 *Subscription Management:*\n\nChoose an option:"
            
        else:
            # User has no subscription or expired - show subscribe options
            keyboard = [
                [
                    InlineKeyboardButton("📊 Check Status", callback_data="sub_status"),
                    InlineKeyboardButton("💳 Subscribe Now", callback_data="sub_subscribe")
                ],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu")
                ]
            ]
            message = f"{status_message}\n\n💰 *Subscription Management:*\n\nChoose an option:"
        
        # Handle both callback queries and regular messages
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        elif effective_message:
            await effective_message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error in subscription management: {e}")
        # Handle both callback queries and regular messages
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Error loading subscription options. Please try again.")
        elif effective_message:
            await effective_message.reply_text("❌ Error loading subscription options. Please try again.")
    finally:
        await db.close()

async def cancel_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription cancellation command"""
    user = update.effective_user
    effective_message = update.effective_message
    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db, context.bot)
        
        # Check current subscription status
        status_info = await sub_manager.check_subscription_status(user.id)
        
        if not status_info['is_active'] and status_info['status'] == 'no_subscription':
            if effective_message:
                await effective_message.reply_text("❌ You don't have an active subscription to cancel.")
            return
        
        # Cancel the subscription
        result = await sub_manager.cancel_subscription(user.id)
        
        if result['success']:
            if effective_message:
                await effective_message.reply_text(
                    f"✅ {result['message']}\n\n"
                    "💔 Your subscription has been cancelled.\n"
                    "You can subscribe again anytime using 💰 Manage Subscription."
                )
        else:
            if effective_message:
                await effective_message.reply_text(f"❌ {result['message']}")
            
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        if effective_message:
            await effective_message.reply_text("❌ Error cancelling subscription. Please try again.")
    finally:
        await db.close()

async def confirm_subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription confirmation"""
    user = update.effective_user
    effective_message = update.effective_message
    
    if effective_message:
        await effective_message.reply_text(
            "📝 *Subscription Confirmation*\n\n"
            "This command is used during the payment process.\n\n"
            "If you haven't started the payment process, use /subscribe first."
        )
