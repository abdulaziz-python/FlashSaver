import asyncio
import aiosqlite
from datetime import datetime
from typing import List, Dict, Any, Optional
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.exceptions import TelegramAPIError
from database.models import User, BroadcastMessage
from database.operations import get_user
from admin.analytics import AnalyticsManager
from utils.constants import DB_PATH, ADMIN_ID, EMOJI
from utils.helpers import format_file_size
from utils.i18n import i18n
import logging

logger = logging.getLogger(__name__)

class AdminPanel:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.analytics = AnalyticsManager()
    
    async def get_user_list(self, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        offset = (page - 1) * per_page
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM users')
            total_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute('''
                SELECT user_id, username, first_name, last_name, language, join_date, download_count, last_activity 
                FROM users 
                ORDER BY join_date DESC 
                LIMIT ? OFFSET ?
            ''', (per_page, offset))
            users = await cursor.fetchall()
        
        total_pages = (total_users + per_page - 1) // per_page
        
        users_data = []
        for user in users:
            users_data.append({
                'user_id': user[0],
                'username': user[1] or 'No username',
                'first_name': user[2] or 'Unknown',
                'last_name': user[3] or '',
                'language': user[4],
                'join_date': user[5],
                'download_count': user[6] or 0,
                'last_activity': user[7]
            })
        
        return {
            'users': users_data,
            'page': page,
            'total_pages': total_pages,
            'total_users': total_users
        }
    
    async def send_broadcast(self, message_data: Dict[str, Any]) -> Dict[str, int]:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('SELECT user_id FROM users WHERE is_active = 1')
            active_users = [row[0] for row in await cursor.fetchall()]
        
        sent_count = 0
        failed_count = 0
        
        for user_id in active_users:
            try:
                if message_data.get('media_file_id'):
                    if message_data['media_type'] == 'photo':
                        await self.bot.send_photo(
                            chat_id=user_id,
                            photo=message_data['media_file_id'],
                            caption=message_data['text'],
                            reply_markup=self._create_broadcast_keyboard(message_data)
                        )
                    elif message_data['media_type'] == 'video':
                        await self.bot.send_video(
                            chat_id=user_id,
                            video=message_data['media_file_id'],
                            caption=message_data['text'],
                            reply_markup=self._create_broadcast_keyboard(message_data)
                        )
                    elif message_data['media_type'] == 'animation':
                        await self.bot.send_animation(
                            chat_id=user_id,
                            animation=message_data['media_file_id'],
                            caption=message_data['text'],
                            reply_markup=self._create_broadcast_keyboard(message_data)
                        )
                else:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message_data['text'],
                        reply_markup=self._create_broadcast_keyboard(message_data)
                    )
                
                sent_count += 1
                await asyncio.sleep(0.05)
                
            except TelegramAPIError as e:
                failed_count += 1
                logger.warning(f"Failed to send broadcast to {user_id}: {e}")
                await asyncio.sleep(0.1)
            except Exception as e:
                failed_count += 1
                logger.error(f"Unexpected error sending broadcast to {user_id}: {e}")
        
        await self._save_broadcast_message(message_data, sent_count)
        
        return {
            'sent': sent_count,
            'failed': failed_count,
            'total': len(active_users)
        }
    
    def _create_broadcast_keyboard(self, message_data: Dict[str, Any]):
        if message_data.get('button_text') and message_data.get('button_url'):
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text=message_data['button_text'],
                    url=message_data['button_url']
                )
            ]])
            return keyboard
        return None
    
    async def _save_broadcast_message(self, message_data: Dict[str, Any], sent_count: int):
        broadcast = BroadcastMessage(
            text=message_data['text'],
            media_type=message_data.get('media_type'),
            media_file_id=message_data.get('media_file_id'),
            button_text=message_data.get('button_text'),
            button_url=message_data.get('button_url'),
            created_at=datetime.now(),
            sent_count=sent_count
        )
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT INTO broadcast_messages (text, media_type, media_file_id, button_text, button_url, created_at, sent_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                broadcast.text,
                broadcast.media_type,
                broadcast.media_file_id,
                broadcast.button_text,
                broadcast.button_url,
                broadcast.created_at.isoformat(),
                broadcast.sent_count
            ))
            await db.commit()
    
    async def generate_and_send_stats_charts(self, chat_id: int):
        try:
            user_growth_chart = await self.analytics.generate_user_growth_chart()
            if user_growth_chart:
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=FSInputFile(user_growth_chart),
                    caption=f"{EMOJI['stats']} User Growth Chart"
                )
            
            download_stats_chart = await self.analytics.generate_download_stats_chart()
            if download_stats_chart:
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=FSInputFile(download_stats_chart),
                    caption=f"{EMOJI['download']} Download Statistics Chart"
                )
            
            platform_chart = await self.analytics.generate_platform_distribution_chart()
            if platform_chart:
                await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=FSInputFile(platform_chart),
                    caption=f"{EMOJI['stats']} Platform Distribution"
                )
        
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
            await self.bot.send_message(chat_id, "Error generating charts")
    
    async def get_detailed_stats(self) -> str:
        user_stats = await self.analytics.get_user_stats()
        download_stats = await self.analytics.get_download_stats()
        system_stats = await self.analytics.get_system_stats()
        
        stats_text = f"""
{EMOJI['stats']} **Detailed Statistics**

**{EMOJI['users']} Users:**
• Total: {user_stats['total']:,}
• Active: {user_stats['active']:,}
• New Today: {user_stats['new_today']:,}

**{EMOJI['download']} Downloads:**
• Total: {download_stats['total']:,}
• Successful: {download_stats['successful']:,} ({download_stats['successful']/max(download_stats['total'], 1)*100:.1f}%)
• Failed: {download_stats['failed']:,}
• Today: {download_stats['today']:,}

**{EMOJI['settings']} Platform Breakdown:**
        """
        
        for platform, count in download_stats['platforms'].items():
            emoji_map = {'youtube': EMOJI['youtube'], 'instagram': EMOJI['instagram']}
            platform_emoji = emoji_map.get(platform.lower(), '📱')
            stats_text += f"• {platform_emoji} {platform.title()}: {count:,}\n"
        
        stats_text += f"""

**{EMOJI['health']} System:**
• CPU: {system_stats['cpu_percent']:.1f}%
• Memory: {system_stats['memory_percent']:.1f}%
• Disk: {system_stats['disk_percent']:.1f}%
• Available Memory: {format_file_size(system_stats['memory_available'])}
• Free Disk: {format_file_size(system_stats['disk_free'])}
        """
        
        return stats_text
