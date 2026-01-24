"""
Referral System
Handles referral code generation, tracking, and earnings management
"""

import logging
import random
import string
from typing import Optional, Dict, List, Tuple
from bot.database import DatabaseManager

logger = logging.getLogger(__name__)

class ReferralManager:
    """Manages referral system functionality"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager
    
    async def generate_referral_code(self, user_id: int) -> str:
        """Generate unique referral code for user"""
        try:
            # Generate deterministic code: REF + user_id (12 digits total)
            # This ensures the same user always gets the same code
            code = f"REF{str(user_id).zfill(12)}"
            
            # Check if code already exists in users table (should not happen with deterministic generation)
            if await self.referral_code_exists(code):
                # If by chance it exists, use user_id + 1000000 as fallback
                fallback_user_id = user_id + 1000000
                code = f"REF{str(fallback_user_id).zfill(12)}"
            
            # Save referral code to users table
            update_query = """
                UPDATE users 
                SET referral_code = $1 
                WHERE user_id = $2
            """
            await self.db.execute_query(update_query, (code, user_id))
            
            logger.info(f"Generated referral code {code} for user {user_id}")
            return code
            
        except Exception as e:
            logger.error(f"Error generating referral code for user {user_id}: {e}")
            return f"REF{str(user_id).zfill(12)}"  # Fallback code
    
    async def referral_code_exists(self, code: str) -> bool:
        """Check if referral code already exists in users table"""
        try:
            query = "SELECT 1 FROM users WHERE referral_code = $1"
            result = await self.db.execute_query(query, (code,))
            return len(result) > 0
        except Exception as e:
            logger.error(f"Error checking referral code existence: {e}")
            return False
    
    async def get_user_referral_code(self, user_id: int) -> Optional[str]:
        """Get existing referral code for user or generate new one"""
        try:
            # First check if user already has a referral code
            query = "SELECT referral_code FROM users WHERE user_id = $1"
            result = await self.db.execute_query(query, (user_id,))
            
            if result and result[0]['referral_code']:
                # User already has a code, return it
                return result[0]['referral_code']
            else:
                # Generate new code only if user doesn't have one
                return await self.generate_referral_code(user_id)
                
        except Exception as e:
            logger.error(f"Error getting referral code for user {user_id}: {e}")
            return None
    
    async def get_referral_link(self, user_id: int, bot_username: str = None) -> str:
        """Generate referral link for user"""
        referral_code = await self.get_user_referral_code(user_id)
        if not referral_code:
            return None

        # Get bot username from environment or use default
        import os
        bot_name = bot_username or os.getenv('BOT_USER_NAME', 'ethiopianjobbot')
        
        return f"https://t.me/{bot_name}?start={referral_code}"
    
    async def process_referral(self, referral_code: str, new_user_id: int) -> Tuple[bool, Optional[int]]:
        """Process referral when new user signs up with referral code"""
        try:
            # Get referrer ID from referral code in users table
            query = """
                SELECT user_id FROM users 
                WHERE referral_code = $1
            """
            result = await self.db.execute_query(query, (referral_code,))
            
            if not result:
                logger.warning(f"Invalid referral code: {referral_code}")
                return False, None
            
            referrer_id = result[0]['user_id']
            
            # Check if new user was already referred
            check_query = "SELECT 1 FROM users WHERE referred_by = $1"
            existing_referral = await self.db.execute_query(check_query, (new_user_id,))
            
            if existing_referral:
                logger.info(f"User {new_user_id} was already referred")
                return False, None
            
            # Don't allow self-referral
            if referrer_id == new_user_id:
                logger.warning(f"User {new_user_id} tried to refer themselves")
                return False, None
            
            # Update referrer's earnings and balance in users table
            update_query = """
                UPDATE users 
                SET 
                    total_earnings = COALESCE(total_earnings, 0) + $1,
                    available_balance = COALESCE(available_balance, 0) + $2
                WHERE user_id = $3
            """
            await self.db.execute_query(update_query, (1.00, 1.00, referrer_id))
            
            # Update referred_by field for new user
            referred_by_query = """
                UPDATE users 
                SET referred_by = $1 
                WHERE user_id = $2
            """
            await self.db.execute_query(referred_by_query, (referrer_id, new_user_id))
            
            # Update referral_data JSON for referrer
            referrer_update_query = """
                UPDATE users 
                SET referral_data = jsonb_set(
                    COALESCE(referral_data, '{}'),
                    'referrals',
                    COALESCE(jsonb_extract(referral_data, 'referrals', '[]') || 
                    jsonb_build_object(
                        'referred_id', $1,
                        'date', CURRENT_DATE::TEXT,
                        'earnings', $2
                    ),
                    true
                )
                WHERE user_id = $3
            """
            await self.db.execute_query(referrer_update_query, (new_user_id, 1.00, referrer_id))
                
            logger.info(f"Successfully processed referral: {referrer_id} -> {new_user_id}")
            return True, referrer_id
                
        except Exception as e:
            logger.error(f"Error processing referral: {e}")
            return False, None
    
    async def get_user_referral_stats(self, user_id: int) -> Dict:
        """Get user's referral statistics"""
        try:
            # Get user's current data from users table
            user_query = """
                SELECT total_earnings, available_balance, referral_code, referral_data
                FROM users
                WHERE user_id = $1
            """
            user_result = await self.db.execute_query(user_query, (user_id,))
            
            if not user_result:
                return {}
            
            user_data = user_result[0]
            
            # Get referral count from referral_data JSON
            referrals_count = 0
            if user_data.get('referral_data'):
                import json
                try:
                    referral_data = json.loads(user_data['referral_data']) if isinstance(user_data['referral_data'], str) else user_data['referral_data']
                    referrals_count = len(referral_data.get('referrals', []))
                except:
                    pass
            
            return {
                'referral_code': user_data['referral_code'],
                'total_earnings': float(user_data['total_earnings'] or 0),
                'available_balance': float(user_data['available_balance'] or 0),
                'total_referrals': referrals_count,
                'confirmed_referrals': referrals_count,
                'recent_referrals': []
            }
                
        except Exception as e:
            logger.error(f"Error getting referral stats for user {user_id}: {e}")
            return {}
    
    async def get_referral_earnings_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's referral earnings history from JSON data"""
        try:
            # Get user's referral data from users table
            user_query = """
                SELECT referral_data FROM users
                WHERE user_id = $1
            """
            user_result = await self.db.execute_query(user_query, (user_id,))
            
            if not user_result or not user_result[0].get('referral_data'):
                return []
            
            # Parse referral data from JSON
            import json
            referral_data = json.loads(user_result[0]['referral_data']) if isinstance(user_result[0]['referral_data'], str) else user_result[0]['referral_data']
            
            # Get all earnings from referral data
            all_earnings = []
            for referral in referral_data.get('referrals', []):
                all_earnings.append({
                    'amount': referral.get('earnings', 0),
                    'type': 'referral',
                    'status': 'available',
                    'description': f"Referral bonus for user {referral.get('referred_id', 'Unknown')}",
                    'created_at': referral.get('date', ''),
                    'referred_id': referral.get('referred_id')
                })
            
            # Sort by date and limit
            all_earnings.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return all_earnings[:limit]
            
        except Exception as e:
            logger.error(f"Error getting earnings history for user {user_id}: {e}")
            return []
    
    async def withdraw_earnings(self, user_id: int, amount: float) -> Tuple[bool, str]:
        """Process withdrawal of referral earnings"""
        try:
            # Check available balance from users table
            balance_query = """
                SELECT available_balance FROM users
                WHERE user_id = $1
            """
            result = await self.db.execute_query(balance_query, (user_id,))
            
            if not result:
                return False, "User not found"
            
            available_balance = float(result[0]['available_balance'] or 0)
            
            if available_balance < amount:
                return False, f"Insufficient balance. Available: {available_balance} ETB"
            
            # Process withdrawal in users table
            withdraw_query = """
                UPDATE users
                SET available_balance = available_balance - $1
                WHERE user_id = $2
                RETURNING available_balance
            """
            await self.db.execute_query(withdraw_query, (amount, user_id))
            
            # Update referral_data JSON to track withdrawal
            user_update_query = """
                UPDATE users 
                SET referral_data = jsonb_set(
                    COALESCE(referral_data, '{}'),
                    'withdrawals',
                    COALESCE(jsonb_extract(referral_data, 'withdrawals', '[]') || 
                    jsonb_build_object(
                        'amount', $1,
                        'date', CURRENT_DATE::TEXT,
                        'type', 'withdrawal'
                    ),
                    true
                )
                WHERE user_id = $2
            """
            await self.db.execute_query(user_update_query, (amount, user_id))
            
            logger.info(f"Processed withdrawal of {amount} ETB for user {user_id}")
            return True, f"Withdrawal of {amount} ETB processed successfully"
            
        except Exception as e:
            logger.error(f"Error processing withdrawal for user {user_id}: {e}")
            return False, "Error processing withdrawal. Please try again."
    
    async def get_top_referrers(self, limit: int = 10) -> List[Dict]:
        """Get top referrers leaderboard from users table"""
        try:
            query = """
                SELECT user_id, first_name, last_name,
                       total_earnings, referral_code
                FROM users
                WHERE total_earnings > 0
                ORDER BY total_earnings DESC
                LIMIT $1
            """
            result = await self.db.execute_query(query, (limit,))
            
            # Add referral count from JSON data
            for user in result:
                referral_count = 0
                if user.get('referral_data'):
                    import json
                    referral_data = json.loads(user['referral_data']) if isinstance(user['referral_data'], str) else user['referral_data']
                    referral_count = len(referral_data.get('referrals', []))
                user['referral_count'] = referral_count
            
            return result or []
            
        except Exception as e:
            logger.error(f"Error getting top referrers: {e}")
            return []
