"""
Subscription Management System
Handles trial subscriptions, payments, and premium features
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.payment_approval import PaymentApprovalSystem

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Manages user subscriptions and payments"""
    
    def __init__(self, db_manager: DatabaseManager, bot_instance=None):
        self.db = db_manager
        self.bot = bot_instance  # Telegram bot instance for sending admin notifications
        self.subscription_states = {}  # Track user subscription processes
        
        # Payment methods
        self.payment_methods = {
            'telebirr': {
                'display': 'Telebirr',
                'instructions': 'Dial *847# and follow the prompts',
                'number': '847'
            },
            'cbebirr': {
                'display': 'CBE Birr',
                'instructions': 'Use CBE Birr mobile app',
                'number': None
            },
            'hello_cash': {
                'display': 'Hello Cash',
                'instructions': 'Use Hello Cash app',
                'number': None
            },
            'manual': {
                'display': 'Manual Payment',
                'instructions': 'Contact support for manual payment',
                'number': None
            }
        }
    
    async def create_trial_subscription(self, user_id: int) -> Dict[str, Any]:
        """Create 1-day free trial subscription"""
        trial_end = datetime.now() + timedelta(days=1)
        
        # Ensure database connection is open
        if not self.db.connection or self.db.connection.is_closed():
            try:
                await self.db.connect()
                logger.info("Database connection reopened for trial subscription")
            except Exception as e:
                logger.error(f"Failed to connect to database for trial: {e}")
                return {
                    'success': False,
                    'message': '❌ Database connection error. Please try again.',
                    'subscription': None
                }
        
        try:
            # Check if user already has active subscription
            existing = await self.get_active_subscription(user_id)
            if existing and existing['status'] == 'active':
                return {
                    'success': False,
                    'message': 'You already have an active subscription.',
                    'subscription': existing
                }
            
            # Create trial subscription
            subscription_query = """
                INSERT INTO subscriptions (user_id, status, start_date, end_date, payment_method, transaction_ref, amount_birr)
                VALUES ($1, 'trial', CURRENT_DATE, $2, 'trial', 'free_trial', 0.00)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    status = EXCLUDED.status,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    payment_method = EXCLUDED.payment_method,
                    transaction_ref = EXCLUDED.transaction_ref,
                    amount_birr = EXCLUDED.amount_birr,
                    created_at = CURRENT_TIMESTAMP
                RETURNING subscription_id, status, start_date, end_date, payment_method
            """
            
            result = await self.db.connection.fetchrow(
                subscription_query, 
                user_id, 
                trial_end.date()
            )
            
            subscription = dict(result)
            
            logger.info(f"Created trial subscription for user {user_id}")
            
            return {
                'success': True,
                'message': f'1-day free trial activated! Ends on {trial_end.strftime("%B %d, %Y")}',
                'subscription': subscription
            }
            
        except Exception as e:
            logger.error(f"Error creating trial subscription for user {user_id}: {e}")
            return {
                'success': False,
                'message': 'Error creating trial subscription. Please try again.',
                'subscription': None
            }
    
    async def get_active_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's current active subscription"""
        try:
            query = """
                SELECT subscription_id, status, start_date, end_date, payment_method, 
                       transaction_ref, amount_birr, renewal_count, created_at
                FROM subscriptions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            result = await self.db.connection.fetchrow(query, user_id)
            
            if result:
                subscription = dict(result)
                
                # Check if subscription is expired
                if subscription['end_date'] < datetime.now().date():
                    subscription['status'] = 'expired'
                
                return subscription
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting subscription for user {user_id}: {e}")
            return None
    
    async def check_subscription_status(self, user_id: int) -> Dict[str, Any]:
        """Check detailed subscription status"""
        subscription = await self.get_active_subscription(user_id)
        
        if not subscription:
            return {
                'status': 'no_subscription',
                'days_remaining': 0,
                'is_active': False,
                'message': 'No active subscription'
            }
        
        days_remaining = (subscription['end_date'] - datetime.now().date()).days
        is_active = subscription['status'] == 'active' or (subscription['status'] == 'trial' and days_remaining > 0)
        
        status_messages = {
            'trial': f'Trial - {days_remaining} days remaining',
            'active': f'Active - {days_remaining} days remaining',
            'expired': 'Expired',
            'canceled': 'Canceled'
        }
        
        return {
            'status': subscription['status'],
            'days_remaining': max(0, days_remaining),
            'is_active': is_active,
            'message': status_messages.get(subscription['status'], 'Unknown'),
            'subscription': subscription
        }
    
    async def start_subscription_process(self, user_id: int) -> str:
        """Start subscription upgrade process"""
        subscription = await self.get_active_subscription(user_id)
        
        # Store process state
        self.subscription_states[user_id] = {
            'step': 'payment_method',
            'subscription': subscription,
            'start_time': datetime.now()
        }
        
        message = (
            "*Premium Subscription - 50 Birr/Month*\n\n"
            "*Premium Benefits:*\n"
            "Unlimited job matches\n"
            "Priority application processing\n"
            "Direct employer contact\n"
            "Resume highlighting\n"
            "Daily job alerts\n\n"
            "*Select Payment Method:*\n"
        )
        
        return message
    
    def get_payment_keyboard(self) -> InlineKeyboardMarkup:
        """Get payment method selection keyboard as inline buttons"""
        keyboard = []
        
        for method_key, method_info in self.payment_methods.items():
            keyboard.append([InlineKeyboardButton(
                method_info['display'], 
                callback_data=f"payment_method_{method_key}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="payment_cancel")])
        return InlineKeyboardMarkup(keyboard)
    
    async def process_payment_method(self, user_id: int, payment_choice: str) -> Dict[str, Any]:
        """Process payment method selection"""
        if user_id not in self.subscription_states:
            return {'success': False, 'message': 'Payment process not started'}
        
        # Find payment method
        selected_method = None
        for method_key, method_info in self.payment_methods.items():
            if method_info['display'] == payment_choice:
                selected_method = method_key
                break
        
        if not selected_method:
            return {'success': False, 'message': 'Invalid payment method'}
        
        method_info = self.payment_methods[selected_method]
        
        # Update state
        self.subscription_states[user_id]['payment_method'] = selected_method
        self.subscription_states[user_id]['step'] = 'payment_confirmation'
        
        # Generate payment instructions
        instructions = (
            f"*Payment Instructions*\n\n"
            f"*Amount:* 50 Birr\n"
            f"*Method:* {method_info['display']}\n\n"
            f"*Instructions:*\n"
            f"{method_info['instructions']}\n\n"
            f"*After payment:* Send 'PAID' to confirm\n"
            f"*Reference:* SUB{user_id}{datetime.now().strftime('%Y%m%d')}\n\n"
            f"*Cancel:* Type 'cancel'"
        )
        
        return {
            'success': True,
            'message': instructions,
            'payment_method': selected_method
        }
    
    async def confirm_payment(self, user_id: int, confirmation: str) -> Dict[str, Any]:
        """Confirm payment and submit for admin approval"""
        if user_id not in self.subscription_states:
            logger.error(f"No payment process found for user {user_id}")
            return {'success': False, 'message': 'No payment process found'}
        
        state = self.subscription_states[user_id]
        
        if confirmation.lower() != 'paid':
            return {'success': False, 'message': 'Please type "PAID" to confirm payment'}
        
        # Ensure database connection is open
        if not self.db.connection or self.db.connection.is_closed():
            try:
                await self.db.connect()
                logger.info("Database connection reopened for payment processing")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                return {'success': False, 'message': '❌ Database connection error. Please try again.'}
        
        try:
            payment_method = state['payment_method']
            amount = 50.00  # Fixed subscription price
            reference = f"SUB{user_id}{datetime.now().strftime('%Y%m%d%H%M')}"
            
            logger.info(f"Processing payment confirmation for user {user_id}, method: {payment_method}, reference: {reference}")
            
            # Store pending payment directly in database
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
            logger.info(f"Payment submitted successfully, payment_id: {payment_id}")
            
            # Send admin notification
            if self.bot:
                try:
                    # Get user info from database
                    user_query = "SELECT first_name, last_name, username, phone_number FROM users WHERE user_id = $1"
                    user_info = await self.db.connection.fetchrow(user_query, user_id)
                    
                    # Format user details
                    full_name = f"{user_info['first_name'] or ''} {user_info['last_name'] or ''}".strip()
                    if not full_name:
                        full_name = 'Unknown'
                    
                    username_display = f"@{user_info['username']}" if user_info['username'] else 'No username'
                    phone_display = user_info['phone_number'] if user_info['phone_number'] else 'No phone'
                    
                    approval_system = PaymentApprovalSystem(self.db, self.bot)
                    await approval_system.notify_admin_payment(
                        payment_id=payment_id,
                        user_id=user_id,
                        user_name=full_name,
                        username=username_display,
                        phone_number=phone_display,
                        payment_method=payment_method,
                        amount=amount,
                        reference=reference
                    )
                    logger.info(f"Admin notification sent for payment {payment_id}")
                except Exception as e:
                    logger.error(f"Failed to send admin notification: {e}")
            else:
                logger.warning("Bot instance not available for admin notifications")
            
            # Clean up state
            del self.subscription_states[user_id]
            
            return {
                'success': True,
                'message': f'Payment submitted for approval!\n\nReference: {reference}\n\nYour payment will be reviewed and you\'ll be notified once approved.\n\nNeed help? Contact @support',
                'payment_id': payment_id
            }
            
        except Exception as e:
            logger.error(f"Error confirming payment for user {user_id}: {e}")
            logger.error(f"Payment state: {state}")
            logger.error(f"Database connection status: {self.db.connection}")
            return {'success': False, 'message': f'Error processing payment: {str(e)}'}
    
    async def cancel_subscription_process(self, user_id: int) -> str:
        """Cancel subscription process"""
        if user_id in self.subscription_states:
            del self.subscription_states[user_id]
        
        return "Payment process cancelled. Type /subscribe to start again."
    
    def format_subscription_status(self, status_info: Dict[str, Any]) -> str:
        """Format subscription status for display"""
        if status_info['status'] == 'no_subscription':
            return (
                "*Subscription Status: Inactive*\n\n"
                "Start with 1-day free trial!\n"
                "Premium: 50 Birr/month\n\n"
                "Type /subscribe to get started"
            )
        
        subscription = status_info.get('subscription', {})
        
        status_text = (
            f"*Subscription Status*\n\n"
            f"Status: {status_info['message']}\n"
            f"Started: {subscription.get('start_date', 'Unknown')}\n"
            f"Expires: {subscription.get('end_date', 'Unknown')}\n"
            f"Method: {subscription.get('payment_method', 'Unknown').title()}\n"
            f"Amount: {subscription.get('amount_birr', 0)} Birr\n"
        )
        
        if subscription.get('renewal_count', 0) > 0:
            status_text += f"Renewals: {subscription['renewal_count']}\n"
        
        if not status_info['is_active']:
            status_text += f"\n\n*Renew subscription:* /subscribe"
        
        return status_text
    
    async def cancel_subscription(self, user_id: int) -> Dict[str, Any]:
        """Cancel user's subscription"""
        try:
            # Ensure database connection is open
            if not self.db.connection or self.db.connection.is_closed():
                await self.db.connect()
            
            # Update subscription status to canceled
            query = """
                UPDATE subscriptions 
                SET status = 'canceled', end_date = CURRENT_DATE
                WHERE user_id = $1 AND status IN ('active', 'trial')
            """
            
            await self.db.connection.execute(query, user_id)
            
            logger.info(f"Subscription canceled for user {user_id}")
            
            return {
                'success': True,
                'message': 'Subscription canceled successfully'
            }
            
        except Exception as e:
            logger.error(f"Error canceling subscription for user {user_id}: {e}")
            return {
                'success': False,
                'message': 'Error canceling subscription. Please try again.'
            }

# Usage examples
if __name__ == "__main__":
    async def test_subscription():
        db = DatabaseManager()
        await db.connect()
        
        manager = SubscriptionManager(db)
        
        # Test trial creation
        result = await manager.create_trial_subscription(12345)
        print(f"Trial creation: {result}")
        
        # Test status check
        status = await manager.check_subscription_status(12345)
        print(f"Subscription status: {status}")
        
        await db.close()
    
    # asyncio.run(test_subscription())
