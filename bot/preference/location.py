"""
Location Management
Handles job locations and related functionality
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class LocationManager:
    """Manages job locations"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        # Ethiopian locations
        self.locations = [
            'Addis Ababa',
            'Dire Dawa'
        ]
        self.db = db_manager  # Store database connection
    
    def get_locations_keyboard(self):
        """Generate inline keyboard for locations"""
        keyboard = []
        
        # Create rows with 2 locations each
        for i in range(0, len(self.locations), 2):
            row = []
            for location in self.locations[i:i+2]:
                row.append(InlineKeyboardButton(f" {location}", callback_data=f"location_{location}"))
            if row:
                keyboard.append(row)
        
        # Add special options
        keyboard.append([
            InlineKeyboardButton("Remote/Work from Home", callback_data="location_remote"),
            InlineKeyboardButton("Any Location", callback_data="location_any")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    def format_locations_message(self):
        """Format locations selection message"""
        return "*Select Your Preferred Locations:*\n\nChoose from Ethiopian cities or remote options:"
    
    def get_all_locations(self) -> list:
        """Get all available locations"""
        return self.ethiopian_locations.copy()
    
    def is_valid_location(self, location: str) -> bool:
        """Check if location is valid"""
        if location.lower() in ['remote', 'any']:
            return True
        return location in self.ethiopian_locations