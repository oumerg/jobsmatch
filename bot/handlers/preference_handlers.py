"""
Preference Handlers
Handles user preference collection and management
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.user_preferences import PreferenceCollector

logger = logging.getLogger(__name__)

# Global preference collectors to maintain state
preference_collectors = {}

async def handle_preference_response(update: Update, user, message_text: str):
    """Handle preference responses for registered users"""
    logger.info(f"Handling preference response for user {user.id}: '{message_text}'")
    
    # Get or create preference collector for this user
    if user.id not in preference_collectors:
        db = DatabaseManager()
        await db.connect()
        from bot.user_preferences import PreferenceCollector
        preference_collectors[user.id] = PreferenceCollector(db)
    
    collector = preference_collectors[user.id]
    
    # Ensure database connection is open for the collector
    try:
        if not collector.manager.db.connection:
            await collector.manager.db.connect()
        elif hasattr(collector.manager.db.connection, 'is_closed'):
            if callable(collector.manager.db.connection.is_closed) and collector.manager.db.connection.is_closed():
                logger.warning(f"Reconnecting database for user {user.id}")
                await collector.manager.db.connect()
    except Exception as e:
        logger.warning(f"Connection check failed, reconnecting: {e}")
        await collector.manager.db.connect()
    
    try:
        
        # Map text responses to preference categories
        preference_mapping = {
            # Job Categories
            "💻 Technology": "technology",
            "💰 Finance": "finance", 
            "🏥 Healthcare": "healthcare",
            "🎓 Education": "education",
            "📢 Sales & Marketing": "sales_marketing",
            "⚙️ Engineering": "engineering",
            "🏨 Hospitality": "hospitality",
            "🏛️ Government": "government",
            "📋 Other": "other",
            # Add more mappings as needed
        }
        
        # Check if this is a known preference selection
        if message_text in preference_mapping:
            # Handle as category selection
            category = preference_mapping[message_text]
            response = await collector.handle_category_selection(user.id, category)
            logger.info(f"Processed category selection: {category}")
            
            # Get next keyboard - always use inline keyboard
            from bot.utils.preference_utils import get_preference_keyboard
            keyboard_list, inline_keyboard = get_preference_keyboard(collector, user.id)
            
            if inline_keyboard:
                # Add navigation buttons to inline keyboard - convert tuple to list first
                if hasattr(inline_keyboard, 'inline_keyboard'):
                    # Convert tuple to list if needed
                    keyboard_rows = list(inline_keyboard.inline_keyboard) if isinstance(inline_keyboard.inline_keyboard, tuple) else inline_keyboard.inline_keyboard
                    
                    # Always add the three navigation buttons
                    keyboard_rows.append([
                        InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
                        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                    ])
                    inline_keyboard = InlineKeyboardMarkup(keyboard_rows)
                await update.message.reply_text(response, reply_markup=inline_keyboard)
            else:
                await update.message.reply_text(response)
            return
        
        # Try to handle as regular preference response
        response = await collector.handle_preference_response(user.id, message_text)
        
        if response:
            logger.info(f"Preference response: '{response}'")
            # Get appropriate keyboard based on current step
            state = collector.user_states.get(user.id, {})
            step = state.get('step', 'categories')
            logger.info(f"Current preference step: {step}")
            
            from bot.utils.preference_utils import get_preference_keyboard
            keyboard_list, inline_keyboard = get_preference_keyboard(collector, user.id)
            
            if inline_keyboard:
                # Check if this is the success message - if so, show no keyboard
                if "Preferences Saved Successfully" in response or ("preferences" in response.lower() and "saved" in response.lower()):
                    await update.message.reply_text(response)
                else:
                    # Add navigation buttons to inline keyboard - convert tuple to list first
                    if hasattr(inline_keyboard, 'inline_keyboard'):
                        # Convert tuple to list if needed
                        keyboard_rows = list(inline_keyboard.inline_keyboard) if isinstance(inline_keyboard.inline_keyboard, tuple) else inline_keyboard.inline_keyboard
                        
                        # Always add the three navigation buttons
                        keyboard_rows.append([
                            InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
                            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu"),
                            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                        ])
                        inline_keyboard = InlineKeyboardMarkup(keyboard_rows)
                    await update.message.reply_text(response, reply_markup=inline_keyboard)
            else:
                await update.message.reply_text(response)
        else:
            # Not a preference response, show help
            # Don't show keyboard here - main menu is ReplyKeyboardMarkup only
            await update.message.reply_text(
                "❓ I didn't understand that. Please use the menu options or /help for commands."
            )
            
    except Exception as e:
        logger.error(f"Error in preference response: {e}")
        await update.message.reply_text("❌ Error updating preferences. Please try again.")
    # Don't close the connection here - keep it open for the preference collection flow
    # Connection will be closed when preference collection is complete or cancelled

async def handle_preference_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
    """Handle preference-related callback queries"""
    query = update.callback_query
    user = update.effective_user

    logger.info(f"Preference callback from user {user.id}: {callback_data}")

    db = DatabaseManager()
    await db.connect()

    try:
        # Get or create preference collector
        if user.id not in preference_collectors:
            from bot.user_preferences import PreferenceCollector
            preference_collectors[user.id] = PreferenceCollector(db)

        collector = preference_collectors[user.id]

        # Handle back navigation
        if callback_data == "back_to_previous":
            # Get current step and go back to previous step
            state = collector.user_states.get(user.id, {})
            current_step = state.get('step', 'categories')

            # Define the flow: categories -> education -> locations -> job_types -> salary -> experience
            step_flow = {
                'categories': None,  # Can't go back from first step
                'education': 'categories',
                'locations': 'education',
                'job_types': 'locations',
                'salary': 'job_types',
                'experience': 'salary'
            }

            previous_step = step_flow.get(current_step)
            if previous_step:
                # Update user state to previous step
                state['step'] = previous_step
                collector.user_states[user.id] = state

                # Get the appropriate message and keyboard for the previous step
                step_messages = {
                    'categories': collector.manager.format_categories_message(),
                    'education': collector.manager.format_education_message(),
                    'locations': collector.manager.format_locations_message(),
                    'job_types': collector.manager.format_job_types_message(),
                    'salary': collector.manager.format_salary_message(),
                    'experience': collector.manager.format_experience_message()
                }

                response = step_messages.get(previous_step, "❌ Error navigating back.")

                # Get the appropriate keyboard for the previous step
                from bot.utils.preference_utils import get_preference_keyboard
                keyboard_list, inline_keyboard = get_preference_keyboard(collector, user.id)

                # Update the message with response and keyboard
                if inline_keyboard:
                    # Add navigation buttons to inline keyboard - convert tuple to list first
                    if hasattr(inline_keyboard, 'inline_keyboard'):
                        keyboard_rows = list(inline_keyboard.inline_keyboard) if isinstance(inline_keyboard.inline_keyboard, tuple) else inline_keyboard.inline_keyboard
                        
                        # Always add the three navigation buttons
                        keyboard_rows.append([
                            InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
                            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu"),
                            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                        ])
                        inline_keyboard = InlineKeyboardMarkup(keyboard_rows)

                    await query.edit_message_text(response, reply_markup=inline_keyboard)
                else:
                    await query.edit_message_text(response)
            else:
                # Can't go back from first step, show main menu
                from bot.utils.menu_utils import show_main_menu
                await show_main_menu(update, user)
            return

        # Handle main menu navigation
        if callback_data == "back_to_main_menu":
            from bot.utils.menu_utils import show_main_menu
            await show_main_menu(update, user)
            return
            
        # Handle cancel operation
        if callback_data == "cancel":
            await query.edit_message_text("Operation cancelled.")
            return

        # Handle different callback types
        if callback_data.startswith("category_"):
            category = callback_data.replace("category_", "")
            response = await collector.handle_category_selection(user.id, category)
        elif callback_data.startswith("location_"):
            location = callback_data.replace("location_", "")
            response = await collector.handle_location_selection(user.id, location)
        elif callback_data.startswith("jobtype_"):
            job_type = callback_data.replace("jobtype_", "")
            response = await collector.handle_job_type_selection(user.id, job_type)
        elif callback_data.startswith("salary_"):
            salary = callback_data.replace("salary_", "")
            response = await collector.handle_salary_selection(user.id, salary)
        elif callback_data.startswith("education_"):
            response = await collector.handle_education_selection(user.id, callback_data)
        elif callback_data.startswith("experience_"):
            response = await collector.handle_experience_selection(user.id, callback_data)
        else:
            response = "❌ Invalid preference selection."

        # Get the appropriate keyboard for the next step
        from bot.utils.preference_utils import get_preference_keyboard
        keyboard_list, inline_keyboard = get_preference_keyboard(collector, user.id)

        # Update the message with response and keyboard
        if inline_keyboard:
            # Check if this is the success message - if so, show no keyboard
            if "Preferences Saved Successfully" in response or ("preferences" in response.lower() and "saved" in response.lower()):
                # Show clean success message with no keyboard
                try:
                    await query.edit_message_text(response, reply_markup=None)
                except Exception as e:
                    logger.warning(f"Could not edit message: {e}")
                    await query.message.reply_text(response)
            else:
                # Add navigation buttons to inline keyboard - convert tuple to list first
                if hasattr(inline_keyboard, 'inline_keyboard'):
                    keyboard_rows = list(inline_keyboard.inline_keyboard) if isinstance(inline_keyboard.inline_keyboard, tuple) else inline_keyboard.inline_keyboard
                    
                    # Always add the three navigation buttons
                    keyboard_rows.append([
                        InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
                        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                    ])
                    inline_keyboard = InlineKeyboardMarkup(keyboard_rows)

                # Check if message content or keyboard changed to avoid "Message is not modified" error
                try:
                    current_text = query.message.text or ""
                    current_markup = query.message.reply_markup

                    # Only edit if content or keyboard changed
                    if response != current_text or (current_markup is None or str(inline_keyboard) != str(current_markup)):
                        await query.edit_message_text(response, reply_markup=inline_keyboard)
                    else:
                        # Message unchanged, just acknowledge
                        await query.answer("Already selected!")
                except Exception as e:
                    logger.warning(f"Could not edit message, sending new one: {e}")
                    await query.message.reply_text(response, reply_markup=inline_keyboard)
        else:
            # If no keyboard, check if preference collection is complete
            if "Preferences Saved Successfully" in response or ("preferences" in response.lower() and "saved" in response.lower()):
                # Collection complete, show clean success message with no keyboard
                try:
                    await query.edit_message_text(response, reply_markup=None)
                except Exception as e:
                    logger.warning(f"Could not edit message: {e}")
                    await query.message.reply_text(response)
            else:
                try:
                    await query.edit_message_text(response)
                except Exception as e:
                    logger.warning(f"Could not edit message: {e}")
                    await query.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling preference callback: {e}")
        await query.edit_message_text("❌ Error processing preference selection.")
    finally:
        await db.close()
