"""
Subscription Handlers
Handles subscription-related functionality
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.subscription_manager import SubscriptionManager
from bot.payment_approval import PaymentApprovalSystem
from bot.config import Config

logger = logging.getLogger(__name__)

# Global subscription managers to maintain state
subscription_managers = {}

async def handle_subscription_response(update: Update, user, message_text: str) -> None:
    """Handle subscription payment method selection"""
    if user.id not in subscription_managers:
        return
    
    sub_manager = subscription_managers[user.id]
    
    try:
        # Process payment method selection
        result = await sub_manager.process_payment_method(user.id, message_text)
        
        if result['success']:
            await update.message.reply_text(result['message'])
        else:
            await update.message.reply_text(result['message'])
            # Show payment keyboard again on error
            keyboard = sub_manager.get_payment_keyboard()
            await update.message.reply_text("Please select a payment method:", reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error handling subscription response: {e}")
        await update.message.reply_text("❌ Error processing payment selection. Please try again.")

async def handle_payment_confirmation(update: Update, user) -> None:
    """Handle payment confirmation"""
    if user.id not in subscription_managers:
        await update.message.reply_text("❌ No active payment process. Use /subscribe to start.")
        return
    
    sub_manager = subscription_managers[user.id]
    
    try:
        result = await sub_manager.confirm_payment(user.id, "PAID")
        
        if result['success']:
            await update.message.reply_text(result['message'])
            # Clean up subscription manager
            del subscription_managers[user.id]
        else:
            await update.message.reply_text(result['message'])
            
    except Exception as e:
        logger.error(f"Error confirming payment: {e}")
        await update.message.reply_text(f"❌ Error confirming payment: {str(e)}")

async def handle_subscription_cancellation(update: Update, user) -> None:
    """Handle subscription process cancellation"""
    if user.id in subscription_managers:
        sub_manager = subscription_managers[user.id]
        message = await sub_manager.cancel_subscription_process(user.id)
        del subscription_managers[user.id]
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("❌ No active subscription process to cancel.")

async def handle_payment_approval(update: Update, admin_user, payment_id: int, action: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment approval/rejection"""
    # Check if user is admin
    if admin_user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to approve payments.")
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        # Initialize payment approval system
        approval_system = PaymentApprovalSystem(db, context.bot)
        
        if action == "approve":
            result = await approval_system.approve_payment(payment_id, admin_user.id)
            message = f"✅ Payment {payment_id} approved successfully!"
        elif action == "reject":
            result = await approval_system.reject_payment(payment_id, admin_user.id)
            message = f"❌ Payment {payment_id} rejected."
        else:
            message = "❌ Invalid action."
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error handling payment approval: {e}")
        await update.message.reply_text(f"❌ Error processing payment: {str(e)}")
    finally:
        await db.close()

async def handle_payment_verification(update: Update, admin_user, payment_id: int) -> None:
    """Handle payment verification (show details)"""
    # Check if user is admin
    if admin_user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't have permission to verify payments.")
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        # Get payment details
        query = """
            SELECT pp.*, u.first_name, u.last_name, u.username, u.phone_number
            FROM pending_payments pp
            LEFT JOIN users u ON pp.user_id = u.user_id
            WHERE pp.payment_id = $1
        """
        
        payment = await db.connection.fetchrow(query, payment_id)
        
        if not payment:
            await update.message.reply_text(f"❌ Payment {payment_id} not found.")
            return
        
        # Format payment details
        details_text = (
            f"📋 *Payment Details*\n\n"
            f"🆔 *Payment ID:* {payment['payment_id']}\n"
            f"👤 *User:* {payment['first_name']} {payment['last_name'] or ''}\n"
            f"📱 *Username:* @{payment['username'] or 'N/A'}\n"
            f"📞 *Phone:* {payment['phone_number'] or 'Not provided'}\n"
            f"💳 *Method:* {payment['payment_method']}\n"
            f"💰 *Amount:* {payment['amount']} Birr\n"
            f"📞 *Reference:* {payment['reference']}\n"
            f"📅 *Submitted:* {payment['submitted_at']}\n"
            f"📊 *Status:* {payment['status']}\n\n"
            f"🔧 *Actions:*"
        )
        
        # Create action buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{payment_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{payment_id}")
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_payments")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(details_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        await update.message.reply_text(f"❌ Error loading payment details: {str(e)}")
    finally:
        await db.close()
