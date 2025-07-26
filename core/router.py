import os
from typing import Optional
from aiogram import Bot
from aiogram.types import FSInputFile
from pyrogram import Client
from utils.constants import BOT_FILE_LIMIT, USER_BOT_FILE_LIMIT, API_ID, API_HASH, SESSION_NAME
from utils.helpers import get_file_size, cleanup_file
import logging
import asyncio

logger = logging.getLogger(__name__)

class FileRouter:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.userbot: Optional[Client] = None
        self.userbot_connected = False
        self.connection_lock = asyncio.Lock()
        self._setup_userbot()

    def _setup_userbot(self):
        try:
            self.userbot = Client(
                SESSION_NAME,
                api_id=API_ID,
                api_hash=API_HASH,
                workdir=".",
                no_updates=True,
                sleep_threshold=180,
                max_concurrent_transmissions=8,
                workers=8
            )
        except Exception as e:
            logger.warning(f"Userbot setup failed: {e}")

    async def send_file(
        self,
        chat_id: int,
        file_path: str,
        caption: str = "",
        progress_callback: Optional[callable] = None
    ) -> bool:
        try:
            file_size = await get_file_size(file_path)

            if file_size <= BOT_FILE_LIMIT:
                return await self._send_via_bot(chat_id, file_path, caption)
            elif file_size <= USER_BOT_FILE_LIMIT and self.userbot:
                return await self._send_via_userbot(chat_id, file_path, caption, progress_callback)
            else:
                logger.error(f"File too large: {file_size}")
                return False

        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return False
        finally:
            asyncio.create_task(cleanup_file(file_path))

    async def _send_via_bot(self, chat_id: int, file_path: str, caption: str) -> bool:
        try:
            input_file = FSInputFile(file_path)

            if file_path.endswith(('.mp4', '.avi', '.mkv', '.mov', '.webm')):
                await self.bot.send_video(
                    chat_id=chat_id,
                    video=input_file,
                    caption=caption,
                    supports_streaming=True
                )
            elif file_path.endswith(('.mp3', '.wav', '.m4a', '.aac')):
                await self.bot.send_audio(
                    chat_id=chat_id,
                    audio=input_file,
                    caption=caption
                )
            else:
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=input_file,
                    caption=caption
                )
            return True
        except Exception as e:
            logger.error(f"Bot send error: {e}")
            return False

    async def _ensure_userbot_connected(self):
        async with self.connection_lock:
            if not self.userbot_connected and self.userbot:
                try:
                    await self.userbot.start()
                    self.userbot_connected = True
                    logger.info("Userbot connected")
                except Exception as e:
                    logger.error(f"Failed to connect userbot: {e}")
                    return False
            return self.userbot_connected

    async def _send_via_userbot(
        self,
        chat_id: int,
        file_path: str,
        caption: str,
        progress_callback: Optional[callable] = None
    ) -> bool:
        if not await self._ensure_userbot_connected():
            return False

        try:
            if file_path.endswith(('.mp4', '.avi', '.mkv', '.mov', '.webm')):
                await self.userbot.send_video(
                    chat_id=chat_id,
                    video=file_path,
                    caption=caption,
                    progress=progress_callback,
                    supports_streaming=True,
                    thumb=None
                )
            elif file_path.endswith(('.mp3', '.wav', '.m4a', '.aac')):
                await self.userbot.send_audio(
                    chat_id=chat_id,
                    audio=file_path,
                    caption=caption,
                    progress=progress_callback
                )
            else:
                await self.userbot.send_document(
                    chat_id=chat_id,
                    document=file_path,
                    caption=caption,
                    progress=progress_callback
                )

            return True
        except Exception as e:
            logger.error(f"Userbot send error: {e}")
            if "Client is already connected" in str(e):
                self.userbot_connected = True
                return await self._send_via_userbot(chat_id, file_path, caption, progress_callback)
            return False

    async def start_userbot(self):
        if self.userbot and not self.userbot_connected:
            try:
                await self.userbot.start()
                self.userbot_connected = True
                logger.info("Userbot started successfully")
                return True
            except Exception as e:
                logger.warning(f"Failed to start userbot: {e}")
                self.userbot = None
                return False
        return self.userbot_connected

    async def stop_userbot(self):
        if self.userbot and self.userbot_connected:
            try:
                await self.userbot.stop()
                self.userbot_connected = False
                logger.info("Userbot stopped")
            except Exception as e:
                logger.error(f"Error stopping userbot: {e}")
