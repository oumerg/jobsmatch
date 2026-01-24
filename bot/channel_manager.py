"""
Channel and Group Management for Job Scraper
Admin commands to add/remove channels and groups from monitoring
"""

import logging
from typing import List, Dict, Any
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bot.database import DatabaseManager

logger = logging.getLogger(__name__)

class ChannelManager:
    """Manages channels and groups for job scraping"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def get_active_channels(self) -> List[Dict[str, Any]]:
        """Get all active channels for monitoring"""
        try:
            query = """
                SELECT channel_id, channel_username, channel_title, channel_type, 
                       is_active, added_at, last_checked, total_messages_scraped, total_jobs_found, notes
                FROM monitor_channels 
                WHERE is_active = TRUE 
                ORDER BY added_at DESC
            """
            
            rows = await self.db.connection.fetch(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []
    
    async def get_active_groups(self) -> List[Dict[str, Any]]:
        """Get all active groups for monitoring"""
        try:
            query = """
                SELECT group_id, group_username, group_title, group_type,
                       is_active, added_at, last_checked, total_messages_scraped, total_jobs_found, invite_link, notes
                FROM monitor_groups 
                WHERE is_active = TRUE 
                ORDER BY added_at DESC
            """
            
            rows = await self.db.connection.fetch(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []
    
    async def add_channel(self, username: str, title: str = None, channel_type: str = 'channel', notes: str = None) -> bool:
        """Add a new channel to monitor"""
        try:
            query = """
                INSERT INTO monitor_channels (channel_username, channel_title, channel_type, notes)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (channel_username) DO UPDATE SET
                is_active = TRUE,
                channel_title = EXCLUDED.channel_title,
                notes = EXCLUDED.notes
            """
            
            await self.db.connection.execute(query, username, title, channel_type, notes)
            logger.info(f"Added channel: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding channel {username}: {e}")
            return False
    
    async def add_group(self, username: str, title: str = None, group_type: str = 'public', notes: str = None) -> bool:
        """Add a new group to monitor"""
        try:
            query = """
                INSERT INTO monitor_groups (group_username, group_title, group_type, notes)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (group_username) DO UPDATE SET
                is_active = TRUE,
                group_title = EXCLUDED.group_title,
                notes = EXCLUDED.notes
            """
            
            await self.db.connection.execute(query, username, title, group_type, notes)
            logger.info(f"Added group: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding group {username}: {e}")
            return False
    
    async def remove_channel(self, username: str) -> bool:
        """Remove a channel from monitoring (set inactive)"""
        try:
            query = """
                UPDATE monitor_channels 
                SET is_active = FALSE 
                WHERE channel_username = $1
            """
            
            await self.db.connection.execute(query, username)
            logger.info(f"Removed channel: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing channel {username}: {e}")
            return False
    
    async def remove_group(self, username: str) -> bool:
        """Remove a group from monitoring (set inactive)"""
        try:
            query = """
                UPDATE monitor_groups 
                SET is_active = FALSE 
                WHERE group_username = $1
            """
            
            await self.db.connection.execute(query, username)
            logger.info(f"Removed group: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing group {username}: {e}")
            return False
    
    async def update_channel_stats(self, username: str, messages_scraped: int = 0, jobs_found: int = 0) -> bool:
        """Update channel statistics"""
        try:
            query = """
                UPDATE monitor_channels 
                SET last_checked = CURRENT_TIMESTAMP,
                    total_messages_scraped = total_messages_scraped + $1,
                    total_jobs_found = total_jobs_found + $2
                WHERE channel_username = $3
            """
            
            await self.db.connection.execute(query, messages_scraped, jobs_found, username)
            return True
            
        except Exception as e:
            logger.error(f"Error updating channel stats {username}: {e}")
            return False
    
    async def update_group_stats(self, username: str, messages_scraped: int = 0, jobs_found: int = 0) -> bool:
        """Update group statistics"""
        try:
            query = """
                UPDATE monitor_groups 
                SET last_checked = CURRENT_TIMESTAMP,
                    total_messages_scraped = total_messages_scraped + $1,
                    total_jobs_found = total_jobs_found + $2
                WHERE group_username = $3
            """
            
            await self.db.connection.execute(query, messages_scraped, jobs_found, username)
            return True
            
        except Exception as e:
            logger.error(f"Error updating group stats {username}: {e}")
            return False
    
    def format_channels_list(self, channels: List[Dict[str, Any]]) -> str:
        """Format channels list for display"""
        if not channels:
            return "📭 No active channels found."
        
        message = "📭 *Active Job Channels:*\n\n"
        
        for i, channel in enumerate(channels, 1):
            status_emoji = "✅" if channel['is_active'] else "❌"
            message += f"{i}. {status_emoji} *{channel['channel_title']}*\n"
            message += f"   📧 @{channel['channel_username']}\n"
            message += f"   📊 Messages: {channel['total_messages_scraped']}\n"
            message += f"   💼 Jobs found: {channel['total_jobs_found']}\n"
            if channel['notes']:
                message += f"   📝 {channel['notes']}\n"
            message += "\n"
        
        return message
    
    def format_groups_list(self, groups: List[Dict[str, Any]]) -> str:
        """Format groups list for display"""
        if not groups:
            return "👥 No active groups found."
        
        message = "👥 *Active Job Groups:*\n\n"
        
        for i, group in enumerate(groups, 1):
            status_emoji = "✅" if group['is_active'] else "❌"
            message += f"{i}. {status_emoji} *{group['group_title']}*\n"
            message += f"   👥 {group['group_username']}\n"
            message += f"   📊 Messages: {group['total_messages_scraped']}\n"
            message += f"   💼 Jobs found: {group['total_jobs_found']}\n"
            if group['invite_link']:
                message += f"   🔗 [Join Group]({group['invite_link']})\n"
            if group['notes']:
                message += f"   📝 {group['notes']}\n"
            message += "\n"
        
        return message

# Bot command handlers for channel management
async def list_channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all active channels"""
    user = update.effective_user
    
    # Check if user is admin (you should implement proper admin check)
    # For now, allow everyone to view
    
    manager = ChannelManager(DatabaseManager())
    await manager.db.connect()
    
    try:
        channels = await manager.get_active_channels()
        message = manager.format_channels_list(channels)
        
        keyboard = [
            ["➕ Add Channel", "➖ Remove Channel"],
            ["👥 List Groups", "⬅️ Back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        await update.message.reply_text("❌ Error loading channels.")
    finally:
        await manager.db.close()

async def list_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all active groups"""
    user = update.effective_user
    
    manager = ChannelManager(DatabaseManager())
    await manager.db.connect()
    
    try:
        groups = await manager.get_active_groups()
        message = manager.format_groups_list(groups)
        
        keyboard = [
            ["➕ Add Group", "➖ Remove Group"],
            ["📭 List Channels", "⬅️ Back"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error listing groups: {e}")
        await update.message.reply_text("❌ Error loading groups.")
    finally:
        await manager.db.close()

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new channel to monitor"""
    user = update.effective_user
    
    if context.args:
        channel_username = context.args[0].replace('@', '')
        title = ' '.join(context.args[1:]) if len(context.args) > 1 else None
        
        manager = ChannelManager(DatabaseManager())
        await manager.db.connect()
        
        try:
            success = await manager.add_channel(channel_username, title)
            if success:
                message = f"✅ *Channel Added Successfully!*\n\n"
                message += f"📧 @{channel_username}\n"
                if title:
                    message += f"📝 {title}\n"
                message += "\n🔍 The scraper will now monitor this channel for job postings."
                
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("❌ Failed to add channel. Please check the username and try again.")
                
        except Exception as e:
            logger.error(f"Error adding channel: {e}")
            await update.message.reply_text("❌ Error adding channel.")
        finally:
            await manager.db.close()
    else:
        message = (
            "➕ *Add New Channel*\n\n"
            "Usage: /add_channel @channel_name [optional title]\n\n"
            "Example: /add_channel @ethiojobs \"Ethiopian Jobs\"\n\n"
            "The channel will be monitored for job postings 24/7."
        )
        await update.message.reply_text(message)

async def add_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new group to monitor"""
    user = update.effective_user
    
    if context.args:
        group_username = context.args[0].replace('@', '')
        title = ' '.join(context.args[1:]) if len(context.args) > 1 else None
        
        manager = ChannelManager(DatabaseManager())
        await manager.db.connect()
        
        try:
            success = await manager.add_group(group_username, title)
            if success:
                message = f"✅ *Group Added Successfully!*\n\n"
                message += f"👥 {group_username}\n"
                if title:
                    message += f"📝 {title}\n"
                message += "\n🔍 The scraper will now monitor this group for job postings."
                
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("❌ Failed to add group. Please check the username and try again.")
                
        except Exception as e:
            logger.error(f"Error adding group: {e}")
            await update.message.reply_text("❌ Error adding group.")
        finally:
            await manager.db.close()
    else:
        message = (
            "➕ *Add New Group*\n\n"
            "Usage: /add_group @group_name [optional title]\n\n"
            "Example: /add_group @ethiopia_jobs \"Ethiopia Job Network\"\n\n"
            "The group will be monitored for job postings 24/7."
        )
        await update.message.reply_text(message)

async def remove_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a channel from monitoring"""
    user = update.effective_user
    
    if context.args:
        channel_username = context.args[0].replace('@', '')
        
        manager = ChannelManager(DatabaseManager())
        await manager.db.connect()
        
        try:
            success = await manager.remove_channel(channel_username)
            if success:
                message = f"➖ *Channel Removed*\n\n"
                message += f"📧 @{channel_username}\n"
                message += "\n🔍 The scraper will no longer monitor this channel."
                
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("❌ Failed to remove channel. Please check the username.")
                
        except Exception as e:
            logger.error(f"Error removing channel: {e}")
            await update.message.reply_text("❌ Error removing channel.")
        finally:
            await manager.db.close()
    else:
        message = (
            "➖ *Remove Channel*\n\n"
            "Usage: /remove_channel @channel_name\n\n"
            "Example: /remove_channel @ethiojobs\n\n"
            "The channel will be removed from monitoring."
        )
        await update.message.reply_text(message)

async def remove_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a group from monitoring"""
    user = update.effective_user
    
    if context.args:
        group_username = context.args[0].replace('@', '')
        
        manager = ChannelManager(DatabaseManager())
        await manager.db.connect()
        
        try:
            success = await manager.remove_group(group_username)
            if success:
                message = f"➖ *Group Removed*\n\n"
                message += f"👥 {group_username}\n"
                message += "\n🔍 The scraper will no longer monitor this group."
                
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("❌ Failed to remove group. Please check the username.")
                
        except Exception as e:
            logger.error(f"Error removing group: {e}")
            await update.message.reply_text("❌ Error removing group.")
        finally:
            await manager.db.close()
    else:
        message = (
            "➖ *Remove Group*\n\n"
            "Usage: /remove_group @group_name\n\n"
            "Example: /remove_group @ethiopia_jobs\n\n"
            "The group will be removed from monitoring."
        )
        await update.message.reply_text(message)

def register_channel_handlers(application: Application):
    """Register channel management command handlers"""
    application.add_handler(CommandHandler("channels", list_channels_command))
    application.add_handler(CommandHandler("groups", list_groups_command))
    application.add_handler(CommandHandler("add_channel", add_channel_command))
    application.add_handler(CommandHandler("add_group", add_group_command))
    application.add_handler(CommandHandler("remove_channel", remove_channel_command))
    application.add_handler(CommandHandler("remove_group", remove_group_command))
