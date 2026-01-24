"""
Admin Payment Approval System
For manual payment verification and approval
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager

logger = logging.getLogger(__name__)

class PaymentApprovalSystem:
    """Handles payment approval for administrators"""
    
    def __init__(self, db_manager: DatabaseManager, bot_instance=None):
        self.db = db_manager
        self.bot = bot_instance  # Telegram bot instance for sending messages
        self.pending_payments = {}  # Track pending payments
        
    async def submit_payment_for_approval(self, user_id: int, payment_method: str, amount: float, reference: str) -> Dict[str, Any]:
        """Submit payment for admin approval"""
        try:
            # Store pending payment
            pending_query = """
                INSERT INTO pending_payments (user_id, payment_method, amount, reference, status, submitted_at)
                VALUES ($1, $2, $3, $4, 'pending', CURRENT_TIMESTAMP)
                RETURNING payment_id
            """
            
            result = await self.db.connection.fetchrow(
                pending_query,
                user_id,
                payment_method,
                amount,
                reference
            )
            
            payment_id = result['payment_id']
            
            # Get user info for notification
            user_query = """
                SELECT first_name, last_name, username, phone_number 
                FROM users 
                WHERE user_id = $1
            """
            user_info = await self.db.connection.fetchrow(user_query, user_id)
            
            # Format user details
            full_name = f"{user_info['first_name'] or ''} {user_info['last_name'] or ''}".strip()
            if not full_name:
                full_name = 'Unknown'
            
            username_display = f"@{user_info['username']}" if user_info['username'] else 'No username'
            phone_display = user_info['phone_number'] if user_info['phone_number'] else 'No phone'
            
            # Notify admin
            await self.notify_admin_payment(
                payment_id=payment_id,
                user_id=user_id,
                user_name=full_name,
                username=username_display,
                phone_number=phone_display,
                payment_method=payment_method,
                amount=amount,
                reference=reference
            )
            
            return {
                'success': True,
                'message': f'Payment submitted for approval. Reference: {reference}',
                'payment_id': payment_id
            }
            
        except Exception as e:
            logger.error(f"Error submitting payment for approval: {e}")
            return {
                'success': False,
                'message': '❌ Error submitting payment. Please try again.'
            }
    
    async def notify_admin_payment(self, payment_id: int, user_id: int, user_name: str, 
                                username: str, phone_number: str, payment_method: str, 
                                amount: float, reference: str) -> None:
        """Send notification to admin for payment approval"""
        
        # Get admin user IDs from config
        from bot.config import Config
        admin_ids = Config.ADMIN_IDS
        
        message = (
            f"💰 *New Payment Pending Approval*\n\n"
            f"📋 *Payment ID:* {payment_id}\n"
            f"👤 *User Details:*\n"
            f"   📝 Name: {user_name}\n"
            f"   🆔 User ID: {user_id}\n"
            f"   📱 Username: {username}\n"
            f"   📞 Phone: {phone_number}\n\n"
            f"💳 *Payment Details:*\n"
            f"   💳 Method: {payment_method.title()}\n"
            f"   💰 Amount: {amount} Birr\n"
            f"   📝 Reference: {reference}\n"
            f"   📅 Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🔍 *Actions:*"
        )
        
        # Create approval keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_payment_{payment_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_payment_{payment_id}")
            ],
            [
                InlineKeyboardButton("🔍 Verify", callback_data=f"verify_payment_{payment_id}")
            ]
        ])
        
        # Send to all admins
        for admin_id in admin_ids:
            try:
                if self.bot:
                    await self.bot.send_message(
                        chat_id=admin_id, 
                        text=message, 
                        reply_markup=keyboard
                    )
                    logger.info(f"Payment notification sent to admin {admin_id}: {payment_id}")
                else:
                    logger.warning(f"Bot instance not available for admin notifications to {admin_id}")
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    async def approve_payment(self, payment_id: int, admin_id: int) -> Dict[str, Any]:
        """Approve payment and activate subscription"""
        try:
            # Get payment details
            payment_query = """
                SELECT user_id, payment_method, amount, reference
                FROM pending_payments
                WHERE payment_id = $1 AND status = 'pending'
            """
            
            payment = await self.db.connection.fetchrow(payment_query, payment_id)
            if not payment:
                return {'success': False, 'message': 'Payment not found or already processed'}
            
            # Update payment status
            await self.db.connection.execute(
                "UPDATE pending_payments SET status = 'approved', approved_by = $1, approved_at = CURRENT_TIMESTAMP WHERE payment_id = $2",
                admin_id, payment_id
            )
            
            # Activate subscription directly
            end_date = datetime.now() + timedelta(days=30)
            
            subscription_query = """
                INSERT INTO subscriptions (user_id, status, start_date, end_date, payment_method, transaction_ref, amount_birr)
                VALUES ($1, 'active', CURRENT_DATE, $2, $3, $4, $5)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    status = EXCLUDED.status,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    payment_method = EXCLUDED.payment_method,
                    transaction_ref = EXCLUDED.transaction_ref,
                    amount_birr = EXCLUDED.amount_birr,
                    renewal_count = subscriptions.renewal_count + 1
            """
            
            await self.db.connection.execute(
                subscription_query,
                payment['user_id'],
                end_date.date(),
                payment['payment_method'],
                payment['reference'],
                payment['amount']
            )
            
            # Notify user
            await self.notify_user_payment_approved(payment['user_id'], payment_id)
            
            logger.info(f"Payment {payment_id} approved by admin {admin_id}")
            
            return {
                'success': True,
                'message': f'Payment {payment_id} approved and subscription activated',
                'user_id': payment['user_id']
            }
            
        except Exception as e:
            logger.error(f"Error approving payment {payment_id}: {e}")
            return {'success': False, 'message': '❌ Error approving payment'}
    
    async def reject_payment(self, payment_id: int, admin_id: int, reason: str = "Payment not verified") -> Dict[str, Any]:
        """Reject payment"""
        try:
            # Update payment status
            await self.db.connection.execute(
                "UPDATE pending_payments SET status = 'rejected', approved_by = $1, approved_at = CURRENT_TIMESTAMP, notes = $2 WHERE payment_id = $3",
                admin_id, reason, payment_id
            )
            
            # Get user ID for notification
            payment = await self.db.connection.fetchrow(
                "SELECT user_id FROM pending_payments WHERE payment_id = $1", payment_id
            )
            
            if payment:
                await self.notify_user_payment_rejected(payment['user_id'], payment_id, reason)
            
            logger.info(f"Payment {payment_id} rejected by admin {admin_id}")
            
            return {
                'success': True,
                'message': f'Payment {payment_id} rejected',
                'user_id': payment['user_id'] if payment else None
            }
            
        except Exception as e:
            logger.error(f"Error rejecting payment {payment_id}: {e}")
            return {'success': False, 'message': '❌ Error rejecting payment'}
    
    async def notify_user_payment_approved(self, user_id: int, payment_id: int) -> None:
        """Notify user that payment was approved"""
        message = (
            f"✅ *Payment Approved!*\n\n"
            f"🎉 Your payment has been verified and your premium subscription is now active!\n\n"
            f"📋 *Payment ID:* {payment_id}\n"
            f"📅 *Activated:* {datetime.now().strftime('%B %d, %Y')}\n"
            f"⏰ *Duration:* 30 days\n\n"
            f"🌟 *Premium Features Unlocked:*\n"
            f"✅ Unlimited job matches\n"
            f"✅ Priority applications\n"
            f"✅ Direct employer contact\n"
            f"✅ Daily job alerts\n\n"
            f"Use /status to check your subscription details."
        )
        
        # Send message to user
        if self.bot:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
                logger.info(f"Payment approval notification sent to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send approval notification to user {user_id}: {e}")
        else:
            logger.warning(f"Bot instance not available for user notification to {user_id}")
    
    async def notify_user_payment_rejected(self, user_id: int, payment_id: int, reason: str) -> None:
        """Notify user that payment was rejected"""
        message = (
            f"❌ *Payment Not Approved*\n\n"
            f"Your payment could not be verified.\n\n"
            f"📋 *Payment ID:* {payment_id}\n"
            f"📝 *Reason:* {reason}\n\n"
            f"Please check your payment details and try again, or contact support for assistance.\n\n"
            f"💬 *Support:* @JobsMatchSupport"
        )
        
        # Send message to user
        if self.bot:
            try:
                await self.bot.send_message(chat_id=user_id, text=message)
                logger.info(f"Payment rejection notification sent to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send rejection notification to user {user_id}: {e}")
        else:
            logger.warning(f"Bot instance not available for user notification to {user_id}")
    
    async def get_pending_payments(self) -> List[Dict[str, Any]]:
        """Get list of pending payments for admin"""
        try:
            query = """
                SELECT pp.payment_id, pp.user_id, pp.payment_method, pp.amount, pp.reference, 
                       pp.submitted_at, u.first_name, u.username
                FROM pending_payments pp
                LEFT JOIN users u ON pp.user_id = u.user_id
                WHERE pp.status = 'pending'
                ORDER BY pp.submitted_at DESC
            """
            
            results = await self.db.connection.fetch(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting pending payments: {e}")
            return []
    
    async def create_pending_payments_table(self) -> None:
        """Create pending payments table if not exists"""
        try:
            create_table_query = """
                CREATE TABLE IF NOT EXISTS pending_payments (
                    payment_id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(user_id),
                    payment_method VARCHAR(20) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    reference VARCHAR(100) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMP,
                    approved_by BIGINT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            
            await self.db.connection.execute(create_table_query)
            logger.info("Pending payments table created/verified")
            
        except Exception as e:
            logger.error(f"Error creating pending payments table: {e}")

# Usage example
if __name__ == "__main__":
    async def test_payment_approval():
        db = DatabaseManager()
        await db.connect()
        
        approval_system = PaymentApprovalSystem(db)
        await approval_system.create_pending_payments_table()
        
        # Test submitting payment
        result = await approval_system.submit_payment_for_approval(
            user_id=12345,
            payment_method='telebirr',
            amount=50.00,
            reference='SUB1234520250121'
        )
        print(f"Payment submission: {result}")
        
        await db.close()
    
    # asyncio.run(test_payment_approval())
