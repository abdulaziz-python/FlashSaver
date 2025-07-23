# FlashSaver Bot

🔥 A high-performance Telegram bot for downloading videos from YouTube and Instagram with professional features and multi-language support.

## Features

### 🚀 Core Functionality
- **YouTube Downloads**: Videos, playlists, shorts
- **Instagram Downloads**: Posts, reels, stories
- **Audio Extraction**: Extract audio from videos
- **Quality Selection**: Multiple quality options with smart fallback
- **File Size Optimization**: Automatic compression when needed

### 💪 Advanced Features
- **Dual File Support**: 
  - Bot API: Up to 20MB files
  - UserBot: Up to 2GB files (when configured)
- **Multi-language**: Uzbek and Russian support with i18n
- **Real-time Progress**: Live download progress with emoji indicators
- **Smart Routing**: Automatic selection of best delivery method

### 👑 Admin Panel
- **User Statistics**: Comprehensive user analytics
- **Health Monitoring**: System resources and bot health
- **Broadcast System**: Send announcements to all users
- **Visual Analytics**: Charts and graphs for usage patterns
- **Download Statistics**: Success/failure rates and platform breakdown

### 🛡️ Professional Architecture
- **Async/Await**: High-performance concurrent operations
- **Error Handling**: Graceful error recovery and user feedback
- **Database**: Efficient SQLite with async operations
- **Memory Efficient**: Streaming downloads without memory bloat
- **Scalable Design**: Modular architecture for easy maintenance

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Update `.env` file with your credentials

3. **Run the Bot**:
   ```bash
   python main.py
   ```

## Architecture

```
FlashSaver/
├── bot/                    # Bot handlers and keyboards
├── core/                   # Download engine and file routing
├── database/              # Data models and operations
├── admin/                 # Admin panel and analytics
├── utils/                 # Utilities and i18n
├── locales/               # Language files (uz/ru)
└── main.py               # Entry point
```

## Technologies Used

- **aiogram 3.x**: Modern Telegram Bot API wrapper
- **pyrogram 2.x**: UserBot for large file handling
- **yt-dlp**: Advanced video downloader
- **aiosqlite**: Async SQLite operations
- **matplotlib**: Chart generation for analytics
- **psutil**: System monitoring

## Bot Commands

- `/start` - Welcome message and language selection
- `/help` - Usage instructions
- `/admin` - Admin panel (admin only)

## Supported Platforms

✅ YouTube (videos, playlists, shorts)
✅ Instagram (posts, reels, stories)

## Performance Features

- **3 concurrent downloads** maximum
- **Memory streaming** for large files
- **Smart compression** based on file size limits
- **Automatic cleanup** of temporary files
- **Progress tracking** with real-time updates

## Admin Features

- 📊 User statistics and analytics
- 💚 System health monitoring
- 📢 Broadcast messaging with media support
- 📈 Visual charts and graphs
- 👥 User management and activity tracking

---

**FlashSaver Bot** - Built with professional standards for speed, reliability, and user experience.
