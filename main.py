import asyncio
import os
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from utils.i18n import i18n
from utils.constants import BOT_TOKEN, ADMIN_ID, EMOJI, SUPPORT_USERNAME
from utils.helpers import detect_platform, validate_url, format_file_size, get_progress_bar
from database.operations import init_db, add_user, get_user, add_download, update_download_status
from database.models import User, Download, BroadcastMessage
from core.downloader import DownloadManager
from core.router import FileRouter
from core.youtube_api import YouTubeAPI
from bot.keyboards.inline import (
    get_quality_keyboard, get_admin_keyboard, get_language_keyboard,
    get_back_keyboard, get_pagination_keyboard, get_broadcast_confirm_keyboard
)
import logging

LOGGING_FORMAT = '[%(asctime)s] %(levelname)s:%(name)s: %(message)s'
logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

download_manager = DownloadManager()
file_router = FileRouter(bot)
youtube_api = YouTubeAPI()

active_downloads: Dict[int, Dict] = {}
start_time = time.time()

class BroadcastStates(StatesGroup):
    waiting_text = State()
    waiting_media = State()
    waiting_button = State()
    confirm = State()

async def notify_admin_new_user(user: types.User):
    try:
        name = user.full_name or "Unknown"
        username = user.username or "No username"
        await bot.send_message(
            ADMIN_ID,
            i18n.get('user_new', 'uz', name=name, username=username)
        )
    except Exception as e:
        logger.error(f"Failed to notify admin about new user: {e}")

async def start_handler(message: Message):
    user = message.from_user
    
    new_user = User(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language=user.language_code if user.language_code in ['uz', 'ru'] else 'uz',
        join_date=datetime.now(),
        last_activity=datetime.now()
    )
    
    try:
        existing = await get_user(user.id)
        if not existing:
            await add_user(new_user)
            await notify_admin_new_user(user)
    except:
        await add_user(new_user)
        await notify_admin_new_user(user)
    
    lang = new_user.language
    greeting = i18n.get('start', lang)
    
    await message.answer(greeting, reply_markup=get_language_keyboard())

async def help_handler(message: Message):
    try:
        user_data = await get_user(message.from_user.id)
        lang = user_data.language
    except:
        lang = 'uz'
    
    help_text = i18n.get('help', lang, support=SUPPORT_USERNAME)
    await message.answer(help_text)

async def admin_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    admin_text = i18n.get('admin_panel', 'uz')
    await message.answer(admin_text, reply_markup=get_admin_keyboard('uz'))

async def url_handler(message: Message):
    url = message.text.strip()
    
    if not validate_url(url):
        await message.answer(i18n.get('error_invalid_url', 'uz'))
        return
    
    platform = detect_platform(url)
    if platform.value == "unknown":
        await message.answer(i18n.get('error_not_supported', 'uz'))
        return
    
    try:
        user_data = await get_user(message.from_user.id)
        lang = user_data.language
    except:
        lang = 'uz'
    
    processing_msg = await message.answer(i18n.get('processing', lang))
    
    try:
        video_id = youtube_api.extract_video_id(url)
        if video_id:
            info = await youtube_api.get_video_info(video_id)
            if info:
                video_info_text = i18n.get('video_info', lang, title=info['title'], channel=info['channel'],
                                          duration=info['duration'], views=info['views'], date=info['published'])
                thumbnail_url = info['thumbnails'].get('medium')
                if thumbnail_url:
                    await youtube_api.download_thumbnail(thumbnail_url, 'temp/thumbnail.jpg')
                    await message.answer_photo(photo=FSInputFile('temp/thumbnail.jpg'), caption=video_info_text,
                                                reply_markup=get_quality_keyboard(lang))
                else:
                    await processing_msg.edit_text(video_info_text, reply_markup=get_quality_keyboard(lang))
                
                active_downloads[message.from_user.id] = {
                    'url': url,
                    'platform': platform,
                    'title': info['title'],
                    'message_id': processing_msg.message_id
                }
            else:
                await processing_msg.edit_text(i18n.get('error_processing', lang))
                return
        else:
            await processing_msg.edit_text(i18n.get('error_invalid_url', lang))
            return
        
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        await processing_msg.edit_text(i18n.get('error_processing', lang))

async def settings_handler(message: Message):
    try:
        user_data = await get_user(message.from_user.id)
        lang = user_data.language
    except:
        lang = 'uz'
    
    await message.answer(i18n.get('language_select', lang), reply_markup=get_language_keyboard())

async def about_handler(message: Message):
    about_text = "FlashSaver Bot v2.0\n\nProfessional video downloader for YouTube and Instagram\n\nFeatures:\n• High-speed downloads\n• Multiple quality options\n• Audio extraction\n• Thumbnail previews\n• Multi-language support\n\nDeveloped with modern technologies for best user experience."
    await message.answer(about_text)

async def commands_handler(message: Message):
    try:
        user_data = await get_user(message.from_user.id)
        lang = user_data.language
    except:
        lang = 'uz'
    
    await message.answer(i18n.get('commands_list', lang))

async def quality_callback(callback: CallbackQuery):
    quality = callback.data.split(':')[1]
    user_id = callback.from_user.id
    
    if user_id not in active_downloads:
        await callback.answer("Session expired")
        return
    
    try:
        user_data = await get_user(user_id)
        lang = user_data.language
    except:
        lang = 'uz'
    
    download_data = active_downloads[user_id]
    
    await callback.message.edit_text(i18n.get('downloading', lang, progress=0))
    
    try:
        async def progress_callback(progress):
            try:
                if progress % 10 < 1:
                    await callback.message.edit_text(
                        f"{i18n.get('downloading', lang, progress=int(progress))}\n" +
                        get_progress_bar(progress)
                    )
            except:
                pass
        
        from utils.constants import Quality
        quality_map = {
            'best': Quality.BEST,
            '720p': Quality.HIGH,
            '480p': Quality.MEDIUM,
            '360p': Quality.LOW,
            'audio': Quality.AUDIO
        }
        
        file_path = await download_manager.download_video(
            download_data['url'],
            quality_map.get(quality, Quality.BEST),
            progress_callback
        )
        
        await callback.message.edit_text(i18n.get('uploading', lang))
        
        caption = f"{EMOJI['success']} {download_data['title']}"
        success = await file_router.send_file(
            user_id,
            file_path,
            caption
        )
        
        if success:
            await callback.message.edit_text(i18n.get('completed', lang))
        else:
            await callback.message.edit_text(i18n.get('error_processing', lang))
            
        del active_downloads[user_id]
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        await callback.message.edit_text(i18n.get('error_download_failed', lang))
        if user_id in active_downloads:
            del active_downloads[user_id]
    
    await callback.answer()

async def admin_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Access denied")
        return
    
    action = callback.data.split(':')[1]
    
    if action == 'stats':
        await show_stats(callback)
    elif action == 'health':
        await show_health(callback)
    elif action == 'broadcast':
        await start_broadcast_handler(callback)
    elif action == 'main':
        await show_admin_panel(callback)
    
    await callback.answer()

async def show_stats(callback: CallbackQuery):
    import aiosqlite
    
    async with aiosqlite.connect('database/flash_saver.db') as db:
        cursor = await db.execute('SELECT COUNT(*) FROM users')
        total_users = (await cursor.fetchone())[0]
        
        cursor = await db.execute('SELECT COUNT(*) FROM downloads')
        total_downloads = (await cursor.fetchone())[0]
        
        cursor = await db.execute('SELECT COUNT(*) FROM downloads WHERE status="completed"')
        successful = (await cursor.fetchone())[0]
        
        today = datetime.now().date()
        cursor = await db.execute('SELECT COUNT(*) FROM downloads WHERE date(created_at) = ?', (today,))
        today_downloads = (await cursor.fetchone())[0]
    
    stats_text = (
        i18n.get('stats_title', 'uz') +
        i18n.get('stats_users', 'uz', count=total_users) +
        i18n.get('stats_downloads', 'uz', count=total_downloads) +
        i18n.get('stats_success', 'uz', count=successful) +
        i18n.get('stats_today', 'uz', count=today_downloads)
    )
    
    await callback.message.edit_text(stats_text, reply_markup=get_back_keyboard('uz'))

async def show_health(callback: CallbackQuery):
    uptime = str(timedelta(seconds=int(time.time() - start_time)))
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('.')
    
    health_text = (
        i18n.get('health_title', 'uz') +
        i18n.get('health_uptime', 'uz', time=uptime) +
        i18n.get('health_memory', 'uz', memory=f"{memory.percent}%") +
        i18n.get('health_disk', 'uz', disk=f"{disk.percent}%") +
        i18n.get('health_downloads', 'uz', count=len(active_downloads))
    )
    
    await callback.message.edit_text(health_text, reply_markup=get_back_keyboard('uz'))

async def start_broadcast_handler(callback: CallbackQuery):
    await callback.message.edit_text(i18n.get('broadcast_start', 'uz'))

async def show_admin_panel(callback: CallbackQuery):
    admin_text = i18n.get('admin_panel', 'uz')
    await callback.message.edit_text(admin_text, reply_markup=get_admin_keyboard('uz'))

async def language_callback(callback: CallbackQuery):
    lang = callback.data.split(':')[1]
    user_id = callback.from_user.id
    
    import aiosqlite
    async with aiosqlite.connect('database/flash_saver.db') as db:
        await db.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
        await db.commit()
    
    await callback.message.edit_text(i18n.get('language_changed', lang))
    await callback.answer()

def register_handlers():
    dp.message.register(start_handler, F.text.startswith('/start'))
    dp.message.register(help_handler, F.text.startswith('/help'))
    dp.message.register(admin_handler, F.text.startswith('/admin'))
    dp.message.register(settings_handler, F.text.startswith('/settings'))
    dp.message.register(about_handler, F.text.startswith('/about'))
    dp.message.register(commands_handler, F.text.startswith('/commands'))
    dp.message.register(url_handler, F.content_type == ContentType.TEXT, ~F.text.startswith('/'))
    
    dp.callback_query.register(quality_callback, F.data.startswith('quality:'))
    dp.callback_query.register(admin_callback, F.data.startswith('admin:'))
    dp.callback_query.register(language_callback, F.data.startswith('lang:'))

async def on_startup(dp):
    from aiogram.types import BotCommand
    
    commands = [
        BotCommand(command="start", description="Start the bot and get welcome message"),
        BotCommand(command="help", description="Get detailed help and usage guide"),
        BotCommand(command="settings", description="Change language and preferences"),
        BotCommand(command="about", description="About FlashSaver bot"),
        BotCommand(command="commands", description="List all available commands"),
        BotCommand(command="admin", description="Admin panel (admin only)")
    ]
    
    await bot.set_my_commands(commands)
    
    await init_db()
    userbot_started = await file_router.start_userbot()
    if userbot_started:
        logger.info("FlashSaver Bot started with userbot support (2GB file limit)!")
    else:
        logger.info("FlashSaver Bot started with bot API only (20MB file limit)!")
    logger.info("Bot is ready to download from YouTube and Instagram!")

async def on_shutdown(dp):
    await file_router.stop_userbot()
    logger.info("Bot stopped!")

async def main():
    register_handlers()
    await on_startup(dp)
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown(dp)

if __name__ == '__main__':
    asyncio.run(main())
