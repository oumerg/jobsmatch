"""
Education Level Management
Handles education level selection for job matching
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class EducationManager:
    """Manages education levels with simple selection"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        # Education levels (Ethiopian context)
        self.education_levels = [
            'High School', 'Diploma', 'Bachelor', 'Master', 'PhD', 'Other'
        ]
        self.db = db_manager  # Store database connection
        
        # Education levels mapping
        self.education_levels_map = {
            'no_formal': {
                'display': 'No Formal Education',
                'description': 'No formal educational requirements',
                'level': 'no_formal'
            },
            'high_school': {
                'display': 'High School',
                'description': 'High school completion or equivalent',
                'level': 'high_school'
            },
            'diploma': {
                'display': 'Diploma/Certificate',
                'description': 'Diploma or certificate program',
                'level': 'diploma'
            },
            'bachelor': {
                'display': 'Bachelor\'s Degree',
                'description': 'Undergraduate degree',
                'level': 'bachelor'
            },
            'master': {
                'display': 'Master\'s Degree',
                'description': 'Graduate degree',
                'level': 'master'
            },
            'phd': {
                'display': 'PhD/Doctorate',
                'description': 'Doctoral degree or highest academic qualification',
                'level': 'phd'
            }
        }
    
    def get_education_keyboard(self):
        """Generate inline keyboard for education level selection"""
        keyboard = []

        # Create rows with 2 education levels each
        education_items = list(self.education_levels_map.items())
        for i in range(0, len(education_items), 2):
            row = []
            for key, display_info in education_items[i:i+2]:
                row.append(InlineKeyboardButton(f"• {display_info['display']}", callback_data=f"education_{key}"))
            if row:
                keyboard.append(row)

        return InlineKeyboardMarkup(keyboard)
    
    def get_education_requirements(self, level: str):
        """Get requirements for education level"""
        return self.education_levels.get(level, {})
    
    def format_education_message(self):
        """Format education selection message"""
        return (
            "*Select Your Education Level*\n\n"
            "Choose your highest educational qualification:"
        )
    
    def validate_education_match(self, candidate_education: str, required_level: str) -> bool:
        """Validate if candidate education matches requirement"""
        education_hierarchy = {
            'no_formal': 0,
            'high_school': 1,
            'diploma': 2,
            'bachelor': 3,
            'master': 4,
            'phd': 5
        }
        
        candidate_level = education_hierarchy.get(candidate_education, 0)
        required_level_value = education_hierarchy.get(required_level, 0)
        
        return candidate_level >= required_level_value

# Example usage functions
def create_education_template(education_level: str) -> dict:
    """Create a simple education level template"""
    manager = EducationManager()
    
    return {
        'level': education_level,
        'requirements': manager.get_education_requirements(education_level)
    }

if __name__ == "__main__":
    # Example usage
    manager = EducationManager()
    
    # Test education requirements
    print("=== Education Requirements ===")
    for level in manager.education_levels.keys():
        req = manager.get_education_requirements(level)
        print(f"{level}: {req.get('display')}")
    
    # Test education validation
    print("\n=== Education Validation ===")
    test_cases = [
        ('high_school', 'high_school', True),      # Meets requirement
        ('bachelor', 'high_school', True),          # Exceeds requirement
        ('diploma', 'bachelor', False),             # Doesn't meet requirement
        ('master', 'bachelor', True),               # Exceeds requirement
        ('phd', 'master', True),                    # Exceeds requirement
    ]
    
    for education, required, expected in test_cases:
        result = manager.validate_education_match(education, required)
        status = "PASS" if result == expected else "FAIL"
        print(f"Education: {education}, Required: {required}, Expected: {expected}, Result: {status}")
