"""
Salary Management
Handles salary preferences and related functionality
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class SalaryManager:
    """Manages salary preferences"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        # Salary ranges in Birr (Ethiopian context)
        self.salary_ranges = [
            ('10,000 Birr', '10000'), 
            ('15,000 Birr', '15000'),
            ('20,000 Birr', '20000'),
            ('25,000 Birr', '25000'),
            ('30,000 Birr', '30000'),
            ('Above 30,000 Birr', 'above_30000')
        ]
        self.db = db_manager  # Store database connection
    
    def get_salary_keyboard(self):
        """Generate inline keyboard for salary selection"""
        keyboard = []
        
        # Create rows of 2 buttons each
        for i in range(0, len(self.salary_ranges), 2):
            row = []
            for display, value in self.salary_ranges[i:i+2]:
                row.append(InlineKeyboardButton(f"{display}", callback_data=f"salary_{value}"))
            if row:
                keyboard.append(row)
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_salary_message(self):
        """Format salary selection message"""
        return "*Select Your Minimum Expected Salary:*\n\nChoose from the options below:"
    
    def get_salary_ranges(self) -> list:
        """Get all available salary ranges"""
        return self.salary_ranges.copy()
    
    def parse_salary_input(self, salary_text: str) -> int:
        """Parse salary input from user"""
        try:
            # Remove non-numeric characters and convert to int
            clean_salary = ''.join(filter(str.isdigit, salary_text))
            return int(clean_salary) if clean_salary else 0
        except (ValueError, TypeError):
            return 0
    
    def is_valid_salary(self, salary: int) -> bool:
        """Check if salary is valid"""
        return salary > 0 and salary <= 1000000  # Reasonable range for Ethiopian salaries
