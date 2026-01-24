"""
Experience Level Management
Handles simple year-based experience selection
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class ExperienceManager:
    """Manages experience levels with simple year-based selection"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        # Simple year-based experience levels
        self.experience_levels = {
            '0_years': {
                'display': '🎓 Entry Level (0 years)',
                'description': 'No experience required',
                'years': 0
            },
            '3_years': {
                'display': '� 3 Years Experience',
                'description': '3 years of professional experience',
                'years': 3
            },
            '5_years': {
                'display': '� 5 Years Experience',
                'description': '5 years of professional experience',
                'years': 5
            },
            'above_5_years': {
                'display': '🎯 Above 5 Years',
                'description': 'More than 5 years of experience',
                'years': 6
            }
        }
        self.db = db_manager  # Store database connection
    
    def get_experience_keyboard(self):
        """Generate inline keyboard for experience level selection"""
        keyboard = []
        
        # Create rows with 2 experience levels each
        experience_items = list(self.experience_levels.items())
        for i in range(0, len(experience_items), 2):
            row = []
            for key, display_info in experience_items[i:i+2]:
                row.append(InlineKeyboardButton(f"• {display_info['display']}", callback_data=f"experience_{key}"))
            if row:
                keyboard.append(row)
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_experience_requirements(self, level: str):
        """Get requirements for experience level"""
        return self.experience_levels.get(level, {})
    
    def format_experience_message(self):
        """Format experience selection message"""
        return (
            "*Select Your Experience Level*\n\n"
            "Choose from the options below:"
        )
    
    def validate_experience_match(self, candidate_years: int, required_level: str) -> bool:
        """Validate if candidate experience matches requirement"""
        level_info = self.experience_levels.get(required_level, {})
        if not level_info:
            return False
        
        required_years = level_info.get('years', 0)
        
        if required_level == 'above_5_years':
            return candidate_years > 5
        else:
            return candidate_years >= required_years

# Example usage functions
def create_experience_template(experience_level: str, years: int) -> dict:
    """Create a simple experience level template"""
    manager = ExperienceManager()
    
    return {
        'level': experience_level,
        'requirements': manager.get_experience_requirements(experience_level),
        'validation': manager.validate_experience_match(years, experience_level)
    }

if __name__ == "__main__":
    # Example usage
    manager = ExperienceManager()
    
    # Test experience requirements
    print("=== Experience Requirements ===")
    for level in manager.experience_levels.keys():
        req = manager.get_experience_requirements(level)
        print(f"{level}: {req.get('display')}")
    
    # Test experience validation
    print("\n=== Experience Validation ===")
    test_cases = [
        (0, '0_years', True),      # Meets requirement
        (1, '0_years', True),      # Meets requirement (0 years accepts any)
        (3, '3_years', True),      # Meets requirement
        (4, '3_years', True),      # Meets requirement (>= 3 years)
        (2, '3_years', False),     # Doesn't meet requirement
        (5, '5_years', True),      # Meets requirement
        (6, '5_years', True),      # Meets requirement (>= 5 years)
        (6, 'above_5_years', True), # Meets requirement
        (5, 'above_5_years', False),# Doesn't meet requirement
    ]
    
    for years, level, expected in test_cases:
        result = manager.validate_experience_match(years, level)
        status = "PASS" if result == expected else "FAIL"
        print(f"Years: {years}, Level: {level}, Expected: {expected}, Result: {status}")
