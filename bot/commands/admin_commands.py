"""
Admin Commands
Handles admin-specific commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.payment_approval import PaymentApprovalSystem
from bot.config import Config

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in Config.ADMIN_IDS

async def admin_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin menu with available commands"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    keyboard = [
        [InlineKeyboardButton("💰 View Pending Payments", callback_data="admin_payments")],
        [InlineKeyboardButton("📺 Manage Channels", callback_data="admin_channels")],
        [InlineKeyboardButton("👥 Manage Groups", callback_data="admin_groups")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="admin_add_channel")],
        [InlineKeyboardButton("➕ Add Group", callback_data="admin_add_group")],
        [InlineKeyboardButton("📊 View Statistics", callback_data="admin_stats")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛠️ *Admin Panel*\n\nChoose an action:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view all channels"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        channels = await db.get_active_channels()
        
        if not channels:
            await update.message.reply_text("📺 No channels found in database.")
            return
        
        # Format channels list
        channels_text = f"📺 *Monitored Channels ({len(channels)}):*\n\n"
        
        for channel in channels:
            status = "✅ Active" if channel.get('is_active', True) else "❌ Inactive"
            channels_text += (
                f"🔗 *Username:* {channel['channel_username']}\n"
                f"📝 *Title:* {channel.get('channel_title', 'No title')}\n"
                f"📋 *Type:* {channel.get('channel_type', 'channel')}\n"
                f"🟢 *Status:* {status}\n\n"
            )
        
        await update.message.reply_text(channels_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin channels command: {e}")
        await update.message.reply_text("❌ Error loading channels.")
    finally:
        await db.close()

async def admin_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view all groups"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        groups = await db.get_active_groups()
        
        if not groups:
            await update.message.reply_text("👥 No groups found in database.")
            return
        
        # Format groups list
        groups_text = f"👥 *Monitored Groups ({len(groups)}):*\n\n"
        
        for group in groups:
            status = "✅ Active" if group.get('is_active', True) else "❌ Inactive"
            groups_text += (
                f"🔗 *Username:* {group['group_username']}\n"
                f"📝 *Title:* {group.get('group_title', 'No title')}\n"
                f"📋 *Type:* {group.get('group_type', 'public')}\n"
                f"🟢 *Status:* {status}\n\n"
            )
        
        await update.message.reply_text(groups_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin groups command: {e}")
        await update.message.reply_text("❌ Error loading groups.")
    finally:
        await db.close()

async def admin_add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to add a new channel"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    # Check if channel username was provided
    if not context.args:
        await update.message.reply_text(
            "📺 *Add New Channel*\n\n"
            "Usage: `/addchannel @username [title] [type] [notes]`\n\n"
            "Example: `/addchannel @newjobs \"New Job Channel\" channel \"IT jobs only\"`\n\n"
            "*Parameters:*\n"
            "• `username` - Channel username (with @)\n"
            "• `title` - Channel display name (optional)\n"
            "• `type` - channel/group/private (default: channel)\n"
            "• `notes` - Description (optional)",
            parse_mode='Markdown'
        )
        return
    
    try:
        username = context.args[0]
        title = context.args[1] if len(context.args) > 1 else None
        channel_type = context.args[2] if len(context.args) > 2 else 'channel'
        notes = ' '.join(context.args[3:]) if len(context.args) > 3 else None
        
        # Extract Telegram ID using Telethon
        telegram_id = await extract_telegram_id(username)
        
        if telegram_id is None:
            await update.message.reply_text(
                f"❌ *Could not find channel*\n\n"
                f"Channel `{username}` not found or no access.\n"
                f"Please check:\n"
                f"• Username is correct\n"
                f"• Channel is public\n"
                f"• Bot has access to the channel",
                parse_mode='Markdown'
            )
            return
        
        db = DatabaseManager()
        await db.connect()
        
        try:
            success = await db.add_monitor_channel(username, title, channel_type, notes, telegram_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ *Channel Added Successfully!*\n\n"
                    f"🔗 *Username:* {username}\n"
                    f"📝 *Title:* {title or 'No title'}\n"
                    f"📋 *Type:* {channel_type}\n"
                    f"🆔 *Telegram ID:* {telegram_id}\n"
                    f"📝 *Notes:* {notes or 'No notes'}\n\n"
                    f"The channel will be monitored in the next scraper restart.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Failed to add channel to database. Please try again.")
                
        except Exception as db_error:
            logger.error(f"Database error adding channel {username}: {db_error}")
            await update.message.reply_text(
                f"❌ *Database Error*\n\n"
                f"Failed to add channel `{username}` to database.\n\n"
                f"🆔 *Telegram ID was extracted:* {telegram_id}\n\n"
                f"💡 *Possible database issues:*\n"
                f"• Database connection problem\n"
                f"• Constraint violation\n"
                f"• Invalid data format\n\n"
                f"Please check the logs and try again."
            )
        finally:
            await db.close()
        
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        await update.message.reply_text("❌ Error adding channel.")

async def admin_add_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to add a new group"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    # Check if group username was provided
    if not context.args:
        await update.message.reply_text(
            "👥 *Add New Group*\n\n"
            "Usage: `/addgroup @username [title] [type] [notes]`\n\n"
            "Example: `/addgroup @jobgroup \"Job Discussion Group\" public \"Job discussions\"`\n\n"
            "*Parameters:*\n"
            "• `username` - Group username (with @)\n"
            "• `title` - Group display name (optional)\n"
            "• `type` - public/private/supergroup (default: public)\n"
            "• `notes` - Description (optional)",
            parse_mode='Markdown'
        )
        return
    
    try:
        username = context.args[0]
        title = context.args[1] if len(context.args) > 1 else None
        group_type = context.args[2] if len(context.args) > 2 else 'public'
        notes = ' '.join(context.args[3:]) if len(context.args) > 3 else None
        
        # Extract Telegram ID using Telethon
        telegram_id = await extract_telegram_id(username)
        
        if telegram_id is None:
            await update.message.reply_text(
                f"❌ *Could not find group*\n\n"
                f"Group `{username}` not found or no access.\n\n"
                f"🔍 *Possible reasons:*\n"
                f"• Group username is incorrect\n"
                f"• Group is private (need invite link)\n"
                f"• Bot doesn't have access to the group\n"
                f"• Group doesn't exist\n\n"
                f"💡 *Try:*\n"
                f"• Check the exact username\n"
                f"• Make sure the group is public\n"
                f"• Add bot as member if private",
                parse_mode='Markdown'
            )
            return
        
        db = DatabaseManager()
        await db.connect()
        
        try:
            success = await db.add_monitor_group(username, title, group_type, notes, telegram_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ *Group Added Successfully!*\n\n"
                    f"🔗 *Username:* {username}\n"
                    f"📝 *Title:* {title or 'No title'}\n"
                    f"📋 *Type:* {group_type}\n"
                    f"🆔 *Telegram ID:* {telegram_id}\n"
                    f"📝 *Notes:* {notes or 'No notes'}\n\n"
                    f"The group will be monitored in the next scraper restart.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Failed to add group to database. Please try again.")
                
        except Exception as db_error:
            logger.error(f"Database error adding group {username}: {db_error}")
            await update.message.reply_text(
                f"❌ *Database Error*\n\n"
                f"Failed to add group `{username}` to database.\n\n"
                f"🆔 *Telegram ID was extracted:* {telegram_id}\n\n"
                f"💡 *Possible database issues:*\n"
                f"• Database connection problem\n"
                f"• Constraint violation\n"
                f"• Invalid data format\n\n"
                f"Please check the logs and try again."
            )
        finally:
            await db.close()
        
    except Exception as e:
        logger.error(f"Error adding group: {e}")
        await update.message.reply_text("❌ Error adding group.")

async def extract_telegram_id(username: str) -> int:
    """Extract Telegram ID from username using Telethon"""
    try:
        import os
        from telethon import TelegramClient
        
        # Get Telethon credentials
        api_id = int(os.getenv('TELETHON_API_ID', '0'))
        api_hash = os.getenv('TELETHON_API_HASH', '')
        phone = os.getenv('TELETHON_PHONE', '')
        
        if not api_id or not api_hash or not phone:
            logger.error("Telethon credentials not configured!")
            return None
        
        # Create client
        client = TelegramClient('admin_extractor_session', api_id, api_hash)
        await client.start(phone)
        
        try:
            # Clean username
            clean_username = username.lstrip('@')
            logger.info(f"Attempting to extract Telegram ID for: {username} (clean: {clean_username})")
            
            # Try different methods to get entity
            entity = None
            
            # Method 1: Try with @ prefix
            try:
                logger.info(f"Method 1: Trying with @ prefix for @{clean_username}")
                entity = await client.get_entity(f"@{clean_username}")
                logger.info(f"Method 1 succeeded for {username}")
            except Exception as e:
                logger.info(f"Method 1 failed for {username}: {e}")
                pass
            
            # Method 2: Try without @ prefix
            if not entity:
                try:
                    logger.info(f"Method 2: Trying without @ prefix for {clean_username}")
                    entity = await client.get_entity(clean_username)
                    logger.info(f"Method 2 succeeded for {username}")
                except Exception as e:
                    logger.info(f"Method 2 failed for {username}: {e}")
                    pass
            
            # Method 3: Try as numeric ID
            if not entity and clean_username.isdigit():
                try:
                    logger.info(f"Method 3: Trying as numeric ID for {clean_username}")
                    entity = await client.get_entity(int(clean_username))
                    logger.info(f"Method 3 succeeded for {username}")
                except Exception as e:
                    logger.info(f"Method 3 failed for {username}: {e}")
                    pass
            
            # Method 4: Try with different variations
            if not entity:
                variations = [
                    clean_username,
                    f"@{clean_username}",
                    f"https://t.me/{clean_username}",
                    f"t.me/{clean_username}"
                ]
                
                for variation in variations:
                    try:
                        logger.info(f"Method 4: Trying variation: {variation}")
                        entity = await client.get_entity(variation)
                        logger.info(f"Method 4 succeeded with variation: {variation}")
                        break
                    except Exception as e:
                        logger.info(f"Method 4 failed for {variation}: {e}")
                        continue
            
            if entity:
                telegram_id = entity.id
                logger.info(f"✅ Extracted Telegram ID: {username} -> {telegram_id}")
                return telegram_id
            else:
                logger.error(f"❌ Could not find entity for: {username} (tried all methods)")
                return None
                
        finally:
            await client.disconnect()
            
    except Exception as e:
        logger.error(f"❌ Error extracting Telegram ID for {username}: {e}")
        return None

async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view statistics"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        # Get counts
        channels = await db.get_active_channels()
        groups = await db.get_active_groups()
        
        # Get user stats
        users_query = "SELECT COUNT(*) as total_users FROM users"
        users_result = await db.execute_query(users_query)
        total_users = users_result[0]['total_users'] if users_result else 0
        
        # Get active subscriptions
        subs_query = """
            SELECT COUNT(*) as active_subs 
            FROM subscriptions 
            WHERE status = 'active' AND end_date >= CURRENT_DATE
        """
        subs_result = await db.execute_query(subs_query)
        active_subs = subs_result[0]['active_subs'] if subs_result else 0
        
        stats_text = (
            f"📊 *Bot Statistics*\n\n"
            f"👥 *Total Users:* {total_users}\n"
            f"💳 *Active Subscriptions:* {active_subs}\n"
            f"📺 *Monitored Channels:* {len(channels)}\n"
            f"👥 *Monitored Groups:* {len(groups)}\n\n"
            f"🔗 *Sources Being Monitored:* {len(channels) + len(groups)}"
        )
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin stats command: {e}")
        await update.message.reply_text("❌ Error loading statistics.")
    finally:
        await db.close()

async def admin_payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view pending payments"""
    user = update.effective_user
    
    # Check if user is admin
    if not is_admin(user.id):
        await update.message.reply_text("❌ This command is only available to administrators.")
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        
        # Get pending payments
        query = """
            SELECT payment_id, user_id, payment_method, amount, reference, status, submitted_at
            FROM pending_payments
            WHERE status = 'pending'
            ORDER BY submitted_at DESC
        """
        
        payments = await db.connection.fetch(query)
        
        if not payments:
            await update.message.reply_text("✅ No pending payments to review.")
            return
        
        # Format payments list
        payments_text = "💰 *Pending Payments:*\n\n"
        
        for payment in payments:
            payments_text += (
                f"📋 *Payment ID:* {payment['payment_id']}\n"
                f"👤 *User ID:* {payment['user_id']}\n"
                f"💳 *Method:* {payment['payment_method']}\n"
                f"💰 *Amount:* {payment['amount']} Birr\n"
                f"📞 *Reference:* {payment['reference']}\n"
                f"📅 *Submitted:* {payment['submitted_at']}\n\n"
            )
        
        await update.message.reply_text(payments_text)
        
    except Exception as e:
        logger.error(f"Error in admin payments command: {e}")
        await update.message.reply_text("❌ Error loading pending payments.")
    finally:
        await db.close()
