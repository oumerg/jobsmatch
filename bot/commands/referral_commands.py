"""
Referral Commands
Handles referral system commands and functionality
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import DatabaseManager
from bot.referral_system import ReferralManager

logger = logging.getLogger(__name__)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /referral command to show referral info and link"""
    user = update.effective_user
    
    db = DatabaseManager()
    try:
        await db.connect()
        referral_manager = ReferralManager(db)
        
        # Get user's referral code and stats
        referral_code = await referral_manager.get_user_referral_code(user.id)
        stats = await referral_manager.get_user_referral_stats(user.id)
        
        if not referral_code:
            await update.message.reply_text("❌ Error generating referral code. Please try again.")
            return
        
        # Generate referral link
        referral_link = await referral_manager.get_referral_link(user.id)
        
        # Create referral message
        message = (
            f"🎁 *Your Referral Program*\n\n"
            f"🔗 *Your Referral Code:* `{referral_code}`\n"
            f"📱 *Referral Link:* {referral_link}\n\n"
            f"💰 *Earn 1 ETB per referral!*\n\n"
            f"📊 *Your Stats:*\n"
            f"• Total Referrals: {stats.get('total_referrals', 0)}\n"
            f"• Confirmed Referrals: {stats.get('confirmed_referrals', 0)}\n"
            f"• Total Earnings: {stats.get('total_earnings', 0):.2f} ETB\n"
            f"• Available Balance: {stats.get('available_balance', 0):.2f} ETB\n\n"
            f"📋 *How it works:*\n"
            f"1. Share your referral link with friends\n"
            f"2. They sign up using your link\n"
            f"3. You earn 1 ETB for each successful referral\n"
            f"4. Withdraw earnings anytime\n\n"
            f"🚀 *Start earning now!*"
        )
        
        # Create inline keyboard for sharing
        keyboard = [
            [InlineKeyboardButton("📤 Share Referral Link", callback_data="share_referral")],
            [InlineKeyboardButton("📊 View Earnings History", callback_data="earnings_history")],
            [InlineKeyboardButton("💸 Withdraw Earnings", callback_data="withdraw_earnings")],
            [InlineKeyboardButton("🏆 Top Referrers", callback_data="top_referrers")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in referral command: {e}")
        await update.message.reply_text("❌ Error loading referral information. Please try again.")
    finally:
        await db.close()

async def earnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /earnings command to show earnings history"""
    user = update.effective_user
    
    db = DatabaseManager()
    try:
        await db.connect()
        referral_manager = ReferralManager(db)
        
        # Get earnings history
        earnings = await referral_manager.get_referral_earnings_history(user.id)
        stats = await referral_manager.get_user_referral_stats(user.id)
        
        if not earnings:
            message = (
                f"💰 *Your Earnings*\n\n"
                f"• Total Earnings: {stats.get('total_earnings', 0):.2f} ETB\n"
                f"• Available Balance: {stats.get('available_balance', 0):.2f} ETB\n\n"
                f"📝 *No earnings yet*\n\n"
                f"Start referring friends to earn 1 ETB per referral!\n\n"
                f"Use /referral to get your referral link."
            )
        else:
            message = (
                f"💰 *Your Earnings*\n\n"
                f"• Total Earnings: {stats.get('total_earnings', 0):.2f} ETB\n"
                f"• Available Balance: {stats.get('available_balance', 0):.2f} ETB\n\n"
                f"📝 *Recent Transactions:*\n\n"
            )
            
            for earning in earnings[:10]:  # Show last 10 transactions
                amount = earning['amount']
                status = earning['status']
                description = earning['description'] or 'Referral bonus'
                date = earning['created_at'].strftime('%b %d, %Y')
                
                status_emoji = {
                    'available': '✅',
                    'withdrawn': '💸',
                    'pending': '⏳'
                }.get(status, '❓')
                
                message += f"{status_emoji} {amount:.2f} ETB - {description}\n"
                message += f"   📅 {date}\n\n"
            
            message += f"💸 *Want to withdraw?*\n"
            message += f"Use /withdraw <amount> or click the button in /referral"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in earnings command: {e}")
        await update.message.reply_text("❌ Error loading earnings. Please try again.")
    finally:
        await db.close()

async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /withdraw command"""
    user = update.effective_user
    
    # Check if amount is provided
    if not context.args or len(context.args) == 0:
        message = (
            f"💸 *Withdraw Earnings*\n\n"
            f"Usage: /withdraw <amount>\n\n"
            f"Example: /withdraw 10\n\n"
            f"Minimum withdrawal: 5 ETB\n"
            f"Maximum withdrawal: Your available balance\n\n"
            f"Use /earnings to check your balance."
        )
        await update.message.reply_text(message, parse_mode='Markdown')
        return
    
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please use a number like /withdraw 10")
        return
    
    if amount < 5:
        await update.message.reply_text("❌ Minimum withdrawal is 5 ETB")
        return
    
    db = DatabaseManager()
    try:
        await db.connect()
        referral_manager = ReferralManager(db)
        
        # Process withdrawal
        success, message = await referral_manager.withdraw_earnings(user.id, amount)
        
        if success:
            response = f"✅ *Withdrawal Successful!*\n\n{message}"
        else:
            response = f"❌ *Withdrawal Failed*\n\n{message}"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        await update.message.reply_text("❌ Error processing withdrawal. Please try again.")
    finally:
        await db.close()

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /leaderboard command to show top referrers"""
    db = DatabaseManager()
    try:
        await db.connect()
        referral_manager = ReferralManager(db)
        
        # Get top referrers
        top_referrers = await referral_manager.get_top_referrers(10)
        
        if not top_referrers:
            message = "🏆 *Referral Leaderboard*\n\nNo referrers yet. Be the first!"
        else:
            message = "🏆 *Referral Leaderboard*\n\n"
            
            for i, referrer in enumerate(top_referrers, 1):
                name = f"{referrer['first_name']} {referrer.get('last_name', '')}".strip()
                earnings = referrer['total_earnings']
                referrals = referrer['referral_count']
                
                medal = ""
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"{i}."
                
                message += f"{medal} {name}\n"
                message += f"   💰 {earnings:.2f} ETB | 👥 {referrals} referrals\n\n"
        
        message += f"\n🚀 *Start referring to join the leaderboard!*\n"
        message += f"Use /referral to get your referral link."
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error loading leaderboard: {e}")
        await update.message.reply_text("❌ Error loading leaderboard. Please try again.")
    finally:
        await db.close()

async def share_referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle share referral callback"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    db = DatabaseManager()
    try:
        await db.connect()
        referral_manager = ReferralManager(db)
        
        referral_link = await referral_manager.get_referral_link(user.id)
        referral_code = await referral_manager.get_user_referral_code(user.id)
        
        share_message = (
            f"🎁 *Join Ethiopian Job Bot!*\n\n"
            f"I've been using this amazing job bot and thought you'd like it too!\n\n"
            f"🔗 *Use my referral code:* `{referral_code}`\n"
            f"📱 *Or click this link:* {referral_link}\n\n"
            f"🤖 Find your dream job in Ethiopia! 🇪🇹"
        )
        
        await query.edit_message_text(
            f"📤 *Share this message:*\n\n{share_message}\n\n"
            f"💡 *Tip:* Copy and share this message with friends!",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in share referral callback: {e}")
        await query.edit_message_text("❌ Error generating share message. Please try again.")
    finally:
        await db.close()

async def earnings_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle earnings history callback"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Redirect to earnings command
    await earnings_command(update, context)

async def withdraw_earnings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdraw earnings callback"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    db = DatabaseManager()
    try:
        await db.connect()
        referral_manager = ReferralManager(db)
        stats = await referral_manager.get_user_referral_stats(user.id)
        available_balance = stats.get('available_balance', 0)
        
        if available_balance < 5:
            await query.edit_message_text(
                f"💸 *Withdraw Earnings*\n\n"
                f"❌ Insufficient balance\n\n"
                f"Available: {available_balance:.2f} ETB\n"
                f"Minimum withdrawal: 5 ETB\n\n"
                f"Start referring friends to earn more!"
            )
        else:
            await query.edit_message_text(
                f"💸 *Withdraw Earnings*\n\n"
                f"Available balance: {available_balance:.2f} ETB\n\n"
                f"To withdraw, use: /withdraw <amount>\n"
                f"Example: /withdraw {min(available_balance, 50):.0f}\n\n"
                f"Minimum: 5 ETB\n"
                f"Maximum: {available_balance:.2f} ETB"
            )
        
    except Exception as e:
        logger.error(f"Error in withdraw callback: {e}")
        await query.edit_message_text("❌ Error loading withdrawal info. Please try again.")
    finally:
        await db.close()

async def top_referrers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle top referrers callback"""
    query = update.callback_query
    await query.answer()
    
    # Redirect to leaderboard command
    await leaderboard_command(update, context)
