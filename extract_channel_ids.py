#!/usr/bin/env python3
"""
Channel ID Extractor
Utility to extract exact Telegram channel IDs using Telethon
"""

import asyncio
import os
from telethon import TelegramClient
from bot.config import Config

async def extract_channel_ids():
    """Extract exact channel IDs from Telegram"""
    
    # Get Telethon credentials
    api_id = int(os.getenv('TELETHON_API_ID', '0'))
    api_hash = os.getenv('TELETHON_API_HASH', '')
    phone = os.getenv('TELETHON_PHONE', '')
    
    if not api_id or not api_hash or not phone:
        print("❌ Telethon credentials not configured!")
        print("Please set TELETHON_API_ID, TELETHON_API_HASH, and TELETHON_PHONE in your .env file")
        return
    
    # Create client
    client = TelegramClient('channel_extractor_session', api_id, api_hash)
    
    try:
        await client.start(phone)
        print("✅ Connected to Telegram")
        
        # Load channels from database instead of hardcoded list
        from bot.database import DatabaseManager
        db = DatabaseManager()
        await db.connect()
        
        channels_to_check = []
        
        # Get channels from database
        try:
            channels = await db.get_active_channels()
            for channel in channels:
                channels_to_check.append(channel['channel_username'])
        except Exception as e:
            print(f"⚠️ Error loading channels from database: {e}")
        
        # Get groups from database  
        try:
            groups = await db.get_active_groups()
            for group in groups:
                channels_to_check.append(group['group_username'])
        except Exception as e:
            print(f"⚠️ Error loading groups from database: {e}")
        
        await db.close()
        
        if not channels_to_check:
            print("⚠️ No channels or groups found in database")
            print("💡 Add channels/groups using admin commands first:")
            print("   /addchannel @username")
            print("   /addgroup @username")
            return
        
        print("\n🔍 Extracting Channel IDs...\n")
        
        for channel in channels_to_check:
            try:
                # Try different methods to get entity
                entity = None
                
                # Method 1: With @ prefix
                try:
                    entity = await client.get_entity(f"@{channel.lstrip('@')}")
                except:
                    pass
                
                # Method 2: Without @ prefix
                if not entity:
                    try:
                        entity = await client.get_entity(channel.lstrip('@'))
                    except:
                        pass
                
                # Method 3: As numeric ID
                if not entity and channel.isdigit():
                    try:
                        entity = await client.get_entity(int(channel))
                    except:
                        pass
                
                if entity:
                    print(f"✅ {channel}")
                    print(f"   ID: {entity.id}")
                    print(f"   Username: @{entity.username}" if entity.username else "   Username: None")
                    print(f"   Title: {entity.title}")
                    print(f"   Type: {type(entity).__name__}")
                    print(f"   Access Hash: {getattr(entity, 'access_hash', 'N/A')}")
                    print()
                else:
                    print(f"❌ {channel} - Not found or no access")
                    
            except Exception as e:
                print(f"❌ {channel} - Error: {e}")
        
        # Interactive mode
        print("\n🔧 Interactive Mode - Enter channel usernames to check:")
        print("💡 You can check any channel, even if not in database")
        print("Type 'quit' to exit\n")
        
        while True:
            channel_input = input("Enter channel username (with or without @): ").strip()
            
            if channel_input.lower() == 'quit':
                break
                
            if not channel_input:
                continue
                
            try:
                entity = None
                
                # Try with @ prefix
                try:
                    entity = await client.get_entity(f"@{channel_input.lstrip('@')}")
                except:
                    pass
                
                # Try without @ prefix
                if not entity:
                    try:
                        entity = await client.get_entity(channel_input.lstrip('@'))
                    except:
                        pass
                
                if entity:
                    print(f"✅ Found: {entity.title}")
                    print(f"   Database ID: {entity.id}")
                    print(f"   Username: @{entity.username}" if entity.username else "   Username: None")
                    print(f"   Type: {type(entity).__name__}")
                    print()
                else:
                    print(f"❌ Channel not found or no access")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()
        print("\n👋 Disconnected")

if __name__ == '__main__':
    asyncio.run(extract_channel_ids())
