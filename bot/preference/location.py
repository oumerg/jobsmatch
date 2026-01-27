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
    
    
    def get_locations_keyboard(self, selected_locations: list = None):
        """Generate inline keyboard for locations"""
        if selected_locations is None:
            selected_locations = []
            
        keyboard = []
        
        # Add "All Locations" / "Any" toggle
        is_any_selected = 'Any Location' in selected_locations or 'any' in selected_locations
        any_text = "✅ Any Location" if is_any_selected else "Any Location"
        keyboard.append([InlineKeyboardButton(any_text, callback_data="location_any")])
        
        # Create rows with 2 locations each
        for i in range(0, len(self.locations), 2):
            row = []
            for location in self.locations[i:i+2]:
                is_selected = location in selected_locations
                display_text = f"✅ {location}" if is_selected else f"📍 {location}"
                row.append(InlineKeyboardButton(display_text, callback_data=f"location_{location}"))
            if row:
                keyboard.append(row)
        
        # Add Remote option
        is_remote_selected = 'Remote' in selected_locations or 'remote' in selected_locations
        remote_text = "✅ Remote/Work from Home" if is_remote_selected else "🏠 Remote/Work from Home"
        keyboard.append([
            InlineKeyboardButton(remote_text, callback_data="location_remote")
        ])
        
        # Add Done button if there are selections
        if selected_locations:
            keyboard.append([InlineKeyboardButton("✅ Done / Continue", callback_data="location_done")])
        
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