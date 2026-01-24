"""
User Commands
Handles user-specific commands like profile, preferences, jobs, applications
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.user_preferences import PreferenceCollector

logger = logging.getLogger(__name__)

async def preferences_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle job preferences setup"""
    user = update.effective_user
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        # Check if user is registered
        user_data = await db.get_user(user.id)
        if not user_data or not user_data.get('phone_number'):
            # Handle both message and callback query
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ Please complete registration first.\n"
                    "Use /start to begin registration."
                )
            else:
                await update.message.reply_text(
                    "❌ Please complete registration first.\n"
                    "Use /start to begin registration."
                )
            return
        
        # Start preference collection - use global collector to maintain state
        from bot.handlers.preference_handlers import preference_collectors
        
        if user.id not in preference_collectors:
            collector = PreferenceCollector(db)
            preference_collectors[user.id] = collector
        else:
            collector = preference_collectors[user.id]
            # Ensure collector's database connection is open
            if not collector.manager.db.connection:
                collector.manager.db = db
                await db.connect()
            elif hasattr(collector.manager.db.connection, 'is_closed'):
                if callable(collector.manager.db.connection.is_closed) and collector.manager.db.connection.is_closed():
                    collector.manager.db = db
                    await db.connect()
        
        response = collector.start_preference_collection(user.id)
        
        # Import here to avoid circular imports
        from bot.utils.preference_utils import get_preference_keyboard
        
        keyboard_list, inline_keyboard = get_preference_keyboard(collector, user.id)
        if inline_keyboard:
            # Add back button to inline keyboard - convert tuple to list first
            if hasattr(inline_keyboard, 'inline_keyboard'):
                # Convert tuple to list if needed
                keyboard_rows = list(inline_keyboard.inline_keyboard) if isinstance(inline_keyboard.inline_keyboard, tuple) else inline_keyboard.inline_keyboard
                keyboard_rows.append([
                    InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous")
                ])
                keyboard_rows.append([
                    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu")
                ])
                inline_keyboard = InlineKeyboardMarkup(keyboard_rows)
            # Handle both message and callback query
            if update.callback_query:
                await update.callback_query.edit_message_text(response, reply_markup=inline_keyboard)
            else:
                await update.message.reply_text(response, reply_markup=inline_keyboard)
        else:
            # Handle both message and callback query
            if update.callback_query:
                await update.callback_query.edit_message_text(response)
            else:
                await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Error in preferences command: {e}")
        # Handle both message and callback query
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Error loading preferences. Please try again.")
        else:
            await update.message.reply_text("❌ Error loading preferences. Please try again.")
    # Don't close db here - keep connection open for preference collection flow

async def jobs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available job listings."""
    user = update.effective_user
    
    # Sample job listings (replace with actual database queries)
    jobs_text = (
        "🔍 *Available Jobs:*\n\n"
        "1️⃣ *Software Developer*\n"
        "   🏢 Tech Ethiopia\n"
        "   💰 15,000-25,000 Birr\n"
        "   📍 Addis Ababa\n\n"
        "2️⃣ *Accountant*\n"
        "   🏢 Finance Plus\n"
        "   💰 8,000-12,000 Birr\n"
        "   📍 Adama\n\n"
        "3️⃣ *Marketing Manager*\n"
        "   🏢 Marketing Pro\n"
        "   💰 12,000-18,000 Birr\n"
        "   📍 Remote\n\n"
        "4️⃣ *Nurse*\n"
        "   🏢 Medical Center\n"
        "   💰 10,000-15,000 Birr\n"
        "   📍 Bahir Dar\n\n"
        "💼 *Apply now with /apply [job number]*\n"
        "📊 *View your profile with /profile*"
    )
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [
            InlineKeyboardButton("1️⃣ Apply for Job 1", callback_data="apply_job_1"),
            InlineKeyboardButton("2️⃣ Apply for Job 2", callback_data="apply_job_2")
        ],
        [
            InlineKeyboardButton("3️⃣ Apply for Job 3", callback_data="apply_job_3"),
            InlineKeyboardButton("4️⃣ Apply for Job 4", callback_data="apply_job_4")
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Handle both message and callback query
    if update.callback_query:
        await update.callback_query.edit_message_text(jobs_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(jobs_text, reply_markup=reply_markup)

async def apply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle job application."""
    user = update.effective_user
    
    # Check if user provided a job number
    if context.args and len(context.args) > 0:
        job_num = context.args[0]
        # Import here to avoid circular imports
        from bot.handlers.job_handlers import handle_job_application
        await handle_job_application(update, user, job_num)
    else:
        await update.message.reply_text(
            "📝 *Job Application*\n\n"
            "Please specify a job number:\n"
            "• /apply 1 - Software Developer\n"
            "• /apply 2 - Accountant\n"
            "• /apply 3 - Marketing Manager\n"
            "• /apply 4 - Nurse\n\n"
            "Or use /jobs to see all available jobs."
        )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user profile information."""
    user = update.effective_user
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        # Get user data
        user_data = await db.get_user(user.id)
        if not user_data:
            # Handle both message and callback query
            if update.callback_query:
                await update.callback_query.edit_message_text("❌ Profile not found. Please use /start to register.")
            else:
                await update.message.reply_text("❌ Profile not found. Please use /start to register.")
            return
        
        # Get subscription status
        from bot.subscription_manager import SubscriptionManager
        sub_manager = SubscriptionManager(db, context.bot)
        status_info = await sub_manager.check_subscription_status(user.id)
        
        # Get user preferences
        from bot.user_preferences import PreferenceManager
        pref_manager = PreferenceManager(db)
        preferences = await pref_manager.get_user_preferences(user.id)
        
        # Format profile text
        profile_text = (
            f"Your Profile\n\n"
            f"Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}\n"
            f"Phone: {user_data.get('phone_number', 'Not set')}\n"
            f"Username: @{user_data.get('username', 'N/A')}\n\n"
            f"Subscription Status: {status_info.get('message', 'Unknown')}\n\n"
        )

        if preferences:
            # Handle potential None values from database
            locations = preferences.preferred_locations or []
            job_types = preferences.preferred_job_types or []
            categories = preferences.preferred_categories or []

            profile_text += (
                f"Your Preferences:\n"
                f"Locations: {', '.join(locations) if locations else 'Not set'}\n"
                f"Job Types: {', '.join(job_types) if job_types else 'Not set'}\n"
                f"Categories: {', '.join(categories) if categories else 'Not set'}\n"
                f"Min Salary: {preferences.min_salary or 'Not set'} Birr\n"
                f"Education: {preferences.education_level or 'Not set'}\n"
            )
        else:
            profile_text += "Preferences: Not set. Use /preferences to set them.\n"

        profile_text += f"\nMember Since: {user_data.get('created_at', 'Unknown')}"
        
        # Create navigation keyboard with back and main menu buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
                InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Determine how to send the message (callback query vs regular message)
        if update.callback_query:
            await update.callback_query.edit_message_text(profile_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(profile_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error loading profile: {e}")
        # Handle both message and callback query
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Error loading profile. Please try again.")
        else:
            await update.message.reply_text("❌ Error loading profile. Please try again.")
    finally:
        await db.close()

async def education_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle education level preference update"""
    user = update.effective_user
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        # Check if user is registered
        user_data = await db.get_user(user.id)
        if not user_data or not user_data.get('phone_number'):
            await update.message.reply_text(
                "❌ Please complete registration first.\n"
                "Use /start to begin registration."
            )
            return
        
        # Start education preference collection
        from bot.utils.preference_utils import start_education_preference
        await start_education_preference(update, user, db)
            
    except Exception as e:
        logger.error(f"Error in education command: {e}")
        await update.message.reply_text("❌ Error updating education preference. Please try again.")
    finally:
        await db.close()
