"""
Job Handlers
Handles job applications and job-related functionality
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def handle_job_application(update: Update, user, job_num: str):
    """Handle job application from clickable button"""
    
    job_details = {
        "1": {"title": "Software Developer", "company": "Tech Ethiopia", "salary": "15,000-25,000 Birr", "location": "Addis Ababa"},
        "2": {"title": "Accountant", "company": "Finance Plus", "salary": "8,000-12,000 Birr", "location": "Adama"},
        "3": {"title": "Marketing Manager", "company": "Marketing Pro", "salary": "12,000-18,000 Birr", "location": "Remote"},
        "4": {"title": "Nurse", "company": "Medical Center", "salary": "10,000-15,000 Birr", "location": "Bahir Dar"}
    }
    
    if job_num in job_details:
        job = job_details[job_num]
        
        application_text = (
            f"📋 *Job Application*\n\n"
            f"🏢 *Position:* {job['title']}\n"
            f"🏛️ *Company:* {job['company']}\n"
            f"💰 *Salary:* {job['salary']}\n"
            f"📍 *Location:* {job['location']}\n\n"
            f"👤 *Applicant:* {user.first_name} {user.last_name or ''}\n"
            f"🆔 *User ID:* {user.id}\n\n"
            f"❓ *Confirm application?*"
        )
        
        keyboard = [
            ["✅ Confirm Application"],
            ["❌ Cancel", "⬅️ Back to Jobs"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(application_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text("❌ Job not found. Please try again.")

async def confirm_job_application(update: Update, user):
    """Confirm and submit job application"""
    
    confirmation_text = (
        "✅ *Application Submitted!*\n\n"
        "🎉 Your job application has been successfully submitted.\n\n"
        "📋 *Application Details:*\n"
        f"👤 *Name:* {user.first_name} {user.last_name or ''}\n"
        f"🆔 *User ID:* {user.id}\n"
        f"📅 *Date:* {update.message.date.strftime('%Y-%m-%d %H:%M')}\n\n"
        "📞 *Next Steps:*\n"
        "• Employers will review your application\n"
        "• You'll be contacted if selected\n"
        "• Check your profile for application status\n\n"
        "💼 *Good luck with your job search!* 🇪🇹"
    )
    
    keyboard = [
        ["📊 View Profile", "🔍 Search Jobs"],
        ["⬅️ Back to Main Menu"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
