import logging
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from bot.config import Config
from bot.database import DatabaseManager
from bot.user_preferences import PreferenceCollector
from bot.subscription_manager import SubscriptionManager
from bot.payment_approval import PaymentApprovalSystem
from bot.job_models import Job, JobSeeker, EducationLevel, JobType
from bot.channel_manager import register_channel_handlers
from bot.registration_flow import RegistrationFlow

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with a contact button when the command /start is issued."""
    user = update.effective_user
    
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
                await show_main_menu(update, user)
            else:
                # User has contact but no subscription, start registration
                user_data_to_save = {
                    'user_id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'phone_number': user_data.get('phone_number')
                }
                
                reg_flow = RegistrationFlow(DatabaseManager())
                await reg_flow.db.connect()
                
                message = await reg_flow.start_registration(user.id, user_data_to_save)
                keyboard = reg_flow.get_keyboard_for_step(user.id)
                
                if keyboard:
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(message, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(message)
                
                await reg_flow.db.close()
                
        except Exception as e:
            logger.error(f"Error checking registration status: {e}")
            await update.message.reply_text("❌ Error checking your account. Please try again.")
        finally:
            await reg_flow.db.close()
            
    else:
        # User needs to share contact
        contact_button = KeyboardButton(
            text="📞 Share Contact",
            request_contact=True
        )
        
        keyboard = [[contact_button]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        welcome_message = (
            f"👋 Welcome {user.first_name}!\n\n"
            "🤖 This is Ethiopian Job Bot - Your AI-powered job matching assistant!\n\n"
            "🎁 *Get 7 Days FREE Trial*\n"
            "💰 After trial: Only 50 Birr/month\n\n"
            "📱 To get started, please share your contact information:"
        )
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup
        )

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when a user shares their contact."""
    contact = update.message.contact
    user = update.effective_user
    
    logger.info(f"Contact received from {contact.first_name} {contact.last_name}: {contact.phone_number}")
    
    # Save user data to database
    user_data = {
        'user_id': contact.user_id,
        'first_name': contact.first_name,
        'last_name': contact.last_name,
        'username': user.username,
        'phone_number': contact.phone_number
    }
    
    db = DatabaseManager()
    try:
        await db.connect()
        success = await db.save_user(user_data)
        if success:
            logger.info(f"User {contact.user_id} saved to database")
        else:
            logger.error(f"Failed to save user {contact.user_id} to database")
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        await db.close()
    
    # Start registration flow
    reg_flow = RegistrationFlow(DatabaseManager())
    await reg_flow.db.connect()
    
    try:
        message = await reg_flow.start_registration(contact.user_id, user_data)
        keyboard = reg_flow.get_keyboard_for_step(contact.user_id)
        
        if keyboard:
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message)
            
    except Exception as e:
        logger.error(f"Error starting registration: {e}")
        await update.message.reply_text("❌ Error starting registration. Please try again.")
    finally:
        await reg_flow.db.close()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 *Ethiopian Job Bot Commands:*\n\n"
        "👤 *Profile & Preferences:*\n"
        "/start - Start using the bot\n"
        "/profile - View your profile\n"
        "/preferences - Set your job preferences\n"
        "/education - Update your education level\n"
        "/help - Show this help message\n\n"
        "💼 *Job Search:*\n"
        "/jobs - View available jobs\n"
        "/apply <job_number> - Apply for a job\n\n"
        "💰 *Subscription:*\n"
        "/subscribe - Get premium subscription (50 Birr/month)\n"
        "/status - Check subscription status\n"
        "/confirm_subscribe - Confirm payment\n\n"
        "🔧 *Admin Commands:*\n"
        "/admin_payments - View pending payments\n\n"
        "📱 *Contact:* @support for assistance"
    )
    
    await update.message.reply_text(help_text)

async def preferences_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle job preferences setup"""
    user = update.effective_user
    
    # Check if user is registered
    db = DatabaseManager()
    await db.connect()
    
    try:
        user_data = await db.get_user(user.id)
        
        if not user_data or not user_data.get('phone_number'):
            # User not registered, show registration prompt
            contact_button = KeyboardButton(
                text="📞 Share Contact",
                request_contact=True
            )
            keyboard = [[contact_button]]
            reply_markup = ReplyKeyboardMarkup(
                keyboard,
                resize_keyboard=True,
                one_time_keyboard=True
            )
            
            message = (
                "🚫 *Registration Required*\n\n"
                "You need to complete registration first to set preferences.\n\n"
                "📱 Please share your contact to get started:"
            )
            
            await update.message.reply_text(message, reply_markup=reply_markup)
            return
        
        # User is registered, start preference collection
        from bot.user_preferences import PreferenceCollector
        
        # Get or create preference collector for this user
        if user.id not in preference_collectors:
            preference_collectors[user.id] = PreferenceCollector(db)
        
        collector = preference_collectors[user.id]
        
        # Start preference collection
        message = collector.start_preference_collection(user.id)
        
        # Show categories inline keyboard
        keyboard = collector.manager.get_categories_keyboard()
        await update.message.reply_text(message, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in preferences command: {e}")
        await update.message.reply_text("❌ Error loading preferences. Please try again.")
    finally:
        await db.close()

async def jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available job listings."""
    user = update.effective_user
    
    jobs_text = (
        "💼 *Available Jobs:*\n\n"
        "🔍 *Recent Job Matches:*\n"
        "1. Software Developer - Addis Ababa - 15,000-25,000 Birr\n"
        "2. Accountant - Adama - 8,000-12,000 Birr\n"
        "3. Marketing Manager - Remote - 12,000-18,000 Birr\n"
        "4. Customer Service - Addis Ababa - 6,000-9,000 Birr\n\n"
        "📝 *To apply:* Tap on a job number below\n"
        "⚙️ *Better matches:* Update your preferences\n"
        "💰 *Premium:* Subscribe for unlimited matches"
    )
    
    keyboard = [
        ["1️⃣ Apply for Job 1", "2️⃣ Apply for Job 2"],
        ["3️⃣ Apply for Job 3", "4️⃣ Apply for Job 4"],
        ["⚙️ Update Preferences", "💰 Subscribe"],
        ["⬅️ Back to Main Menu"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(jobs_text, reply_markup=reply_markup)

async def apply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle job application."""
    user = update.effective_user
    
    # Check if job ID provided
    if context.args:
        job_id = context.args[0]
        apply_text = f"📝 *Applying for Job #{job_id}*\n\n"
        apply_text += "Please confirm your application:\n"
        apply_text += f"👤 Name: {user.first_name} {user.last_name or ''}\n"
        apply_text += f"📱 Phone: [Will be shared with employer]\n"
        apply_text += f"📧 Email: [Add if available]\n\n"
        apply_text += "✅ *Confirm Application* - /confirm_apply {job_id}\n"
        apply_text += "❌ *Cancel* - /cancel"
        
        await update.message.reply_text(apply_text)
    else:
        await update.message.reply_text(
            "📝 *To apply for a job:*\n\n"
            "Use: /apply [job_id]\n\n"
            "Example: /apply 123\n\n"
            "View available jobs with /jobs"
        )

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription process"""
    user = update.effective_user
    
    # Initialize subscription manager
    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db, context.bot)  # Pass bot instance for admin notifications
        
        # Start subscription process
        response = await sub_manager.start_subscription_process(user.id)
        keyboard = sub_manager.get_payment_keyboard()
        
        await update.message.reply_text(response, reply_markup=keyboard)
        
        # Store subscription manager for this user
        subscription_managers[user.id] = sub_manager
        
    except Exception as e:
        logger.error(f"Error in subscribe command: {e}")
        await update.message.reply_text("❌ Error starting subscription process. Please try again.")
    finally:
        await db.close()

async def confirm_subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription confirmation"""
    user = update.effective_user
    
    await update.message.reply_text(
        "💳 *Payment Confirmation*\n\n"
        "Please complete your payment first, then type 'PAID' to confirm.\n\n"
        "If you haven't started the payment process, use /subscribe first."
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription status check"""
    user = update.effective_user
    
    # Initialize subscription manager
    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db, context.bot)  # Pass bot instance for admin notifications
        
        # Check subscription status
        status_info = await sub_manager.check_subscription_status(user.id)
        status_message = sub_manager.format_subscription_status(status_info)
        
        await update.message.reply_text(status_message)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await update.message.reply_text("❌ Error checking subscription status. Please try again.")
    finally:
        await db.close()

async def subscription_management_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription management with proper flow"""
    user = update.effective_user
    
    # Check current subscription status first
    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db, context.bot)
        
        # Get current subscription status
        status_info = await sub_manager.check_subscription_status(user.id)
        status_message = sub_manager.format_subscription_status(status_info)
        
        # Create appropriate keyboard based on status
        if status_info['status'] == 'trial':
            # User has trial - show upgrade options
            keyboard = [
                ["📊 Check Status", "💳 Upgrade to Premium"],
                ["⬅️ Back to Main Menu"]
            ]
            message = f"{status_message}\n\n💰 *Subscription Management:*\n\nChoose an option:"
            
        elif status_info['is_active'] and status_info['status'] == 'active':
            # User has active paid subscription - show management options
            keyboard = [
                ["📊 Check Status", "⬅️ Back to Main Menu"],
                ["❌ Cancel Subscription"]
            ]
            message = f"{status_message}\n\n💰 *Subscription Management:*\n\nChoose an option:"
            
        else:
            # User has no subscription or expired - show subscribe options
            keyboard = [
                ["📊 Check Status", "💳 Subscribe Now"],
                ["⬅️ Back to Main Menu"]
            ]
            message = f"{status_message}\n\n💰 *Subscription Management:*\n\nChoose an option:"
        
        await update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        
    except Exception as e:
        logger.error(f"Error in subscription management: {e}")
        await update.message.reply_text("❌ Error loading subscription options. Please try again.")
    finally:
        await db.close()

async def check_subscription_status(update: Update, user) -> None:
    """Check subscription status command"""
    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db)
        
        # Get subscription status
        status_info = await sub_manager.check_subscription_status(user.id)
        status_message = sub_manager.format_subscription_status(status_info)
        
        await update.message.reply_text(status_message)
        
    except Exception as e:
        logger.error(f"Error checking subscription status: {e}")
        await update.message.reply_text("❌ Error checking subscription status. Please try again.")
    finally:
        await db.close()

async def admin_payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view pending payments"""
    user = update.effective_user
    
    # Check if user is admin (you should implement proper admin verification)
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        # Pass bot instance to PaymentApprovalSystem
        bot_instance = context.bot
        approval_system = PaymentApprovalSystem(db, bot_instance)
        await approval_system.create_pending_payments_table()
        
        # Get pending payments
        pending_payments = await approval_system.get_pending_payments()
        
        if not pending_payments:
            await update.message.reply_text("✅ No pending payments.")
            return
        
        message = "💰 *Pending Payments*\n\n"
        
        for payment in pending_payments[:10]:  # Show max 10 payments
            message += (
                f"📋 ID: {payment['payment_id']}\n"
                f"👤 User: {payment['first_name']} ({payment['user_id']})\n"
                f"💳 Method: {payment['payment_method']}\n"
                f"💰 Amount: {payment['amount']} Birr\n"
                f"📝 Ref: {payment['reference']}\n"
                f"📅 {payment['submitted_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            )
        
        if len(pending_payments) > 10:
            message += f"... and {len(pending_payments) - 10} more"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in admin_payments command: {e}")
        await update.message.reply_text("❌ Error fetching pending payments.")
    finally:
        await db.close()

async def education_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle education level preference update"""
    user = update.effective_user
    
    # Initialize database and preference collector
    db = DatabaseManager()
    try:
        await db.connect()
        collector = PreferenceCollector(db)
        
        # Start education preference collection
        response = collector.manager.format_education_message()
        await update.message.reply_text(response, reply_markup=collector.manager.get_education_keyboard())
        
        # Store collector for this user
        preference_collectors[user.id] = collector
        
    except Exception as e:
        logger.error(f"Error in education command: {e}")
        await update.message.reply_text("❌ Error updating education preference. Please try again.")
    finally:
        await db.close()

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user profile information."""
    user = update.effective_user
    
    # Get user data from database
    db = DatabaseManager()
    try:
        await db.connect()
        user_data = await db.get_user(user.id)
        
        # Also get user preferences
        preferences = None
        if user_data:
            from bot.user_preferences import PreferenceManager
            pref_manager = PreferenceManager(db)
            preferences = await pref_manager.get_user_preferences(user.id)
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        user_data = None
        preferences = None
    finally:
        await db.close()
    
    if user_data:
        profile_text = (
            f"👤 Your Profile:\n\n"
            f"Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
            f"Username: @{user_data.get('username', 'N/A')}\n"
            f"User ID: {user_data.get('user_id', 'N/A')}\n"
            f"📱 Phone: {user_data.get('phone_number', 'Not shared')}\n"
            f"📅 Registered: {user_data.get('created_at', 'N/A')}"
        )
        
        # Add preferences section if available
        if preferences:
            profile_text += (
                f"\n\n🎯 Your Job Preferences:\n"
                f"📂 Categories: {', '.join(preferences.preferred_categories) if preferences.preferred_categories else 'Not set'}\n"
                f"📍 Locations: {', '.join(preferences.preferred_locations) if preferences.preferred_locations else 'Not set'}\n"
                f"⏰ Job Types: {', '.join(preferences.preferred_job_types) if preferences.preferred_job_types else 'Not set'}\n"
                f"💰 Min Salary: {preferences.min_salary if preferences.min_salary else 'Not set'} Birr\n"
                f"🎓 Education: {preferences.education_level if preferences.education_level else 'Not set'}\n"
                f"🔧 Keywords: {', '.join(preferences.keywords) if preferences.keywords else 'Not set'}"
            )
        else:
            profile_text += "\n\n🎯 Job Preferences: Not set yet\nUse /preferences to set your job preferences"
            
    else:
        profile_text = (
            f"👤 Your Profile:\n\n"
            f"Name: {user.first_name} {user.last_name or ''}\n"
            f"Username: @{user.username or 'N/A'}\n"
            f"User ID: {user.id}\n\n"
            f"📱 Phone: Not shared yet\n\n"
            f"Use /start to share your contact information!"
        )
    
    await update.message.reply_text(profile_text)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    
    user = update.effective_user
    callback_data = query.data
    
    logger.info(f"Callback received from user {user.id}: {callback_data}")
    
    # Get or create preference collector for this user
    if user.id not in preference_collectors:
        db = DatabaseManager()
        await db.connect()
        preference_collectors[user.id] = PreferenceCollector(db)
    
    collector = preference_collectors[user.id]
    
    # Handle different callback types
    if callback_data.startswith("category_"):
        category = callback_data.replace("category_", "")
        response = await collector.handle_category_selection(user.id, f"📂 {category.replace('_', ' ').title()}")
        # Only edit if response is different (avoid "Message is not modified" error)
        if response != query.message.text:
            await query.edit_message_text(response, reply_markup=collector.manager.get_education_keyboard())
        else:
            await query.edit_message_reply_markup(reply_markup=collector.manager.get_education_keyboard())
    
    elif callback_data.startswith("education_"):
        education_level = callback_data.replace("education_", "")
        response = await collector.handle_education_selection(user.id, education_level)
        logger.info(f"Education selection response: '{response}'")
        if "🌍" in response or "Select Your Preferred Locations" in response:  # Location prompt - show location keyboard
            await query.edit_message_text(response, reply_markup=collector.manager.get_locations_keyboard())
        else:
            # Only edit if response is different (avoid "Message is not modified" error)
            if response != query.message.text:
                await query.edit_message_text(response, reply_markup=collector.manager.get_education_keyboard())
            else:
                await query.edit_message_reply_markup(reply_markup=collector.manager.get_education_keyboard())
        
    elif callback_data.startswith("location_"):
        location = callback_data.replace("location_", "")
        if location == "remote":
            response = await collector.handle_location_selection(user.id, "🌍 Remote/Work from Home")
        elif location == "any":
            response = await collector.handle_location_selection(user.id, "🇪🇹 Any Location")
        else:
            response = await collector.handle_location_selection(user.id, f"📍 {location}")
        # Only edit if response is different (avoid "Message is not modified" error)
        if response != query.message.text:
            await query.edit_message_text(response, reply_markup=collector.manager.get_job_types_keyboard())
        else:
            await query.edit_message_reply_markup(reply_markup=collector.manager.get_job_types_keyboard())
        
    elif callback_data.startswith("jobtype_"):
        job_type = callback_data.replace("jobtype_", "").replace("_", " ").title()
        response = await collector.handle_job_type_selection(user.id, f"• {job_type}")
        logger.info(f"Job type selection response: '{response}'")
        if "💰" in response:  # Salary prompt - always show salary keyboard
            await query.edit_message_text(response, reply_markup=collector.manager.get_salary_keyboard())
        else:
            # Only edit if response is different (avoid "Message is not modified" error)
            if response != query.message.text:
                await query.edit_message_text(response, reply_markup=collector.manager.get_job_types_keyboard())
            else:
                await query.edit_message_reply_markup(reply_markup=collector.manager.get_job_types_keyboard())

    elif callback_data.startswith("salary_"):
        salary_value = callback_data.replace("salary_", "")
        response = await collector.handle_salary_selection(user.id, salary_value)
        logger.info(f"Salary selection response: '{response}'")
        if "📊" in response:  # Experience prompt - show experience keyboard
            await query.edit_message_text(response, reply_markup=collector.manager.get_experience_keyboard())
        else:
            # Only edit if response is different (avoid "Message is not modified" error)
            if response != query.message.text:
                await query.edit_message_text(response, reply_markup=collector.manager.get_salary_keyboard())
            else:
                await query.edit_message_reply_markup(reply_markup=collector.manager.get_salary_keyboard())

    elif callback_data.startswith("experience_"):
        experience_level = callback_data.replace("experience_", "")
        response = await collector.handle_experience_selection(user.id, experience_level)
        logger.info(f"Experience selection response: '{response}'")
        if "✅" in response:  # Success message
            await query.edit_message_text(response)
        elif "Select your" in response:  # Experience prompt
            await query.edit_message_text(response, reply_markup=collector.manager.get_experience_keyboard())
        else:
            # Only edit if response is different (avoid "Message is not modified" error)
            if response != query.message.text:
                await query.edit_message_text(response, reply_markup=collector.manager.get_experience_keyboard())
            else:
                await query.edit_message_reply_markup(reply_markup=collector.manager.get_experience_keyboard())
    
    # Handle payment approval callbacks
    elif callback_data.startswith("approve_payment_"):
        payment_id = int(callback_data.replace("approve_payment_", ""))
        await handle_payment_approval(update, user, payment_id, "approve", context)
    
    elif callback_data.startswith("reject_payment_"):
        payment_id = int(callback_data.replace("reject_payment_", ""))
        await handle_payment_approval(update, user, payment_id, "reject", context)
    
    elif callback_data.startswith("verify_payment_"):
        payment_id = int(callback_data.replace("verify_payment_", ""))
        await handle_payment_verification(update, user, payment_id)
            
    elif callback_data == "back_to_job_types":
        response = collector.manager.format_job_types_message()
        await query.edit_message_text(response, reply_markup=collector.manager.get_job_types_keyboard())
        
    elif callback_data == "back_to_categories":
        response = collector.manager.format_categories_message()
        await query.edit_message_text(response, reply_markup=collector.manager.get_categories_keyboard())
        
    elif callback_data == "back_to_locations":
        response = collector.manager.format_locations_message()
        await query.edit_message_text(response, reply_markup=collector.manager.get_locations_keyboard())
        
    elif callback_data == "cancel":
        if user.id in collector.user_states:
            del collector.user_states[user.id]
        await query.edit_message_text("Preference collection cancelled.")
        
    elif callback_data == "custom_categories":
        if user.id in collector.user_states:
            collector.user_states[user.id]['step'] = 'custom_categories'
        await query.edit_message_text("Please type the job categories you're interested in (separate with commas):")
        
    elif callback_data == "search_jobs":
        await query.edit_message_text("🔍 *Job Search*\n\nThis feature is coming soon! Use /jobs to see available positions.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages during registration and preferences."""
    user = update.effective_user
    message_text = update.message.text
    
    # Handle back button
    if message_text == "⬅️ Back to Main Menu":
        await show_main_menu(update, user)
        return
    
    # Handle clickable menu options
    if message_text == "📊 View Profile":
        await profile_command(update, context)
        return
    elif message_text == "⚙️ Update Preferences":
        await preferences_command(update, context)
        return
    elif message_text == "🔍 Search Jobs":
        await jobs_command(update, context)
        return
    elif message_text == "💰 Manage Subscription":
        await subscription_management_command(update, context)
        return
    elif message_text == "📊 Check Status":
        await status_command(update, context)
        return
    elif message_text == "💳 Subscribe Now":
        await subscribe_command(update, context)
        return
    elif message_text == "💳 Upgrade to Premium":
        await subscribe_command(update, context)
        return
    elif message_text == "❌ Cancel Subscription":
        await cancel_subscription_command(update, user)
        return
    elif message_text == "📞 Contact Support":
        await update.message.reply_text(
            "📞 *Support Contact*\n\n"
            "Need help? Contact us:\n"
            "📧 Email: support@ethiopianjobbot.com\n"
            "📱 Phone: +251911234567\n"
            "💬 Telegram: @ethiopian_job_support\n\n"
            "We're here to help! 🇪🇹"
        )
        return
    elif message_text in ["1️⃣ Apply for Job 1", "2️⃣ Apply for Job 2", "3️⃣ Apply for Job 3", "4️⃣ Apply for Job 4"]:
        job_num = message_text.split("⃣")[0]
        await handle_job_application(update, user, job_num)
        return
    elif message_text == "✅ Confirm Application":
        await confirm_job_application(update, user)
        return
    
    # Handle subscription payment confirmation
    elif message_text.upper() == "PAID":
        await handle_payment_confirmation(update, user)
        return
    elif message_text.lower() == "cancel":
        await handle_subscription_cancellation(update, user)
        return
    
    # Check if user is in subscription process
    if user.id in subscription_managers:
        await handle_subscription_response(update, user, message_text)
        return
    
    # Check if user is in registration flow
    reg_flow = RegistrationFlow(DatabaseManager())
    await reg_flow.db.connect()
    
    try:
        # Only handle registration if user is actually in registration flow
        if user.id in reg_flow.registration_states:
            logger.info(f"User {user.id} is in registration flow, step: {reg_flow.registration_states[user.id].get('step')}")
            response = await reg_flow.handle_registration_response(user.id, message_text)
            
            if response:
                keyboard = reg_flow.get_keyboard_for_step(user.id)
                
                if keyboard:
                    # Add back button to registration keyboards
                    keyboard.append(["⬅️ Back to Main Menu"])
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text(response, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(response)
        else:
            # Handle preference responses for registered users
            logger.info(f"User {user.id} not in registration flow, handling as preference response")
            await handle_preference_response(update, user, message_text)
                
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("❌ Error processing your request. Please try again.")
    finally:
        await reg_flow.db.close()

async def handle_job_application(update: Update, user, job_num: str):
    """Handle job application from clickable button"""
    
    job_details = {
        "1": {"title": "Software Developer", "company": "Tech Ethiopia", "salary": "15,000-25,000 Birr", "location": "Addis Ababa"},
        "2": {"title": "Accountant", "company": "Finance Plus", "salary": "8,000-12,000 Birr", "location": "Adama"},
        "3": {"title": "Marketing Manager", "company": "Marketing Pro", "salary": "12,000-18,000 Birr", "location": "Remote"},
        "4": {"title": "Customer Service", "company": "Service Hub", "salary": "6,000-9,000 Birr", "location": "Addis Ababa"}
    }
    
    if job_num in job_details:
        job = job_details[job_num]
        
        application_text = (
            f"📝 *Applying for: {job['title']}*\n\n"
            f"🏢 **Company:** {job['company']}\n"
            f"💰 **Salary:** {job['salary']}\n"
            f"📍 **Location:** {job['location']}\n\n"
            f"👤 **Your Information:**\n"
            f"Name: {user.first_name} {user.last_name or ''}\n"
            f"Username: @{user.username or 'Not set'}\n\n"
            f"📱 Your phone number will be shared with the employer\n\n"
            f"✅ *Confirm Application* - Click below to proceed\n"
            f"❌ *Cancel* - Click 'Back to Main Menu'"
        )
        
        keyboard = [
            ["✅ Confirm Application", "❌ Cancel"],
            ["⬅️ Back to Main Menu"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(application_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text("❌ Job not found. Please try again.")

async def confirm_job_application(update: Update, user):
    """Confirm and submit job application"""
    
    confirmation_text = (
        "🎉 *Application Submitted Successfully!*\n\n"
        "✅ Your application has been sent to the employer\n"
        "📱 Your phone number will be shared for contact\n"
        "📧 You'll receive updates via Telegram\n\n"
        "📋 *Application Details:*\n"
        "Status: Pending Review\n"
        "Submitted: Just now\n\n"
        "🔔 *You'll be notified when:*\n"
        "• Employer views your application\n"
        "• Interview is scheduled\n"
        "• Application status changes\n\n"
        "🚀 *What's next?*\n"
        "• Wait for employer response\n"
        "• Browse more jobs\n"
        "• Update your profile"
    )
    
    keyboard = [
        ["🔍 Browse More Jobs", "📊 View Applications"],
        ["⚙️ Update Profile", "⬅️ Back to Main Menu"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)

async def show_main_menu(update: Update, user):
    """Show main menu with clickable options"""
    keyboard = [
        ["📊 View Profile", "⚙️ Update Preferences"],
        ["🔍 Search Jobs", "💰 Manage Subscription"],
        ["📞 Contact Support", "❓ Help"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    message = (
        f"👋 Welcome back {user.first_name}!\n\n"
        "🔧 *Main Menu:*\n\n"
        "Choose an option below:\n\n"
        "1. View Profile\n"
        "2. Update Preferences\n"
        "3. Search Jobs\n"
        "4. Manage Subscription\n"
        "5. Contact Support\n"
        "6. Help"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup)

# Global preference collectors to maintain state
preference_collectors = {}
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
        logger.info(f"Handling payment confirmation for user {user.id}")
        result = await sub_manager.confirm_payment(user.id, "PAID")
        
        if result['success']:
            await update.message.reply_text(result['message'])
            # Clean up
            del subscription_managers[user.id]
        else:
            await update.message.reply_text(result['message'])
            # Show payment keyboard again on error
            keyboard = sub_manager.get_payment_keyboard()
            await update.message.reply_text("Please select a payment method:", reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error confirming payment: {e}")
        await update.message.reply_text(f"❌ Error confirming payment: {str(e)}")

async def cancel_subscription_command(update: Update, user) -> None:
    """Handle subscription cancellation command"""
    db = DatabaseManager()
    try:
        await db.connect()
        sub_manager = SubscriptionManager(db, update.message.bot)
        
        # Check current subscription status
        status_info = await sub_manager.check_subscription_status(user.id)
        
        if not status_info['is_active'] and status_info['status'] == 'no_subscription':
            await update.message.reply_text("❌ You don't have an active subscription to cancel.")
            return
        
        # Cancel the subscription
        result = await sub_manager.cancel_subscription(user.id)
        
        if result['success']:
            await update.message.reply_text(
                f"✅ {result['message']}\n\n"
                "💔 Your subscription has been cancelled.\n"
                "You can subscribe again anytime using 💰 Manage Subscription."
            )
        else:
            await update.message.reply_text(f"❌ {result['message']}")
            
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        await update.message.reply_text("❌ Error cancelling subscription. Please try again.")
    finally:
        await db.close()

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
        await update.callback_query.answer("❌ Admin access required.", show_alert=True)
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        # Pass bot instance for user notifications
        bot_instance = context.bot
        approval_system = PaymentApprovalSystem(db, bot_instance)
        
        if action == "approve":
            result = await approval_system.approve_payment(payment_id, admin_user.id)
            message = f"✅ Payment {payment_id} approved!" if result['success'] else f"❌ Error: {result['message']}"
        else:  # reject
            result = await approval_system.reject_payment(payment_id, admin_user.id, "Payment not verified")
            message = f"❌ Payment {payment_id} rejected!" if result['success'] else f"❌ Error: {result['message']}"
        
        await update.callback_query.answer(message, show_alert=True)
        
        # Update the message to remove buttons
        await update.callback_query.edit_message_text(
            f"💰 *Payment {payment_id}*\n\n✅ *Processed: {action.title()}*\n\nBy: {admin_user.first_name}"
        )
        
    except Exception as e:
        logger.error(f"Error handling payment approval: {e}")
        await update.callback_query.answer("❌ Error processing payment", show_alert=True)
    finally:
        await db.close()

async def handle_payment_verification(update: Update, admin_user, payment_id: int) -> None:
    """Handle payment verification (show details)"""
    # Check if user is admin
    if admin_user.id not in Config.ADMIN_IDS:
        await update.callback_query.answer("❌ Admin access required.", show_alert=True)
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        # Get payment details
        payment_query = """
            SELECT pp.*, u.first_name, u.username, u.phone_number
            FROM pending_payments pp
            LEFT JOIN users u ON pp.user_id = u.user_id
            WHERE pp.payment_id = $1
        """
        
        payment = await db.connection.fetchrow(payment_query, payment_id)
        
        if not payment:
            await update.callback_query.answer("Payment not found", show_alert=True)
            return
        
        details = (
            f"💰 *Payment Details*\n\n"
            f"📋 *ID:* {payment['payment_id']}\n"
            f"👤 *User:* {payment['first_name']} (@{payment['username'] or 'N/A'})\n"
            f"📱 *Phone:* {payment['phone_number'] or 'Not provided'}\n"
            f"💳 *Method:* {payment['payment_method']}\n"
            f"💰 *Amount:* {payment['amount']} Birr\n"
            f"📝 *Reference:* {payment['reference']}\n"
            f"📅 *Submitted:* {payment['submitted_at']}\n"
            f"📊 *Status:* {payment['status']}"
        )
        
        await update.callback_query.answer(details, show_alert=True)
        
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        await update.callback_query.answer("❌ Error fetching payment details", show_alert=True)
    finally:
        await db.close()

async def check_subscription_status(update: Update, user) -> None:
    """Check subscription status (for menu button)"""
    await status_command(update, None)

async def handle_preference_response(update: Update, user, message_text: str):
    """Handle preference responses for registered users"""
    logger.info(f"Handling preference response for user {user.id}: '{message_text}'")
    db = DatabaseManager()
    await db.connect()
    
    try:
        # Get or create preference collector for this user
        if user.id not in preference_collectors:
            from bot.user_preferences import PreferenceCollector
            preference_collectors[user.id] = PreferenceCollector(db)
        
        collector = preference_collectors[user.id]
        
        # Try to handle as preference response
        response = await collector.handle_preference_response(user.id, message_text)
        
        if response:
            logger.info(f"Preference response: '{response}'")
            # Get appropriate keyboard based on current step
            state = collector.user_states.get(user.id, {})
            step = state.get('step', 'categories')
            logger.info(f"Current preference step: {step}")
            
            if step == 'categories':
                keyboard = collector.manager.get_categories_keyboard()
            elif step == 'locations':
                keyboard = collector.manager.get_locations_keyboard()
            elif step == 'job_types':
                keyboard = collector.manager.get_job_types_keyboard()
            elif step == 'salary':
                keyboard = collector.manager.get_salary_keyboard()
            else:
                # No keyboard needed for completed preferences
                await update.message.reply_text(response)
                return
            
            # Send response with keyboard
            if step == 'categories':
                keyboard = collector.manager.get_categories_keyboard()
            elif step == 'locations':
                keyboard = collector.manager.get_locations_keyboard()
            elif step == 'job_types':
                keyboard = collector.manager.get_job_types_keyboard()
            elif step == 'salary':
                keyboard = collector.manager.get_salary_keyboard()
            else:
                # No keyboard needed for completed preferences
                await update.message.reply_text(response)
                return
            
            # Handle different keyboard types
            if isinstance(keyboard, list):
                # It's a list of buttons, create ReplyKeyboardMarkup
                keyboard_list = keyboard.copy()
                keyboard_list.append(["⬅️ Back to Main Menu"])
                reply_markup = ReplyKeyboardMarkup(keyboard_list, resize_keyboard=True)
            elif hasattr(keyboard, 'inline_keyboard'):
                # It's an InlineKeyboardMarkup, return as is (no back button for inline keyboards)
                reply_markup = keyboard
            else:
                # Fallback: create basic keyboard with back button
                reply_markup = ReplyKeyboardMarkup([["⬅️ Back to Main Menu"]], resize_keyboard=True)
            
            await update.message.reply_text(response, reply_markup=reply_markup)
        else:
            # Not a preference response, show help
            await update.message.reply_text(
                "❓ I didn't understand that. Please use the menu options or /help for commands.",
                reply_markup=ReplyKeyboardMarkup([
                    ["📊 View Profile", "⚙️ Update Preferences"],
                    ["🔍 Search Jobs", "💰 Manage Subscription"],
                    ["⬅️ Back to Main Menu"]
                ], resize_keyboard=True)
            )
            
    except Exception as e:
        logger.error(f"Error handling preference response: {e}")
        await update.message.reply_text("❌ Error updating preferences. Please try again.")
    # Don't close db connection here - preference collectors manage their own connections

async def main() -> None:
    """Start the bot."""
    token = Config.TELEGRAM_BOT_TOKEN
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in configuration!")
        return
    
    # Configure bot with timeout settings
    application = Application.builder().token(token).build()
    
    # Set connection timeouts to prevent hanging (if available)
    try:
        application.bot.connection_pool.connect_timeout = 30.0
        application.bot.connection_pool.read_timeout = 30.0
        application.bot.connection_pool.write_timeout = 30.0
    except AttributeError:
        logger.warning("Connection pool timeout settings not available in this version")
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("preferences", preferences_command))
    application.add_handler(CommandHandler("education", education_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("confirm_subscribe", confirm_subscribe_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("admin_payments", admin_payments_command))
    application.add_handler(CommandHandler("jobs", jobs_command))
    application.add_handler(CommandHandler("apply", apply_command))
    
    # Register channel management handlers
    register_channel_handlers(application)
    
    # Register message handlers
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    application.add_handler(MessageHandler(filters.CONTACT, contact_received))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info("Starting Ethiopian Job Bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    main()
