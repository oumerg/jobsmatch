"""
Callback Handlers
Handles inline keyboard button presses
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.payment_approval import PaymentApprovalSystem

logger = logging.getLogger(__name__)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses"""
    query = update.callback_query
    try:
        await query.answer()  # Acknowledge the button press
    except Exception as e:
        logger.warning(f"Failed to answer callback query: {e}")
    
    callback_data = query.data
    user = update.effective_user
    
    logger.info(f"Callback query from user {user.id}: {callback_data}")
    
    # Handle registration callbacks
    if callback_data.startswith("reg_"):
        from bot.registration_flow import RegistrationFlow
        
        reg_flow = RegistrationFlow(DatabaseManager())
        await reg_flow.db.connect()
        
        try:
            # Extract registration step and value from callback
            parts = callback_data.split("_", 2)  # reg_industry_technology -> ['reg', 'industry', 'technology']
            if len(parts) >= 3:
                step_type = parts[1]  # industry, location, education, etc.
                value = parts[2]  # technology, addis, etc.
                
                # Map callback value to display text
                value_mapping = {
                    'industry': {
                        'technology': 'Technology / IT',
                        'finance': 'Banking / Finance',
                        'healthcare': 'Healthcare',
                        'education': 'Education',
                        'manufacturing': 'Manufacturing',
                        'retail': 'Retail / Sales',
                        'marketing': 'Marketing / Media',
                        'government': 'Government',
                        'construction': 'Construction',
                        'transportation': 'Transportation',
                        'agriculture': 'Agriculture',
                        'hospitality': 'Hospitality',
                        'legal': 'Legal',
                        'research': 'Research',
                        'hr': 'HR / Recruitment',
                        'consulting': 'Consulting',
                        'creative': 'Creative / Design',
                        'other': 'Other'
                    },
                    'location': {
                        'addis': 'Addis Ababa',
                        'adama': 'Adama / Nazret',
                        'dire': 'Dire Dawa',
                        'mekelle': 'Mekelle',
                        'bahir': 'Bahir Dar',
                        'hawassa': 'Hawassa',
                        'jimma': 'Jimma',
                        'gondar': 'Gondar',
                        'other': 'Other Ethiopia',
                        'remote': 'Remote'
                    },
                    'education': {
                        'highschool': 'High School',
                        'diploma': 'Diploma',
                        'bachelor': 'Bachelor\'s Degree',
                        'master': 'Master\'s Degree',
                        'phd': 'PhD / Doctorate',
                        'other': 'Other / Professional'
                    },
                    'experience': {
                        'student': 'Student / Intern',
                        'entry': 'Entry Level (0-2 years)',
                        'junior': 'Junior (2-5 years)',
                        'mid': 'Mid-Level (5-10 years)',
                        'senior': 'Senior (10+ years)',
                        'manager': 'Manager / Team Lead',
                        'director': 'Director / Executive',
                        'other': 'Other'
                    },
                    'salary': {
                        '5000': '< 5,000 Birr',
                        '10000': '5,000 - 10,000 Birr',
                        '15000': '10,000 - 15,000 Birr',
                        '25000': '15,000 - 25,000 Birr',
                        '40000': '25,000 - 40,000 Birr',
                        '60000': '40,000 - 60,000 Birr',
                        '60000plus': '> 60,000 Birr',
                        'negotiable': 'Negotiable'
                    }
                }
                
                display_text = value_mapping.get(step_type, {}).get(value, value)
                
                # Handle registration response
                if user.id in reg_flow.registration_states:
                    response = await reg_flow.handle_registration_response(user.id, display_text)
                    keyboard = reg_flow.get_keyboard_for_step(user.id)
                    
                    if keyboard:
                        # Add back button to inline keyboard - convert tuple to list first
                        if hasattr(keyboard, 'inline_keyboard'):
                            # Convert tuple to list if needed
                            keyboard_rows = list(keyboard.inline_keyboard) if isinstance(keyboard.inline_keyboard, tuple) else keyboard.inline_keyboard
                            keyboard_rows.append([
                                InlineKeyboardButton("Back to Main Menu", callback_data="back_to_main_menu")
                            ])
                            keyboard = InlineKeyboardMarkup(keyboard_rows)
                        await query.edit_message_text(response, reply_markup=keyboard)
                    else:
                        await query.edit_message_text(response)
                    
                    # If registration is complete, show main menu
                    if "registration complete" in response.lower():
                        from bot.utils.menu_utils import show_main_menu
                        await show_main_menu(update, user)
        except Exception as e:
            logger.error(f"Error handling registration callback: {e}")
            await query.edit_message_text("Error processing your selection. Please try again.")
        finally:
            await reg_flow.db.close()
        return
    
    # Handle subscription callbacks
    if callback_data.startswith("sub_"):
        from bot.commands.subscription_commands import (
            status_command, subscribe_command, cancel_subscription_command
        )
        from bot.utils.menu_utils import show_main_menu
        
        if callback_data == "sub_status":
            await status_command(update, context)
        elif callback_data == "sub_subscribe" or callback_data == "sub_upgrade":
            await subscribe_command(update, context)
        elif callback_data == "sub_cancel":
            await cancel_subscription_command(update, context)
        return
    
    # Handle payment method callbacks
    if callback_data.startswith("payment_method_"):
        from bot.handlers.subscription_handlers import subscription_managers
        
        method_key = callback_data.replace("payment_method_", "")
        method_display = {
            'telebirr': 'Telebirr',
            'cbebirr': 'CBE Birr',
            'hello_cash': 'Hello Cash',
            'manual': 'Manual Payment'
        }
        
        if user.id in subscription_managers:
            sub_manager = subscription_managers[user.id]
            result = await sub_manager.process_payment_method(user.id, method_display.get(method_key, method_key))
            
            if result['success']:
                await query.edit_message_text(result['message'])
            else:
                await query.edit_message_text(result['message'])
        return
    
    if callback_data == "payment_cancel":
        from bot.handlers.subscription_handlers import handle_subscription_cancellation
        await handle_subscription_cancellation(update, user)
        return
    
    # Handle job application callbacks
    if callback_data.startswith("apply_job_"):
        job_num = callback_data.replace("apply_job_", "")
        from bot.handlers.job_handlers import handle_job_application
        await handle_job_application(update, user, job_num)
        return
    
    # Handle preference callbacks
    if callback_data.startswith(("category_", "location_", "jobtype_", "salary_", "education_", "experience_", "back_to_previous", "back_to_main_menu", "cancel")):
        from .preference_handlers import handle_preference_callback
        await handle_preference_callback(update, context, callback_data)
        return
    
    # Handle payment approval callbacks
    if callback_data.startswith(("approve_", "reject_", "verify_")):
        from .subscription_handlers import handle_payment_approval
        parts = callback_data.split("_")
        action = parts[0]
        payment_id = int(parts[1])
        
        await handle_payment_approval(update, user, payment_id, action, context)
        return
    
    # Handle referral callbacks
    if callback_data in ["share_referral", "earnings_history", "withdraw_earnings", "top_referrers"]:
        from bot.commands.referral_commands import (
            share_referral_callback,
            earnings_history_callback, 
            withdraw_earnings_callback,
            top_referrers_callback
        )
        
        if callback_data == "share_referral":
            await share_referral_callback(update, context)
        elif callback_data == "earnings_history":
            await earnings_history_callback(update, context)
        elif callback_data == "withdraw_earnings":
            await withdraw_earnings_callback(update, context)
        elif callback_data == "top_referrers":
            await top_referrers_callback(update, context)
        return
    
    # Handle main menu callbacks
    if callback_data == "view_profile":
        from bot.commands.user_commands import profile_command
        await profile_command(update, context)
        return
    elif callback_data == "update_preferences":
        from bot.commands.user_commands import preferences_command
        await preferences_command(update, context)
        return
    elif callback_data == "search_jobs":
        from bot.commands.user_commands import jobs_command
        await jobs_command(update, context)
        return
    elif callback_data == "manage_subscription":
        from bot.commands.subscription_commands import subscription_management_command
        await subscription_management_command(update, context)
        return
    elif callback_data == "contact_support":
        await query.edit_message_text(
            "*Contact Support*\n\n"
            "Need help? Reach out to us:\n\n"
            "Email: support@jobsmatch.bot\n"
            "Telegram: @JobsMatchSupport\n"
            "Website: www.jobsmatch.bot\n\n"
            "We'll respond within 24 hours!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back", callback_data="back_to_previous")],
                [InlineKeyboardButton("Main Menu", callback_data="back_to_main_menu")]
            ])
        )
        return
    elif callback_data == "help":
        await query.edit_message_text(
            "*Help & FAQ*\n\n"
            "*How to use the bot:*\n"
            "1. Set up your profile preferences\n"
            "2. Browse matching job listings\n"
            "3. Apply with one click\n"
            "4. Track your applications\n\n"
            "*Commands:*\n"
            "/start - Begin using the bot\n"
            "/profile - View your profile\n"
            "/preferences - Update job preferences\n"
            "/jobs - Browse available jobs\n"
            "/subscription - Manage your subscription\n"
            "/help - Show this help message\n\n"
            "*Tips:*\n"
            "• Keep your preferences updated for better matches\n"
            "• Check back daily for new job postings\n"
            "• Upgrade to Premium for unlimited applications\n\n"
            "Need more help? Contact support!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Contact Support", callback_data="contact_support")],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data="back_to_previous"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main_menu")
                ]
            ])
        )
        return
    
    # Handle navigation callbacks
    if callback_data == "back_to_categories":
        await query.edit_message_text(
            "*Select Job Categories:*\n\nChoose from the options below:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Technology", callback_data="category_technology"),
                InlineKeyboardButton("Finance", callback_data="category_finance")
            ]])
        )
    elif callback_data == "cancel":
        await query.edit_message_text("Operation cancelled.")
    elif callback_data == "search_jobs":
        await query.edit_message_text("*Job Search*\n\nThis feature is coming soon! Use /jobs to see available positions.")
