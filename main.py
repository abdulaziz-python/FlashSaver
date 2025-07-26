import asyncio
import os
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, FSInputFile, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.enums import ParseMode, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramUnauthorizedError, TelegramBadRequest

from utils.i18n import i18n
from utils.constants import BOT_TOKEN, ADMIN_ID, SUPPORT_USERNAME
from utils.helpers import detect_platform, validate_url, format_file_size, get_progress_bar, format_duration
from database.operations import init_db, add_user, get_user, add_download, update_download_status
from database.models import User, Download, BroadcastMessage
from core.downloader import DownloadManager
from core.router import FileRouter
from core.youtube_api import YouTubeAPI
from bot.keyboards.inline import (
    get_quality_keyboard, get_admin_keyboard, get_language_keyboard,
    get_back_keyboard, get_pagination_keyboard, get_broadcast_confirm_keyboard
)
from bot.keyboards.reply import get_main_menu_keyboard, get_admin_menu_keyboard, remove_keyboard
import logging

LOGGING_FORMAT = '[%(asctime)s] %(levelname)s:%(name)s: %(message)s'
logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_bot_token(token: str) -> bool:
    if not token:
        return False
    parts = token.split(':')
    if len(parts) != 2:
        return False
    try:
        bot_id = int(parts[0])
        auth_token = parts[1]
        return len(auth_token) >= 35 and bot_id > 0
    except ValueError:
        return False

if not validate_bot_token(BOT_TOKEN):
    logger.error("Invalid bot token format. Check your BOT_TOKEN in constants.py")
    exit(1)

try:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
except Exception as e:
    logger.error(f"Failed to create bot instance: {e}")
    exit(1)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

download_manager = DownloadManager()
file_router = FileRouter(bot)
youtube_api = YouTubeAPI()

active_downloads: Dict[int, Dict] = {}
start_time = time.time()

class BroadcastStates(StatesGroup):
    waiting_media = State()
    waiting_text = State()
    waiting_button = State()
    confirm = State()

broadcast_data = {}

async def test_bot_token():
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot token valid: @{bot_info.username} ({bot_info.first_name})")
        return True
    except TelegramUnauthorizedError:
        logger.error("Bot token invalid/expired. Check BOT_TOKEN in constants.py")
        return False
    except Exception as e:
        logger.error(f"Error testing bot token: {e}")
        return False

async def notify_admin_new_user(user: types.User):
    try:
        name = user.full_name or "Unknown"
        username = user.username or "No username"
        await bot.send_message(ADMIN_ID, i18n.get('user_new', 'uz', name=name, username=username))
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

    await message.answer(greeting, reply_markup=get_main_menu_keyboard(lang))

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
    await message.answer(admin_text, reply_markup=get_admin_menu_keyboard('uz'))

async def settings_handler(message: Message):
    try:
        user_data = await get_user(message.from_user.id)
        lang = user_data.language
    except:
        lang = 'uz'

    await message.answer(i18n.get('language_select', lang), reply_markup=get_language_keyboard())

async def about_handler(message: Message):
    about_text = """FlashSaver Bot v2.0

Professional video downloader for YouTube and Instagram

Features:
• High-speed downloads with progress tracking
• Multiple quality options (up to 4K)
• Audio extraction in MP3 format
• Thumbnail previews before download
• Multi-language support (Uzbek/Russian)
• Smart compression preserving quality
• Support for files up to 2GB

Built with modern async architecture for optimal performance.
Developed using aiogram 3.x, pyrogram, and yt-dlp.

Contact: @yordam_42"""

    await message.answer(about_text)

async def commands_handler(message: Message):
    try:
        user_data = await get_user(message.from_user.id)
        lang = user_data.language
    except:
        lang = 'uz'

    await message.answer(i18n.get('commands_list', lang))

async def url_handler(message: Message):
    url = message.text.strip()

    if not validate_url(url):
        try:
            user_data = await get_user(message.from_user.id)
            lang = user_data.language
        except:
            lang = 'uz'
        await message.answer(i18n.get('error_invalid_url', lang))
        return

    platform = detect_platform(url)
    if platform.value == "unknown":
        try:
            user_data = await get_user(message.from_user.id)
            lang = user_data.language
        except:
            lang = 'uz'
        await message.answer(i18n.get('error_not_supported', lang))
        return

    try:
        user_data = await get_user(message.from_user.id)
        lang = user_data.language
    except:
        lang = 'uz'

    processing_msg = await message.answer(i18n.get('processing', lang), reply_markup=remove_keyboard())

    try:
        if platform.value == "youtube":
            video_id = youtube_api.extract_video_id(url)
            api_info = None

            if video_id and youtube_api.youtube:
                try:
                    api_info = await youtube_api.get_video_info(video_id)
                except Exception as e:
                    logger.warning(f"YouTube API failed, using yt-dlp: {e}")

            if api_info:
                duration_formatted = format_duration(api_info['duration'])
                views_formatted = youtube_api.format_number(api_info['views'])

                video_info_text = i18n.get(
                    'video_info', lang,
                    title=api_info['title'][:100] + '...' if len(api_info['title']) > 100 else api_info['title'],
                    channel=api_info['channel'],
                    duration=duration_formatted,
                    views=views_formatted,
                    date=api_info['published']
                )

                thumbnail_url = api_info['thumbnails'].get('medium') or api_info['thumbnails'].get('high')
                if thumbnail_url:
                    thumbnail_path = f"temp/thumb_{message.from_user.id}.jpg"
                    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

                    if await youtube_api.download_thumbnail(thumbnail_url, thumbnail_path):
                        try:
                            await processing_msg.delete()
                            await message.answer_photo(
                                photo=FSInputFile(thumbnail_path),
                                caption=video_info_text,
                                reply_markup=get_quality_keyboard(lang)
                            )
                            try:
                                os.remove(thumbnail_path)
                            except:
                                pass
                        except Exception as e:
                            logger.warning(f"Failed to send photo: {e}")
                            await processing_msg.edit_text(video_info_text, reply_markup=get_quality_keyboard(lang))
                    else:
                        await processing_msg.edit_text(video_info_text, reply_markup=get_quality_keyboard(lang))
                else:
                    await processing_msg.edit_text(video_info_text, reply_markup=get_quality_keyboard(lang))

                active_downloads[message.from_user.id] = {
                    'url': url,
                    'platform': platform,
                    'title': api_info['title'],
                    'message_id': processing_msg.message_id
                }
                return
            else:
                logger.info("Using yt-dlp for YouTube video info")

        try:
            media_info = await download_manager.get_video_info(url)

            video_title = media_info.title[:100] + '...' if len(media_info.title) > 100 else media_info.title
            info_text = f"📹 {video_title}\n\n" + i18n.get('quality_select', lang)

            try:
                await processing_msg.edit_text(info_text, reply_markup=get_quality_keyboard(lang))
            except:
                try:
                    await processing_msg.delete()
                except:
                    pass
                processing_msg = await message.answer(info_text, reply_markup=get_quality_keyboard(lang))

            active_downloads[message.from_user.id] = {
                'url': url,
                'platform': platform,
                'title': media_info.title,
                'message_id': processing_msg.message_id
            }

        except Exception as e:
            logger.error(f"yt-dlp info extraction failed: {e}")
            error_msg = "Failed to extract video information. Please check the URL and try again."
            if "Private video" in str(e):
                error_msg = "This video is private or unavailable."
            elif "Video unavailable" in str(e):
                error_msg = "This video is not available in your region or has been removed."
            elif "age-gated" in str(e).lower():
                error_msg = "This video is age-restricted and cannot be downloaded."

            try:
                await processing_msg.edit_text(f"❌ {error_msg}")
            except:
                await message.answer(f"❌ {error_msg}")
            return

    except Exception as e:
        logger.error(f"Unexpected error processing URL {url}: {e}")
        try:
            await processing_msg.edit_text(i18n.get('error_processing', lang))
        except:
            await message.answer(i18n.get('error_processing', lang))

async def quality_callback(callback: CallbackQuery):
    quality = callback.data.split(':')[1]
    user_id = callback.from_user.id

    if user_id not in active_downloads:
        try:
            await callback.answer("Session expired. Please send the link again.", show_alert=True)
        except:
            pass
        return

    try:
        user_data = await get_user(user_id)
        lang = user_data.language
    except:
        lang = 'uz'

    download_data = active_downloads[user_id]

    try:
        await callback.answer()
    except:
        pass

    progress_msg = await callback.message.answer(i18n.get('downloading', lang, progress=0))

    try:
        download_start_time = time.time()
        last_update_time = 0

        async def progress_callback(progress):
            nonlocal last_update_time
            current_time = time.time()

            if current_time - last_update_time > 2 or int(progress) % 10 == 0:
                try:
                    await progress_msg.edit_text(
                        i18n.get('downloading', lang, progress=int(progress)) + "\n" +
                        get_progress_bar(progress)
                    )
                    last_update_time = current_time
                except Exception as e:
                    if "message is not modified" not in str(e).lower():
                        logger.debug(f"Progress update error: {e}")

        from utils.constants import Quality
        quality_map = {
            'best': Quality.BEST,
            '720p': Quality.HIGH,
            '480p': Quality.MEDIUM,
            '360p': Quality.LOW,
            'audio': Quality.AUDIO
        }

        logger.info(f"Starting download: {download_data['url']} with quality: {quality}")

        file_path = await download_manager.download_video(
            download_data['url'],
            quality_map.get(quality, Quality.BEST),
            progress_callback
        )

        download_time = time.time() - download_start_time
        logger.info(f"Download completed in {download_time:.2f} seconds")

        try:
            await progress_msg.edit_text(i18n.get('uploading', lang))
        except:
            try:
                await progress_msg.delete()
            except:
                pass
            progress_msg = await callback.message.answer(i18n.get('uploading', lang))

        try:
            bot_me = await bot.get_me()
            bot_username = bot_me.username or "FlashSaver"
        except:
            bot_username = "FlashSaver"

        title = download_data['title'][:80] + '...' if len(download_data['title']) > 80 else download_data['title']
        caption = f"📥 {title}\n\n🤖 @{bot_username}"

        if quality != 'best':
            caption += f" | {quality.upper()}"

        upload_start_time = time.time()
        success = await file_router.send_file(user_id, file_path, caption)
        upload_time = time.time() - upload_start_time

        if success:
            try:
                await progress_msg.edit_text(
                    i18n.get('completed', lang) +
                    f"\n⏱ Download: {download_time:.1f}s | Upload: {upload_time:.1f}s"
                )
            except:
                await callback.message.answer(i18n.get('completed', lang))
        else:
            try:
                await progress_msg.edit_text(i18n.get('error_processing', lang))
            except:
                await callback.message.answer(i18n.get('error_processing', lang))

        try:
            from database.operations import add_download
            from database.models import Download

            platform_value = download_data['platform']
            if hasattr(platform_value, 'value'):
                platform_str = platform_value.value
            elif hasattr(platform_value, 'name'):
                platform_str = platform_value.name.lower()
            else:
                platform_str = str(platform_value).lower()

            download_record = Download(
                user_id=user_id,
                url=download_data['url'],
                platform=platform_str,
                quality=quality,
                status="completed" if success else "failed",
                created_at=datetime.now()
            )
            await add_download(download_record)
        except Exception as e:
            logger.error(f"Failed to record download: {e}")
            logger.debug(f"Platform data: {download_data.get('platform')}, Type: {type(download_data.get('platform'))}")

        del active_downloads[user_id]

    except Exception as e:
        logger.error(f"Download error for {download_data['url']}: {e}")

        error_msg = i18n.get('error_download_failed', lang)
        if "HTTP Error 403" in str(e):
            error_msg = "❌ Access denied. The video might be private or region-blocked."
        elif "HTTP Error 404" in str(e):
            error_msg = "❌ Video not found. It might have been deleted."
        elif "This video is unavailable" in str(e):
            error_msg = "❌ Video is unavailable. It might be private or deleted."
        elif "age-gated" in str(e).lower():
            error_msg = "❌ Age-restricted video cannot be downloaded."
        elif "timeout" in str(e).lower():
            error_msg = "❌ Download timeout. Please try again."
        elif "No space left" in str(e):
            error_msg = "❌ Server storage full. Please try again later."

        try:
            await progress_msg.edit_text(error_msg)
        except:
            await callback.message.answer(error_msg)

        if user_id in active_downloads:
            del active_downloads[user_id]

async def reply_menu_handler(message: Message):
    text = message.text
    user_id = message.from_user.id

    try:
        user_data = await get_user(user_id)
        lang = user_data.language
    except:
        lang = 'uz'

    if "Statistics" in text and user_id == ADMIN_ID:
        await show_stats_inline(message)
    elif "Users" in text and user_id == ADMIN_ID:
        await show_users_inline(message)
    elif "Broadcast" in text and user_id == ADMIN_ID:
        await start_broadcast_process(message)
    elif "System Health" in text and user_id == ADMIN_ID:
        await show_health_inline(message)
    elif "Settings" in text:
        await settings_handler(message)
    elif "Help" in text:
        await help_handler(message)
    elif "Main Menu" in text:
        await message.answer("Main Menu", reply_markup=get_main_menu_keyboard(lang))

async def start_broadcast_process(message: Message, state: FSMContext = None):
    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        i18n.get('broadcast_step1', 'uz'),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="/skip"), types.KeyboardButton(text="❌ Cancel")]],
            resize_keyboard=True
        )
    )

    if state:
        await state.set_state(BroadcastStates.waiting_media)

async def broadcast_media_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text == "/skip":
        broadcast_data[ADMIN_ID] = {}
    elif message.text == "❌ Cancel":
        await state.clear()
        await message.answer("Broadcast cancelled", reply_markup=get_admin_menu_keyboard())
        return
    else:
        media_data = {}
        if message.photo:
            media_data = {'type': 'photo', 'file_id': message.photo[-1].file_id}
        elif message.video:
            media_data = {'type': 'video', 'file_id': message.video.file_id}
        elif message.animation:
            media_data = {'type': 'animation', 'file_id': message.animation.file_id}

        broadcast_data[ADMIN_ID] = {'media': media_data}

    await message.answer(i18n.get('broadcast_step2', 'uz'))
    await state.set_state(BroadcastStates.waiting_text)

async def broadcast_text_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text == "❌ Cancel":
        await state.clear()
        await message.answer("Broadcast cancelled", reply_markup=get_admin_menu_keyboard())
        return

    if ADMIN_ID not in broadcast_data:
        broadcast_data[ADMIN_ID] = {}

    broadcast_data[ADMIN_ID]['text'] = message.text

    await message.answer(i18n.get('broadcast_step3', 'uz'))
    await state.set_state(BroadcastStates.waiting_button)

async def broadcast_button_handler(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text == "/skip":
        broadcast_data[ADMIN_ID]['button'] = None
    elif message.text == "❌ Cancel":
        await state.clear()
        await message.answer("Broadcast cancelled", reply_markup=get_admin_menu_keyboard())
        return
    else:
        try:
            parts = message.text.split('|', 1)
            if len(parts) == 2:
                button_text, button_url = parts[0].strip(), parts[1].strip()
                broadcast_data[ADMIN_ID]['button'] = {'text': button_text, 'url': button_url}
            else:
                broadcast_data[ADMIN_ID]['button'] = None
        except:
            broadcast_data[ADMIN_ID]['button'] = None

    import aiosqlite
    async with aiosqlite.connect('database/flash_saver.db') as db:
        cursor = await db.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        user_count = (await cursor.fetchone())[0]

    confirm_text = i18n.get('broadcast_confirm', 'uz', count=user_count)
    await message.answer(confirm_text, reply_markup=get_broadcast_confirm_keyboard())
    await state.set_state(BroadcastStates.confirm)

async def broadcast_confirm_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return

    if callback.data == "broadcast:confirm":
        from admin.panel import AdminPanel
        admin_panel = AdminPanel(bot)

        message_data = broadcast_data.get(ADMIN_ID, {})
        result = await admin_panel.send_broadcast(message_data)

        await callback.message.edit_text(
            i18n.get('broadcast_sent', 'uz',
                    sent=result['sent'],
                    failed=result['failed'],
                    total=result['total']),
            reply_markup=None
        )

        await callback.message.answer("Broadcast completed", reply_markup=get_admin_menu_keyboard())

    await state.clear()
    if ADMIN_ID in broadcast_data:
        del broadcast_data[ADMIN_ID]

async def show_stats_inline(message: Message):
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

    await message.answer(stats_text)

async def show_health_inline(message: Message):
    uptime = str(timedelta(seconds=int(time.time() - start_time)))
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('.')

    health_text = (
        i18n.get('health_title', 'uz') +
        i18n.get('health_uptime', 'uz', time=uptime) +
        i18n.get('health_memory', 'uz', memory=f"{memory.percent:.1f}%") +
        i18n.get('health_disk', 'uz', disk=f"{disk.percent:.1f}%") +
        i18n.get('health_downloads', 'uz', count=len(active_downloads))
    )

    await message.answer(health_text)

async def show_users_inline(message: Message):
    from admin.panel import AdminPanel
    admin_panel = AdminPanel(bot)

    users_data = await admin_panel.get_user_list(page=1, per_page=10)

    users_text = f"Users List (Page 1/{users_data['total_pages']})\n\n"
    for user in users_data['users']:
        users_text += f"• {user['first_name']} (@{user['username']})\n"
        users_text += f"  Downloads: {user['download_count']}\n"
        users_text += f"  Language: {user['language']}\n\n"

    await message.answer(users_text)

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

    dp.message.register(broadcast_media_handler, BroadcastStates.waiting_media)
    dp.message.register(broadcast_text_handler, BroadcastStates.waiting_text)
    dp.message.register(broadcast_button_handler, BroadcastStates.waiting_button)

    dp.message.register(reply_menu_handler, F.text.in_([
        "📊 Statistics", "👥 Users", "📢 Broadcast", "💚 System Health",
        "⚙️ Settings", "ℹ️ Help", "🏠 Main Menu"
    ]))

    dp.message.register(url_handler, F.content_type == ContentType.TEXT, ~F.text.startswith('/'))

    dp.callback_query.register(quality_callback, F.data.startswith('quality:'))
    dp.callback_query.register(language_callback, F.data.startswith('lang:'))
    dp.callback_query.register(broadcast_confirm_callback, F.data.startswith('broadcast:'))

async def on_startup(dp):
    logger.info("Starting FlashSaver Bot...")

    if not await test_bot_token():
        logger.error("Bot token validation failed. Exiting...")
        return False

    try:
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
        logger.info("Bot commands set successfully")
    except TelegramBadRequest as e:
        logger.warning(f"Failed to set bot commands (non-critical): {e}")
    except Exception as e:
        logger.error(f"Error setting bot commands: {e}")

    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

    try:
        os.makedirs("temp", exist_ok=True)
        logger.info("Temp directory created/verified")
    except Exception as e:
        logger.error(f"Failed to create temp directory: {e}")

    try:
        userbot_started = await file_router.start_userbot()
        if userbot_started:
            logger.info("FlashSaver Bot started with userbot support (2GB file limit)!")
        else:
            logger.info("FlashSaver Bot started with bot API only (50MB file limit)!")
    except Exception as e:
        logger.warning(f"Userbot startup failed: {e}")
        logger.info("Bot will work with bot API only (50MB file limit)")

    logger.info("✅ Bot is ready to download from YouTube and Instagram!")
    return True

async def on_shutdown(dp):
    logger.info("Shutting down bot...")

    try:
        await file_router.stop_userbot()
        logger.info("Userbot stopped")
    except Exception as e:
        logger.error(f"Error stopping userbot: {e}")

    try:
        await bot.session.close()
        logger.info("Bot session closed")
    except Exception as e:
        logger.error(f"Error closing bot session: {e}")

    logger.info("Bot stopped!")

async def main():
    try:
        register_handlers()
        startup_success = await on_startup(dp)
        if not startup_success:
            logger.error("Startup failed. Exiting...")
            return

        logger.info("Starting bot polling...")
        await dp.start_polling(bot, skip_updates=True)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
    finally:
        await on_shutdown(dp)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
