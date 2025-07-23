import re
import os
import aiofiles
import asyncio
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from .constants import Platform, TEMP_DIR

async def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"

def format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def detect_platform(url: str) -> Platform:
    youtube_patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)',
        r'youtube\.com/playlist\?list=',
        r'youtube\.com/shorts/'
    ]
    
    instagram_patterns = [
        r'instagram\.com/p/',
        r'instagram\.com/reel/',
        r'instagram\.com/stories/'
    ]
    
    for pattern in youtube_patterns:
        if re.search(pattern, url):
            return Platform.YOUTUBE
            
    for pattern in instagram_patterns:
        if re.search(pattern, url):
            return Platform.INSTAGRAM
            
    return Platform.UNKNOWN

def validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

async def cleanup_file(file_path: str):
    try:
        if os.path.exists(file_path):
            await asyncio.to_thread(os.remove, file_path)
    except:
        pass

def sanitize_filename(filename: str) -> str:
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    return sanitized[:100]

def get_progress_bar(progress: float, length: int = 10) -> str:
    filled = int(length * progress / 100)
    bar = '█' * filled + '░' * (length - filled)
    return f"{bar} {progress:.1f}%"

async def get_file_size(file_path: str) -> int:
    try:
        stat = await asyncio.to_thread(os.stat, file_path)
        return stat.st_size
    except:
        return 0
