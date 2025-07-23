from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from utils.constants import DownloadStatus, Platform

@dataclass
class User:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: str = "uz"
    join_date: datetime = None
    download_count: int = 0
    last_activity: datetime = None
    is_active: bool = True

@dataclass
class Download:
    id: Optional[int] = None
    user_id: int = 0
    url: str = ""
    platform: Platform = Platform.UNKNOWN
    title: str = ""
    file_size: int = 0
    quality: str = ""
    status: DownloadStatus = DownloadStatus.PENDING
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class Analytics:
    id: Optional[int] = None
    date: datetime = None
    total_downloads: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    unique_users: int = 0
    youtube_downloads: int = 0
    instagram_downloads: int = 0

@dataclass
class BroadcastMessage:
    id: Optional[int] = None
    text: str = ""
    media_type: Optional[str] = None
    media_file_id: Optional[str] = None
    button_text: Optional[str] = None
    button_url: Optional[str] = None
    created_at: datetime = None
    sent_count: int = 0
