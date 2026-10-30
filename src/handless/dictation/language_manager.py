"""Language Registry and Manager for 100+ Dictation Languages.

Supports auto-detection and 100+ languages powered by Groq Whisper Large v3:
- English, Spanish, French, German, Hindi, Mandarin, Japanese, Arabic, Russian, Portuguese, etc.
- Pins active spoken language to cut latency and prevent acoustic hallucinations.
- Integrated directly into the desktop Flow bar and Modern Sidebar.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Complete ISO 639-1 languages supported by Whisper
WHISPER_LANGUAGES: Dict[str, Tuple[str, str]] = {
    "auto": ("Auto-Detect", "🌐 Auto"),
    "en": ("English", "English"),
    "hi": ("Hindi", "हिन्दी"),
    "es": ("Spanish", "Español"),
    "fr": ("French", "Français"),
    "de": ("German", "Deutsch"),
    "zh": ("Chinese (Mandarin)", "中文"),
    "ja": ("Japanese", "日本語"),
    "ar": ("Arabic", "العربية"),
    "pt": ("Portuguese", "Português"),
    "ru": ("Russian", "Русский"),
    "it": ("Italian", "Italiano"),
    "ko": ("Korean", "한국어"),
    "nl": ("Dutch", "Nederlands"),
    "tr": ("Turkish", "Türkçe"),
    "pl": ("Polish", "Polski"),
    "sv": ("Swedish", "Svenska"),
    "vi": ("Vietnamese", "Tiếng Việt"),
    "id": ("Indonesian", "Bahasa Indonesia"),
    "uk": ("Ukrainian", "Українська"),
    "el": ("Greek", "Ελληνικά"),
    "cs": ("Czech", "Čeština"),
    "ro": ("Romanian", "Română"),
    "da": ("Danish", "Dansk"),
    "fi": ("Finnish", "Suomi"),
    "hu": ("Hungarian", "Magyar"),
    "he": ("Hebrew", "עברית"),
    "no": ("Norwegian", "Norsk"),
    "th": ("Thai", "ไทย"),
    "bn": ("Bengali", "বাংলা"),
    "ta": ("Tamil", "தமிழ்"),
    "te": ("Telugu", "తెలుగు"),
    "mr": ("Marathi", "मराठी"),
    "gu": ("Gujarati", "ગુજરાતી"),
    "kn": ("Kannada", "ಕನ್ನಡ"),
    "ml": ("Malayalam", "മലയാളം"),
    "pa": ("Punjabi", "ਪੰਜਾਬੀ"),
    "ur": ("Urdu", "اردو"),
    "fa": ("Persian", "فارسی"),
    "ms": ("Malay", "Bahasa Melayu"),
    "tl": ("Tagalog (Filipino)", "Tagalog"),
    "sk": ("Slovak", "Slovenčina"),
    "hr": ("Croatian", "Hrvatski"),
    "bg": ("Bulgarian", "Български"),
    "sr": ("Serbian", "Српски"),
    "sl": ("Slovenian", "Slovenščina"),
    "lt": ("Lithuanian", "Lietuvių"),
    "lv": ("Latvian", "Latviešu"),
    "et": ("Estonian", "Eesti"),
    "ca": ("Catalan", "Català"),
    "gl": ("Galician", "Galego"),
    "eu": ("Basque", "Euskara"),
    "af": ("Afrikaans", "Afrikaans"),
    "is": ("Icelandic", "Íslenska"),
    "cy": ("Welsh", "Cymraeg"),
    "ga": ("Irish", "Gaeilge"),
    "sq": ("Albanian", "Shqip"),
    "mk": ("Macedonian", "Македонски"),
    "hy": ("Armenian", "Հայերեն"),
    "ka": ("Georgian", "ქართული"),
    "az": ("Azerbaijani", "Azərbaycan"),
    "kk": ("Kazakh", "Қазақша"),
    "uz": ("Uzbek", "Oʻzbekcha"),
    "mn": ("Mongolian", "Монгол"),
    "ne": ("Nepali", "नेपाली"),
    "si": ("Sinhala", "සිංහල"),
    "km": ("Khmer", "ខ្មែរ"),
    "my": ("Burmese", "မြန်မာစာ"),
    "lo": ("Lao", "ລາວ"),
    "am": ("Amharic", "አማርኛ"),
    "sw": ("Swahili", "Kiswahili"),
    "yo": ("Yoruba", "Èdè Yorùbá"),
    "ig": ("Igbo", "Asụsụ Igbo"),
    "ha": ("Hausa", "Harshen Hausa"),
    "zu": ("Zulu", "isiZulu"),
    "xh": ("Xhosa", "isiXhosa"),
    "so": ("Somali", "Soomaaliga"),
    "la": ("Latin", "Latina"),
    "eo": ("Esperanto", "Esperanto"),
    "sa": ("Sanskrit", "संस्कृतम्"),
    "jw": ("Javanese", "Basa Jawa"),
    "su": ("Sundanese", "Basa Sunda"),
    "bs": ("Bosnian", "Bosanski"),
    "lb": ("Luxembourgish", "Lëtzebuergesch"),
    "mt": ("Maltese", "Malti"),
    "yi": ("Yiddish", "ייִדיש"),
    "oc": ("Occitan", "Occitan"),
    "br": ("Breton", "Brezhoneg"),
    "fo": ("Faroese", "Føroyskt"),
    "haw": ("Hawaiian", "ʻŌlelo Hawaiʻi"),
    "mg": ("Malagasy", "Malagasy"),
    "sn": ("Shona", "chiShona"),
    "st": ("Southern Sotho", "Sesotho"),
    "tt": ("Tatar", "Татарча"),
    "tg": ("Tajik", "Тоҷикӣ"),
    "tk": ("Turkmen", "Türkmençe"),
    "ps": ("Pashto", "پښتو"),
    "sd": ("Sindhi", "سنڌي"),
    "as": ("Assamese", "অসমীয়া"),
    "ba": ("Bashkir", "Башҡортса"),
    "bo": ("Tibetan", "བོད་སྐད"),
    "ht": ("Haitian Creole", "Kreyòl ayisyen"),
    "kmr": ("Kurdish (Kurmanji)", "Kurdî"),
    "ckb": ("Kurdish (Sorani)", "کوردی"),
    "mi": ("Maori", "Te Reo Māori"),
    "nn": ("Norwegian Nynorsk", "Norsk Nynorsk"),
    "sa": ("Sanskrit", "संस्कृतम्"),
    "yi": ("Yiddish", "ייִדיש"),
}

# Top 12 quick access languages for Flow Bar popup
PINNED_LANGUAGES: List[str] = [
    "auto",
    "en",
    "hi",
    "es",
    "fr",
    "de",
    "zh",
    "ja",
    "ar",
    "pt",
    "ru",
    "it",
]


class LanguageManager:
    """Manages active dictation language and Whisper code resolution."""

    def __init__(self, current_language: str = "en") -> None:
        self._current_language = current_language.lower().strip() if current_language else "en"
        if self._current_language not in WHISPER_LANGUAGES:
            self._current_language = "en"

    @property
    def current_language(self) -> str:
        return self._current_language

    @property
    def whisper_language(self) -> Optional[str]:
        """Return the ISO code to pass to Groq Whisper. Returns None if 'auto'."""
        return self.get_whisper_code()

    @property
    def pinned_languages(self) -> List[Tuple[str, str]]:
        """Return list of (iso_code, english_name) for quick access."""
        return [(code, WHISPER_LANGUAGES[code][0]) for code in PINNED_LANGUAGES]

    def resolve_code(self, name_or_code: str) -> str:
        """Resolve a name (e.g. 'Spanish', 'hindi') or code ('es', 'hi') to an ISO code."""
        cleaned = name_or_code.lower().strip()
        if cleaned in WHISPER_LANGUAGES:
            return cleaned
        for iso, (eng, nat) in WHISPER_LANGUAGES.items():
            if cleaned == eng.lower() or cleaned == nat.lower():
                return iso
        return "en"

    def get_language_name(self, code: Optional[str] = None) -> str:
        return self.get_display_name(code)

    def set_language(self, code: str) -> bool:
        """Set active language. Accepts ISO code or language name."""
        code_clean = code.lower().strip()
        if code_clean in WHISPER_LANGUAGES:
            self._current_language = code_clean
            logger.info("LanguageManager: Set active language to %s (%s)", code_clean, self.get_display_name(code_clean))
            return True

        # Search by English or native name
        for iso, (eng, nat) in WHISPER_LANGUAGES.items():
            if code_clean == eng.lower() or code_clean == nat.lower():
                self._current_language = iso
                logger.info("LanguageManager: Resolved and set language to %s (%s)", iso, eng)
                return True

        logger.warning("LanguageManager: Unknown language '%s', retaining %s", code, self._current_language)
        return False

    def get_whisper_code(self) -> Optional[str]:
        """Return the ISO code to pass to Groq Whisper. Returns None if 'auto'."""
        if self._current_language == "auto":
            return None
        return self._current_language

    def get_display_name(self, code: Optional[str] = None) -> str:
        target = (code or self._current_language).lower().strip()
        info = WHISPER_LANGUAGES.get(target)
        if info:
            return info[0]
        return target.upper()

    def get_short_badge(self, code: Optional[str] = None) -> str:
        target = (code or self._current_language).lower().strip()
        if target == "auto":
            return "Auto"
        return target.upper()

    def get_pinned_languages(self) -> List[Tuple[str, str, str]]:
        """Return list of (iso_code, english_name, native_name) for pinned list."""
        result = []
        for code in PINNED_LANGUAGES:
            eng, nat = WHISPER_LANGUAGES[code]
            result.append((code, eng, nat))
        return result

    def get_all_languages(self) -> List[Tuple[str, str, str]]:
        """Return all 100+ supported languages sorted alphabetically."""
        items = []
        for code, (eng, nat) in WHISPER_LANGUAGES.items():
            items.append((code, eng, nat))
        return sorted(items, key=lambda x: (x[0] != "auto", x[1]))
