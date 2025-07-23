import aiosqlite
from datetime import datetime
from typing import List, Optional
from .models import User, Download, Analytics, BroadcastMessage
from utils.constants import DB_PATH, Platform, DownloadStatus


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT DEFAULT 'uz',
                join_date TEXT,
                download_count INTEGER DEFAULT 0,
                last_activity TEXT,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                url TEXT,
                platform TEXT,
                title TEXT,
                file_size INTEGER,
                quality TEXT,
                status TEXT,
                created_at TEXT,
                completed_at TEXT,
                file_path TEXT,
                error_message TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            );

            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                total_downloads INTEGER DEFAULT 0,
                successful_downloads INTEGER DEFAULT 0,
                failed_downloads INTEGER DEFAULT 0,
                unique_users INTEGER DEFAULT 0,
                youtube_downloads INTEGER DEFAULT 0,
                instagram_downloads INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS broadcast_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                media_type TEXT,
                media_file_id TEXT,
                button_text TEXT,
                button_url TEXT,
                created_at TEXT,
                sent_count INTEGER DEFAULT 0
            );
        ''')
    await create_indices()


async def create_indices():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript('''
            CREATE INDEX IF NOT EXISTS idx_users_activity ON users (last_activity);
            CREATE INDEX IF NOT EXISTS idx_downloads_created ON downloads (created_at);
            CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads (status);
        ''')


async def add_user(user: User):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, language, join_date, last_activity, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user.user_id, user.username, user.first_name, user.last_name, user.language, user.join_date.isoformat(), user.last_activity.isoformat(), int(user.is_active)))
        await db.commit()


async def get_user(user_id: int) -> Optional[User]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT user_id, username, first_name, last_name, language, join_date, download_count, last_activity, is_active FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return User(
                    user_id=row[0],
                    username=row[1],
                    first_name=row[2],
                    last_name=row[3],
                    language=row[4] or 'uz',
                    join_date=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    download_count=row[6] or 0,
                    last_activity=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                    is_active=bool(row[8])
                )
            return None


async def add_download(download: Download):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO downloads (user_id, url, platform, title, file_size, quality, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (download.user_id, download.url, download.platform.value, download.title, download.file_size, download.quality, download.status.value, download.created_at.isoformat()))
        await db.commit()


async def update_download_status(download_id: int, status: str, completed_at: datetime = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            UPDATE downloads
            SET status = ?, completed_at = ?
            WHERE id = ?
        ''', (status, completed_at.isoformat() if completed_at else None, download_id))
        await db.commit()


async def add_analytics(analytics: Analytics):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO analytics (date, total_downloads, successful_downloads, failed_downloads, unique_users, youtube_downloads, instagram_downloads)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (analytics.date.isoformat(), analytics.total_downloads, analytics.successful_downloads, analytics.failed_downloads, analytics.unique_users, analytics.youtube_downloads, analytics.instagram_downloads))
        await db.commit()


async def get_analytics(date: datetime) -> Analytics:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM analytics WHERE date = ?', (date.isoformat(),)) as cursor:
            row = await cursor.fetchone()
            if row:
                return Analytics(**row)
            return Analytics(date=date)


async def add_broadcast_message(message: BroadcastMessage):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO broadcast_messages (text, media_type, media_file_id, button_text, button_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (message.text, message.media_type, message.media_file_id, message.button_text, message.button_url, message.created_at.isoformat()))
        await db.commit()
