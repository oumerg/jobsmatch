#!/usr/bin/env python3
"""
Fix referral codes for existing users
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def generate_referral_codes():
    conn = await asyncpg.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'jobbot'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres')
    )
    
    try:
        # Get all users without referral codes
        users = await conn.fetch('SELECT user_id FROM users WHERE referral_code IS NULL')
        print(f'Generating referral codes for {len(users)} users...')
        
        for user in users:
            user_id = user[0]
            # Generate deterministic referral code
            code = 'REF' + str(user_id).zfill(12)
            
            # Update the user
            await conn.execute('UPDATE users SET referral_code = $1 WHERE user_id = $2', code, user_id)
            print(f'Generated referral code {code} for user {user_id}')
            
        print('✅ All referral codes generated successfully!')
        
        # Verify the codes were saved
        updated_users = await conn.fetch('SELECT user_id, referral_code FROM users')
        print('\nCurrent users with referral codes:')
        for user in updated_users:
            print(f'  User {user[0]}: {user[1]}')
            
    except Exception as e:
        print(f'Error: {e}')
        
    await conn.close()

if __name__ == '__main__':
    asyncio.run(generate_referral_codes())
