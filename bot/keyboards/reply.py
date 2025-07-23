from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from utils.i18n import i18n

def get_main_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📥 YouTube Video"),
                KeyboardButton(text="📱 Instagram Media")
            ],
            [
                KeyboardButton(text="🎵 Audio Only"),
                KeyboardButton(text="📋 Playlist")
            ],
            [
                KeyboardButton(text="⚙️ Settings"),
                KeyboardButton(text="ℹ️ Help")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Send video link or use menu..."
    )
    return keyboard

def get_admin_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Statistics"),
                KeyboardButton(text="👥 Users")
            ],
            [
                KeyboardButton(text="📢 Broadcast"),
                KeyboardButton(text="💚 System Health")
            ],
            [
                KeyboardButton(text="⬇️ Downloads"),
                KeyboardButton(text="⚙️ Settings")
            ],
            [
                KeyboardButton(text="🏠 Main Menu")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_broadcast_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="/skip"),
                KeyboardButton(text="❌ Cancel")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()

def get_quality_selection_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔥 Best Quality"),
                KeyboardButton(text="⭐ High (720p)")
            ],
            [
                KeyboardButton(text="👍 Medium (480p)"),
                KeyboardButton(text="👌 Low (360p)")
            ],
            [
                KeyboardButton(text="🎵 Audio Only")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard
