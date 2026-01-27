"""
Job Types Management
Handles job types and related functionality
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class JobTypesManager:
    """Manages job types"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        # Job types (Ethiopian context)
        self.job_types = [
            'Full Time', 'Part Time', 'Remote', 'Freelance', 'Contract', 'Internship'
        ]
        self.db = db_manager  # Store database connection
        
        # Job types mapping
        self.job_types_mapping = {
            'full time': 'full_time',
            'full_time': 'full_time',
            'fulltime': 'full_time',
            'part time': 'part_time', 
            'part_time': 'part_time',
            'parttime': 'part_time',
            'remote': 'remote',
            'hybrid': 'hybrid',
            'contract': 'contract',
            'internship': 'internship'
        }
        
        self.job_types_display = {
            'full_time': '💼 Full Time',
            'part_time': '⏰ Part Time',
            'remote': '🏠 Remote',
            'hybrid': '🏠 Hybrid',
            'contract': '🤝 Contract',
            'internship': '🎓 Internship'
        }
    
    
    def get_job_types_keyboard(self, selected_types: list = None):
        """Generate inline keyboard for job types"""
        if selected_types is None:
            selected_types = []
            
        keyboard = []
        
        # Add "All Job Types" options
        all_selected = len(selected_types) == len(self.job_types_display)
        all_text = "✅ All Job Types" if all_selected else "All Job Types"
        keyboard.append([InlineKeyboardButton(all_text, callback_data="jobtype_all")])
        
        # Create rows with 2 job types each
        job_type_items = list(self.job_types_display.items())
        for i in range(0, len(job_type_items), 2):
            row = []
            for key, display in job_type_items[i:i+2]:
                is_selected = key in selected_types
                
                # Get clean display name
                clean_display = display.replace("💼 ", "").replace("⏰ ", "").replace("🏠 ", "").replace("🤝 ", "").replace("🎓 ", "")
                
                # Format with checkmark or bullet
                if is_selected:
                    row_text = f"✅ {clean_display}"
                else:
                    # Get icon if possible
                    icon = display.split(" ")[0] if " " in display else ""
                    row_text = f"{icon} {clean_display}" if icon else f"• {clean_display}"
                
                row.append(InlineKeyboardButton(row_text, callback_data=f"jobtype_{key}"))
            if row:
                keyboard.append(row)
        
        # Add Done button if there are selections
        if selected_types:
            keyboard.append([InlineKeyboardButton("✅ Done / Continue", callback_data="jobtype_done")])
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_job_types_message(self):
        """Format job types selection message"""
        return "⏰ *Select Your Preferred Job Types:*\n\n🔹 Choose from the options below:"
    
    def get_job_type_mapping(self) -> dict:
        """Get job type mapping"""
        return self.job_types_mapping
    
    def get_job_type_display(self, job_type: str) -> str:
        """Get display name for job type"""
        return self.job_types_display.get(job_type, job_type.title())
    
    def map_job_type(self, job_type: str) -> str:
        """Map display job type to internal value"""
        return self.job_types_mapping.get(job_type.lower().strip(), job_type.lower().strip())