#!/usr/bin/env python3

import os
import sys
import asyncio
import aiohttp

def check_required_vars():
    required_vars = [
        'BOT_TOKEN',
        'ADMIN_ID',
        'SUPPORT_USERNAME'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var) and not hasattr(__import__('utils.constants', fromlist=[var]), var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        return False
    
    print("✅ All required variables present")
    return True

def validate_token_format(token):
    if not token:
        return False, "Token is empty"
    
    parts = token.split(':')
    if len(parts) != 2:
        return False, "Invalid token format (should be ID:TOKEN)"
    
    try:
        bot_id = int(parts[0])
        auth_token = parts[1]
        if bot_id <= 0:
            return False, "Invalid bot ID"
        if len(auth_token) < 35:
            return False, "Auth token too short"
        return True, "Token format valid"
    except ValueError:
        return False, "Bot ID should be numeric"

async def test_telegram_api(token):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{token}/getMe"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        bot_info = data['result']
                        return True, f"Bot: @{bot_info.get('username', 'unknown')} ({bot_info.get('first_name', 'Unknown')})"
                    else:
                        return False, f"API Error: {data.get('description', 'Unknown error')}"
                elif response.status == 401:
                    return False, "Unauthorized - Invalid token"
                else:
                    return False, f"HTTP {response.status}"
    except asyncio.TimeoutError:
        return False, "Request timeout"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

def check_dependencies():
    required_packages = [
        'aiogram',
        'yt_dlp',
        'aiohttp',
        'aiosqlite',
        'pyrogram'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    print("✅ All required packages installed")
    return True

def check_directories():
    dirs = ['temp', 'database', 'logs']
    for directory in dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Created directory: {directory}")
            except Exception as e:
                print(f"❌ Failed to create {directory}: {e}")
                return False
        else:
            print(f"✅ Directory exists: {directory}")
    return True

async def main():
    print("🔍 FlashSaver Bot Configuration Check\n")
    
    if not check_dependencies():
        return
    
    if not check_required_vars():
        return
    
    if not check_directories():
        return
    
    try:
        from utils.constants import BOT_TOKEN, ADMIN_ID
        
        print(f"\n📋 Configuration:")
        print(f"Admin ID: {ADMIN_ID}")
        
        is_valid, msg = validate_token_format(BOT_TOKEN)
        if is_valid:
            print(f"✅ Token format: {msg}")
            
            print("\n🔗 Testing Telegram API connection...")
            api_valid, api_msg = await test_telegram_api(BOT_TOKEN)
            if api_valid:
                print(f"✅ API Test: {api_msg}")
                print("\n🎉 Configuration is valid! You can start the bot.")
            else:
                print(f"❌ API Test failed: {api_msg}")
                print("\n🔧 Fix your BOT_TOKEN and try again.")
        else:
            print(f"❌ Token validation: {msg}")
            print("\n🔧 Get a valid token from @BotFather")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure utils/constants.py exists with proper configuration")

if __name__ == '__main__':
    asyncio.run(main())