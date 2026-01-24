"""
Message Handlers
Handles regular text messages and routing
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.registration_flow import RegistrationFlow
from bot.user_preferences import PreferenceCollector

logger = logging.getLogger(__name__)

# Global collectors to maintain state
preference_collectors = {}

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages during registration and preferences."""
    user = update.effective_user
    message_text = update.message.text
    
    logger.info(f"Received message from user {user.id}: '{message_text}'")

    # Handle common greetings by reusing the /start flow
    normalized_text = (message_text or "").strip().lower()
    if normalized_text in {"hi", "hello", "hey", "menu", "start"}:
        from bot.commands.start_commands import start
        await start(update, context)
        return
    
    # Handle subscription payment confirmation
    if message_text.upper() == "PAID":
        from .subscription_handlers import handle_payment_confirmation
        await handle_payment_confirmation(update, user)
        return
    elif message_text.lower() == "cancel":
        from .subscription_handlers import handle_subscription_cancellation
        await handle_subscription_cancellation(update, user)
        return
    
    # Handle main menu buttons BEFORE preference handling
    if message_text == "View Profile":
        from bot.commands.user_commands import profile_command
        await profile_command(update, context)
        return
    elif message_text == "Update Preferences":
        from bot.commands.user_commands import preferences_command
        await preferences_command(update, context)
        return
    elif message_text == "Search Jobs":
        from bot.commands.user_commands import jobs_command
        await jobs_command(update, context)
        return
    elif message_text == "Manage Subscription":
        from bot.commands.subscription_commands import subscription_management_command
        await subscription_management_command(update, context)
        return
    elif message_text == "Check Status":
        from bot.commands.subscription_commands import status_command
        await status_command(update, context)
        return
    elif message_text == "Subscribe Now":
        from bot.commands.subscription_commands import subscribe_command
        await subscribe_command(update, context)
        return
    elif message_text == "Upgrade to Premium":
        from bot.commands.subscription_commands import subscribe_command
        await subscribe_command(update, context)
        return
    elif message_text == "Cancel Subscription":
        from bot.commands.subscription_commands import cancel_subscription_command
        await cancel_subscription_command(update, context)
        return
    elif message_text == "Contact Support":
        await update.message.reply_text(
            "📞 *Contact Support*\n\n"
            "Need help? Contact us:\n"
            "Email: support@jobsmatch.bot\n"
            "Phone: +251911234567\n"
            "Telegram: @JobsMatchSupport\n\n"
            "We're here to help!"
        )
        return
    elif message_text == "Back to Main Menu":
        from bot.utils.menu_utils import show_main_menu
        await show_main_menu(update, user)
        return
    elif message_text == "Referral Program":
        from bot.commands.referral_commands import referral_command
        await referral_command(update, context)
        return
    elif message_text == "Help":
        from bot.commands.start_commands import help_command
        await help_command(update, context)
        return
    
    # Handle preference selections (emoji-based responses)
    if any(emoji in message_text for emoji in ["💻", "💰", "🏥", "🎓", "📢", "⚙️", "🏨", "🏛️", "📋", "🌍", "🇪🇹", "📍", "🏠", "💼", "⏰", "🤝", "🎓", "💵", "🎯", "🔧", "📝", "📞", "🔨", "🌱", "🏗️", "🚜", "🚚", "✈️", "⚕️", "🔬", "🎭", "🎨", "📷", "🖥️", "📱", "🌐", "🔒", "⚖️", "🏛️", "📚", "🔬", "💊", "🍽️", "👔", "👷", "🔧", "⚡", "💧", "🌾", "🐄", "🐟", "🌳", "🏭", "🛒", "📦", "🚚", "🚢", "✈️", "🚂", "🚁", "⛵", "🚤", "🛳️"]):
        # This looks like a preference selection, handle it as such
        from .preference_handlers import handle_preference_response
        await handle_preference_response(update, user, message_text)
        return
    
    # Check if user is in subscription process
    from .subscription_handlers import subscription_managers
    if user.id in subscription_managers:
        from .subscription_handlers import handle_subscription_response
        await handle_subscription_response(update, user, message_text)
        return
    
    # Check if user is in registration flow
    reg_flow = RegistrationFlow(DatabaseManager())
    await reg_flow.db.connect()
    
    try:
        # Only handle registration if user is actually in registration flow
        if user.id in reg_flow.registration_states:
            logger.info(f"User {user.id} is in registration flow, step: {reg_flow.registration_states[user.id].get('step')}")
            
            # Handle "Back to Main Menu" button
            if message_text == "⬅️ Back to Main Menu":
                # Remove user from registration flow
                del reg_flow.registration_states[user.id]
                logger.info(f"User {user.id} exited registration flow")
                
                # Show main menu
                from bot.utils.menu_utils import show_main_menu
                await show_main_menu(update, user)
                return
            
            response = await reg_flow.handle_registration_response(user.id, message_text)
            
            if response:
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
                    
                    # If registration is complete, show main menu
                    if "registration complete" in response.lower():
                        logger.info(f"Registration completed detected, showing main menu for user {user.id}")
                        from bot.utils.menu_utils import show_main_menu
                        await show_main_menu(update, user)
                        return
            else:
                await update.message.reply_text(response)
        else:
            # Handle preference responses for registered users
            logger.info(f"User {user.id} not in registration flow, handling as preference response")
            
            # Handle "Back to Main Menu" button directly
            if message_text == "⬅️ Back to Main Menu":
                logger.info(f"User {user.id} requested main menu")
                from bot.utils.menu_utils import show_main_menu
                await show_main_menu(update, user)
                return
            
            from .preference_handlers import handle_preference_response
            await handle_preference_response(update, user, message_text)
                
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("Error processing your request. Please try again.")
    finally:
        await reg_flow.db.close()
