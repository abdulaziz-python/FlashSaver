from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.constants import EMOJI, Quality
from utils.i18n import i18n

def get_quality_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=i18n.get('quality_best', lang), 
                callback_data="quality:best"
            ),
            InlineKeyboardButton(
                text=i18n.get('quality_high', lang), 
                callback_data="quality:720p"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n.get('quality_medium', lang), 
                callback_data="quality:480p"
            ),
            InlineKeyboardButton(
                text=i18n.get('quality_low', lang), 
                callback_data="quality:360p"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n.get('quality_audio', lang), 
                callback_data="quality:audio"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_format_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=i18n.get('format_video', lang), 
                callback_data="format:video"
            ),
            InlineKeyboardButton(
                text=i18n.get('format_audio', lang), 
                callback_data="format:audio"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_compress_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=i18n.get('compress_yes', lang), 
                callback_data="compress:yes"
            ),
            InlineKeyboardButton(
                text=i18n.get('compress_no', lang), 
                callback_data="compress:no"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=i18n.get('admin_stats', lang), 
                callback_data="admin:stats"
            ),
            InlineKeyboardButton(
                text=i18n.get('admin_users', lang), 
                callback_data="admin:users"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n.get('admin_broadcast', lang), 
                callback_data="admin:broadcast"
            ),
            InlineKeyboardButton(
                text=i18n.get('admin_health', lang), 
                callback_data="admin:health"
            )
        ],
        [
            InlineKeyboardButton(
                text=i18n.get('admin_downloads', lang),
                callback_data="admin:downloads"
            ),
            InlineKeyboardButton(
                text=i18n.get('admin_help', lang),
                callback_data="admin:help"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="🇺🇿 O'zbek", 
                callback_data="lang:uz"
            ),
            InlineKeyboardButton(
                text="🇷🇺 Русский", 
                callback_data="lang:ru"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=i18n.get('admin_back', lang), 
                callback_data="admin:main"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_pagination_keyboard(page: int, total_pages: int, prefix: str, lang: str = "uz") -> InlineKeyboardMarkup:
    buttons = []
    
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(
            text="◀️", 
            callback_data=f"{prefix}:{page-1}"
        ))
    
    row.append(InlineKeyboardButton(
        text=f"{page}/{total_pages}", 
        callback_data="noop"
    ))
    
    if page < total_pages:
        row.append(InlineKeyboardButton(
            text="▶️", 
            callback_data=f"{prefix}:{page+1}"
        ))
    
    buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton(
            text=i18n.get('admin_back', lang), 
            callback_data="admin:main"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_broadcast_confirm_keyboard(lang: str = "uz") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="Send", 
                callback_data="broadcast:confirm"
            ),
            InlineKeyboardButton(
                text=i18n.get('cancel', lang), 
                callback_data="admin:main"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
