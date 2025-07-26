import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "FlashSaverBot")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

BOT_FILE_LIMIT = 20 * 1024 * 1024
USER_BOT_FILE_LIMIT = 2 * 1024 * 1024 * 1024
CONCURRENT_DOWNLOADS = 3
TEMP_DIR = "temp"
DB_PATH = "database/flash_saver.db"

class Platform(Enum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    UNKNOWN = "unknown"

class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Quality(Enum):
    BEST = "best"
    HIGH = "720p"
    MEDIUM = "480p"
    LOW = "360p"
    AUDIO = "audio"

@dataclass
class MediaInfo:
    title: str
    duration: int
    quality_options: Dict[str, Any]
    file_size: int
    platform: Platform

EMOJI = {
    "download": "⬇️",
    "processing": "⚙️", 
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "video": "🎥",
    "audio": "🎵",
    "instagram": "📷",
    "youtube": "📺",
    "fire": "🔥",
    "rocket": "🚀",
    "stats": "📊",
    "users": "👥",
    "admin": "👑",
    "broadcast": "📢",
    "health": "💚",
    "back": "⬅️",
    "next": "➡️",
    "settings": "⚙️",
    "compress": "🗜️",
    "quality": "🎯"
}

LANGUAGES = ["uz", "ru"]
DEFAULT_LANGUAGE = "uz"
DOWNLOAD_TIMEOUT = 300  
COMPRESSION_TIMEOUT = 300  
PROGRESS_UPDATE_INTERVAL = 2
