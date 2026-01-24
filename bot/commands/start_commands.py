"""
Start and Registration Commands
Handles /start, contact, and initial registration flow
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.registration_flow import RegistrationFlow

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with a contact button when the command /start is issued."""
    user = update.effective_user
    
    # Extract referral code from start command if present
    referral_code = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        logger.info(f"User {user.id} started with referral code: {referral_code}")
    
    # Check if user already has contact info
    db = DatabaseManager()
    user_data = None
    try:
        await db.connect()
        user_data = await db.get_user(user.id)
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        await db.close()
    
    # Check if user already has phone number and preferences
    if user_data and user_data.get('phone_number'):
        # Check if user has completed registration
        reg_flow = RegistrationFlow(DatabaseManager())
        await reg_flow.db.connect()
        
        try:
            trial_status = await reg_flow.check_trial_status(user.id)
            
            if trial_status['status'] != 'no_subscription':
                # User already registered, show main menu
                from bot.utils.menu_utils import show_main_menu
                await show_main_menu(update, user)
            else:
                # User has contact but no subscription, start registration
                user_data_to_save = {
                    'user_id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name or '',
                    'username': user.username or ''
                }
                
                # Start registration flow
                response = await reg_flow.start_registration(user.id, user_data_to_save)
                keyboard = reg_flow.get_keyboard_for_step(user.id)
                
                if keyboard:
                    # Add back button to inline keyboard - convert tuple to list first
                    if hasattr(keyboard, 'inline_keyboard'):
                        # Convert tuple to list if needed
                        keyboard_rows = list(keyboard.inline_keyboard) if isinstance(keyboard.inline_keyboard, tuple) else keyboard.inline_keyboard
                        keyboard_rows.append([
                            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main_menu")
                        ])
                        keyboard = InlineKeyboardMarkup(keyboard_rows)
                    await update.message.reply_text(response, reply_markup=keyboard)
                else:
                    await update.message.reply_text(response)
                    
        except Exception as e:
            logger.error(f"Error checking registration status: {e}")
            await update.message.reply_text("❌ Error checking your status. Please try again.")
        finally:
            await reg_flow.db.close()
    else:
        # New user, request contact
        welcome_text = (
            f"👋 Welcome {user.first_name}!\n\n"
            "🤖 *Ethiopian Job Bot*\n\n"
            "To get started, I need your phone number for job applications.\n\n"
            "📱 Please share your contact:"
        )
        
        # Add referral bonus message if referral code is present
        if referral_code and referral_code.startswith('REF'):
            welcome_text += f"\n\n🎁 *Special Bonus!*\nYou've been invited with a referral code!\nYou'll get access to premium features after registration."
        
        contact_keyboard = [
            [KeyboardButton("📱 Share Contact", request_contact=True)]
        ]
        reply_markup = ReplyKeyboardMarkup(contact_keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
        # Store referral code in context for later processing after registration
        if referral_code:
            context.user_data['referral_code'] = referral_code

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when a user shares their contact."""
    contact = update.message.contact
    user = update.effective_user
    
    # Save user data with phone number
    db = DatabaseManager()
    try:
        await db.connect()
        
        user_data = {
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name or '',
            'username': user.username or '',
            'phone_number': contact.phone_number,
            'telegram_id': user.id
        }
        
        # Save user to database
        await db.save_user(user_data)
        
        # Process referral code if present
        referral_code = context.user_data.get('referral_code')
        if referral_code and referral_code.startswith('REF'):
            from bot.referral_system import ReferralManager
            referral_manager = ReferralManager(db)
            success, referrer_id = await referral_manager.process_referral(referral_code, user.id)
            
            if success:
                logger.info(f"Successfully processed referral from user {referrer_id} for new user {user.id}")
                # Clear referral code from context
                context.user_data.pop('referral_code', None)
        
        # Start registration flow
        reg_flow = RegistrationFlow(DatabaseManager())
        await reg_flow.db.connect()
        
        try:
            response = await reg_flow.start_registration(user.id, user_data)
            keyboard = reg_flow.get_keyboard_for_step(user.id)
            
            if keyboard:
                # For registration, we use ReplyKeyboardMarkup, so convert to list format
                reply_keyboard = [["⬅️ Back to Main Menu"]]
                reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
                await update.message.reply_text(response, reply_markup=reply_markup)
            else:
                await update.message.reply_text(response)
                
        finally:
            await reg_flow.db.close()
            
    except Exception as e:
        logger.error(f"Error saving contact: {e}")
        await update.message.reply_text("❌ Error saving your contact. Please try again.")
    finally:
        await db.close()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user = update.effective_user
    
    # Check if user is admin
    from bot.commands.admin_commands import is_admin
    is_user_admin = is_admin(user.id)
    
    help_text = (
        "🤖 *Ethiopian Job Bot Commands:*\n\n"
        "📋 *Main Commands:*\n"
        "• /start - Start bot\n"
        "• /help - Show this help message\n"
        "• /profile - View your profile\n"
        "• /preferences - Update job preferences\n"
        "• /jobs - View available jobs\n"
        "• /apply - Apply for jobs\n\n"
        "💰 *Subscription Commands:*\n"
        "• /subscribe - Subscribe to premium features\n"
        "• /status - Check subscription status\n"
        "• /cancel - Cancel subscription\n\n"
        "🎁 *Referral Commands:*\n"
        "• /referral - Get your referral link and stats\n"
        "• /earnings - View your earnings history\n"
        "• /withdraw <amount> - Withdraw your earnings\n"
        "• /leaderboard - View top referrers\n\n"
    )
    
    # Add admin commands section only for admins
    if is_user_admin:
        help_text += (
            "🛠️ *Admin Commands:*\n"
            "• /admin - Admin control panel\n"
            "• /admin_channels - View monitored channels\n"
            "• /admin_groups - View monitored groups\n"
            "• /addchannel @username - Add new channel\n"
            "• /addgroup @username - Add new group\n"
            "• /admin_stats - View bot statistics\n"
            "• /admin_payments - View pending payments\n\n"
        )
    
    help_text += (
        "📞 *Need Help?*\n"
        "Contact: @JobsMatchSupport\n\n"
        "🇪🇹 *Find your dream job in Ethiopia!*"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')
