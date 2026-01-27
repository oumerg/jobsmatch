"""
Job Categories Management
Handles job categories and related functionality
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.database import DatabaseManager
from typing import List
import logging

logger = logging.getLogger(__name__)

class JobCategoriesManager:
    """Manages job categories"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        # Job categories (Ethiopian context)
        self.job_categories = {
            'technology': [
                'Software Developer', 'IT Support', 'Network Engineer', 'Data Analyst', 
                'Web Developer', 'Mobile Developer', 'Database Administrator', 'System Administrator'
            ],
            'finance': [
                'Accountant', 'Financial Analyst', 'Bank Teller', 'Loan Officer', 
                'Investment Advisor', 'Insurance Agent', 'Tax Consultant'
            ],
            'healthcare': [
                'Doctor', 'Nurse', 'Pharmacist', 'Medical Lab Technician', 
                'Healthcare Administrator', 'Hospital Administrator', 'Physician Assistant'
            ],
            'education': [
                'Teacher', 'Lecturer', 'Academic Administrator', 'Librarian', 
                'Curriculum Developer', 'Education Consultant', 'School Principal'
            ],
            'sales_marketing': [
                'Sales Representative', 'Marketing Manager', 'Customer Service', 
                'Business Development', 'Brand Manager', 'Public Relations Officer'
            ],
            'engineering': [
                'Civil Engineer', 'Mechanical Engineer', 'Electrical Engineer', 
                'Construction Manager', 'Manufacturing Engineer', 'Quality Control Manager'
            ],
            'hospitality': [
                'Hotel Manager', 'Chef', 'Waiter/Waitress', 'Tour Guide', 
                'Hospitality Manager', 'Front Desk Staff', 'Housekeeping Staff'
            ],
            'government': [
                'Civil Servant', 'Administrative Officer', 'Policy Analyst', 
                'Public Relations Officer', 'Urban Planner', 'Social Worker'
            ],
            'other': [
                'Driver', 'Security Guard', 'Cleaner', 'General Labor',
                'ሹፌር', 'ደህንነት ጠባቂ', 'ጠረገጋ'
            ]
        }
        self.db = db_manager  # Store database connection

    
    
    def get_categories_keyboard(self, selected_categories: List[str] = None):
        """Generate inline keyboard for job categories"""
        if selected_categories is None:
            selected_categories = []
            
        keyboard = []

        # Create rows with 2 categories each
        category_items = list(self.job_categories.items())
        
        # Add "All Categories" option at the top
        all_selected = len(selected_categories) == len(category_items)
        all_text = "✅ All Categories" if all_selected else "All Categories"
        keyboard.append([InlineKeyboardButton(all_text, callback_data="category_all")])
        
        for i in range(0, len(category_items), 2):
            row = []
            for category, jobs in category_items[i:i+2]:
                # Add checkmark if selected
                is_selected = category in selected_categories
                display_text = f"✅ {category.title()}" if is_selected else category.title()
                
                # Check for display icons mapping if needed, simplified here
                icon_map = {
                    'technology': '💻', 'finance': '💰', 'healthcare': '🏥', 
                    'education': '🎓', 'sales_marketing': '📢', 'engineering': '⚙️',
                    'hospitality': '🏨', 'government': '🏛️', 'other': '📋'
                }
                
                # Use mapped icon if available
                icon = icon_map.get(category, '')
                if icon and not is_selected:
                    display_text = f"{icon} {display_text}"
                elif icon and is_selected:
                    display_text = f"✅ {display_text.replace('✅ ', '')}"
                
                row.append(InlineKeyboardButton(display_text, callback_data=f"category_{category}"))
            if row:
                keyboard.append(row)
        
        # Add Done button if there are selections
        if selected_categories:
            keyboard.append([InlineKeyboardButton("✅ Done / Continue", callback_data="category_done")])

        return InlineKeyboardMarkup(keyboard)
    
    def format_categories_message(self):
        """Format categories selection message"""
        return "*Select Job Categories:*\n\nChoose from the options below:"
    
    def get_category_jobs(self, category: str) -> List[str]:
        """Get jobs for a specific category"""
        return self.job_categories.get(category, [])