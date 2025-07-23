from typing import Dict, Any
from locales.uz.messages import MESSAGES as UZ_MESSAGES
from locales.ru.messages import MESSAGES as RU_MESSAGES
from .constants import DEFAULT_LANGUAGE

class I18n:
    def __init__(self):
        self.messages = {
            "uz": UZ_MESSAGES,
            "ru": RU_MESSAGES
        }
    
    def get(self, key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
        messages = self.messages.get(lang, self.messages[DEFAULT_LANGUAGE])
        message = messages.get(key, f"[Missing: {key}]")
        
        try:
            return message.format(**kwargs)
        except:
            return message

i18n = I18n()
