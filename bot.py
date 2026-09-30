"""
Telegram kino bot.

SOZLASH:
1) BOT_TOKEN environment variable'iga BotFather tokenini kiriting.
2) ADMIN_IDS environment variable'iga Telegram ID'ingizni kiriting.
   Bir nechta admin bo'lsa, vergul bilan ajrating: 123,456.
3) CHANNEL_ID environment variable'iga post kanali @username yoki -100... ID sini
   kiriting.
Maxfiy qiymatlar kod ichida saqlanmaydi.
Bot ma'lumotlari bot.py yonidagi SQLite faylida saqlanadi.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from threading import RLock
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError
from urllib.parse import quote

from telegram import (
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    Message,
    MessageEntity,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.error import BadRequest, NetworkError, RetryAfter, TelegramError
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("kino-bot")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ========================= SOZLAMALAR =========================
# Token, admin ID va boshqa maxfiy qiymatlar faqat environment variable orqali olinadi.
# ========================= SOZLAMALAR =========================


def parse_admin_ids(value: str) -> set[int]:
    return {
        int(item.strip())
        for item in value.split(",")
        if item.strip().lstrip("-").isdigit()
    }


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", "").strip())
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1003193203879").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "@Primeuz_TVbot").strip().lstrip("@")
_configured_db_path = os.getenv("DB_PATH", "").strip() or "bot.sqlite3"
DB_PATH = str(
    Path(_configured_db_path).expanduser()
    if Path(_configured_db_path).expanduser().is_absolute()
    else Path(__file__).resolve().parent / Path(_configured_db_path).expanduser()
)
DB_BACKUP_PATH = f"{DB_PATH}.backup"
MOVIES_PAGE_SIZE = 12
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OPENAI_KEY_SOURCE = "workspace Secret" if OPENAI_API_KEY else "sozlanmagan"
GEMINI_KEY_SOURCE = "workspace Secret" if GEMINI_API_KEY else "sozlanmagan"
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash").strip()
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image").strip()
OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL",
    os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "https://api.openai.com/v1"),
).rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg").strip() or "ffmpeg"
POSTER_INTRO_SECONDS = 3
MAX_MUSIC_SECONDS = 60 * 60
MAX_MUSIC_UPLOAD_BYTES = 49 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 49 * 1024 * 1024

SEARCH_BUTTON = "🔎 Kino qidirish"
TOP_BUTTON = "🔥 Top kinolar"
FAVORITES_BUTTON = "😍 Sevimli kinolarim"
VIP_BUTTON = "💎 VIP"

ADD_MOVIE_BUTTON = "🎬 Kino qo‘shish"
ADD_SERIAL_BUTTON = "📺 Serial qo‘shish"
MANAGE_MOVIES_BUTTON = "📋 Kino boshqarish"
CREATE_POST_BUTTON = "🚀 Post yaratish"
BROADCAST_BUTTON = "📤 Xabar yuborish"
CHANNELS_BUTTON = "📢 Majburiy obuna"
VIP_SETTINGS_BUTTON = "💎 VIP sozlamalari"
AUTOSAVE_BUTTON = "💾 Avto saqlash"
STATS_BUTTON = "📊 Statistika"
SETTINGS_BUTTON = "⚙️ Sozlamalar"
AI_STATUS_BUTTON = "🤖 AI holati"
PREMIUM_EMOJI_BUTTON = "✨ Premium emoji"
DATABASE_BUTTON = "🗄 Baza"
ADD_MUSIC_BUTTON = "🎼 Musiqa qo‘shish"
ADD_MUSIC_COLLECTION_BUTTON = "📁 Musiqa to‘plami"
MANAGE_MUSIC_BUTTON = "📚 Musiqalar"
FORWARD_PROTECTION_BUTTON = "🔐 Forward himoyasi"
BACK_BUTTON = "⬅️ Oddiy menu"
ADMIN_PANEL_BUTTON = "⚙️ Admin panelga o‘tish"
CANCEL_BUTTON = "❌ Bekor qilish"
COLLECTION_DONE_BUTTON = "✅ To‘plamni tugatish"
SKIP_BUTTON = "⏭ Tavsifsiz saqlash"
DONE_BUTTON = "✅ Tayyor"
SEND_NOW_BUTTON = "🚀 Hoziroq yuborish"
SCHEDULE_BUTTON = "⏰ Vaqtga rejalashtirish"
ALL_USERS_BUTTON = "📊 Barchaga yuborish"
COUNT_USERS_BUTTON = "🔢 Foydalanuvchilar soni"
MUSIC_SEARCH_BUTTON = "🎵 Musiqa qidirish"
PRAYER_TIMES_BUTTON = "🕌 Namoz vaqti"
TRANSLATOR_BUTTON = "🌐 Tarjimon"
LOGO_BUTTON = "🎨 Logo yasash"
VIDEO_DOWNLOADER_BUTTON = "📥 Video yuklash"
LANGUAGE_BUTTON = "🌐 Til / Язык"
RUSSIAN_SEARCH_BUTTON = "🔎 Поиск кино"
RUSSIAN_TOP_BUTTON = "🔥 Топ фильмов"
RUSSIAN_FAVORITES_BUTTON = "😍 Избранные фильмы"
RUSSIAN_MUSIC_BUTTON = "🎵 Найти музыку"
RUSSIAN_PRAYER_BUTTON = "🕌 Время намаза"
RUSSIAN_VIP_BUTTON = "💎 VIP"
UZBEK_LANGUAGE_BUTTON = "🇺🇿 O‘zbekcha"
RUSSIAN_LANGUAGE_BUTTON = "🇷🇺 Русский"

DEFAULT_PREMIUM_EMOJIS = {
    "😍": "5337080053119336309",
    "🔎": "5231012545799666522",
    "🎵": "5217933090483098080",
    "🕌": "5323796436532343111",
    "💎": "5251422397893989847",
    "🔥": "5373310043586310463",
}

# Namoz joylari. O‘zbekiston uchun 12 ta viloyat, boshqa joylar uchun
# alohida davlatlar beriladi. Davlatlar poytaxti/ko‘rsatilgan shahri bo‘yicha hisoblanadi.
PRAYER_LOCATIONS = {
    "andijan": ("Andijon", "Uzbekistan"),
    "bukhara": ("Buxoro", "Uzbekistan"),
    "jizzakh": ("Jizzax", "Uzbekistan"),
    "qashqadaryo": ("Qarshi", "Uzbekistan"),
    "navoi": ("Navoiy", "Uzbekistan"),
    "namangan": ("Namangan", "Uzbekistan"),
    "samarkand": ("Samarqand", "Uzbekistan"),
    "sirdaryo": ("Guliston", "Uzbekistan"),
    "surkhandarya": ("Termiz", "Uzbekistan"),
    "tashkent": ("Toshkent", "Uzbekistan"),
    "fergana": ("Farg‘ona", "Uzbekistan"),
    "khorezm": ("Urganch", "Uzbekistan"),
    "turkey": ("Istanbul", "Turkey"),
    "saudi": ("Riyadh", "Saudi Arabia"),
    "france": ("Paris", "France"),
    "russia": ("Moscow", "Russia"),
    "usa": ("New York", "United States"),
}

PRAYER_CITIES = {key: value[0] for key, value in PRAYER_LOCATIONS.items()}
PRAYER_COUNTRIES = {
    "turkey": "🇹🇷 Turkiya",
    "saudi": "🇸🇦 Saudiya Arabistoni",
    "france": "🇫🇷 Fransiya",
    "russia": "🇷🇺 Rossiya",
    "usa": "🇺🇸 AQSh",
}

MEDIA_URL_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "m.youtube.com",
    "facebook.com",
    "www.facebook.com",
    "fb.watch",
    "instagram.com",
    "www.instagram.com",
    "tiktok.com",
    "www.tiktok.com",
    "soundcloud.com",
    "www.soundcloud.com",
}


def now_text() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


def user_language(user_id: int | None) -> str:
    if not user_id:
        return "uz"
    row = db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,), one=True)
    return str(row["language"]) if row and row["language"] in {"uz", "ru"} else "uz"


def russian_user_text(user_id: int | None, uzbek: str, russian: str) -> str:
    return russian if user_language(user_id) == "ru" else uzbek


def utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def utf16_slice(value: str, offset: int, length: int) -> str:
    encoded = value.encode("utf-16-le")
    return encoded[offset * 2 : (offset + length) * 2].decode(
        "utf-16-le", errors="ignore"
    )


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = RLock()
        self.setup()

    def setup(self) -> None:
        with self.lock, self.connection:
            self.connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=FULL;
                PRAGMA foreign_keys=ON;
                PRAGMA busy_timeout=10000;
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language TEXT NOT NULL DEFAULT 'uz',
                    joined_at TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    poster_file_id TEXT,
                    video_file_id TEXT,
                    source_url TEXT NOT NULL DEFAULT '',
                    media_type TEXT NOT NULL DEFAULT 'video',
                    caption TEXT NOT NULL DEFAULT '',
                    views INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    content_type TEXT NOT NULL DEFAULT 'movie'
                );
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    movie_id INTEGER NOT NULL,
                    episode_number INTEGER NOT NULL,
                    video_file_id TEXT NOT NULL,
                    media_type TEXT NOT NULL DEFAULT 'video',
                    created_at TEXT NOT NULL,
                    UNIQUE(movie_id, episode_number),
                    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id INTEGER NOT NULL,
                    movie_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, movie_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS movie_ratings (
                    user_id INTEGER NOT NULL,
                    movie_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, movie_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    invite_link TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    member_limit INTEGER,
                    verification_type TEXT NOT NULL DEFAULT 'telegram'
                );
                CREATE TABLE IF NOT EXISTS vip_users (
                    user_id INTEGER PRIMARY KEY,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS vip_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    receipt_file_id TEXT NOT NULL,
                    receipt_type TEXT NOT NULL DEFAULT 'photo',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS external_subscription_checks (
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    checked_at TEXT NOT NULL,
                    PRIMARY KEY(user_id, channel_id)
                );
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    media_type TEXT NOT NULL,
                    media_file_id TEXT NOT NULL,
                    caption TEXT NOT NULL DEFAULT '',
                    buttons_json TEXT NOT NULL DEFAULT '[]',
                    audience_type TEXT NOT NULL DEFAULT 'all',
                    audience_limit INTEGER,
                    scheduled_at TEXT,
                    status TEXT NOT NULL DEFAULT 'queued',
                    sent_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS premium_emojis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unicode_emoji TEXT NOT NULL UNIQUE,
                    custom_emoji_id TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS music_library (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    performer TEXT NOT NULL DEFAULT '',
                    file_id TEXT NOT NULL,
                    media_type TEXT NOT NULL DEFAULT 'audio',
                    caption TEXT NOT NULL DEFAULT '',
                    source_url TEXT NOT NULL DEFAULT '',
                    collection_id INTEGER,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS music_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                INSERT OR IGNORE INTO settings(key, value)
                    VALUES ('auto_save', '0');
                INSERT OR IGNORE INTO settings(key, value)
                    VALUES ('premium_emoji_enabled', '1');
                INSERT OR IGNORE INTO settings(key, value)
                    VALUES ('forward_protection', '0');
                INSERT OR IGNORE INTO settings(key, value)
                    VALUES ('start_count', '0');
                """
            )
            user_columns = {
                str(row["name"])
                for row in self.connection.execute("PRAGMA table_info(users)").fetchall()
            }
            if "language" not in user_columns:
                self.connection.execute(
                    "ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'uz'"
                )
            movie_columns = {
                str(row["name"])
                for row in self.connection.execute("PRAGMA table_info(movies)").fetchall()
            }
            if "content_type" not in movie_columns:
                self.connection.execute(
                    "ALTER TABLE movies ADD COLUMN content_type TEXT NOT NULL DEFAULT 'movie'"
                )
            if "source_url" not in movie_columns:
                self.connection.execute(
                    "ALTER TABLE movies ADD COLUMN source_url TEXT NOT NULL DEFAULT ''"
                )
            music_columns = {
                str(row["name"])
                for row in self.connection.execute("PRAGMA table_info(music_library)").fetchall()
            }
            if "collection_id" not in music_columns:
                self.connection.execute(
                    "ALTER TABLE music_library ADD COLUMN collection_id INTEGER"
                )
            channel_columns = {
                str(row["name"])
                for row in self.connection.execute("PRAGMA table_info(channels)").fetchall()
            }
            if "verification_type" not in channel_columns:
                self.connection.execute(
                    "ALTER TABLE channels ADD COLUMN verification_type TEXT NOT NULL DEFAULT 'telegram'"
                )
            self.connection.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES ('vip_price', '5000')"
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES ('vip_card_number', '')"
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES ('vip_card_owner', '')"
            )
            for unicode_emoji, custom_emoji_id in DEFAULT_PREMIUM_EMOJIS.items():
                self.connection.execute(
                    """
                    INSERT INTO premium_emojis(unicode_emoji, custom_emoji_id, active)
                    VALUES (?, ?, 1)
                    ON CONFLICT(unicode_emoji) DO UPDATE SET
                        custom_emoji_id = excluded.custom_emoji_id,
                        active = 1
                    """,
                    (unicode_emoji, custom_emoji_id),
                )
            self.connection.commit()

            self.connection.execute("PRAGMA synchronous=FULL")
            self.connection.execute("PRAGMA foreign_keys=ON")
            self.connection.execute("PRAGMA busy_timeout=10000")

    def backup(self, destination: str | None = None) -> str:
        """Create a consistent SQLite backup without interrupting the bot."""
        backup_path = Path(destination or f"{self.path}.backup")
        with self.lock:
            self.connection.commit()
            temporary = backup_path.with_name(f".{backup_path.name}.tmp")
            temporary.unlink(missing_ok=True)
            target = sqlite3.connect(str(temporary))
            try:
                self.connection.backup(target)
                target.commit()
            finally:
                target.close()
            os.replace(temporary, backup_path)
        return str(backup_path)

    def validate_database(self, source: str) -> tuple[bool, str]:
        """Check an uploaded file before it is allowed to replace the live DB."""
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(f"file:{Path(source).resolve()}?mode=ro", uri=True)
            check = connection.execute("PRAGMA quick_check").fetchone()
            if not check or str(check[0]).lower() != "ok":
                return False, "SQLite quick_check tekshiruvdan o‘tmadi."
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            required = {"movies", "users", "settings"}
            missing = required - tables
            if missing:
                return False, f"Kerakli jadvallar yo‘q: {', '.join(sorted(missing))}"
            return True, "Baza fayli yaroqli."
        except (OSError, sqlite3.Error) as error:
            return False, f"Baza faylini o‘qib bo‘lmadi: {error}"
        finally:
            if connection:
                connection.close()

    def merge_from_file(self, source: str) -> dict[str, int]:
        """Merge an old SQLite database into the current one without deleting data."""
        with self.lock:
            self.connection.commit()
            self.backup(DB_BACKUP_PATH)
            source_connection = sqlite3.connect(
                f"file:{Path(source).resolve()}?mode=ro", uri=True
            )
            source_connection.row_factory = sqlite3.Row
            try:
                source_tables = {
                    str(row[0])
                    for row in source_connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
                imported = {
                    "users": 0,
                    "movies": 0,
                    "episodes": 0,
                    "favorites": 0,
                    "ratings": 0,
                    "music": 0,
                }
                movie_ids: dict[int, int] = {}
                collection_ids: dict[int, int] = {}
                channel_ids: dict[int, int] = {}

                def source_rows(table: str) -> list[sqlite3.Row]:
                    if table not in source_tables:
                        return []
                    return source_connection.execute(f"SELECT * FROM {table}").fetchall()

                def value(row: sqlite3.Row, key: str, default: Any = None) -> Any:
                    return row[key] if key in row.keys() else default

                def insert_row(
                    table: str, columns: list[str], row_values: list[Any]
                ) -> int:
                    placeholders = ", ".join("?" for _ in columns)
                    return int(
                        self.connection.execute(
                            f"INSERT OR IGNORE INTO {table} ({', '.join(columns)}) "
                            f"VALUES ({placeholders})",
                            tuple(row_values),
                        ).lastrowid
                        or 0
                    )

                self.connection.execute("BEGIN")
                for row in source_rows("users"):
                    before = self.connection.total_changes
                    insert_row(
                        "users",
                        ["user_id", "username", "first_name", "language", "joined_at",
                         "last_seen", "active"],
                        [
                            value(row, "user_id"),
                            value(row, "username"),
                            value(row, "first_name"),
                            value(row, "language", "uz"),
                            value(row, "joined_at", now_text()),
                            value(row, "last_seen", now_text()),
                            value(row, "active", 1),
                        ],
                    )
                    imported["users"] += int(self.connection.total_changes > before)

                for row in source_rows("movies"):
                    code = str(value(row, "code", "") or "").strip()
                    if not code:
                        continue
                    before = self.connection.total_changes
                    insert_row(
                        "movies",
                        ["code", "title", "poster_file_id", "video_file_id", "source_url",
                         "media_type", "caption", "views", "created_at", "content_type"],
                        [
                            code,
                            str(value(row, "title", "Nomsiz kino") or "Nomsiz kino"),
                            value(row, "poster_file_id"),
                            value(row, "video_file_id"),
                            value(row, "source_url", ""),
                            value(row, "media_type", "video"),
                            value(row, "caption", ""),
                            value(row, "views", 0),
                            value(row, "created_at", now_text()),
                            value(row, "content_type", "movie"),
                        ],
                    )
                    current = self.connection.execute(
                        "SELECT id FROM movies WHERE code = ?", (code,)
                    ).fetchone()
                    if current and value(row, "id") is not None:
                        movie_ids[int(value(row, "id"))] = int(current[0])
                    imported["movies"] += int(self.connection.total_changes > before)

                for row in source_rows("episodes"):
                    old_movie_id = value(row, "movie_id")
                    new_movie_id = movie_ids.get(int(old_movie_id)) if old_movie_id is not None else None
                    if not new_movie_id or not value(row, "video_file_id"):
                        continue
                    before = self.connection.total_changes
                    insert_row(
                        "episodes",
                        ["movie_id", "episode_number", "video_file_id", "media_type", "created_at"],
                        [
                            new_movie_id,
                            value(row, "episode_number", 1),
                            value(row, "video_file_id"),
                            value(row, "media_type", "video"),
                            value(row, "created_at", now_text()),
                        ],
                    )
                    imported["episodes"] += int(self.connection.total_changes > before)

                for row in source_rows("favorites"):
                    new_movie_id = movie_ids.get(int(value(row, "movie_id", 0)))
                    if not new_movie_id:
                        continue
                    before = self.connection.total_changes
                    insert_row("favorites", ["user_id", "movie_id"], [value(row, "user_id"), new_movie_id])
                    imported["favorites"] += int(self.connection.total_changes > before)

                for row in source_rows("movie_ratings"):
                    new_movie_id = movie_ids.get(int(value(row, "movie_id", 0)))
                    if not new_movie_id:
                        continue
                    before = self.connection.total_changes
                    insert_row(
                        "movie_ratings",
                        ["user_id", "movie_id", "rating", "created_at"],
                        [value(row, "user_id"), new_movie_id, value(row, "rating", 1), value(row, "created_at", now_text())],
                    )
                    imported["ratings"] += int(self.connection.total_changes > before)

                for row in source_rows("channels"):
                    channel_id = str(value(row, "channel_id", "") or "").strip()
                    if not channel_id:
                        continue
                    insert_row(
                        "channels",
                        ["channel_id", "title", "invite_link", "active", "member_limit", "verification_type"],
                        [
                            channel_id,
                            value(row, "title", channel_id),
                            value(row, "invite_link", ""),
                            value(row, "active", 1),
                            value(row, "member_limit"),
                            value(row, "verification_type", "telegram"),
                        ],
                    )
                    current = self.connection.execute(
                        "SELECT id FROM channels WHERE channel_id = ?", (channel_id,)
                    ).fetchone()
                    if current and value(row, "id") is not None:
                        channel_ids[int(value(row, "id"))] = int(current[0])

                for table, columns in (
                    ("vip_users", ["user_id", "expires_at"]),
                    ("premium_emojis", ["unicode_emoji", "custom_emoji_id", "active"]),
                ):
                    for row in source_rows(table):
                        insert_row(table, columns, [value(row, column) for column in columns])

                for row in source_rows("vip_payments"):
                    insert_row(
                        "vip_payments",
                        ["user_id", "amount", "receipt_file_id", "receipt_type", "status", "created_at", "reviewed_at"],
                        [value(row, column) for column in (
                            "user_id", "amount", "receipt_file_id", "receipt_type",
                            "status", "created_at", "reviewed_at"
                        )],
                    )

                for row in source_rows("external_subscription_checks"):
                    new_channel_id = channel_ids.get(int(value(row, "channel_id", 0)))
                    if new_channel_id:
                        insert_row(
                            "external_subscription_checks",
                            ["user_id", "channel_id", "checked_at"],
                            [value(row, "user_id"), new_channel_id, value(row, "checked_at", now_text())],
                        )

                for row in source_rows("broadcasts"):
                    insert_row(
                        "broadcasts",
                        ["media_type", "media_file_id", "caption", "buttons_json", "audience_type",
                         "audience_limit", "scheduled_at", "status", "sent_count", "failed_count",
                         "created_at", "completed_at"],
                        [value(row, column) for column in (
                            "media_type", "media_file_id", "caption", "buttons_json", "audience_type",
                            "audience_limit", "scheduled_at", "status", "sent_count", "failed_count",
                            "created_at", "completed_at"
                        )],
                    )

                for row in source_rows("settings"):
                    key = str(value(row, "key", "") or "")
                    if key:
                        insert_row("settings", ["key", "value"], [key, value(row, "value", "")])

                for row in source_rows("music_collections"):
                    name = str(value(row, "name", "") or "").strip()
                    if not name:
                        continue
                    insert_row(
                        "music_collections", ["name", "created_at"],
                        [name, value(row, "created_at", now_text())],
                    )
                    current = self.connection.execute(
                        "SELECT id FROM music_collections WHERE name = ?", (name,)
                    ).fetchone()
                    if current and value(row, "id") is not None:
                        collection_ids[int(value(row, "id"))] = int(current[0])

                for row in source_rows("music_library"):
                    old_collection_id = value(row, "collection_id")
                    new_collection_id = (
                        collection_ids.get(int(old_collection_id))
                        if old_collection_id is not None else None
                    )
                    before = self.connection.total_changes
                    insert_row(
                        "music_library",
                        ["title", "performer", "file_id", "media_type", "caption",
                         "source_url", "collection_id", "created_at"],
                        [
                            value(row, "title", "Nomsiz musiqa"),
                            value(row, "performer", ""),
                            value(row, "file_id"),
                            value(row, "media_type", "audio"),
                            value(row, "caption", ""),
                            value(row, "source_url", ""),
                            new_collection_id,
                            value(row, "created_at", now_text()),
                        ],
                    )
                    imported["music"] += int(self.connection.total_changes > before)

                self.connection.commit()
                self.backup(DB_BACKUP_PATH)
                return imported
            except Exception:
                self.connection.rollback()
                raise
            finally:
                source_connection.close()

    def execute(
        self,
        query: str,
        params: tuple[Any, ...] = (),
        *,
        one: bool = False,
        all_rows: bool = False,
    ) -> Any:
        with self.lock, self.connection:
            cursor = self.connection.execute(query, params)
            if one:
                return cursor.fetchone()
            if all_rows:
                return cursor.fetchall()
            return cursor.lastrowid

    def setting(self, key: str, default: str = "") -> str:
        row = self.execute(
            "SELECT value FROM settings WHERE key = ?", (key,), one=True
        )
        return str(row["value"]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.execute(
            """
            INSERT INTO settings(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def user_ids(self, limit: int | None = None) -> list[int]:
        query = "SELECT user_id FROM users WHERE active = 1 ORDER BY user_id"
        params: tuple[Any, ...] = ()
        if limit:
            query += " LIMIT ?"
            params = (limit,)
        return [int(row["user_id"]) for row in self.execute(query, params, all_rows=True)]


db = Database(DB_PATH)
db.backup(DB_BACKUP_PATH)


def premium_entities(text: str) -> list[MessageEntity]:
    """Replace mapped Unicode emoji with Telegram custom-emoji entities.

    Telegram keyboard button labels cannot contain entities, so mappings apply to
    messages, captions, and the visible status text around menus.
    """
    if not text or db.setting("premium_emoji_enabled", "1") != "1":
        return []
    mappings = db.execute(
        """
        SELECT unicode_emoji, custom_emoji_id
        FROM premium_emojis
        WHERE active = 1
        ORDER BY LENGTH(unicode_emoji) DESC
        """,
        all_rows=True,
    )
    entities: list[MessageEntity] = []
    for mapping in mappings:
        symbol = str(mapping["unicode_emoji"])
        custom_id = str(mapping["custom_emoji_id"])
        if not symbol or not custom_id:
            continue
        start = 0
        while True:
            position = text.find(symbol, start)
            if position < 0:
                break
            entities.append(
                MessageEntity(
                    type=MessageEntity.CUSTOM_EMOJI,
                    offset=utf16_length(text[:position]),
                    length=utf16_length(symbol),
                    custom_emoji_id=custom_id,
                )
            )
            start = position + len(symbol)
    entities.sort(key=lambda entity: (entity.offset, -entity.length))
    # Do not send overlapping entities if one mapped emoji contains another.
    result: list[MessageEntity] = []
    occupied_until = -1
    for entity in entities:
        if entity.offset >= occupied_until:
            result.append(entity)
            occupied_until = entity.offset + entity.length
    return result


def normalize_emojis(text: str) -> str:
    """Keep ordinary Unicode emoji unchanged."""
    return text


def custom_emoji_id_from_message(message: Message) -> str | None:
    """Custom emoji entity, caption entity yoki oddiy ID matnini qabul qiladi."""
    entity_groups = [
        (message.text or "", message.entities or []),
        (message.caption or "", message.caption_entities or []),
    ]
    for source, entities in entity_groups:
        for entity in entities:
            if entity.type == MessageEntity.CUSTOM_EMOJI and entity.custom_emoji_id:
                return str(entity.custom_emoji_id)
    raw = (message.text or "").strip()
    if re.fullmatch(r"\d{5,}", raw):
        return raw
    return None


def forward_protection_enabled() -> bool:
    return db.setting("forward_protection", "0") == "1"


def styled_reply_button(
    text: str,
    style: str | None = None,
    custom_emoji_id: str | None = None,
) -> KeyboardButton:
    """Create a styled reply button with an optional Premium custom-emoji icon."""
    kwargs: dict[str, Any] = {}
    if style:
        kwargs["style"] = style
    if custom_emoji_id:
        kwargs["icon_custom_emoji_id"] = str(custom_emoji_id)
    if not kwargs:
        return KeyboardButton(text)
    try:
        return KeyboardButton(text, **kwargs)
    except TypeError:
        # Older python-telegram-bot builds may not expose the new fields
        # as constructor arguments, but can still forward them through api_kwargs.
        try:
            return KeyboardButton(text, api_kwargs=kwargs)
        except TypeError:
            # Preserve compatibility if the installed library predates both fields.
            if style:
                try:
                    return KeyboardButton(text, style=style)
                except TypeError:
                    pass
            return KeyboardButton(text)


def premium_button_label(text: str) -> str:
    """When a custom emoji icon is attached to a reply button, Telegram sends
    the button text separately from the icon. Remove the duplicate Unicode
    emoji from the text so the button visibly contains only one icon."""
    for symbol in DEFAULT_PREMIUM_EMOJIS:
        if text.startswith(symbol):
            return text[len(symbol):].lstrip()
    return text


def premium_reply_button(text: str, style: str | None = None) -> KeyboardButton:
    """Use the saved Premium custom emoji as the button icon, without a
    duplicate Unicode emoji in the button text."""
    custom_id = None
    for symbol, emoji_id in DEFAULT_PREMIUM_EMOJIS.items():
        if text.startswith(symbol):
            custom_id = emoji_id
            break
    return styled_reply_button(premium_button_label(text), style, custom_id)


def styled_inline_button(text: str, *, style: str | None = None, **kwargs: Any) -> InlineKeyboardButton:
    """Create a colored inline button while preserving URL/callback behavior."""
    if not style:
        return InlineKeyboardButton(text, **kwargs)
    try:
        return InlineKeyboardButton(text, style=style, **kwargs)
    except TypeError:
        api_kwargs = dict(kwargs.pop("api_kwargs", {}) or {})
        api_kwargs["style"] = style
        try:
            return InlineKeyboardButton(text, api_kwargs=api_kwargs, **kwargs)
        except TypeError:
            return InlineKeyboardButton(text, **kwargs)


def user_keyboard(
    admin_view: bool = False, language: str = "uz"
) -> ReplyKeyboardMarkup:
    russian = language == "ru"
    rows = [
        [premium_reply_button(RUSSIAN_MUSIC_BUTTON if russian else MUSIC_SEARCH_BUTTON, "success")],
        [premium_reply_button(RUSSIAN_SEARCH_BUTTON if russian else SEARCH_BUTTON, "success")],
        [
            premium_reply_button(RUSSIAN_TOP_BUTTON if russian else TOP_BUTTON, "primary"),
            RUSSIAN_FAVORITES_BUTTON if russian else FAVORITES_BUTTON,
        ],
        [
            premium_reply_button(
                RUSSIAN_PRAYER_BUTTON if russian else PRAYER_TIMES_BUTTON,
                "success",
            ),
            TRANSLATOR_BUTTON,
        ],
        [styled_reply_button(VIDEO_DOWNLOADER_BUTTON, "success")],
        [styled_reply_button(LOGO_BUTTON, "danger")],
        [premium_reply_button(RUSSIAN_VIP_BUTTON if russian else VIP_BUTTON, "primary")],
        [styled_reply_button(LANGUAGE_BUTTON, "primary")],
    ]
    if admin_view:
        rows.append([ADMIN_PANEL_BUTTON])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=False,
    )


def is_supported_media_url(value: str) -> bool:
    """Accept any normal HTTP(S) URL and let yt-dlp decide whether it supports it.

    Keeping a hard-coded host allow-list here caused newly supported yt-dlp sites
    to be rejected before yt-dlp even got a chance to process the URL.
    """
    if not isinstance(value, str):
        return False
    parsed = value.strip()
    return bool(re.match(r"^https?://[^\s<>]+$", parsed, re.I))


def _download_audio(url: str) -> tuple[str, str]:
    """Download only the audio stream selected from a music result."""
    import yt_dlp

    folder = tempfile.mkdtemp(prefix="kino-bot-")
    output_template = str(Path(folder) / "%(title).80s-%(id)s.%(ext)s")
    options: dict[str, Any] = {
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        # Download a little more than Telegram's send limit, then trim and
        # encode the final one-hour file below to stay under that limit.
        "max_filesize": 160 * 1024 * 1024,
        "socket_timeout": 30,
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
    }
    options["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    ffmpeg_path = shutil.which(FFMPEG_BIN)
    if ffmpeg_path:
        options["ffmpeg_location"] = str(Path(ffmpeg_path).parent)
        options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }
        ]
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        title = str(info.get("title") or "Musiqa")
    candidates = [
        path
        for path in Path(folder).iterdir()
        if path.is_file() and not path.name.endswith((".part", ".ytdl"))
    ]
    if not candidates:
        raise RuntimeError("Media fayli topilmadi.")
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    selected = candidates[0]
    ffmpeg_path = shutil.which(FFMPEG_BIN)
    if ffmpeg_path:
        trimmed = selected.with_name(f"{selected.stem}.1hour.mp3")
        command = [
            ffmpeg_path, "-y", "-i", str(selected),
            "-t", str(MAX_MUSIC_SECONDS), "-vn",
            "-ac", "2", "-ar", "44100", "-b:a", "96k",
            str(trimmed),
        ]
        limited = subprocess.run(
            command, capture_output=True, text=True, timeout=240
        )
        if limited.returncode == 0 and trimmed.exists():
            selected.unlink(missing_ok=True)
            selected = trimmed
        if selected.stat().st_size > MAX_MUSIC_UPLOAD_BYTES and ffmpeg_path:
            compressed = selected.with_name(f"{selected.stem}.telegram.mp3")
            command = [
                ffmpeg_path, "-y", "-i", str(selected),
                "-t", str(MAX_MUSIC_SECONDS), "-vn",
                "-ac", "1", "-ar", "32000", "-b:a", "64k",
                str(compressed),
            ]
            limited = subprocess.run(
                command, capture_output=True, text=True, timeout=240
            )
            if limited.returncode == 0 and compressed.exists():
                selected.unlink(missing_ok=True)
                selected = compressed
    return str(selected), title


async def download_music_audio(url: str) -> tuple[str, str]:
    return await asyncio.to_thread(_download_audio, url)


def _download_video(url: str) -> tuple[str, str]:
    """Download a public video with several yt-dlp fallbacks.

    The bot does not require ffmpeg: when a site exposes a progressive MP4
    (video + audio in one stream), that is preferred. If a site exposes only
    separate streams, a second yt-dlp strategy tries a combined/best format;
    if ffmpeg is available on the server, yt-dlp may merge them.
    """
    import yt_dlp

    # Do not use one hard-coded format: some sites expose only webm, some only
    # progressive MP4, and YouTube frequently changes the available formats.
    format_candidates = [
        "best[ext=mp4][vcodec!=none][acodec!=none]/best[vcodec!=none][acodec!=none]",
        "best[ext=mp4]/best",
    ]
    last_error: Exception | None = None

    for selected_format in format_candidates:
        folder = tempfile.mkdtemp(prefix="video-download-")
        output_template = str(Path(folder) / "%(title).80s-%(id)s.%(ext)s")
        options: dict[str, Any] = {
            "outtmpl": output_template,
            "format": selected_format,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": True,
            "socket_timeout": 45,
            "retries": 5,
            "fragment_retries": 5,
            "extractor_retries": 5,
            "file_access_retries": 3,
            "concurrent_fragment_downloads": 1,
            "max_filesize": MAX_VIDEO_UPLOAD_BYTES,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 "
                    "Chrome/140.0 Mobile Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
        ffmpeg_path = shutil.which(FFMPEG_BIN)
        if ffmpeg_path:
            options["ffmpeg_location"] = str(Path(ffmpeg_path).parent)

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                title = str(info.get("title") or "Video")

            candidates = [
                path
                for path in Path(folder).iterdir()
                if path.is_file() and not path.name.endswith((".part", ".ytdl"))
            ]
            if not candidates:
                raise RuntimeError("Video fayli topilmadi.")
            candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
            selected = candidates[0]
            if selected.stat().st_size > MAX_VIDEO_UPLOAD_BYTES:
                raise RuntimeError("Video 49 MB dan katta.")
            return str(selected), title
        except Exception as error:
            last_error = error
            shutil.rmtree(folder, ignore_errors=True)
            logger.warning(
                "Video yuklash strategiyasi ishlamadi (%s): %s",
                selected_format, error,
            )

    if last_error:
        raise last_error
    raise RuntimeError("Video yuklab bo‘lmadi.")


async def download_video(url: str) -> tuple[str, str]:
    return await asyncio.to_thread(_download_video, url)


async def send_local_video_with_fallback(
    bot: Any,
    chat_id: int,
    path: str,
    *,
    caption: str = "",
    **kwargs: Any,
) -> Message:
    """Try Telegram video upload first, then retry the same file as a document."""
    video_kwargs = dict(kwargs)
    supports_streaming = bool(video_kwargs.pop("supports_streaming", True))
    try:
        with Path(path).open("rb") as video_file:
            return await bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=caption,
                supports_streaming=supports_streaming,
                **video_kwargs,
            )
    except TelegramError as error:
        logger.warning("Video sifatida yuborish rad etildi, document sinovi: %s", error)
        with Path(path).open("rb") as document_file:
            return await bot.send_document(
                chat_id=chat_id,
                document=document_file,
                caption=caption,
                **video_kwargs,
            )


async def send_project_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the two deployable files to the configured admin in Telegram."""
    user = update.effective_user
    message = update.effective_message
    if not user or not message or not is_admin(user.id):
        if message:
            await message.reply_text("🚫 Bu buyruq faqat admin uchun.")
        return
    folder = Path(__file__).resolve().parent
    bot_path = folder / "bot.py"
    if not bot_path.is_file():
        bot_path = Path(__file__).resolve()
    requirements_path = folder / "requirements.txt"
    if not requirements_path.is_file():
        candidates = sorted(path for path in folder.glob("requirements*.txt") if path.is_file())
        requirements_path = candidates[0] if candidates else None
    files = [
        (bot_path, "bot.py", "🤖 Kino botining asosiy fayli"),
        (requirements_path, "requirements.txt", "📦 Kerakli kutubxonalar"),
    ]
    missing = [target_name for path, target_name, _ in files if not path]
    if missing:
        await message.reply_text(
            "❌ Fayl topilmadi: " + ", ".join(missing)
        )
        return
    for file_path, target_name, caption in files:
        assert file_path is not None
        with file_path.open("rb") as stream:
            await message.reply_document(
                document=InputFile(stream, filename=target_name),
                caption=caption,
            )


async def send_database_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send both the live SQLite database and its latest safe backup."""
    user = update.effective_user
    message = update.effective_message
    if not user or not message or not is_admin(user.id):
        return
    try:
        backup_path = db.backup(DB_BACKUP_PATH)
        for path, caption in (
            (DB_PATH, "🗄 Ishlayotgan baza fayli"),
            (backup_path, "🛡 Baza zaxira nusxasi"),
        ):
            file_path = Path(path)
            if file_path.is_file():
                with file_path.open("rb") as database_file:
                    await message.reply_document(
                        document=database_file,
                        filename=file_path.name,
                        caption=caption,
                    )
        await message.reply_text(
            "✅ Baza fayllari yuborildi. Qayta tiklash uchun .sqlite3 yoki .db faylni "
            "shu botga yuboring va tasdiqlang."
        )
        context.user_data["state"] = "database_import"
    except (OSError, sqlite3.Error) as error:
        logger.exception("Baza fayllarini yuborishda xatolik: %s", error)
        await message.reply_text("❌ Baza faylini tayyorlab bo‘lmadi.")


def first_supported_url(value: str) -> str:
    for candidate in re.findall(r"https?://[^\s<>]+", value or ""):
        cleaned = candidate.rstrip(".,);]}>'\"")
        if is_supported_media_url(cleaned):
            return cleaned[:1024]
    return ""


def _search_music(query: str) -> list[dict[str, str]]:
    import yt_dlp

    query = re.sub(r"\s+", " ", query or "").strip()
    if not query:
        return []
    options = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "noplaylist": True,
        "retries": 2,
        "extractor_retries": 2,
    }
    # YouTube search is useful for finding titles, but its hosted downloads are
    # frequently blocked on cloud IPs. Prefer SoundCloud search because its
    # public audio streams can be downloaded reliably by the bot.
    result = None
    for provider in ("scsearch5:", "ytsearch5:"):
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                result = ydl.extract_info(f"{provider}{query}", download=False)
            if result:
                break
        except Exception as error:
            logger.warning("%s qidiruvi ishlamadi (%s): %s", provider[:-1], type(error).__name__, error)
    if not result:
        return []
    entries = result.get("entries") or []
    return [
        {
            "title": str(item.get("title") or "Nomsiz qo‘shiq"),
            "url": str(item.get("webpage_url") or item.get("url") or ""),
            "duration": str(item.get("duration_string") or ""),
        }
        for item in entries
        if item.get("webpage_url") or item.get("url")
    ]


async def search_music(query: str) -> list[dict[str, str]]:
    return await asyncio.to_thread(_search_music, query)


async def music_results_from_input(query: str) -> list[dict[str, str]]:
    """Return YouTube results or a direct public media URL as an audio candidate."""
    if is_supported_media_url(query):
        import yt_dlp

        def inspect_url() -> dict[str, str]:
            options = {"quiet": True, "no_warnings": True, "noplaylist": True}
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(query, download=False)
            return {
                "title": str(info.get("title") or "Musiqa"),
                "url": str(info.get("webpage_url") or query),
                "duration": str(info.get("duration_string") or ""),
            }

        return [await asyncio.to_thread(inspect_url)]
    return await search_music(query)


def _music_library_search(query: str) -> list[sqlite3.Row]:
    terms = [part for part in re.findall(r"[^\W_]+", query.casefold(), flags=re.UNICODE) if len(part) > 1]
    if not terms:
        return []
    rows = db.execute(
        """
        SELECT m.*, c.name AS collection_name
        FROM music_library m
        LEFT JOIN music_collections c ON c.id = m.collection_id
        ORDER BY m.id DESC LIMIT 100
        """,
        all_rows=True,
    )
    return [
        row for row in rows
        if all(
            term in (
                f"{row['title']} {row['performer']} {row['caption']} "
                f"{row['collection_name'] or ''}"
            ).casefold()
            for term in terms
        )
    ][:10]


def _music_collection_search(query: str) -> list[sqlite3.Row]:
    terms = [
        part for part in re.findall(r"[^\W_]+", query.casefold(), flags=re.UNICODE)
        if len(part) > 1
    ]
    if not terms:
        return []
    rows = db.execute(
        """
        SELECT c.*, COUNT(m.id) AS track_count
        FROM music_collections c
        LEFT JOIN music_library m ON m.collection_id = c.id
        GROUP BY c.id
        ORDER BY c.id DESC
        """,
        all_rows=True,
    )
    return [
        row
        for row in rows
        if all(term in str(row["name"]).casefold() for term in terms)
    ][:10]


def _gemini_identify_music(audio_path: str) -> dict[str, str]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY sozlanmagan.")
    audio = Path(audio_path).read_bytes()
    if len(audio) > 7_500_000:
        audio = audio[:7_500_000]
    payload = json.dumps(
        {
            "contents": [{
                "parts": [
                    {
                        "text": (
                            "You identify music from this audio. Return only JSON with "
                            "title, artist, search_query and confidence. If unknown, "
                            "use empty strings. Do not invent details."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "audio/mpeg",
                            "data": __import__("base64").b64encode(audio).decode("ascii"),
                        }
                    },
                ]
            }],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 8192},
        },
    ).encode("utf-8")
    endpoint = os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")
    req = urllib_request.Request(
        f"{endpoint}/models/{GEMINI_TEXT_MODEL}:generateContent?key={quote(GEMINI_API_KEY)}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=90) as response:
        result = json.loads(response.read().decode("utf-8"))
    content = str(
        result["candidates"][0]["content"]["parts"][0].get("text", "")
    )
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        return {"title": "", "artist": "", "search_query": content[:200], "confidence": ""}
    parsed = json.loads(match.group(0))
    return {
        "title": str(parsed.get("title") or ""),
        "artist": str(parsed.get("artist") or ""),
        "search_query": str(parsed.get("search_query") or ""),
        "confidence": str(parsed.get("confidence") or ""),
    }


def _gemini_generate_content(
    prompt: str,
    *,
    model: str = GEMINI_TEXT_MODEL,
    inline_data: tuple[str, bytes] | None = None,
    response_modalities: list[str] | None = None,
) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY sozlanmagan.")
    parts: list[dict[str, Any]] = [{"text": prompt}]
    if inline_data:
        mime_type, data = inline_data
        parts.append(
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(data).decode("ascii"),
                }
            }
        )
    generation_config: dict[str, Any] = {"maxOutputTokens": 8192}
    if response_modalities:
        generation_config["responseModalities"] = response_modalities
    payload = json.dumps(
        {
            "contents": [{"parts": parts}],
            "generationConfig": generation_config,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    endpoint = os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
    ).rstrip("/")
    request = urllib_request.Request(
        f"{endpoint}/models/{model}:generateContent?key={quote(GEMINI_API_KEY)}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


def _gemini_text_from_response(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
    return "\n".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict) and part.get("text")
    ).strip()


def _gemini_translate_text(text: str, target_code: str) -> str:
    language = TRANSLATION_LANGUAGES.get(target_code)
    if not language:
        raise ValueError("Tarjima tili topilmadi.")
    result = _gemini_text_from_response(
        _gemini_generate_content(
            f"You are a professional translator. Translate the following text into "
            f"{language[1]}. Detect the source language automatically. Translate "
            "the complete text faithfully; do not summarize, omit, soften, or "
            "rewrite meaning. Preserve names, numbers, punctuation, line breaks, "
            "emoji, and formatting. Return only the translation with no explanation.\n\n"
            f"Text:\n{text}"
        )
    )
    if not result:
        raise RuntimeError("Gemini tarjima qaytarmadi.")
    return result


def _gemini_translate_audio(audio_path: str, target_code: str) -> tuple[str, str]:
    language = TRANSLATION_LANGUAGES.get(target_code)
    if not language:
        raise ValueError("Tarjima tili topilmadi.")
    audio = Path(audio_path).read_bytes()
    if len(audio) > 7_500_000:
        raise ValueError(
            "Gemini fallback uchun audio 7.5 MB dan kichik bo‘lishi kerak."
        )
    payload = _gemini_generate_content(
        "Listen to the attached audio and return only valid JSON with exactly "
        f"two string fields: transcript and translation. Translate the speech "
        f"into {language[1]}. Preserve names and numbers. "
        "If the speech is unclear, keep the best short transcript.\n"
        "Do not wrap the JSON in markdown.",
        inline_data=("audio/mpeg", audio),
    )
    content = _gemini_text_from_response(payload)
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        raise RuntimeError("Gemini audio tarjima formati noto‘g‘ri.")
    result = json.loads(match.group(0))
    transcript = str(result.get("transcript") or "").strip()
    translation = str(result.get("translation") or "").strip()
    if not transcript or not translation:
        raise RuntimeError("Gemini audio tarjima qaytarmadi.")
    return transcript, translation


def _gemini_generate_logo(prompt: str) -> tuple[str, bytes | None]:
    payload = _gemini_generate_content(
        "Create a clean, professional square logo for a Telegram project. "
        "Use a strong readable symbol, simple typography, and no mockup, "
        "watermark, phone screen, or extra unrelated text. "
        f"User brief: {prompt[:1500]}",
        model=GEMINI_IMAGE_MODEL,
        response_modalities=["IMAGE"],
    )
    candidates = payload.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
    for part in parts:
        image_data = part.get("inlineData") or part.get("inline_data")
        if not isinstance(image_data, dict):
            continue
        encoded = image_data.get("data")
        if encoded:
            return "gemini-logo.png", base64.b64decode(str(encoded))
    raise RuntimeError("Gemini logo rasmi qaytmadi.")



def _gemini_identify_music_bytes(data: bytes, mime_type: str) -> dict[str, str]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY sozlanmagan.")
    if len(data) > 20_000_000:
        raise ValueError("AI tahlili uchun audio/video 20 MB dan kichik bo‘lishi kerak.")
    payload = json.dumps(
        {
            "contents": [{"parts": [
                {"text": (
                    "Identify the music in the attached audio or video. Return only JSON "
                    "with title, artist, search_query and confidence. If unknown, use "
                    "empty strings. Do not invent details. Listen to the audio track; "
                    "ignore unrelated speech when possible."
                )},
                {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(data).decode("ascii")}},
            ]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 8192},
        }, ensure_ascii=False,
    ).encode("utf-8")
    endpoint = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    req = urllib_request.Request(
        f"{endpoint}/models/{GEMINI_TEXT_MODEL}:generateContent?key={quote(GEMINI_API_KEY)}",
        data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib_request.urlopen(req, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))
    content = _gemini_text_from_response(result)
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        raise RuntimeError("Gemini musiqa aniqlash javobi noto‘g‘ri.")
    parsed = json.loads(match.group(0))
    return {
        "title": str(parsed.get("title") or ""),
        "artist": str(parsed.get("artist") or ""),
        "search_query": str(parsed.get("search_query") or ""),
        "confidence": str(parsed.get("confidence") or ""),
    }


def _gemini_translate_media_bytes(data: bytes, mime_type: str, target_code: str) -> tuple[str, str]:
    language = TRANSLATION_LANGUAGES.get(target_code)
    if not language:
        raise ValueError("Tarjima tili topilmadi.")
    if len(data) > 20_000_000:
        raise ValueError("AI tarjimasi uchun audio/video 20 MB dan kichik bo‘lishi kerak.")
    payload = json.dumps(
        {
            "contents": [{"parts": [
                {"text": (
                    "Listen to the attached audio/video and return only valid JSON with "
                    "exactly two string fields: transcript and translation. Detect the "
                    "source language automatically and translate the speech into "
                    f"{language[1]}. Preserve names and numbers. If unclear, give the "
                    "best possible transcript and translation. Do not add explanations."
                )},
                {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(data).decode("ascii")}},
            ]}],
            "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 8192},
        }, ensure_ascii=False,
    ).encode("utf-8")
    endpoint = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    req = urllib_request.Request(
        f"{endpoint}/models/{GEMINI_TEXT_MODEL}:generateContent?key={quote(GEMINI_API_KEY)}",
        data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib_request.urlopen(req, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))
    content = _gemini_text_from_response(result)
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        raise RuntimeError("Gemini media tarjima formati noto‘g‘ri.")
    parsed = json.loads(match.group(0))
    transcript = str(parsed.get("transcript") or "").strip()
    translation = str(parsed.get("translation") or "").strip()
    if not transcript or not translation:
        raise RuntimeError("Gemini media tarjima qaytarmadi.")
    return transcript, translation


async def identify_music_from_message(
    bot: Any, message: Message, progress: Any = None
) -> tuple[dict[str, str], list[dict[str, str]]]:
    media = media_from_message(message)
    if not media or media[0] not in {"video", "audio", "document"}:
        raise ValueError("Video yoki audio yuboring.")
    if media[0] == "document" and not (
        str(message.document.mime_type or "").startswith(("audio/", "video/"))
    ):
        raise ValueError("Bu fayl audio yoki video emas.")
    with tempfile.TemporaryDirectory(prefix="music-identify-") as folder:
        source = Path(folder) / "source"
        if progress:
            await progress(20, "📥 Video/audio olinmoqda...")
        await (await bot.get_file(media[1])).download_to_drive(custom_path=str(source))
        if source.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("AI musiqa aniqlashi uchun fayl 20 MB dan kichik bo‘lsin.")
        if progress:
            await progress(55, "🤖 AI musiqani aniqlamoqda...")
        mime = str(message.document.mime_type or "") if media[0] == "document" else (
            "video/mp4" if media[0] == "video" else ("audio/ogg" if media[0] == "voice" else "audio/mpeg")
        )
        if not mime.startswith(("audio/", "video/")):
            mime = "video/mp4" if media[0] == "video" else "audio/mpeg"
        identified = await asyncio.to_thread(_gemini_identify_music_bytes, source.read_bytes(), mime)
        query = identified.get("search_query") or " ".join(
            part for part in (identified.get("artist"), identified.get("title")) if part
        )
        if progress:
            await progress(80, "🔎 To‘liq trek qidirilmoqda...")
        results = await music_results_from_input(query) if query else []
        if progress:
            await progress(100, "✅ Musiqa aniqlandi.")
        return identified, results


async def identify_music_from_url(
    url: str, progress: Any = None
) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Analyze a public reel/video without requiring FFmpeg on the host."""
    downloaded_path = ""
    try:
        if progress:
            await progress(20, "📥 Havoladagi audio/video yuklanmoqda...")
        downloaded_path, source_title = await download_music_audio(url)
        path = Path(downloaded_path)
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("AI musiqa aniqlashi uchun yuklangan fayl 20 MB dan kichik bo‘lsin.")
        if progress:
            await progress(55, "🤖 AI musiqani aniqlamoqda...")
        suffix = path.suffix.lower()
        mime = "video/mp4" if suffix in {".mp4", ".mov", ".webm", ".mkv"} else (
            "audio/ogg" if suffix == ".ogg" else "audio/mpeg"
        )
        identified = await asyncio.to_thread(_gemini_identify_music_bytes, path.read_bytes(), mime)
        if not identified.get("title") and source_title:
            identified["search_query"] = source_title
        query = identified.get("search_query") or " ".join(
            part for part in (identified.get("artist"), identified.get("title")) if part
        )
        if progress:
            await progress(80, "🔎 To‘liq trek qidirilmoqda...")
        results = await music_results_from_input(query) if query else []
        if progress:
            await progress(100, "✅ Musiqa aniqlandi.")
        return identified, results
    finally:
        if downloaded_path:
            try:
                Path(downloaded_path).unlink(missing_ok=True)
            except OSError:
                pass


async def send_library_music(bot: Any, chat_id: int, row: sqlite3.Row) -> None:
    caption = normalize_emojis(
        f"🎵 {row['title']}" + (f"\n👤 {row['performer']}" if row["performer"] else "")
        + (
            f"\n📁 To‘plam: {row['collection_name']}"
            if "collection_name" in row.keys() and row["collection_name"]
            else ""
        )
        + (f"\n\n{row['caption']}" if row["caption"] else "")
    )[:1024]
    if str(row["media_type"]) == "document":
        await bot.send_document(
            chat_id=chat_id,
            document=str(row["file_id"]),
            caption=caption,
            caption_entities=premium_entities(caption) or None,
        )
    else:
        await bot.send_audio(
            chat_id=chat_id,
            audio=str(row["file_id"]),
            title=str(row["title"])[:255],
            performer=str(row["performer"] or "")[:255],
            caption=caption,
            caption_entities=premium_entities(caption) or None,
        )


def prayer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            styled_inline_button("🇺🇿 O‘zbekiston — 12 viloyat", style="primary", callback_data="prayer_menu:uz"),
        ],
        [
            styled_inline_button("🌍 Davlatlar", style="primary", callback_data="prayer_menu:world"),
        ],
    ])


def prayer_uzbekistan_keyboard() -> InlineKeyboardMarkup:
    items = [(key, PRAYER_LOCATIONS[key][0]) for key in (
        "andijan", "bukhara", "jizzakh", "qashqadaryo", "navoi", "namangan",
        "samarkand", "sirdaryo", "surkhandarya", "tashkent", "fergana", "khorezm"
    )]
    rows = [
        [styled_inline_button(name, style="success", callback_data=f"prayer:{key}")]
        for key, name in items
    ]
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="prayer_menu:main")])
    return InlineKeyboardMarkup(rows)


def prayer_world_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [styled_inline_button(PRAYER_COUNTRIES[key], style="primary", callback_data=f"prayer:{key}")]
        for key in PRAYER_COUNTRIES
    ]
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="prayer_menu:main")])
    return InlineKeyboardMarkup(rows)


async def send_prayer_times(bot: Any, chat_id: int, city_key: str) -> None:
    city, country = PRAYER_LOCATIONS[city_key]

    def request_times() -> dict[str, Any]:
        # school=1 = Hanafi Asr. Bu Asrni Shofi’iy hisobidagi 15:33 kabi
        # erta vaqt emas, Hanafi usulidagi vaqtga moslaydi.
        endpoint = (
            "https://api.aladhan.com/v1/timingsByCity"
            f"?city={quote(city)}&country={quote(country)}&method=2&school=1"
        )
        with urllib_request.urlopen(endpoint, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    payload = await asyncio.to_thread(request_times)
    data = payload.get("data") or {}
    timings = data.get("timings") or {}
    date_info = data.get("date") or {}
    readable_date = str(date_info.get("readable") or "")
    if not timings:
        raise RuntimeError("Namoz vaqtlari topilmadi.")
    await send_text(
        bot,
        chat_id,
        f"🕌 {city}, {country} uchun namoz vaqtlari\n📅 {readable_date}\n\n"
        f"Bomdod: {timings.get('Fajr', '—')}\n"
        f"Quyosh: {timings.get('Sunrise', '—')}\n"
        f"Peshin: {timings.get('Dhuhr', '—')}\n"
        f"Asr: {timings.get('Asr', '—')}\n"
        f"Shom: {timings.get('Maghrib', '—')}\n"
        f"Xufton: {timings.get('Isha', '—')}",
        reply_markup=user_keyboard(),
    )


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [ADD_MOVIE_BUTTON, ADD_SERIAL_BUTTON],
            [ADD_MUSIC_BUTTON, ADD_MUSIC_COLLECTION_BUTTON],
            [MANAGE_MUSIC_BUTTON],
            [MANAGE_MOVIES_BUTTON],
            [CREATE_POST_BUTTON, BROADCAST_BUTTON],
            [CHANNELS_BUTTON, AUTOSAVE_BUTTON],
            [DATABASE_BUTTON],
            [VIP_SETTINGS_BUTTON],
            [STATS_BUTTON],
            [AI_STATUS_BUTTON],
            [PREMIUM_EMOJI_BUTTON],
            [FORWARD_PROTECTION_BUTTON, SETTINGS_BUTTON],
            [BACK_BUTTON],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=False,
    )


def flow_keyboard(*rows: str) -> ReplyKeyboardMarkup:
    buttons = []
    for row in rows:
        row_buttons = []
        for item in row.split("|"):
            row_buttons.append(
                styled_reply_button(item, "danger" if item == CANCEL_BUTTON else None)
            )
        buttons.append(row_buttons)
    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=False,
    )


def is_admin(user_id: int | None) -> bool:
    return bool(user_id and user_id in ADMIN_IDS)


async def send_text(
    bot: Any,
    chat_id: int,
    text: str,
    *,
    reply_markup: Any = None,
    entities_enabled: bool = True,
) -> Message:
    text = normalize_emojis(text)
    entities = premium_entities(text) if entities_enabled else []
    return await bot.send_message(
        chat_id=chat_id,
        text=text,
        entities=entities or None,
        reply_markup=reply_markup,
    )


async def reply_text(
    update: Update, text: str, *, reply_markup: Any = None
) -> Message:
    message = update.effective_message
    text = normalize_emojis(text)
    entities = premium_entities(text)
    return await message.reply_text(
        text, entities=entities or None, reply_markup=reply_markup
    )


def progress_text(label: str, percent: int) -> str:
    percent = max(0, min(100, int(percent)))
    filled = percent // 20
    return f"{label}\n{'🟩' * filled}{'⬜' * (5 - filled)} {percent}%"


async def update_progress(message: Message, label: str, percent: int) -> None:
    text = progress_text(label, percent)
    try:
        await message.edit_text(
            text,
            entities=premium_entities(text) or None,
        )
    except TelegramError as error:
        logger.debug("Progress xabarini yangilab bo‘lmadi: %s", error)


def remember_user(update: Update) -> None:
    user = update.effective_user
    if not user:
        return
    db.execute(
        """
        INSERT INTO users(user_id, username, first_name, joined_at, last_seen, active)
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_seen = excluded.last_seen,
            active = 1
        """,
        (user.id, user.username or "", user.first_name or "", now_text(), now_text()),
    )


async def required_channels() -> list[sqlite3.Row]:
    return db.execute(
        "SELECT * FROM channels WHERE active = 1 ORDER BY id", all_rows=True
    )


def vip_active(user_id: int) -> bool:
    row = db.execute(
        "SELECT expires_at FROM vip_users WHERE user_id = ?", (user_id,), one=True
    )
    if not row:
        return False
    try:
        return datetime.fromisoformat(str(row["expires_at"])) > datetime.now()
    except ValueError:
        return False


def vip_expiry_text(user_id: int) -> str:
    row = db.execute(
        "SELECT expires_at FROM vip_users WHERE user_id = ?", (user_id,), one=True
    )
    return str(row["expires_at"]) if row else ""


async def vip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    price = db.setting("vip_price", "5000")
    card = db.setting("vip_card_number", "")
    owner = db.setting("vip_card_owner", "")
    if vip_active(user_id):
        await reply_text(
            update,
            f"💎 VIP obunangiz faol.\n⏳ Amal qilish muddati: {vip_expiry_text(user_id)}",
            reply_markup=user_keyboard(is_admin(user_id)),
        )
        return
    if not card:
        await reply_text(update, "💎 VIP hozircha sozlanmagan. Admin karta raqamini kiritishi kerak.")
        return
    owner_line = f"\n👤 Qabul qiluvchi: {owner}" if owner else ""
    context.user_data["state"] = "vip_payment"
    await reply_text(
        update,
        f"💎 1 oylik VIP: {price} so‘m\n\n"
        f"💳 Karta: {card}{owner_line}\n\n"
        "To‘lovni amalga oshirib, chek rasmini yoki faylini shu yerga yuboring. "
        "Admin tasdiqlagandan keyin VIP faollashadi.",
        reply_markup=flow_keyboard(CANCEL_BUTTON),
    )


async def notify_vip_payment_admins(
    bot: Any, payment_id: int, user_id: int, amount: int, message: Message
) -> None:
    caption = (
        f"💎 Yangi VIP to‘lovi #{payment_id}\n"
        f"👤 Foydalanuvchi: {user_id}\n"
        f"💰 Summa: {amount} so‘m"
    )
    markup = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"vip_approve:{payment_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"vip_reject:{payment_id}"),
        ]]
    )
    for admin_id in ADMIN_IDS:
        try:
            if message.photo:
                await bot.send_photo(
                    admin_id, message.photo[-1].file_id, caption=caption, reply_markup=markup
                )
            elif message.document:
                await bot.send_document(
                    admin_id, message.document.file_id, caption=caption, reply_markup=markup
                )
        except TelegramError:
            logger.warning("VIP to‘lovini adminga yuborib bo‘lmadi: %s", admin_id)


async def subscription_check(
    bot: Any, user_id: int
) -> tuple[bool, str | None]:
    if is_admin(user_id):
        return True, None
    for channel in await required_channels():
        if str(channel["verification_type"] or "telegram") == "external":
            checked = db.execute(
                """
                SELECT 1 FROM external_subscription_checks
                WHERE user_id = ? AND channel_id = ?
                """,
                (user_id, int(channel["id"])),
                one=True,
            )
            if not checked:
                return False, None
            continue
        try:
            member = await bot.get_chat_member(str(channel["channel_id"]), user_id)
            if member.status in {"left", "kicked"} or (
                member.status == "restricted" and not member.is_member
            ):
                return False, None
        except TelegramError as error:
            logger.warning(
                "Kanal obunasini tekshirib bo'lmadi: %s (%s)",
                channel["channel_id"],
                error,
            )
            return False, str(channel["title"] or channel["channel_id"])
    return True, None


async def subscribed_to_required(bot: Any, user_id: int) -> bool:
    subscribed, _ = await subscription_check(bot, user_id)
    return subscribed


async def subscription_prompt(update: Update) -> None:
    prompt_count = int(db.setting("subscription_prompt_count", "0") or "0") + 1
    db.set_setting("subscription_prompt_count", str(prompt_count))
    channels = await required_channels()
    rows = []
    for channel in channels:
        if channel["invite_link"]:
            rows.append(
                [
                    InlineKeyboardButton(
                        f"{'🔗' if channel['verification_type'] == 'external' else '📢'} {channel['title']}",
                        url=str(channel["invite_link"]),
                    )
                ]
            )
        elif channel["verification_type"] != "external":
            rows.append(
                [InlineKeyboardButton(f"📢 {channel['title']}", callback_data="subinfo")]
            )
    if any(str(channel["verification_type"] or "telegram") == "external" for channel in channels):
        rows.append(
            [InlineKeyboardButton("✅ Tashqi havolalarga obuna bo‘ldim", callback_data="external_subcheck")]
        )
    rows.append([InlineKeyboardButton("✅ Tekshirish", callback_data="subcheck")])
    await reply_text(
        update,
        "📢 Kino olishdan oldin quyidagi kanallarga obuna bo‘ling, keyin tekshirish tugmasini bosing.",
        reply_markup=InlineKeyboardMarkup(rows),
    )


def movie_by_id(movie_id: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,), one=True)


def movie_search(query: str) -> list[sqlite3.Row]:
    normalized = re.sub(r"[\u2018\u2019\u02bb`]", "'", query.strip().casefold())
    if not normalized:
        return []
    terms = [
        item
        for item in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
        if len(item) > 1
    ]
    if not terms:
        return []
    rows = db.execute("SELECT * FROM movies ORDER BY views DESC, id DESC", all_rows=True)
    scored: list[tuple[int, sqlite3.Row]] = []
    for row in rows:
        title = re.sub(
            r"[\u2018\u2019\u02bb`]", "'", str(row["title"] or "").casefold()
        )
        haystack = " ".join(
            str(row[key] or "")
            for key in ("code", "title", "caption", "content_type")
        ).casefold().replace("’", "'")
        field_tokens = re.findall(r"[^\W_]+", haystack, flags=re.UNICODE)
        score = 0.0
        misses = 0
        for term in terms:
            if term in title:
                score += 7
            elif term in haystack:
                score += 3
            else:
                close = max(
                    (
                        SequenceMatcher(None, term, candidate).ratio()
                        for candidate in field_tokens
                        if abs(len(candidate) - len(term)) <= 3
                    ),
                    default=0.0,
                )
                if close >= 0.72:
                    score += 2.5 * close
                else:
                    misses += 1
        if misses > 1 or score == 0:
            continue
        if normalized in haystack:
            score += 8
        scored.append((int(score * 10), row))
    scored.sort(key=lambda item: (item[0], int(item[1]["views"])), reverse=True)
    return [row for _, row in scored[:20]]


def _openai_search_codes(query: str, rows: list[sqlite3.Row]) -> list[str]:
    catalog = [
        {
            "code": str(row["code"]),
            "title": str(row["title"]),
            "info": str(row["caption"] or ""),
            "type": str(row["content_type"] or "movie"),
        }
        for row in rows
    ]
    body = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You search a Telegram movie catalog. Match Uzbek, Russian "
                        "or English requests by title, year, genre, language or "
                        "description. Return only JSON: {\"codes\": []}. Never invent codes."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"query": query, "catalog": catalog},
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": 500,
        },
    ).encode("utf-8")
    request = urllib_request.Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = str(payload["choices"][0]["message"]["content"])
    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        return []
    result = json.loads(match.group(0))
    return [str(code) for code in result.get("codes", [])][:20]


TRANSLATION_LANGUAGES = {
    "uz": ("🇺🇿 O‘zbek tili", "Uzbek"),
    "ru": ("🇷🇺 Rus tili", "Russian"),
    "en": ("🇬🇧 Ingliz tili", "English"),
    "tr": ("🇹🇷 Turk tili", "Turkish"),
    "ko": ("🇰🇷 Koreys tili", "Korean"),
    "ar": ("🇸🇦 Arab tili", "Arabic"),
    "kk": ("🇰🇿 Qozoq tili", "Kazakh"),
    "ky": ("🇰🇬 Qirg‘iz tili", "Kyrgyz"),
    "de": ("🇩🇪 Nemis tili", "German"),
    "fr": ("🇫🇷 Fransuz tili", "French"),
    "es": ("🇪🇸 Ispan tili", "Spanish"),
    "zh": ("🇨🇳 Xitoy tili", "Chinese"),
    "ja": ("🇯🇵 Yapon tili", "Japanese"),
    "hi": ("🇮🇳 Hind tili", "Hindi"),
}


def translation_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(TRANSLATION_LANGUAGES["uz"][0], callback_data="translate_lang:uz"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["ru"][0], callback_data="translate_lang:ru"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["en"][0], callback_data="translate_lang:en")],
        [InlineKeyboardButton(TRANSLATION_LANGUAGES["tr"][0], callback_data="translate_lang:tr"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["ko"][0], callback_data="translate_lang:ko"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["ar"][0], callback_data="translate_lang:ar")],
        [InlineKeyboardButton(TRANSLATION_LANGUAGES["kk"][0], callback_data="translate_lang:kk"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["ky"][0], callback_data="translate_lang:ky"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["de"][0], callback_data="translate_lang:de")],
        [InlineKeyboardButton(TRANSLATION_LANGUAGES["fr"][0], callback_data="translate_lang:fr"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["es"][0], callback_data="translate_lang:es"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["zh"][0], callback_data="translate_lang:zh")],
        [InlineKeyboardButton(TRANSLATION_LANGUAGES["ja"][0], callback_data="translate_lang:ja"),
         InlineKeyboardButton(TRANSLATION_LANGUAGES["hi"][0], callback_data="translate_lang:hi"),
         InlineKeyboardButton("❌ Bekor qilish", callback_data="translate_cancel")],
    ]
    return InlineKeyboardMarkup(rows)


def _openai_json_request(
    endpoint: str, payload: dict[str, Any], timeout: int = 90
) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY sozlanmagan.")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib_request.Request(
        f"{OPENAI_BASE_URL}/{endpoint.lstrip('/')}",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _openai_translate_text(text: str, target_code: str) -> str:
    language = TRANSLATION_LANGUAGES.get(target_code)
    if not language:
        raise ValueError("Tarjima tili topilmadi.")
    payload = _openai_json_request(
        "chat/completions",
        {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are a professional translator. Detect the source language "
                        f"and translate the complete text faithfully into {language[1]}. "
                        "Do not summarize, omit, soften, or rewrite meaning. Preserve "
                        "names, numbers, punctuation, line breaks, emoji, and formatting. "
                        "Return only the translation with no explanation. "
                        "If the input is already in the target language, return it unchanged."
                    ),
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
        },
        timeout=45,
    )
    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in content
        )
    result = str(content).strip()
    if not result:
        raise RuntimeError("OpenAI tarjima qaytarmadi.")
    return result


def _translate_text_with_fallback(text: str, target_code: str) -> str:
    translated_parts: list[str] = []
    for part in split_translation_chunks(text):
        try:
            result = _openai_translate_text(part, target_code)
            db.set_setting("ai_last_provider", "OpenAI")
            db.set_setting("ai_last_success_at", now_text())
        except Exception as openai_error:
            logger.warning(
                "OpenAI tarjima ishlamadi; Gemini fallback ishga tushadi (%s): %s",
                type(openai_error).__name__,
                openai_error,
            )
            try:
                result = _gemini_translate_text(part, target_code)
                db.set_setting("ai_last_provider", "Gemini")
                db.set_setting("ai_last_success_at", now_text())
            except Exception as gemini_error:
                logger.exception("OpenAI va Gemini tarjimasi ishlamadi: %s", gemini_error)
                raise RuntimeError("OpenAI va Gemini tarjimasi ishlamadi.") from gemini_error
        translated_parts.append(result)
    return "\n".join(translated_parts)


def _multipart_body(
    fields: dict[str, str],
    field_name: str,
    filename: str,
    content_type: str,
    file_data: bytes,
) -> tuple[bytes, str]:
    boundary = f"----KinoBot{int(time.time() * 1_000_000)}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{filename}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            file_data,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), boundary


def _openai_transcribe_audio(audio_path: str, content_type: str = "audio/mpeg") -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY sozlanmagan.")
    path = Path(audio_path)
    data, boundary = _multipart_body(
        {"model": "whisper-1", "response_format": "json"},
        "file",
        path.name,
        content_type,
        path.read_bytes(),
    )
    request = urllib_request.Request(
        f"{OPENAI_BASE_URL}/audio/transcriptions",
        data=data,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib_request.urlopen(request, timeout=180) as response:
        payload = json.loads(response.read().decode("utf-8"))
    text = str(payload.get("text") or "").strip()
    if not text:
        raise RuntimeError("Audio ichidan matn topilmadi.")
    return text


async def translate_media_message(
    bot: Any, message: Message, target_code: str
) -> tuple[str, str]:
    media_id = ""
    is_video = False
    mime_type = ""
    if message.voice:
        media_id, mime_type = message.voice.file_id, "audio/ogg"
    elif message.audio:
        media_id, mime_type = message.audio.file_id, str(message.audio.mime_type or "audio/mpeg")
    elif message.video:
        media_id, mime_type, is_video = message.video.file_id, "video/mp4", True
    elif message.document:
        mime_type = str(message.document.mime_type or "")
        if not (mime_type.startswith("audio/") or mime_type.startswith("video/")):
            raise ValueError("Audio, video yoki voice fayl yuboring.")
        media_id = message.document.file_id
        is_video = mime_type.startswith("video/")
    else:
        raise ValueError("Matn, audio, video yoki voice yuboring.")

    with tempfile.TemporaryDirectory(prefix="translator-") as folder:
        suffix = ".mp4" if is_video else (".ogg" if mime_type == "audio/ogg" else ".mp3")
        source = Path(folder) / f"source{suffix}"
        telegram_file = await bot.get_file(media_id)
        await telegram_file.download_to_drive(custom_path=str(source))
        size = source.stat().st_size
        # Telegram/Bot API va AI providerlar uchun xavfsizroq amaliy limit.
        if size > 100 * 1024 * 1024:
            raise ValueError("Fayl 100 MB dan katta bo‘lmasin.")

        # If the server has FFmpeg, keep the old high-quality Whisper path.
        # If it does not, audio/voice goes directly to Whisper and video goes to Gemini.
        ffmpeg_path = shutil.which(FFMPEG_BIN)
        if ffmpeg_path:
            audio = Path(folder) / "translation.mp3"
            command = [
                ffmpeg_path, "-y", "-i", str(source), "-t", str(MAX_MUSIC_SECONDS),
                "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k", str(audio),
            ]
            try:
                converted = await asyncio.to_thread(
                    subprocess.run, command, capture_output=True, text=True, timeout=300
                )
            except (OSError, subprocess.TimeoutExpired) as ffmpeg_error:
                logger.warning("FFmpeg conversion ishlamadi; fallback davom etadi: %s", ffmpeg_error)
                converted = None

            if converted is not None and converted.returncode == 0 and audio.exists():
                try:
                    transcript = await asyncio.to_thread(_openai_transcribe_audio, str(audio))
                    translation = await asyncio.to_thread(
                        _translate_text_with_fallback, transcript, target_code
                    )
                    return transcript, translation
                except Exception as openai_error:
                    logger.warning(
                        "OpenAI audio tarjimasi ishlamadi; Gemini fallback: %s",
                        openai_error,
                    )
                    try:
                        return await asyncio.to_thread(
                            _gemini_translate_audio, str(audio), target_code
                        )
                    except Exception as gemini_error:
                        logger.warning("Gemini audio fallback ham ishlamadi: %s", gemini_error)

        # No FFmpeg: direct media analysis. This fixes voice/audio on hosts without FFmpeg
        # and supports video through Gemini without installing a system package.
        if is_video:
            if size > 20 * 1024 * 1024:
                raise ValueError("FFmpegsiz video tarjimasi uchun video 20 MB dan kichik bo‘lsin.")
            transcript, translation = await asyncio.to_thread(
                _gemini_translate_media_bytes, source.read_bytes(), mime_type, target_code
            )
            db.set_setting("ai_last_provider", "Gemini")
            db.set_setting("ai_last_success_at", now_text())
            return transcript, translation

        try:
            transcript = await asyncio.to_thread(_openai_transcribe_audio, str(source), mime_type)
            translation = await asyncio.to_thread(
                _translate_text_with_fallback, transcript, target_code
            )
            return transcript, translation
        except Exception as openai_error:
            logger.warning("FFmpegsiz OpenAI audio tarjimasi ishlamadi; Gemini fallback: %s", openai_error)
            transcript, translation = await asyncio.to_thread(
                _gemini_translate_media_bytes, source.read_bytes(), mime_type, target_code
            )
            db.set_setting("ai_last_provider", "Gemini")
            db.set_setting("ai_last_success_at", now_text())
            return transcript, translation


def _openai_generate_logo(prompt: str) -> tuple[str, bytes | None]:
    payload = _openai_json_request(
        "images/generations",
        {
            "model": "gpt-image-1",
            "prompt": (
                "Create a professional, clean logo for a Telegram project. "
                "Use a strong readable symbol and elegant typography. "
                "Do not include mockups, phone screens, watermarks or extra text. "
                f"User's brief: {prompt[:1500]}"
            ),
            "size": "1024x1024",
        },
        timeout=180,
    )
    item = (payload.get("data") or [{}])[0]
    encoded = item.get("b64_json")
    if encoded:
        return "logo.png", base64.b64decode(str(encoded))
    url = str(item.get("url") or "")
    if url:
        return url, None
    raise RuntimeError("Logo rasmi qaytmadi.")


def _generate_logo_with_fallback(prompt: str) -> tuple[str, bytes | None]:
    try:
        result = _openai_generate_logo(prompt)
        db.set_setting("ai_last_provider", "OpenAI")
        db.set_setting("ai_last_success_at", now_text())
        return result
    except Exception as openai_error:
        logger.warning(
            "OpenAI logo ishlamadi; Gemini fallback ishga tushadi (%s): %s",
            type(openai_error).__name__,
            openai_error,
        )
        try:
            result = _gemini_generate_logo(prompt)
            db.set_setting("ai_last_provider", "Gemini")
            db.set_setting("ai_last_success_at", now_text())
            return result
        except Exception as gemini_error:
            logger.exception("OpenAI va Gemini logo yaratmadi: %s", gemini_error)
            raise RuntimeError("OpenAI va Gemini logo yaratmadi.") from gemini_error


async def smart_movie_search(query: str) -> list[sqlite3.Row]:
    local = movie_search(query)
    if local or not OPENAI_API_KEY:
        return local
    catalog = db.execute(
        "SELECT * FROM movies ORDER BY views DESC, id DESC LIMIT 250",
        all_rows=True,
    )
    if not catalog:
        return []
    try:
        codes = await asyncio.to_thread(_openai_search_codes, query, catalog)
    except (OSError, URLError, TimeoutError, KeyError, TypeError, json.JSONDecodeError):
        logger.exception("OpenAI kino qidiruvi xatosi")
        return []
    if not codes:
        return []
    placeholders = ",".join("?" for _ in codes)
    return db.execute(
        f"SELECT * FROM movies WHERE code IN ({placeholders}) ORDER BY views DESC, id DESC",
        tuple(codes),
        all_rows=True,
    )


def movie_by_code(code: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM movies WHERE code = ?", (code.strip(),), one=True)


def extract_movie_code(value: str) -> str | None:
    patterns = (
        r"(?i)\b(?:kino\s*)?kodi?\s*[:#\-]?\s*([A-Za-z0-9][A-Za-z0-9_-]{0,63})",
        r"(?i)\bstart\s*=\s*([A-Za-z0-9][A-Za-z0-9_-]{0,63})",
    )
    for pattern in patterns:
        match = re.search(pattern, value or "")
        if match:
            return match.group(1)
    return None


def extract_movie_title(caption: str, code: str) -> str:
    for line in (caption or "").splitlines():
        cleaned = line.strip()
        if "🎬" in cleaned:
            title = cleaned.split("🎬", 1)[1].strip(" :-")
            if title and title != code:
                return title[:255]
    return f"Kino kodi {code}"[:255]


def next_auto_code(message: Message) -> str:
    base = f"auto-{int(time.time())}-{message.message_id}"
    code = base[:64]
    suffix = 1
    while movie_by_code(code):
        code = f"{base[:58]}-{suffix}"
        suffix += 1
    return code


def save_auto_movie(
    message: Message,
    media: tuple[str, str] | None,
    *,
    poster_file_id: str | None = None,
) -> tuple[str, bool]:
    caption = (message.caption or "").strip()
    source_url = first_supported_url(caption or (message.text or ""))
    code = extract_movie_code(caption) or next_auto_code(message)
    title = extract_movie_title(caption, code)
    poster_id = poster_file_id or (media[1] if media and media[0] == "photo" else None)
    video_id = media[1] if media and media[0] in {"video", "document"} else None
    media_kind = media[0] if media and media[0] in {"video", "document"} else "video"
    existing = movie_by_code(code)

    if existing:
        current_title = str(existing["title"] or "")
        current_caption = str(existing["caption"] or "")
        db.execute(
            """
            UPDATE movies
            SET title = ?, poster_file_id = COALESCE(?, poster_file_id),
                video_file_id = COALESCE(?, video_file_id),
                source_url = COALESCE(NULLIF(?, ''), source_url),
                media_type = CASE WHEN ? IS NULL THEN media_type ELSE ? END,
                caption = ?
            WHERE id = ?
            """,
            (
                title if caption else current_title,
                poster_id,
                video_id,
                source_url,
                video_id,
                media_kind,
                caption or current_caption,
                int(existing["id"]),
            ),
        )
        db.backup(DB_BACKUP_PATH)
        return code, True

    db.execute(
        """
        INSERT INTO movies(
            code, title, poster_file_id, video_file_id, source_url, media_type,
            caption, created_at, content_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'movie')
        """,
        (
            code,
            title,
            poster_id,
            video_id,
            source_url,
            media_kind,
            caption,
            now_text(),
        ),
    )
    db.backup(DB_BACKUP_PATH)
    return code, False


async def movie_start_link(bot: Any, code: str) -> str | None:
    username = BOT_USERNAME
    if not username:
        me = await bot.get_me()
        username = (me.username or "").strip().lstrip("@")
    return f"https://t.me/{username}?start={quote(str(code), safe='')}" if username else None


def movie_caption(movie: sqlite3.Row) -> str:
    details = f"🎬 {movie['title']}\n🔢 Kodi: {movie['code']}"
    if movie["caption"]:
        details += f"\n\n{movie['caption']}"
    rating = db.execute(
        "SELECT AVG(rating) AS average, COUNT(*) AS total FROM movie_ratings WHERE movie_id = ?",
        (int(movie["id"]),),
        one=True,
    )
    if rating and rating["total"]:
        details += f"\n\n⭐ Reyting: {float(rating['average']):.1f}/5 ({rating['total']} ta)"
    details += f"\n\n👀 Ko‘rishlar: {movie['views']}"
    if movie["source_url"]:
        details += "\n🔗 Manba havolasi saqlangan"
    return details


def movie_buttons(movie: sqlite3.Row) -> InlineKeyboardMarkup:
    movie_id = int(movie["id"])
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("😍 Sevimli", callback_data=f"fav:{movie_id}")],
            [
                InlineKeyboardButton(f"⭐{rating}", callback_data=f"rate:{movie_id}:{rating}")
                for rating in range(1, 6)
            ],
        ]
    )


async def send_movie_card(
    bot: Any, chat_id: int, movie: sqlite3.Row, *, direct: bool = False
) -> None:
    if direct:
        await send_movie_media(bot, chat_id, movie, remove_menu=True)
        return
    caption = movie_caption(movie)
    caption = normalize_emojis(caption[:1024])
    if movie["poster_file_id"]:
        await bot.send_photo(
            chat_id,
            photo=str(movie["poster_file_id"]),
            caption=caption,
            caption_entities=premium_entities(caption) or None,
            reply_markup=movie_buttons(movie),
            protect_content=forward_protection_enabled(),
        )
    else:
        await send_text(
            bot,
            chat_id,
            caption,
            reply_markup=movie_buttons(movie),
        )


async def send_serial_parts(bot: Any, chat_id: int, movie: sqlite3.Row) -> None:
    episodes = db.execute(
        """
        SELECT id, episode_number FROM episodes
        WHERE movie_id = ? ORDER BY episode_number
        """,
        (int(movie["id"]),),
        all_rows=True,
    )
    if not episodes:
        await send_text(bot, chat_id, "❌ Bu serialda hali qismlar yo‘q.")
        return
    buttons = [
        [
            InlineKeyboardButton(
                f"🎞 {row['episode_number']}-qism",
                callback_data=f"episode:{movie['id']}:{row['id']}",
            )
        ]
        for row in episodes
    ]
    await send_text(
        bot,
        chat_id,
        f"📺 {movie['title']}\n🎞 Kerakli qismni tanlang:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def send_movie_media(
    bot: Any, chat_id: int, movie: sqlite3.Row, *, remove_menu: bool = False
) -> None:
    if str(movie["content_type"] or "movie") == "serial":
        await send_serial_parts(bot, chat_id, movie)
        return
    caption = normalize_emojis(movie_caption(movie)[:1024])
    file_id = movie["video_file_id"]
    if not file_id:
        if movie["source_url"]:
            await send_text(
                bot,
                chat_id,
                f"🔗 {movie['title']}\nHavola orqali ko‘rish uchun tugmani bosing.\n"
                f"👀 Ko‘rishlar: {movie['views']}",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("▶️ Havolani ochish", url=str(movie["source_url"]))]]
                    + movie_buttons(movie).inline_keyboard,
                ),
            )
        else:
            await send_text(bot, chat_id, "❌ Bu kino uchun video hali saqlanmagan.")
        return
    entities = premium_entities(caption[:1024]) or None
    if movie["media_type"] == "document":
        await bot.send_document(
            chat_id,
            document=str(file_id),
            caption=caption,
            caption_entities=entities,
            protect_content=forward_protection_enabled(),
            reply_markup=movie_buttons(movie),
        )
    else:
        try:
            await bot.send_video(
                chat_id,
                video=str(file_id),
                caption=caption,
                caption_entities=entities,
                supports_streaming=True,
                protect_content=forward_protection_enabled(),
                reply_markup=movie_buttons(movie),
            )
        except TelegramError as error:
            logger.warning("Kino video sifatida yuborilmadi, document sinovi: %s", error)
            await bot.send_document(
                chat_id,
                document=str(file_id),
                caption=caption,
                caption_entities=entities,
                protect_content=forward_protection_enabled(),
                reply_markup=movie_buttons(movie),
            )


async def send_episode_media(bot: Any, chat_id: int, episode: sqlite3.Row, movie: sqlite3.Row) -> None:
    caption = normalize_emojis(
        f"🎬 {movie['title']}\n🎞️ {episode['episode_number']}-qism"
    )
    if movie["caption"]:
        caption += f"\n\n{movie['caption']}"
    entities = premium_entities(caption[:1024]) or None
    if episode["media_type"] == "document":
        await bot.send_document(
            chat_id,
            document=str(episode["video_file_id"]),
            caption=caption[:1024],
            caption_entities=entities,
            protect_content=forward_protection_enabled(),
        )
    else:
        try:
            await bot.send_video(
                chat_id,
                video=str(episode["video_file_id"]),
                caption=caption[:1024],
                caption_entities=entities,
                supports_streaming=True,
                protect_content=forward_protection_enabled(),
            )
        except TelegramError as error:
            logger.warning("Serial qismi video sifatida yuborilmadi, document sinovi: %s", error)
            await bot.send_document(
                chat_id,
                document=str(episode["video_file_id"]),
                caption=caption[:1024],
                caption_entities=entities,
                protect_content=forward_protection_enabled(),
            )


async def process_movie_video(
    bot: Any,
    *,
    poster_file_id: str,
    video_file_id: str,
    owner_chat_id: int,
) -> tuple[str, str]:
    """Poster intro va Prime TV watermark qo‘shib, yangi Telegram file_id qaytaradi."""
    if not poster_file_id or not video_file_id:
        return video_file_id, "video"
    try:
        with tempfile.TemporaryDirectory(prefix="prime-tv-") as temp_dir:
            temp = Path(temp_dir)
            poster_path = temp / "poster.jpg"
            source_path = temp / "source.mp4"
            output_path = temp / "prime-tv.mp4"
            await (await bot.get_file(poster_file_id)).download_to_drive(
                custom_path=str(poster_path)
            )
            await (await bot.get_file(video_file_id)).download_to_drive(
                custom_path=str(source_path)
            )
            filter_graph = (
                "[0:v]scale=iw*0.90:-2[poster];"
                "[1:v][poster]overlay=(W-w)/2:(H-h)/2:"
                f"enable='between(t,0,{POSTER_INTRO_SECONDS})',"
                "drawtext=text='Prime TV':fontcolor=white@0.86:"
                "fontsize=36:box=1:boxcolor=black@0.38:boxborderw=10:"
                "x=w-tw-24:y=24[v]"
            )
            command = [
                FFMPEG_BIN,
                "-y",
                "-loop",
                "1",
                "-i",
                str(poster_path),
                "-i",
                str(source_path),
                "-filter_complex",
                filter_graph,
                "-map",
                "[v]",
                "-map",
                "1:a?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-shortest",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            completed = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                timeout=900,
            )
            if completed.returncode != 0 or not output_path.exists():
                logger.error("ffmpeg xatosi: %s", completed.stderr[-2000:])
                return video_file_id, "video"
            processed_caption = normalize_emojis("📥 Prime TV poster va watermark tayyor.")
            processed = await send_local_video_with_fallback(
                bot,
                owner_chat_id,
                str(output_path),
                caption=processed_caption,
                caption_entities=premium_entities(processed_caption) or None,
                supports_streaming=True,
                protect_content=True,
            )
            try:
                await bot.delete_message(owner_chat_id, processed.message_id)
            except TelegramError:
                pass
            if processed.video:
                return processed.video.file_id, "video"
            if processed.document:
                return processed.document.file_id, "document"
            return video_file_id, "video"
    except (OSError, TelegramError, subprocess.TimeoutExpired) as error:
        logger.exception("Video qayta ishlanmadi: %s", error)
        return video_file_id, "video"


async def show_search_results(bot: Any, chat_id: int, query: str) -> None:
    cleaned_query = query.strip()
    code_query = extract_movie_code(cleaned_query) or cleaned_query
    exact = movie_by_code(code_query)
    if not exact and cleaned_query.isdigit():
        exact = movie_by_code(str(int(cleaned_query)))
    if exact:
        await send_movie_media(bot, chat_id, exact, remove_menu=True)
        return
    matches = await smart_movie_search(query)
    if not matches:
        await send_text(bot, chat_id, "❌ Kino topilmadi. Kod yoki nomni qayta yuboring.")
        return
    if len(matches) == 1:
        await send_movie_media(bot, chat_id, matches[0], remove_menu=True)
        return
    buttons = [
        [InlineKeyboardButton(f"🎬 {row['title']} · {row['code']}", callback_data=f"movie:{row['id']}")]
        for row in matches
    ]
    await send_text(
        bot,
        chat_id,
        f"🔎 {len(matches)} ta kino topildi. Keraklisini tanlang:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


def draft_summary(draft: dict[str, Any]) -> str:
    return (
        f"👀 Kino preview\n\n"
        f"📝 Nomi: {draft.get('title', '')}\n"
        f"🔢 Kodi: {draft.get('code', '')}\n"
        f"🎥 Media: {'tayyor' if draft.get('video_file_id') else 'yo‘q'}\n\n"
        f"{draft.get('caption') or '📝 Tavsifsiz'}"
    )


async def show_movie_draft(bot: Any, chat_id: int, draft: dict[str, Any]) -> None:
    poster = draft.get("poster_file_id")
    if poster:
        caption = normalize_emojis("🖼 Poster preview")
        await bot.send_photo(
            chat_id,
            photo=poster,
            caption=caption,
            caption_entities=premium_entities(caption) or None,
        )
    if draft.get("video_file_id"):
        if draft.get("media_type") == "document":
            await bot.send_document(chat_id, document=draft["video_file_id"])
        else:
            await bot.send_video(chat_id, video=draft["video_file_id"])
    await send_text(
        bot,
        chat_id,
        draft_summary(draft),
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Saqlash", callback_data="movie_save")],
                [
                    InlineKeyboardButton("✏️ Kod", callback_data="draft_edit:code"),
                    InlineKeyboardButton("✏️ Nom", callback_data="draft_edit:title"),
                ],
                [
                    InlineKeyboardButton("✏️ Poster", callback_data="draft_edit:poster"),
                    InlineKeyboardButton("✏️ Video", callback_data="draft_edit:video"),
                ],
                [InlineKeyboardButton("✏️ Tavsif", callback_data="draft_edit:caption")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="flow_cancel")],
            ]
        ),
    )


async def start_add_movie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    context.user_data["state"] = "add_code"
    await reply_text(
        update,
        "[1/5] 🔢 Kino kodini yuboring:",
        reply_markup=flow_keyboard(CANCEL_BUTTON),
    )


async def start_add_serial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    context.user_data["state"] = "serial_code"
    await reply_text(
        update,
        "[1/4] 🔢 Serial kodini yuboring:",
        reply_markup=flow_keyboard(CANCEL_BUTTON),
    )


async def start_add_music(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    context.user_data["state"] = "music_add_file"
    await reply_text(
        update,
        "🎼 Musiqa audio yoki audio fayl ko‘rinishida yuboring:",
        reply_markup=flow_keyboard(CANCEL_BUTTON),
    )


async def start_add_music_collection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    context.user_data.clear()
    context.user_data["state"] = "music_collection_name"
    await reply_text(
        update,
        "📁 Yangi musiqa to‘plami nomini yuboring.\n"
        "Masalan: PrimeTv to‘plami",
        reply_markup=flow_keyboard(CANCEL_BUTTON),
    )


async def show_music_library(bot: Any, chat_id: int) -> None:
    rows = db.execute(
        """
        SELECT c.id, c.name, COUNT(m.id) AS track_count
        FROM music_collections c
        LEFT JOIN music_library m ON m.collection_id = c.id
        GROUP BY c.id
        ORDER BY c.id DESC
        LIMIT 50
        """,
        all_rows=True,
    )
    ungrouped = db.execute(
        "SELECT COUNT(*) AS n FROM music_library WHERE collection_id IS NULL",
        one=True,
    )["n"]
    lines = [
        f"{index}. 📁 {row['name']} — {row['track_count']} ta musiqa"
        for index, row in enumerate(rows, 1)
    ]
    if ungrouped:
        lines.append(f"🎵 To‘plamsiz musiqalar — {ungrouped} ta")
    text = "📚 Musiqa katalogi\n\n" + (
        "\n".join(lines) if lines else "Hali musiqa qo‘shilmagan."
    )
    await send_text(bot, chat_id, text, reply_markup=admin_keyboard())


async def show_music_collection(
    bot: Any,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    collection_id: int,
    offset: int = 0,
) -> None:
    collection = db.execute(
        "SELECT * FROM music_collections WHERE id = ?",
        (collection_id,),
        one=True,
    )
    if not collection:
        await send_text(bot, chat_id, "❌ Musiqa to‘plami topilmadi.")
        return
    page_size = 25
    rows = db.execute(
        """
        SELECT m.*, c.name AS collection_name
        FROM music_library m
        JOIN music_collections c ON c.id = m.collection_id
        WHERE m.collection_id = ?
        ORDER BY m.id
        LIMIT ? OFFSET ?
        """,
        (collection_id, page_size, max(0, offset)),
        all_rows=True,
    )
    total = db.execute(
        "SELECT COUNT(*) AS n FROM music_library WHERE collection_id = ?",
        (collection_id,),
        one=True,
    )["n"]
    context.user_data["music_results"] = [
        {
            "title": str(row["title"]),
            "url": "",
            "duration": "",
            "library_id": str(row["id"]),
        }
        for row in rows
    ]
    buttons = [
        [
            InlineKeyboardButton(
                f"{offset + index + 1}. {str(row['title'])[:42]}",
                callback_data=f"music:{index}",
            )
        ]
        for index, row in enumerate(rows)
    ]
    navigation: list[InlineKeyboardButton] = []
    if offset > 0:
        navigation.append(
            InlineKeyboardButton(
                "⬅️ Oldingi",
                callback_data=f"music_collection_page:{collection_id}:{max(0, offset - page_size)}",
            )
        )
    if offset + page_size < total:
        navigation.append(
            InlineKeyboardButton(
                "Keyingi ➡️",
                callback_data=f"music_collection_page:{collection_id}:{offset + page_size}",
            )
        )
    if navigation:
        buttons.append(navigation)
    await send_text(
        bot,
        chat_id,
        f"📁 To‘plam: {collection['name']}\n🎵 {total} ta musiqa\n"
        f"Ko‘rsatilmoqda: {offset + 1}–{min(offset + page_size, total)}",
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
    )


async def start_database_import(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    context.user_data["state"] = "database_import"
    await reply_text(
        update,
        "🗄 SQLite baza faylini (.sqlite3 yoki .db) yuboring.\n"
        "Eski baza joriy bazaga qo‘shiladi, joriy ma’lumotlar o‘chirilmaydi. "
        "Tasdiqlashdan oldin avtomatik zaxira olinadi.",
        reply_markup=flow_keyboard(CANCEL_BUTTON),
    )


async def start_manage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await show_all_movies(context.bot, update.effective_chat.id, page=0)


async def manage_results(bot: Any, chat_id: int, rows: list[sqlite3.Row]) -> None:
    if not rows:
        await send_text(bot, chat_id, "❌ Kino topilmadi.")
        return
    buttons = []
    for row in rows:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"🎬 {row['title']} · {row['code']}", callback_data=f"manage:{row['id']}"
                )
            ]
        )
    await send_text(
        bot,
        chat_id,
        f"📋 {len(rows)} ta kino:",
        reply_markup=InlineKeyboardMarkup(
            buttons + [[InlineKeyboardButton("📚 Barcha kinolar", callback_data="manage_page:0")]]
        ),
    )


async def show_all_movies(bot: Any, chat_id: int, page: int = 0) -> None:
    total = int(db.execute("SELECT COUNT(*) AS n FROM movies", one=True)["n"])
    if total == 0:
        await send_text(bot, chat_id, "📋 Hali kinolar saqlanmagan.")
        return

    total_pages = max(1, (total + MOVIES_PAGE_SIZE - 1) // MOVIES_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    rows = db.execute(
        """
        SELECT id, code, title, content_type
        FROM movies
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (MOVIES_PAGE_SIZE, page * MOVIES_PAGE_SIZE),
        all_rows=True,
    )
    buttons = [
        [
            InlineKeyboardButton(
                f"{'📺' if row['content_type'] == 'serial' else '🎬'} "
                f"{str(row['title'])[:42]} · {row['code']}",
                callback_data=f"manage:{row['id']}",
            )
        ]
        for row in rows
    ]
    navigation = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton("⬅️ Oldingi", callback_data=f"manage_page:{page - 1}")
        )
    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton("Keyingi ➡️", callback_data=f"manage_page:{page + 1}")
        )
    if navigation:
        buttons.append(navigation)
    buttons.append([InlineKeyboardButton("⬅️ Admin panel", callback_data="admin_home")])
    await send_text(
        bot,
        chat_id,
        f"📋 Kinolar: {total} ta\n"
        f"📄 Sahifa: {page + 1}/{total_pages}\n"
        "Kod va nom bo‘yicha kerakli kinoni tanlang:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_manage_movie(bot: Any, chat_id: int, movie: sqlite3.Row) -> None:
    await send_movie_card(bot, chat_id, movie)
    await send_text(
        bot,
        chat_id,
        "Kino boshqaruvi:",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✏️ Kod", callback_data=f"movie_edit:{movie['id']}:code"),
                    InlineKeyboardButton("✏️ Nom", callback_data=f"movie_edit:{movie['id']}:title"),
                ],
                [
                    InlineKeyboardButton("✏️ Poster", callback_data=f"movie_edit:{movie['id']}:poster"),
                    InlineKeyboardButton("✏️ Video", callback_data=f"movie_edit:{movie['id']}:video"),
                ],
                [
                    InlineKeyboardButton("✏️ Tavsif", callback_data=f"movie_edit:{movie['id']}:caption"),
                    InlineKeyboardButton("🗑 O‘chirish", callback_data=f"movie_delete:{movie['id']}"),
                ],
                [InlineKeyboardButton("📚 Kinolar ro‘yxati", callback_data="manage_page:0")],
            ]
        ),
    )


async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not CHANNEL_ID:
        await reply_text(update, "❌ CHANNEL_ID sozlanmagan. Avval kanal ID sini kiriting.")
        return
    context.user_data.clear()
    context.user_data["state"] = "post_code"
    await reply_text(
        update,
        "[1/3] 🎬 Kino kodini kiriting:",
        reply_markup=flow_keyboard(CANCEL_BUTTON),
    )


def media_from_message(message: Message) -> tuple[str, str] | None:
    if message.video:
        return "video", message.video.file_id
    if message.photo:
        return "photo", message.photo[-1].file_id
    if message.audio:
        return "audio", message.audio.file_id
    if message.animation:
        return "animation", message.animation.file_id
    if message.document:
        return "document", message.document.file_id
    return None


def split_translation_chunks(text: str, limit: int = 6000) -> list[str]:
    """Split long input without dropping any characters before AI translation."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        boundary = remaining.rfind("\n", 0, limit + 1)
        if boundary < limit // 2:
            boundary = remaining.rfind(" ", 0, limit + 1)
        if boundary <= 0:
            boundary = limit
        else:
            boundary += 1
        chunks.append(remaining[:boundary])
        remaining = remaining[boundary:]
    return chunks


async def send_media(
    bot: Any,
    chat_id: int | str,
    media_type: str,
    file_id: str,
    caption: str = "",
    reply_markup: Any = None,
    protect_content: bool | None = None,
) -> Message:
    caption = normalize_emojis(caption)
    kwargs: dict[str, Any] = {"chat_id": chat_id, "caption": caption[:1024] or None}
    kwargs["protect_content"] = (
        forward_protection_enabled()
        if protect_content is None
        else protect_content
    )
    if caption:
        kwargs["caption_entities"] = premium_entities(caption[:1024]) or None
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    if media_type == "photo":
        return await bot.send_photo(photo=file_id, **kwargs)
    if media_type == "video":
        kwargs["supports_streaming"] = True
        return await bot.send_video(video=file_id, **kwargs)
    if media_type == "audio":
        return await bot.send_audio(audio=file_id, **kwargs)
    if media_type == "animation":
        return await bot.send_animation(animation=file_id, **kwargs)
    return await bot.send_document(document=file_id, **kwargs)


async def create_post_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.user_data
    await send_media(
        context.bot,
        update.effective_chat.id,
        data["media_type"],
        data["media_file_id"],
        data.get("caption", ""),
        InlineKeyboardMarkup(
            [
                [styled_inline_button("🎬 Filmni ko‘rish", style="primary", callback_data="post_preview_watch")],
                [InlineKeyboardButton("✅ E'lon qilish", callback_data="post_publish")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="flow_cancel")],
            ]
        ),
    )
    await reply_text(update, "👀 Postni ko‘rib chiqing. Tayyor bo‘lsa, e'lon qilishni bosing.")


async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    context.user_data["state"] = "broadcast_media"
    await reply_text(
        update,
        "🖼 Rasm, video, audio, GIF yoki fayl yuboring. Tagiga matn yozishingiz mumkin.",
        reply_markup=flow_keyboard(CANCEL_BUTTON),
    )


async def start_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await channels_menu(update.effective_chat.id, context.bot)
    context.user_data["state"] = ""


async def channels_menu(chat_id: int, bot: Any) -> None:
    channels = db.execute("SELECT * FROM channels ORDER BY id", all_rows=True)
    text = "📢 Majburiy obuna kanallari\n\n"
    if not channels:
        text += "Hozircha kanal qo‘shilmagan."
    else:
        for channel in channels:
            status = "🟢 Faol" if channel["active"] else "⏸️ To‘xtatilgan"
            limit = channel["member_limit"] or "Cheksiz"
            text += (
                f"\n📢 {channel['title']}\n"
                f"🆔 {channel['channel_id']}\n"
                f"🔎 Tekshiruv: {'Tashqi havola' if channel['verification_type'] == 'external' else 'Telegram kanal'}\n"
                f"{status} · 🎯 Limit: {limit}\n"
            )
    buttons = [
        [InlineKeyboardButton("➕ Kanal qo‘shish", callback_data="channel_add")]
    ]
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    f"📢 {channel['title']}", callback_data=f"channel:{channel['id']}"
                )
            ]
            for channel in channels
        ]
    )
    buttons.append([InlineKeyboardButton("⬅️ Admin panel", callback_data="admin_home")])
    await send_text(bot, chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))


async def show_channel(bot: Any, chat_id: int, channel_id: int) -> None:
    channel = db.execute("SELECT * FROM channels WHERE id = ?", (channel_id,), one=True)
    if not channel:
        await channels_menu(chat_id, bot)
        return
    status = "🟢 Faol" if channel["active"] else "⏸️ To‘xtatilgan"
    await send_text(
        bot,
        chat_id,
        f"📢 {channel['title']}\n🆔 {channel['channel_id']}\n"
        f"🔎 Tekshiruv: {'Tashqi havola' if channel['verification_type'] == 'external' else 'Telegram kanal'}\n"
        f"{status}\n🔗 {channel['invite_link'] or 'Havola yo‘q'}",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⏸️ To‘xtatish" if channel["active"] else "▶️ Yoqish",
                        callback_data=f"channel_toggle:{channel_id}",
                    ),
                    InlineKeyboardButton("✏️ Nomi", callback_data=f"channel_edit:{channel_id}:title"),
                ],
                [
                    InlineKeyboardButton("🔗 Havola", callback_data=f"channel_edit:{channel_id}:link"),
                    InlineKeyboardButton("🎯 Limit", callback_data=f"channel_edit:{channel_id}:limit"),
                ],
                [
                    InlineKeyboardButton("🔄 Nollash", callback_data=f"channel_reset:{channel_id}"),
                    InlineKeyboardButton("🗑 O‘chirish", callback_data=f"channel_delete:{channel_id}"),
                ],
                [InlineKeyboardButton("⬅️ Ro‘yxatga qaytish", callback_data="channels_list")],
            ]
        ),
    )


async def vip_settings_menu(bot: Any, chat_id: int) -> None:
    price = db.setting("vip_price", "5000")
    card = db.setting("vip_card_number", "") or "kiritilmagan"
    owner = db.setting("vip_card_owner", "") or "kiritilmagan"
    pending = db.execute(
        "SELECT COUNT(*) AS n FROM vip_payments WHERE status = 'pending'", one=True
    )["n"]
    await send_text(
        bot,
        chat_id,
        f"💎 VIP sozlamalari\n\n"
        f"💰 1 oy narxi: {price} so‘m\n"
        f"💳 Karta: {card}\n"
        f"👤 Egasi: {owner}\n"
        f"⏳ Kutilayotgan to‘lovlar: {pending}",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💳 Kartani almashtirish", callback_data="vip_card_edit")],
                [InlineKeyboardButton("💰 Narxni o‘zgartirish", callback_data="vip_price_edit")],
                [InlineKeyboardButton("⬅️ Admin panel", callback_data="admin_home")],
            ]
        ),
    )


def _openai_health_check() -> None:
    _openai_json_request(
        "chat/completions",
        {
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": "Reply only: OK"}],
            "max_tokens": 8,
        },
        timeout=30,
    )


def _gemini_health_check() -> None:
    _gemini_generate_content("Reply only: OK")


def _ai_status_text() -> str:
    openai_key = "🟢 sozlangan" if OPENAI_API_KEY else "🔴 yo‘q"
    gemini_key = "🟢 sozlangan" if GEMINI_API_KEY else "🔴 yo‘q"
    last_provider = db.setting("ai_last_provider", "Hali ishlatilmagan")
    last_success = db.setting("ai_last_success_at", "—")
    openai_check = db.setting("ai_openai_check", "Hali tekshirilmagan")
    gemini_check = db.setting("ai_gemini_check", "Hali tekshirilmagan")
    return (
        "🤖 AI holati\n\n"
        f"OpenAI kaliti: {openai_key} ({OPENAI_KEY_SOURCE})\n"
        f"Gemini kaliti: {gemini_key} ({GEMINI_KEY_SOURCE})\n\n"
        "Ishlash tartibi: OpenAI asosiy → Gemini fallback\n"
        f"Oxirgi muvaffaqiyatli provider: {last_provider}\n"
        f"Oxirgi muvaffaqiyatli vaqt: {last_success}\n\n"
        f"OpenAI testi: {openai_check}\n"
        f"Gemini testi: {gemini_check}\n\n"
        "Kalitlarni Replit Secrets bo‘limida yangilang, keyin botni qayta ishga tushiring."
    )


async def ai_status_menu(bot: Any, chat_id: int) -> None:
    await send_text(
        bot,
        chat_id,
        _ai_status_text(),
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🧪 AI ni hozir tekshirish", callback_data="ai_health_check")],
                [InlineKeyboardButton("⬅️ Admin panel", callback_data="admin_home")],
            ]
        ),
    )


async def run_ai_health_check(bot: Any, chat_id: int) -> None:
    await send_text(bot, chat_id, "🧪 OpenAI va Gemini tekshirilmoqda...")
    try:
        await asyncio.to_thread(_openai_health_check)
        db.set_setting("ai_openai_check", f"🟢 ishladi ({now_text()})")
    except Exception as error:
        logger.warning("OpenAI health check xatosi: %s", error)
        db.set_setting("ai_openai_check", f"🔴 ishlamadi ({type(error).__name__})")
    try:
        await asyncio.to_thread(_gemini_health_check)
        db.set_setting("ai_gemini_check", f"🟢 ishladi ({now_text()})")
    except Exception as error:
        logger.warning("Gemini health check xatosi: %s", error)
        db.set_setting("ai_gemini_check", f"🔴 ishlamadi ({type(error).__name__})")
    await ai_status_menu(bot, chat_id)


async def premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    enabled = db.setting("premium_emoji_enabled", "1") == "1"
    mappings = db.execute(
        """
        SELECT id, unicode_emoji, custom_emoji_id, active
        FROM premium_emojis
        ORDER BY id DESC
        """,
        all_rows=True,
    )
    status = "🟢 Yoqilgan" if enabled else "🔴 O‘chirilgan"
    lines = [
        "✨ <b>Premium emoji sozlamalari</b>",
        "",
        f"Holat: {status}",
        "Oddiy emoji belgilarini xabarlarda premium custom emoji ko‘rinishiga almashtiradi.",
        "",
    ]
    if mappings:
        lines.append("<b>Mappinglar:</b>")
        for row in mappings:
            row_status = "🟢" if row["active"] else "⏸️"
            lines.append(
                f"{row_status} {row['unicode_emoji']} · ID: {row['custom_emoji_id']}"
            )
    else:
        lines.append("Hali mapping qo‘shilmagan.")
    buttons = [
        [
            InlineKeyboardButton("➕ Emoji qo‘shish", callback_data="premium_add"),
            InlineKeyboardButton(
                "🔴 O‘chirish" if enabled else "🟢 Yoqish",
                callback_data="premium_toggle",
            ),
        ]
    ]
    for row in mappings:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"✏️ {row['unicode_emoji']} ni almashtirish",
                    callback_data=f"premium_edit:{row['id']}",
                ),
                InlineKeyboardButton(
                    "🗑",
                    callback_data=f"premium_delete:{row['id']}",
                ),
            ]
        )
    buttons.append([InlineKeyboardButton("⬅️ Admin panel", callback_data="admin_home")])
    await send_text(
        context.bot,
        update.effective_chat.id,
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def stats_text() -> str:
    users = db.execute("SELECT COUNT(*) AS n FROM users", one=True)["n"]
    active = db.execute("SELECT COUNT(*) AS n FROM users WHERE active = 1", one=True)["n"]
    new_today = db.execute(
        "SELECT COUNT(*) AS n FROM users WHERE joined_at >= datetime('now', '-1 day')",
        one=True,
    )["n"]
    seen_today = db.execute(
        "SELECT COUNT(*) AS n FROM users WHERE last_seen >= datetime('now', '-1 day')",
        one=True,
    )["n"]
    movies = db.execute("SELECT COUNT(*) AS n FROM movies", one=True)["n"]
    serials = db.execute(
        "SELECT COUNT(*) AS n FROM movies WHERE content_type = 'serial'", one=True
    )["n"]
    episodes = db.execute("SELECT COUNT(*) AS n FROM episodes", one=True)["n"]
    views = db.execute("SELECT COALESCE(SUM(views), 0) AS n FROM movies", one=True)["n"]
    music = db.execute("SELECT COUNT(*) AS n FROM music_library", one=True)["n"]
    favorites = db.execute("SELECT COUNT(*) AS n FROM favorites", one=True)["n"]
    channels = db.execute(
        "SELECT COUNT(*) AS n FROM channels WHERE active = 1", one=True
    )["n"]
    sent = db.execute(
        "SELECT COALESCE(SUM(sent_count), 0) AS n FROM broadcasts", one=True
    )["n"]
    failed = db.execute(
        "SELECT COALESCE(SUM(failed_count), 0) AS n FROM broadcasts", one=True
    )["n"]
    broadcasts = db.execute("SELECT COUNT(*) AS n FROM broadcasts", one=True)["n"]
    starts = db.setting("start_count", "0")
    subscription_prompts = db.setting("subscription_prompt_count", "0")
    subscription_successes = db.setting("subscription_success_count", "0")
    top = db.execute(
        "SELECT title, code, views FROM movies ORDER BY views DESC, id DESC LIMIT 10",
        all_rows=True,
    )
    top_text = "\n".join(
        f"{index}. {row['title']} · {row['views']} ta"
        for index, row in enumerate(top, 1)
    ) or "Hali ko‘rishlar yo‘q."
    return (
        f"📊 Statistika\n\n"
        f"👥 Jami foydalanuvchilar: {users}\n"
        f"🚀 /start bosganlar: {starts}\n"
        f"🟢 Faol foydalanuvchilar: {active}\n"
        f"🆕 Oxirgi 24 soatda yangi: {new_today}\n"
        f"👀 Oxirgi 24 soatda faol: {seen_today}\n"
        f"📢 Obuna oynasi ko‘rsatilgan: {subscription_prompts}\n"
        f"✅ Obunasi tasdiqlangan tekshiruvlar: {subscription_successes}\n"
        f"🎬 Jami kinolar: {movies}\n"
        f"📺 Seriallar: {serials} · 🎞 Qismlar: {episodes}\n"
        f"👀 Jami ko‘rishlar: {views}\n"
        f"🎵 Musiqa katalogi: {music} ta\n"
        f"😍 Sevimlilarga qo‘shilganlar: {favorites}\n"
        f"📢 Majburiy kanallar: {channels}\n"
        f"📤 Broadcastlar: {broadcasts}\n"
        f"✅ Yetkazilgan: {sent} · ❌ Xatolik: {failed}\n"
        f"💾 Baza: {Path(DB_PATH).stat().st_size // 1024 if Path(DB_PATH).exists() else 0} KB\n\n"
        f"🔥 Top kinolar:\n{top_text}"
    )


async def broadcast_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    broadcast_id = int(context.job.data)
    await run_broadcast(context.bot, broadcast_id)


async def database_backup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        db.backup(DB_BACKUP_PATH)
        logger.info("SQLite zaxira nusxasi yangilandi.")
    except sqlite3.Error:
        logger.exception("SQLite zaxira nusxasini yaratib bo‘lmadi.")


async def run_broadcast(bot: Any, broadcast_id: int) -> None:
    row = db.execute(
        "SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,), one=True
    )
    if not row or row["status"] == "done":
        return
    db.execute("UPDATE broadcasts SET status = 'sending' WHERE id = ?", (broadcast_id,))
    buttons_data = json.loads(row["buttons_json"] or "[]")
    markup = None
    if buttons_data:
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(str(label), url=str(url))] for label, url in buttons_data]
        )
    users = db.user_ids(int(row["audience_limit"]) if row["audience_type"] == "count" else None)
    sent_count = 0
    failed_count = 0
    started = time.monotonic()
    for user_id in users:
        try:
            await send_media(
                bot,
                user_id,
                str(row["media_type"]),
                str(row["media_file_id"]),
                str(row["caption"] or ""),
                markup,
            )
            sent_count += 1
            await asyncio.sleep(0.06)
        except RetryAfter as error:
            await asyncio.sleep(float(error.retry_after) + 0.5)
            try:
                await send_media(
                    bot,
                    user_id,
                    str(row["media_type"]),
                    str(row["media_file_id"]),
                    str(row["caption"] or ""),
                    markup,
                )
                sent_count += 1
            except TelegramError:
                failed_count += 1
        except TelegramError:
            failed_count += 1
            db.execute("UPDATE users SET active = 0 WHERE user_id = ?", (user_id,))
    db.execute(
        """
        UPDATE broadcasts
        SET status = 'done', sent_count = ?, failed_count = ?, completed_at = ?
        WHERE id = ?
        """,
        (sent_count, failed_count, now_text(), broadcast_id),
    )
    logger.info(
        "Broadcast #%s tugadi: %s/%s, %.1fs",
        broadcast_id,
        sent_count,
        len(users),
        time.monotonic() - started,
    )


def parse_button_line(line: str) -> tuple[str, str] | None:
    if "|" not in line:
        return None
    label, url = [part.strip() for part in line.split("|", 1)]
    if not label or not (url.startswith("https://") or url.startswith("http://")):
        return None
    return label[:64], url[:512]


async def handle_admin_state(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: str
) -> bool:
    message = update.effective_message
    text = (message.text or "").strip()
    data = context.user_data
    user_id = update.effective_user.id
    language = user_language(user_id)

    if text == VIDEO_DOWNLOADER_BUTTON:
        context.user_data.clear()
        context.user_data["state"] = "video_downloader"
        await reply_text(
            update,
            russian_user_text(
                user_id,
                "📥 Video havolasini yuboring (YouTube, Shorts, Instagram, TikTok, Facebook va yt-dlp qo‘llaydigan boshqa saytlar).\n\n"
                "⚠️ Ochiq/public video bo‘lsin va 49 MB dan kichik bo‘lsin.",
                "📥 Отправьте ссылку на видео (YouTube, Shorts, Instagram, TikTok, Facebook и другие сайты, поддерживаемые yt-dlp).\n\n"
                "⚠️ Видео должно быть открытым и меньше 49 МБ.",
            ),
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
        return True
    elif context.user_data.get("state") == "video_downloader":
        url = first_supported_url(text)
        if not url:
            await reply_text(
                update,
                "❌ To‘g‘ri http/https video havolasini yuboring.",
                reply_markup=flow_keyboard(CANCEL_BUTTON),
            )
            return
        progress_message = await reply_text(
            update, progress_text("📥 Video yuklanmoqda...", 10)
        )
        path = ""
        try:
            await update_progress(progress_message, "📥 Video yuklanmoqda...", 25)
            path, title = await download_video(url)
            await update_progress(progress_message, "📤 Telegramga yuborilmoqda...", 80)
            await send_local_video_with_fallback(
                context.bot,
                update.effective_chat.id,
                path,
                caption=f"🎬 {title[:900]}",
                supports_streaming=True,
            )
            await update_progress(progress_message, "✅ Tayyor", 100)
        except Exception as error:
            logger.exception("Video yuklashda xatolik: %s", error)
            error_text = str(error).lower()
            if "49 mb" in error_text or "max_filesize" in error_text:
                message_text = "❌ Video 49 MB dan katta. Kichikroq video yuboring."
            else:
                message_text = (
                    "❌ Videoni yuklab bo‘lmadi. Havola ochiq/public bo‘lsin, "
                    "yoki boshqa havolani sinab ko‘ring."
                )
            await reply_text(update, message_text)
        finally:
            if path:
                shutil.rmtree(str(Path(path).parent), ignore_errors=True)
            context.user_data.clear()
            await send_text(
                context.bot,
                update.effective_chat.id,
                "Menyu:",
                reply_markup=user_keyboard(is_admin(user_id), language),
            )
        return True
    elif text in {CANCEL_BUTTON, BACK_BUTTON, "/cancel"}:
        context.user_data.clear()
        await reply_text(
            update,
            "❌ Joriy jarayon bekor qilindi.",
            reply_markup=admin_keyboard(),
        )
        return True

    if state == "vip_card_number":
        if not text or len(text) > 64:
            await reply_text(update, "❌ Karta raqamini to‘g‘ri yuboring.")
            return True
        db.set_setting("vip_card_number", text)
        context.user_data["state"] = "vip_card_owner"
        await reply_text(update, "👤 Karta egasi nomini yuboring yoki `-` yozing:")
        return True
    if state == "vip_card_owner":
        db.set_setting("vip_card_owner", "" if text == "-" else text[:128])
        context.user_data.clear()
        await reply_text(update, "✅ VIP karta ma’lumotlari saqlandi.", reply_markup=admin_keyboard())
        return True
    if state == "vip_price":
        if not text.isdigit() or int(text) < 1:
            await reply_text(update, "❌ Narxni musbat son bilan yuboring.")
            return True
        db.set_setting("vip_price", str(int(text)))
        context.user_data.clear()
        await reply_text(update, f"✅ VIP narxi {int(text)} so‘m qilib saqlandi.", reply_markup=admin_keyboard())
        return True
    if state == "vip_payment":
        if not message.photo and not message.document:
            await reply_text(update, "❌ To‘lov chekini rasm yoki fayl ko‘rinishida yuboring.")
            return True
        file_id = (
            message.photo[-1].file_id
            if message.photo
            else message.document.file_id
        )
        receipt_type = "photo" if message.photo else "document"
        payment_id = db.execute(
            """
            INSERT INTO vip_payments(user_id, amount, receipt_file_id, receipt_type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (update.effective_user.id, int(db.setting("vip_price", "5000")), file_id, receipt_type, now_text()),
        )
        context.user_data.clear()
        await notify_vip_payment_admins(
            context.bot, payment_id, update.effective_user.id,
            int(db.setting("vip_price", "5000")), message,
        )
        await reply_text(update, "✅ Chek adminga yuborildi. Tasdiqlanishini kuting.")
        return True

    if state == "database_import":
        document = message.document
        filename = str(document.file_name or "").casefold() if document else ""
        if not document or not filename.endswith((".sqlite", ".sqlite3", ".db")):
            await reply_text(update, "❌ .sqlite, .sqlite3 yoki .db fayl yuboring.")
            return True
        if document.file_size and int(document.file_size) > 100 * 1024 * 1024:
            await reply_text(update, "❌ Baza fayli 100 MB dan katta bo‘lmasin.")
            return True
        try:
            temporary = tempfile.NamedTemporaryFile(
                prefix="database-import-", suffix=".sqlite3", delete=False
            )
            temporary.close()
            await (await context.bot.get_file(document.file_id)).download_to_drive(
                custom_path=temporary.name
            )
            valid, reason = db.validate_database(temporary.name)
            if not valid:
                Path(temporary.name).unlink(missing_ok=True)
                await reply_text(update, f"❌ {reason}")
                return True
            data["database_import_path"] = temporary.name
            data["state"] = ""
            await send_text(
                context.bot,
                update.effective_chat.id,
                "✅ Baza tekshiruvdan o‘tdi. Joriy baza zaxiraga olinadi va yuklangan baza "
                "uning ma’lumotlariga qo‘shiladi. Qo‘shishni tasdiqlaysizmi?",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Ha, qo‘shish", callback_data="database_restore_yes"),
                    InlineKeyboardButton("❌ Yo‘q", callback_data="database_restore_no"),
                ]]),
            )
        except (OSError, TelegramError, sqlite3.Error) as error:
            logger.exception("Baza importida xatolik: %s", error)
            await reply_text(update, "❌ Baza faylini qabul qilib bo‘lmadi.")
        return True

    if state == "music_collection_name":
        if not text or len(text) > 255:
            await reply_text(update, "❌ To‘plam nomini 1–255 belgida yuboring.")
            return True
        collection = db.execute(
            "SELECT id FROM music_collections WHERE name = ?",
            (text,),
            one=True,
        )
        if collection:
            collection_id = int(collection["id"])
            status = "Bu to‘plam avval mavjud edi."
        else:
            collection_id = int(
                db.execute(
                    "INSERT INTO music_collections(name, created_at) VALUES (?, ?)",
                    (text, now_text()),
                )
            )
            status = "Yangi to‘plam yaratildi."
        data["music_collection_id"] = collection_id
        data["music_collection_name"] = text
        data["state"] = "music_collection_file"
        await reply_text(
            update,
            f"✅ {status}\n📁 {text}\n\n"
            "Endi audio yoki audio fayllarni birma-bir yuboring. "
            f"Yakunlagach {COLLECTION_DONE_BUTTON} tugmasini bosing.",
            reply_markup=flow_keyboard(COLLECTION_DONE_BUTTON, CANCEL_BUTTON),
        )
        return True

    if state == "music_collection_file":
        if text == COLLECTION_DONE_BUTTON:
            collection_id = int(data.get("music_collection_id") or 0)
            count = db.execute(
                "SELECT COUNT(*) AS n FROM music_library WHERE collection_id = ?",
                (collection_id,),
                one=True,
            )["n"]
            name = str(data.get("music_collection_name") or "To‘plam")
            db.backup(DB_BACKUP_PATH)
            context.user_data.clear()
            await reply_text(
                update,
                f"✅ 📁 {name} to‘plami saqlandi.\n🎵 Jami: {count} ta musiqa.",
                reply_markup=admin_keyboard(),
            )
            return True
        media = media_from_message(message)
        if not media or media[0] not in {"audio", "document"}:
            await reply_text(
                update,
                "❌ Audio yoki audio fayl yuboring. Tugatish uchun "
                f"{COLLECTION_DONE_BUTTON} ni bosing.",
            )
            return True
        collection_id = int(data["music_collection_id"])
        if message.audio:
            title = str(message.audio.title or "").strip()
            performer = str(message.audio.performer or "").strip()
        else:
            title = ""
            performer = ""
        if not title and message.document:
            title = str(message.document.file_name or "").strip()
        title = (title or (message.caption or "").splitlines()[0].strip() or "Nomsiz musiqa")[:255]
        caption = (message.caption or "")[:1024]
        track_number = db.execute(
            "SELECT COUNT(*) AS n FROM music_library WHERE collection_id = ?",
            (collection_id,),
            one=True,
        )["n"] + 1
        db.execute(
            """
            INSERT INTO music_library(
                title, performer, file_id, media_type, caption, collection_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                performer[:255],
                media[1],
                media[0],
                caption,
                collection_id,
                now_text(),
            ),
        )
        await reply_text(
            update,
            f"✅ {track_number}-musiqa qo‘shildi: {title}\n"
            f"Yana yuboring yoki {COLLECTION_DONE_BUTTON} ni bosing.",
            reply_markup=flow_keyboard(COLLECTION_DONE_BUTTON, CANCEL_BUTTON),
        )
        return True

    if state == "music_add_file":
        media = media_from_message(message)
        if not media or media[0] not in {"audio", "document"}:
            await reply_text(update, "❌ Audio yoki audio fayl yuboring.")
            return True
        data["music_file_id"] = media[1]
        data["music_media_type"] = media[0]
        data["state"] = "music_add_title"
        await reply_text(update, "🎵 Qo‘shiq nomini yuboring:")
        return True
    if state == "music_add_title":
        if not text:
            await reply_text(update, "❌ Qo‘shiq nomi bo‘sh bo‘lmasin.")
            return True
        data["music_title"] = text[:255]
        data["state"] = "music_add_performer"
        await reply_text(update, "👤 Ijrochi nomini yuboring yoki `-` yozing:")
        return True
    if state == "music_add_performer":
        data["music_performer"] = "" if text == "-" else text[:255]
        data["state"] = "music_add_caption"
        await reply_text(
            update,
            "📝 Musiqa tavsifini yuboring yoki ⏭ Tavsifsiz saqlash tugmasini bosing:",
            reply_markup=flow_keyboard(SKIP_BUTTON, CANCEL_BUTTON),
        )
        return True
    if state == "music_add_caption":
        if text == SKIP_BUTTON:
            caption = ""
        elif text:
            caption = text[:1024]
        else:
            await reply_text(update, "❌ Tavsif matn yoki skip tugmasi bo‘lishi kerak.")
            return True
        db.execute(
            """
            INSERT INTO music_library(title, performer, file_id, media_type, caption, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["music_title"],
                data.get("music_performer", ""),
                data["music_file_id"],
                data.get("music_media_type", "audio"),
                caption,
                now_text(),
            ),
        )
        db.backup(DB_BACKUP_PATH)
        context.user_data.clear()
        await reply_text(update, "✅ Musiqa katalogga qo‘shildi.", reply_markup=admin_keyboard())
        return True

    if state == "channel_type":
        value = text.casefold()
        if value not in {"telegram", "external", "tashqi"}:
            await reply_text(update, "❌ `telegram` yoki `external` deb yuboring.")
            return True
        data["channel_type"] = "external" if value in {"external", "tashqi"} else "telegram"
        data["state"] = "channel_id"
        await reply_text(
            update,
            "📢 Telegram kanal ID/@username yuboring. Tashqi havola uchun `external` deb yozing:",
        )
        return True

    if state == "add_code":
        if not text or len(text) > 64:
            await reply_text(update, "❌ Kodni matn ko‘rinishida yuboring.")
            return True
        if db.execute("SELECT id FROM movies WHERE code = ?", (text,), one=True):
            await reply_text(update, "❌ Bu kod band. Boshqa kod yuboring.")
            return True
        data["draft"] = {"code": text}
        data["state"] = "add_title"
        await reply_text(update, "[2/5] 📝 Kino nomini yuboring:")
        return True

    if state == "add_title":
        if not text:
            await reply_text(update, "❌ Kino nomi bo‘sh bo‘lmasin.")
            return True
        data["draft"]["title"] = text[:255]
        data["state"] = "add_video"
        await reply_text(update, "[3/4] 🎥 Kino videosini yuboring:")
        return True

    if state == "add_video":
        if message.video:
            data["draft"]["video_file_id"] = message.video.file_id
            data["draft"]["media_type"] = "video"
        elif message.document:
            data["draft"]["video_file_id"] = message.document.file_id
            data["draft"]["media_type"] = "document"
        else:
            await reply_text(update, "❌ Video yoki video fayl yuboring.")
            return True
        data["state"] = "add_caption"
        await reply_text(update, "[4/4] 📝 Tavsif yuboring yoki ⏭ Tavsifsiz saqlash tugmasini bosing.")
        return True

    if state == "add_caption":
        if text == SKIP_BUTTON:
            data["draft"]["caption"] = ""
        elif text:
            data["draft"]["caption"] = text
        else:
            await reply_text(update, "❌ Tavsif matn yoki skip tugmasi bo‘lishi kerak.")
            return True
        data["state"] = "movie_preview"
        await show_movie_draft(context.bot, update.effective_chat.id, data["draft"])
        return True

    if state == "serial_code":
        if not text or len(text) > 64:
            await reply_text(update, "❌ Serial kodini matn ko‘rinishida yuboring.")
            return True
        if db.execute("SELECT id FROM movies WHERE code = ?", (text,), one=True):
            await reply_text(update, "❌ Bu kod band. Boshqa kod yuboring.")
            return True
        data["serial"] = {"code": text}
        data["state"] = "serial_title"
        await reply_text(update, "[2/4] 📝 Serial nomini yuboring:")
        return True

    if state == "serial_title":
        if not text:
            await reply_text(update, "❌ Serial nomi bo‘sh bo‘lmasin.")
            return True
        data["serial"]["title"] = text[:255]
        data["state"] = "serial_caption"
        await reply_text(
            update,
            "[3/4] 📝 Serial tavsifini yuboring yoki ⏭ Tavsifsiz saqlash tugmasini bosing:",
            reply_markup=flow_keyboard(SKIP_BUTTON, CANCEL_BUTTON),
        )
        return True

    if state == "serial_caption":
        if text == SKIP_BUTTON:
            data["serial"]["caption"] = ""
        elif text:
            data["serial"]["caption"] = text
        else:
            await reply_text(update, "❌ Tavsif matn yoki skip tugmasi bo‘lishi kerak.")
            return True
        data["state"] = "serial_episode"
        await reply_text(
            update,
            "[4/4] 🎞 Serial qismini yuboring. Birinchi video 1-qism bo‘lib saqlanadi:",
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
        return True

    if state == "serial_episode":
        media = media_from_message(message)
        if not media or media[0] not in {"video", "document"}:
            await reply_text(update, "❌ Serial qismini video yoki video fayl qilib yuboring.")
            return True
        serial = data.get("serial", {})
        movie_id = data.get("serial_movie_id")
        if not movie_id:
            try:
                movie_id = int(
                    db.execute(
                        """
                        INSERT INTO movies(
                            code, title, caption, content_type, media_type, created_at
                        ) VALUES (?, ?, ?, 'serial', ?, ?)
                        """,
                        (
                            serial["code"],
                            serial["title"],
                            serial.get("caption", ""),
                            media[0],
                            now_text(),
                        ),
                    )
                )
            except sqlite3.IntegrityError:
                await reply_text(update, "❌ Bu serial kodi band.")
                data.clear()
                return True
            data["serial_movie_id"] = movie_id
            db.backup(DB_BACKUP_PATH)
        next_episode = db.execute(
            """
            SELECT COALESCE(MAX(episode_number), 0) + 1 AS next_episode
            FROM episodes WHERE movie_id = ?
            """,
            (movie_id,),
            one=True,
        )["next_episode"]
        db.execute(
            """
            INSERT INTO episodes(
                movie_id, episode_number, video_file_id, media_type, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (movie_id, next_episode, media[1], media[0], now_text()),
        )
        db.backup(DB_BACKUP_PATH)
        await send_text(
            context.bot,
            update.effective_chat.id,
            f"✅ {next_episode}-qism saqlandi.\nPastdagi tugma orqali yana qism qo‘shishingiz mumkin.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("➕ Yana qism qo‘shish", callback_data=f"serial_add:{movie_id}")],
                    [InlineKeyboardButton("✅ Serialni saqlash", callback_data=f"serial_finish:{movie_id}")],
                ]
            ),
        )
        return True

    if state == "draft_code":
        draft = data["draft"]
        if db.execute(
            "SELECT id FROM movies WHERE code = ?", (text,), one=True
        ):
            await reply_text(update, "❌ Bu kod band.")
            return True
        draft["code"] = text
        data["state"] = "movie_preview"
        await show_movie_draft(context.bot, update.effective_chat.id, draft)
        return True
    if state == "draft_title":
        data["draft"]["title"] = text[:255]
        data["state"] = "movie_preview"
        await show_movie_draft(context.bot, update.effective_chat.id, data["draft"])
        return True
    if state == "draft_caption":
        data["draft"]["caption"] = "" if text == SKIP_BUTTON else text
        data["state"] = "movie_preview"
        await show_movie_draft(context.bot, update.effective_chat.id, data["draft"])
        return True
    if state in {"draft_poster", "draft_video"}:
        if state == "draft_poster" and message.photo:
            data["draft"]["poster_file_id"] = message.photo[-1].file_id
        elif state == "draft_video" and message.video:
            data["draft"]["video_file_id"] = message.video.file_id
            data["draft"]["media_type"] = "video"
        elif state == "draft_video" and message.document:
            data["draft"]["video_file_id"] = message.document.file_id
            data["draft"]["media_type"] = "document"
        else:
            await reply_text(update, "❌ Kerakli media turini yuboring.")
            return True
        data["state"] = "movie_preview"
        await show_movie_draft(context.bot, update.effective_chat.id, data["draft"])
        return True

    if state == "manage_search":
        if text == "/allmovies":
            rows = db.execute(
                "SELECT * FROM movies ORDER BY id DESC LIMIT 50", all_rows=True
            )
        else:
            rows = movie_search(text)
        await manage_results(context.bot, update.effective_chat.id, rows)
        return True

    if state.startswith("movie_edit_"):
        movie_id = int(data["editing_movie_id"])
        movie = movie_by_id(movie_id)
        if not movie:
            await reply_text(update, "❌ Kino topilmadi.")
            data["state"] = ""
            return True
        field = state.removeprefix("movie_edit_")
        if field == "poster":
            if not message.photo:
                await reply_text(update, "❌ Rasm yuboring.")
                return True
            db.execute(
                "UPDATE movies SET poster_file_id = ? WHERE id = ?",
                (message.photo[-1].file_id, movie_id),
            )
        elif field == "video":
            media = media_from_message(message)
            if not media or media[0] not in {"video", "document"}:
                await reply_text(update, "❌ Video yoki video fayl yuboring.")
                return True
            db.execute(
                "UPDATE movies SET video_file_id = ?, media_type = ? WHERE id = ?",
                (media[1], media[0], movie_id),
            )
        elif field == "code":
            if db.execute(
                "SELECT id FROM movies WHERE code = ? AND id != ?", (text, movie_id), one=True
            ):
                await reply_text(update, "❌ Bu kod band.")
                return True
            db.execute("UPDATE movies SET code = ? WHERE id = ?", (text, movie_id))
        elif field == "title":
            db.execute("UPDATE movies SET title = ? WHERE id = ?", (text[:255], movie_id))
        else:
            db.execute("UPDATE movies SET caption = ? WHERE id = ?", (text, movie_id))
        db.backup(DB_BACKUP_PATH)
        data["state"] = ""
        await send_text(context.bot, update.effective_chat.id, "✅ Kino yangilandi.")
        await show_manage_movie(context.bot, update.effective_chat.id, movie_by_id(movie_id))
        return True

    if state == "post_code":
        movie = db.execute("SELECT id FROM movies WHERE code = ?", (text,), one=True)
        if not movie:
            await reply_text(update, "❌ Bu kodli kino topilmadi.")
            return True
        data["post_movie_id"] = int(movie["id"])
        data["state"] = "post_media"
        await reply_text(update, "[2/3] 🖼 Post uchun rasm yoki video yuboring:")
        return True
    if state == "post_media":
        media = media_from_message(message)
        if not media or media[0] not in {"photo", "video"}:
            await reply_text(update, "❌ Post uchun rasm yoki video yuboring.")
            return True
        data["media_type"], data["media_file_id"] = media
        data["state"] = "post_caption"
        await reply_text(update, "[3/3] 📝 Post captionini yuboring:")
        return True
    if state == "post_caption":
        if not text:
            await reply_text(update, "❌ Caption bo‘sh bo‘lmasin.")
            return True
        data["caption"] = text
        data["state"] = "post_preview"
        await create_post_preview(update, context)
        return True

    if state == "broadcast_media":
        media = media_from_message(message)
        if not media:
            await reply_text(update, "❌ Rasm, video, audio, GIF yoki fayl yuboring.")
            return True
        data["media_type"], data["media_file_id"] = media
        data["caption"] = message.caption or ""
        data["buttons"] = []
        data["state"] = "broadcast_buttons"
        await reply_text(
            update,
            "🔘 Inline tugma qo‘shish uchun `Tugma nomi | https://example.com` formatida yuboring. Tayyor bo‘lsa ✅ Tayyor ni bosing.",
            reply_markup=flow_keyboard(DONE_BUTTON, CANCEL_BUTTON),
        )
        return True
    if state == "broadcast_buttons":
        if text == DONE_BUTTON:
            data["state"] = "broadcast_audience"
            await reply_text(
                update,
                "📊 Qamrovni tanlang:",
                reply_markup=flow_keyboard(ALL_USERS_BUTTON, COUNT_USERS_BUTTON, CANCEL_BUTTON),
            )
            return True
        button = parse_button_line(text)
        if not button:
            await reply_text(update, "❌ Format: Tugma nomi | https://example.com")
            return True
        data["buttons"].append(button)
        await reply_text(update, f"✅ Tugma qo‘shildi. Yana qo‘shing yoki {DONE_BUTTON} ni bosing.")
        return True
    if state == "broadcast_audience":
        if text == ALL_USERS_BUTTON:
            data["audience_type"] = "all"
            data["audience_limit"] = None
        elif text == COUNT_USERS_BUTTON:
            data["state"] = "broadcast_count"
            await reply_text(update, "🔢 Nechta foydalanuvchiga yuborilsin? Son kiriting:")
            return True
        else:
            await reply_text(update, "❌ Qamrov tugmasini tanlang.")
            return True
        data["state"] = "broadcast_timing"
        await reply_text(
            update,
            "Yuborish turini tanlang:",
            reply_markup=flow_keyboard(SEND_NOW_BUTTON, SCHEDULE_BUTTON, CANCEL_BUTTON),
        )
        return True
    if state == "broadcast_count":
        if not text.isdigit() or int(text) < 1:
            await reply_text(update, "❌ Musbat son yuboring.")
            return True
        data["audience_type"] = "count"
        data["audience_limit"] = int(text)
        data["state"] = "broadcast_timing"
        await reply_text(
            update,
            "Yuborish turini tanlang:",
            reply_markup=flow_keyboard(SEND_NOW_BUTTON, SCHEDULE_BUTTON, CANCEL_BUTTON),
        )
        return True
    if state == "broadcast_timing":
        if text == SEND_NOW_BUTTON:
            broadcast_id = create_broadcast(data, None)
            data.clear()
            await reply_text(
                update,
                f"🎉 Vazifa qabul qilindi\n🆔 Vazifa raqami: #{broadcast_id}\n🚀 Yuborish boshlandi!",
                reply_markup=admin_keyboard(),
            )
            asyncio.create_task(run_broadcast(context.bot, broadcast_id))
            return True
        if text == SCHEDULE_BUTTON:
            data["state"] = "broadcast_schedule"
            await reply_text(
                update,
                "⏰ Vaqtni `YYYY-MM-DD HH:MM` ko‘rinishida yuboring. Masalan: 2026-08-20 18:30",
            )
            return True
        await reply_text(update, "❌ Yuborish turini tanlang.")
        return True
    if state == "broadcast_schedule":
        try:
            scheduled = datetime.strptime(text, "%Y-%m-%d %H:%M").astimezone()
        except ValueError:
            await reply_text(update, "❌ Vaqt formati noto‘g‘ri.")
            return True
        if scheduled <= datetime.now().astimezone():
            await reply_text(update, "❌ Kelajakdagi vaqtni kiriting.")
            return True
        broadcast_id = create_broadcast(data, scheduled.isoformat())
        context.job_queue.run_once(
            broadcast_job,
            when=scheduled,
            data=broadcast_id,
            name=f"broadcast-{broadcast_id}",
        )
        data.clear()
        await reply_text(
            update,
            f"✅ Vazifa rejalashtirildi\n🆔 Vazifa: #{broadcast_id}\n⏰ {scheduled.strftime('%Y-%m-%d %H:%M')}",
            reply_markup=admin_keyboard(),
        )
        return True

    if state == "channel_id":
        if not text:
            await reply_text(update, "❌ Kanal ID yoki @username yuboring.")
            return True
        data["channel_id"] = text if text != "external" else f"external:{int(time.time() * 1000)}"
        data["state"] = "channel_title"
        await reply_text(update, "📢 Kanal nomini yuboring:")
        return True
    if state == "channel_title":
        data["channel_title"] = text[:255]
        data["state"] = "channel_link"
        await reply_text(update, "🔗 Kanal havolasini yuboring:")
        return True
    if state == "channel_link":
        if not text.startswith(("https://", "http://", "tg://")):
            await reply_text(update, "❌ Kanal havolasi http(s) bilan boshlansin.")
            return True
        try:
            db.execute(
                """
                INSERT INTO channels(channel_id, title, invite_link, verification_type)
                VALUES (?, ?, ?, ?)
                """,
                (
                    data["channel_id"],
                    data["channel_title"],
                    text,
                    data.get("channel_type", "telegram"),
                ),
            )
        except sqlite3.IntegrityError:
            await reply_text(update, "❌ Bu kanal allaqachon qo‘shilgan.")
            return True
        data.clear()
        await reply_text(update, "✅ Majburiy kanal qo‘shildi.", reply_markup=admin_keyboard())
        return True

    if state.startswith("channel_edit_"):
        channel_id = int(data["editing_channel_id"])
        field = state.removeprefix("channel_edit_")
        if field == "title":
            db.execute("UPDATE channels SET title = ? WHERE id = ?", (text[:255], channel_id))
        elif field == "link":
            if not text.startswith(("https://", "http://", "tg://")):
                await reply_text(update, "❌ Havola http(s) bilan boshlansin.")
                return True
            db.execute("UPDATE channels SET invite_link = ? WHERE id = ?", (text, channel_id))
        else:
            if not text.isdigit():
                await reply_text(update, "❌ Limit uchun son yuboring.")
                return True
            db.execute("UPDATE channels SET member_limit = ? WHERE id = ?", (int(text), channel_id))
        data.clear()
        await send_text(context.bot, update.effective_chat.id, "✅ Kanal yangilandi.")
        await channels_menu(update.effective_chat.id, context.bot)
        return True

    if state == "premium_custom":
        custom_id = custom_emoji_id_from_message(message)
        if not custom_id:
            await reply_text(
                update,
                "❌ Custom emoji yuboring, emoji ID raqamini yozing yoki custom emoji bor xabarni forward qiling.",
            )
            return True
        data["pending_custom_id"] = custom_id
        data["state"] = "premium_symbol"
        await reply_text(update, "Endi shu mapping uchun oddiy emoji belgisini yuboring:")
        return True
    if state == "premium_symbol":
        if not text:
            await reply_text(update, "❌ Oddiy emoji yuboring.")
            return True
        symbol = text[:8]
        if (
            len(symbol) > 8
            or any(character.isalnum() for character in symbol)
            or any(character.isspace() for character in symbol)
        ):
            await reply_text(
                update,
                "❌ Faqat bitta oddiy emoji yuboring, masalan: 🎬 yoki ⭐",
            )
            return True
        try:
            db.execute(
                """
                INSERT INTO premium_emojis(unicode_emoji, custom_emoji_id)
                VALUES (?, ?)
                ON CONFLICT(unicode_emoji) DO UPDATE SET
                    custom_emoji_id = excluded.custom_emoji_id, active = 1
                """,
                (symbol, data["pending_custom_id"]),
            )
        except sqlite3.Error:
            await reply_text(update, "❌ Emoji mappingni saqlashda xatolik.")
            return True
        data.clear()
        await reply_text(update, "✅ Premium emoji mapping saqlandi.", reply_markup=admin_keyboard())
        return True
    if state == "premium_edit":
        row_id = int(data["editing_premium_id"])
        custom_id = custom_emoji_id_from_message(message)
        if not custom_id:
            await reply_text(update, "❌ Custom emoji, ID raqami yoki forward qilingan custom emoji yuboring.")
            return True
        db.execute(
            "UPDATE premium_emojis SET custom_emoji_id = ?, active = 1 WHERE id = ?",
            (custom_id, row_id),
        )
        data.clear()
        await reply_text(update, "✅ Premium emoji almashtirildi.", reply_markup=admin_keyboard())
        return True
    return False


def create_broadcast(data: dict[str, Any], scheduled_at: str | None) -> int:
    return int(
        db.execute(
            """
            INSERT INTO broadcasts(
                media_type, media_file_id, caption, buttons_json,
                audience_type, audience_limit, scheduled_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["media_type"],
                data["media_file_id"],
                data.get("caption", ""),
                json.dumps(data.get("buttons", []), ensure_ascii=False),
                data.get("audience_type", "all"),
                data.get("audience_limit"),
                scheduled_at,
                now_text(),
            ),
        )
    )


async def handle_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    text = (message.text or "").strip()
    user_id = update.effective_user.id
    original_text = text
    # Reply-keyboard custom emoji icons are sent separately from button text.
    # Accept both the old Unicode-prefixed text and the new icon-only text.
    premium_aliases = {}
    for button_text in (
        MUSIC_SEARCH_BUTTON, SEARCH_BUTTON, TOP_BUTTON, PRAYER_TIMES_BUTTON,
        VIP_BUTTON, RUSSIAN_MUSIC_BUTTON, RUSSIAN_SEARCH_BUTTON,
        RUSSIAN_TOP_BUTTON, RUSSIAN_PRAYER_BUTTON, RUSSIAN_VIP_BUTTON,
    ):
        premium_aliases[premium_button_label(button_text)] = button_text
    text = premium_aliases.get(text, text)
    text = {
        RUSSIAN_MUSIC_BUTTON: MUSIC_SEARCH_BUTTON,
        RUSSIAN_SEARCH_BUTTON: SEARCH_BUTTON,
        RUSSIAN_TOP_BUTTON: TOP_BUTTON,
        RUSSIAN_FAVORITES_BUTTON: FAVORITES_BUTTON,
        RUSSIAN_PRAYER_BUTTON: PRAYER_TIMES_BUTTON,
        RUSSIAN_VIP_BUTTON: VIP_BUTTON,
    }.get(text, text)
    language = user_language(user_id)
    if original_text == LANGUAGE_BUTTON:
        await reply_text(
            update,
            "🌐 Tilni tanlang / Выберите язык:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🇺🇿 O‘zbekcha", callback_data="lang:uz"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
            ]]),
        )
        return
    if text in {CANCEL_BUTTON, BACK_BUTTON, "/cancel"}:
        context.user_data.clear()
        await reply_text(
            update,
            "❌ Musiqa/qidiruv jarayoni bekor qilindi.",
            reply_markup=user_keyboard(is_admin(user_id), language),
        )
    elif text == VIP_BUTTON:
        context.user_data.clear()
        await vip_menu(update, context)
    elif text == TRANSLATOR_BUTTON:
        context.user_data.clear()
        context.user_data["state"] = "translator_language"
        await reply_text(
            update,
            "🌐 Qaysi tilga tarjima qilay?\n"
            "Matn, video, audio yoki voice yuboring. Manba tili avtomatik aniqlanadi.\n"
            "AI tarjima ma’noni, ism, raqam, emoji va formatni imkon qadar saqlaydi.",
            reply_markup=translation_keyboard(),
        )
    elif text == LOGO_BUTTON:
        context.user_data.clear()
        context.user_data["state"] = "logo_prompt"
        await reply_text(
            update,
            "🎨 Logo uchun nomi, mavzusi va xohlagan uslubingizni yozing.\n"
            "Masalan: «Prime TV uchun qora-qizil, kino lentasi belgisi bilan logo».",
            reply_markup=ReplyKeyboardRemove(),
        )
    elif context.user_data.get("state") == "translator_wait":
        target_code = str(context.user_data.get("translate_language") or "")
        try:
            if message.text and not (
                message.audio or message.voice or message.video or message.document
            ):
                transcript = message.text.strip()
                if not transcript:
                    raise ValueError("Tarjima uchun matn yuboring.")
                translation = await asyncio.to_thread(
                    _translate_text_with_fallback, transcript, target_code
                )
            else:
                progress_message = await reply_text(
                    update, "🎧 Audio/video eshitib olinmoqda..."
                )
                transcript, translation = await translate_media_message(
                    context.bot, message, target_code
                )
                try:
                    await progress_message.edit_text("✅ Audio/video matnga aylantirildi.")
                except TelegramError:
                    pass
            # Telegram sendMessage accepts at most 4096 characters.
            # Normal holatda aynan 2 ta xabar yuboriladi: avval asl matn,
            # keyin tarjima. Tarjima sig‘masa, qo‘shimcha qismlar alohida
            # xabarlarda ✔️ bilan davom ettiriladi. Menyu klaviaturasi oxirgi
            # tarjima xabariga biriktiriladi, shuning uchun ortiqcha xabar chiqmaydi.
            context.user_data.clear()
            await send_text(
                context.bot,
                update.effective_chat.id,
                f"📝 Asl matn:\n{transcript[:3900]}",
            )
            translation_text = translation.strip()
            if not translation_text:
                raise RuntimeError("Tarjima bo‘sh qaytdi.")

            remaining = translation_text
            first_part = True
            while remaining:
                part = remaining[:3900]
                if len(remaining) > 3900:
                    split_at = max(part.rfind("\n"), part.rfind(" "))
                    if split_at >= 1000:
                        part = remaining[:split_at]

                prefix = "✅ Tarjima:" if first_part else "✔️"
                is_last = len(remaining) <= len(part)
                await send_text(
                    context.bot,
                    update.effective_chat.id,
                    f"{prefix}\n{part}",
                    reply_markup=(
                        user_keyboard(is_admin(user_id), language) if is_last else None
                    ),
                )
                remaining = remaining[len(part):].lstrip()
                first_part = False
        except (OSError, URLError, TimeoutError, ValueError, RuntimeError, TelegramError):
            logger.exception("Tarjima jarayonida xatolik")
            await reply_text(
                update,
                "❌ Tarjima qilib bo‘lmadi. Audio/video qisqaroq yoki sifatliroq fayl "
                "yuboring va qayta urinib ko‘ring.",
                reply_markup=user_keyboard(is_admin(user_id), language),
            )
            context.user_data.clear()
    elif context.user_data.get("state") == "logo_prompt":
        if not text:
            await reply_text(update, "❌ Logo tavsifini matn qilib yuboring.")
            return
        try:
            await reply_text(update, "🎨 Logo tayyorlanmoqda, biroz kuting...")
            filename, image_data = await asyncio.to_thread(
                _generate_logo_with_fallback, text
            )
            if image_data:
                with tempfile.NamedTemporaryFile(
                    prefix="generated-logo-", suffix=".png"
                ) as image_file:
                    image_file.write(image_data)
                    image_file.flush()
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=image_file.name,
                        caption="🎨 Siz so‘ragan logo tayyor.",
                    )
            else:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=filename,
                    caption="🎨 Siz so‘ragan logo tayyor.",
                )
            context.user_data.clear()
            await send_text(
                context.bot,
                update.effective_chat.id,
                "Menyu:",
                reply_markup=user_keyboard(is_admin(user_id), language),
            )
        except (OSError, URLError, TimeoutError, RuntimeError, TelegramError):
            logger.exception("Logo yaratishda xatolik")
            context.user_data.clear()
            await reply_text(
                update,
                "❌ Logo yaratib bo‘lmadi. Tavsifni qisqaroq qilib qayta urinib ko‘ring.",
                reply_markup=user_keyboard(is_admin(user_id), language),
            )
    elif text == VIDEO_DOWNLOADER_BUTTON:
        context.user_data.clear()
        context.user_data["state"] = "video_downloader"
        await reply_text(
            update,
            russian_user_text(
                user_id,
                "📥 Video havolasini yuboring (YouTube, Shorts, Instagram, TikTok, Facebook va yt-dlp qo‘llaydigan boshqa saytlar).\n\n"
                "⚠️ Ochiq/public video bo‘lsin va 49 MB dan kichik bo‘lsin.",
                "📥 Отправьте ссылку на видео (YouTube, Shorts, Instagram, TikTok, Facebook и другие сайты, поддерживаемые yt-dlp).\n\n"
                "⚠️ Видео должно быть открытым и меньше 49 МБ.",
            ),
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
    elif context.user_data.get("state") == "video_downloader":
        url = first_supported_url(text)
        if not url:
            await reply_text(
                update,
                "❌ To‘g‘ri http/https video havolasini yuboring.",
                reply_markup=flow_keyboard(CANCEL_BUTTON),
            )
            return
        progress_message = await reply_text(update, progress_text("📥 Video yuklanmoqda...", 10))
        path = ""
        try:
            await update_progress(progress_message, "📥 Video yuklanmoqda...", 25)
            path, title = await download_video(url)
            await update_progress(progress_message, "📤 Telegramga yuborilmoqda...", 80)
            await send_local_video_with_fallback(
                context.bot,
                update.effective_chat.id,
                path,
                caption=f"🎬 {title[:900]}",
                supports_streaming=True,
            )
            await update_progress(progress_message, "✅ Tayyor", 100)
        except Exception as error:
            logger.exception("Video yuklashda xatolik: %s", error)
            error_text = str(error).lower()
            if "49 mb" in error_text or "max_filesize" in error_text:
                message_text = "❌ Video 49 MB dan katta. Kichikroq video yuboring."
            else:
                message_text = (
                    "❌ Videoni yuklab bo‘lmadi. Havola ochiq/public bo‘lsin, "
                    "yoki boshqa havolani sinab ko‘ring."
                )
            await reply_text(update, message_text)
        finally:
            if path:
                shutil.rmtree(str(Path(path).parent), ignore_errors=True)
            context.user_data.clear()
            await send_text(
                context.bot,
                update.effective_chat.id,
                "Menyu:",
                reply_markup=user_keyboard(is_admin(user_id), language),
            )
    elif text == MUSIC_SEARCH_BUTTON:
        context.user_data.clear()
        context.user_data["state"] = "music_search"
        await reply_text(
            update,
            russian_user_text(
                user_id,
                "🎵 Qo‘shiq nomi yoki ijrochini yozing.\n"
                "Xohlasangiz qo‘shiq bor video/audio faylni ham yuborishingiz mumkin.",
                "🎵 Напишите название песни или исполнителя.\n"
                "Можно также отправить видео или аудиофайл с музыкой.",
            ),
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
    elif text == PRAYER_TIMES_BUTTON:
        context.user_data.clear()
        await reply_text(
            update,
            russian_user_text(
                user_id,
                "🕌 Joylashuvni tanlang:\n🇺🇿 O‘zbekiston — 12 viloyat\n🌍 Davlatlar — Turkiya, Saudiya Arabistoni, Fransiya, Rossiya, AQSh",
                "🕌 Выберите место: города Узбекистана или другие страны.",
            ),
            reply_markup=prayer_keyboard(),
        )
    elif context.user_data.get("state") == "music_search":
        if message.video or message.audio or message.document:
            progress_message = await reply_text(
                update, progress_text("🎵 Musiqa aniqlanmoqda...", 0)
            )

            async def show_progress(percent: int, label: str) -> None:
                await update_progress(progress_message, label, percent)

            try:
                identified, results = await identify_music_from_message(
                    context.bot, message, show_progress
                )
                query = identified.get("search_query") or " ".join(
                    part for part in (identified.get("artist"), identified.get("title")) if part
                )
                if not results and query:
                    results = await search_music(query)
                context.user_data["music_results"] = results
                label = " ".join(
                    part for part in (identified.get("artist"), identified.get("title")) if part
                ) or "Musiqa aniqlanmadi"
                if not results:
                    await reply_text(update, f"❌ {label}. Natija topilmadi.")
                    return
                buttons = [
                    [InlineKeyboardButton(
                        f"{index + 1}. {item['title'][:38]}",
                        callback_data=f"music:{index}",
                    )]
                    for index, item in enumerate(results)
                ]
                await send_text(
                    context.bot,
                    update.effective_chat.id,
                    f"✅ AI aniqladi: {label}\n🎵 Natijalardan birini tanlang:",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
            except Exception:
                logger.exception("Video musiqasini aniqlashda xatolik")
                await reply_text(
                    update,
                    "❌ Videodagi musiqani aniqlab bo‘lmadi. Video qisqaroq bo‘lsin "
                    "yoki Instagram havolasini yuboring.",
                )
            return
        if not text:
            await reply_text(update, "❌ Qo‘shiq nomini yoki ijrochini yozing.")
            return
        progress_message = await reply_text(
            update, progress_text("🔎 Musiqa qidirilmoqda...", 0)
        )

        async def show_progress(percent: int, label: str) -> None:
            await update_progress(progress_message, label, percent)

        try:
            collections = _music_collection_search(text)
            library = _music_library_search(text)
            await show_progress(20, "📚 Katalog tekshirilmoqda...")
            results = [
                {
                    "title": str(row["title"]),
                    "url": "",
                    "duration": "",
                    "library_id": str(row["id"]),
                    "collection_name": str(row["collection_name"] or ""),
                }
                for row in library
            ]
            collection_results = [
                {
                    "title": f"📁 {row['name']}",
                    "url": "",
                    "duration": "",
                    "collection_id": str(row["id"]),
                    "track_count": str(row["track_count"]),
                }
                for row in collections
            ]
            results = collection_results + results
            if is_supported_media_url(text):
                identified, url_results = await identify_music_from_url(
                    text, show_progress
                )
                results.extend(url_results)
                label = " ".join(
                    part for part in (identified.get("artist"), identified.get("title"))
                    if part
                )
                if label:
                    await reply_text(update, f"✅ AI aniqladi: {label}")
            else:
                await show_progress(60, "🔎 To‘liq trek qidirilmoqda...")
                results.extend(await music_results_from_input(text))
                await show_progress(100, "✅ Qidiruv tugadi.")
            context.user_data["music_results"] = results
            if not results:
                await send_text(context.bot, update.effective_chat.id, "❌ Qo‘shiq topilmadi.")
                return
            buttons = [
                [
                    InlineKeyboardButton(
                        (
                            f"📁 {item['title'].removeprefix('📁 ')[:34]} "
                            f"({item.get('track_count', '0')} ta)"
                            if item.get("collection_id")
                            else f"{index + 1}. {item['title'][:38]}"
                        ),
                        callback_data=(
                            f"music_collection:{item['collection_id']}"
                            if item.get("collection_id")
                            else f"music:{index}"
                        ),
                    )
                ]
                for index, item in enumerate(results)
            ]
            await send_text(
                context.bot,
                update.effective_chat.id,
                "🎵 Natijalardan birini tanlang:",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        except Exception as error:
            logger.exception("Musiqa qidirishda xatolik")
            error_text = str(error).lower()
            if "404" in error_text or "not found" in error_text:
                user_message = (
                    "⚠️ Bu havola hozir ochilmadi. Instagram videoni o‘chirgan, "
                    "yopgan yoki havola muddati tugagan bo‘lishi mumkin. "
                    "Videoni Telegram’ga yuboring yoki boshqa natijani tanlang."
                )
            else:
                user_message = (
                    "⚠️ Musiqa qidiruvi vaqtincha ishlamadi. "
                    "Videoni Telegram’ga yuboring yoki boshqa havola bilan urinib ko‘ring."
                )
            await send_text(
                context.bot,
                update.effective_chat.id,
                user_message,
            )
    elif text == SEARCH_BUTTON:
        context.user_data["state"] = "user_search"
        await reply_text(
            update,
            "🔎 Kino nomi yoki kodini yuboring:",
            reply_markup=user_keyboard(is_admin(user_id)),
        )
    elif text == TOP_BUTTON:
        rows = db.execute(
            "SELECT * FROM movies ORDER BY views DESC, id DESC LIMIT 10", all_rows=True
        )
        if not rows:
            await reply_text(
                update,
                "❌ Hali kinolar qo‘shilmagan.",
                reply_markup=user_keyboard(is_admin(user_id)),
            )
            return
        await reply_text(
            update,
            "🔥 Top 10 kinolar:",
            reply_markup=user_keyboard(is_admin(user_id)),
        )
        for row in rows:
            await send_movie_card(context.bot, update.effective_chat.id, row)
    elif text == FAVORITES_BUTTON:
        rows = db.execute(
            """
            SELECT m.* FROM movies m
            JOIN favorites f ON f.movie_id = m.id
            WHERE f.user_id = ? ORDER BY m.title
            """,
            (user_id,),
            all_rows=True,
        )
        if not rows:
            await reply_text(
                update,
                "Sizda hozircha sevimli kinolar yo‘q.\n\nSevimli kino qo‘shish uchun kino tagidagi 😍 Sevimli tugmasini bosing.",
                reply_markup=user_keyboard(is_admin(user_id)),
            )
            return
        await reply_text(
            update,
            "😍 Sevimli kinolaringiz:",
            reply_markup=user_keyboard(is_admin(user_id)),
        )
        for row in rows:
            await send_movie_card(context.bot, update.effective_chat.id, row)
    elif context.user_data.get("state") == "user_search" and text:
        if not await subscribed_to_required(context.bot, user_id):
            await subscription_prompt(update)
            return
        await show_search_results(context.bot, update.effective_chat.id, text)
    else:
        await reply_text(
            update,
            "Menyudan kerakli bo‘limni tanlang.",
            reply_markup=user_keyboard(is_admin(user_id)),
        )


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    remember_user(update)
    starts = int(db.setting("start_count", "0") or "0") + 1
    db.set_setting("start_count", str(starts))
    context.user_data.clear()
    language = user_language(update.effective_user.id)
    if not is_admin(update.effective_user.id) and not await subscribed_to_required(
        context.bot, update.effective_user.id
    ):
        await subscription_prompt(update)
        return
    if context.args:
        movie = movie_by_code(context.args[0])
        if movie:
            db.execute("UPDATE movies SET views = views + 1 WHERE id = ?", (int(movie["id"]),))
            movie = movie_by_id(int(movie["id"])) or movie
            await send_movie_media(
                context.bot,
                update.effective_chat.id,
                movie,
                remove_menu=True,
            )
            return
    if is_admin(update.effective_user.id):
        await reply_text(
            update,
            "👋 Admin panelga xush kelibsiz.",
            reply_markup=admin_keyboard(),
        )
    else:
        await reply_text(
            update,
            russian_user_text(
                update.effective_user.id,
                "👋 Kino botiga xush kelibsiz.",
                "👋 Добро пожаловать в кино-бота.",
            ),
            reply_markup=user_keyboard(False, language),
        )


async def on_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    language = user_language(update.effective_user.id)
    markup = (
        admin_keyboard()
        if is_admin(update.effective_user.id)
        else user_keyboard(False, language)
    )
    await reply_text(
        update,
        russian_user_text(
            update.effective_user.id,
            "❌ Joriy jarayon bekor qilindi.",
            "❌ Текущий процесс отменён.",
        ),
        reply_markup=markup,
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Channel posts do not have an effective_user. They are not bot commands
    # and must not be routed through the private user/admin flow.
    if update.channel_post or update.edited_channel_post:
        return
    if not update.effective_user or not update.effective_message:
        return
    remember_user(update)
    user_id = update.effective_user.id
    message = update.effective_message
    state = context.user_data.get("state", "")

    if state == "vip_payment":
        await handle_admin_state(update, context, state)
        return

    user_feature_buttons = {
        MUSIC_SEARCH_BUTTON, PRAYER_TIMES_BUTTON, TRANSLATOR_BUTTON, LOGO_BUTTON,
        VIDEO_DOWNLOADER_BUTTON, VIP_BUTTON, LANGUAGE_BUTTON,
        RUSSIAN_MUSIC_BUTTON, RUSSIAN_SEARCH_BUTTON, RUSSIAN_TOP_BUTTON,
        RUSSIAN_FAVORITES_BUTTON, RUSSIAN_PRAYER_BUTTON, RUSSIAN_VIP_BUTTON,
        SEARCH_BUTTON, TOP_BUTTON, FAVORITES_BUTTON,
    }
    for button_text in (
        MUSIC_SEARCH_BUTTON, SEARCH_BUTTON, TOP_BUTTON, PRAYER_TIMES_BUTTON,
        VIP_BUTTON, RUSSIAN_MUSIC_BUTTON, RUSSIAN_SEARCH_BUTTON,
        RUSSIAN_TOP_BUTTON, RUSSIAN_PRAYER_BUTTON, RUSSIAN_VIP_BUTTON,
    ):
        user_feature_buttons.add(premium_button_label(button_text))
    if (
        message.text in user_feature_buttons
        or state in {"music_search", "music_busy", "translator_wait", "logo_prompt"}
    ):
        await handle_user_action(update, context)
        return

    if is_admin(user_id):
        if context.user_data.get("state") == "user_search" or message.text in {
            SEARCH_BUTTON,
            TOP_BUTTON,
            FAVORITES_BUTTON,
            RUSSIAN_SEARCH_BUTTON,
            RUSSIAN_TOP_BUTTON,
            RUSSIAN_FAVORITES_BUTTON,
        }:
            await handle_user_action(update, context)
            return
        if message.text == "/allmovies":
            context.user_data.clear()
            await show_all_movies(context.bot, update.effective_chat.id, page=0)
            return
        if state:
            handled = await handle_admin_state(update, context, state)
            if handled:
                return
        if message.text == ADD_MOVIE_BUTTON:
            await start_add_movie(update, context)
            return
        if message.text == ADD_SERIAL_BUTTON:
            await start_add_serial(update, context)
            return
        if message.text == ADD_MUSIC_BUTTON:
            await start_add_music(update, context)
            return
        if message.text == ADD_MUSIC_COLLECTION_BUTTON:
            await start_add_music_collection(update, context)
            return
        if message.text == MANAGE_MUSIC_BUTTON:
            await show_music_library(context.bot, update.effective_chat.id)
            return
        if message.text == DATABASE_BUTTON:
            await send_database_files(update, context)
            await reply_text(update, "🗄 Baza tiklash uchun yuqoridagi fayldan keyin yangi .sqlite3 fayl yuboring.", reply_markup=admin_keyboard())
            return
        if message.text == ADMIN_PANEL_BUTTON:
            context.user_data.clear()
            await reply_text(update, "Admin panel:", reply_markup=admin_keyboard())
            return
        if message.text == BACK_BUTTON:
            context.user_data.clear()
            await reply_text(
                update,
                "👤 Oddiy foydalanuvchi menyusi:",
                reply_markup=user_keyboard(True),
            )
            return
        if message.text == MANAGE_MOVIES_BUTTON:
            await start_manage(update, context)
            return
        if message.text == CREATE_POST_BUTTON:
            await start_post(update, context)
            return
        if message.text == BROADCAST_BUTTON:
            await start_broadcast(update, context)
            return
        if message.text == CHANNELS_BUTTON:
            await start_channels(update, context)
            return
        if message.text == VIP_SETTINGS_BUTTON:
            await vip_settings_menu(context.bot, update.effective_chat.id)
            return
        if message.text == AI_STATUS_BUTTON:
            await ai_status_menu(context.bot, update.effective_chat.id)
            return
        if message.text == AUTOSAVE_BUTTON:
            current = db.setting("auto_save", "0") == "1"
            db.set_setting("auto_save", "0" if current else "1")
            await reply_text(
                update,
                f"💾 Avto saqlash: {'🟢 Yoqilgan' if not current else '🔴 O‘chirilgan'}",
                reply_markup=admin_keyboard(),
            )
            return
        if message.text == STATS_BUTTON:
            await reply_text(update, await stats_text(), reply_markup=admin_keyboard())
            return
        if message.text == SETTINGS_BUTTON:
            await reply_text(
                update,
                "⚙️ Sozlamalar\n\n"
                f"BOT_TOKEN: {'🟢 mavjud' if BOT_TOKEN else '🔴 yo‘q'}\n"
                f"ADMIN_IDS: {len(ADMIN_IDS)} ta\n"
                f"Post kanali: {'🟢 mavjud' if CHANNEL_ID else '🔴 yo‘q'}\n"
                f"Forward himoyasi: {'🟢 ON' if forward_protection_enabled() else '🔴 OFF'}\n"
                f"SQLite: {DB_PATH}\n\n"
                "Bot polling rejimida ishlaydi. Kanal qo‘shish uchun Majburiy obuna bo‘limidan foydalaning.",
                reply_markup=admin_keyboard(),
            )
            return
        if message.text == PREMIUM_EMOJI_BUTTON:
            await premium_menu(update, context)
            return
        if message.text == FORWARD_PROTECTION_BUTTON:
            enabled = forward_protection_enabled()
            db.set_setting("forward_protection", "0" if enabled else "1")
            await reply_text(
                update,
                f"🔐 Forward himoyasi: {'🔴 OFF' if enabled else '🟢 ON'}\n"
                "ON bo‘lsa kino va serial videolarini forward/save qilish cheklanadi.",
                reply_markup=admin_keyboard(),
            )
            return
        if db.setting("auto_save", "0") == "1":
            media = media_from_message(message)
            source_url = first_supported_url(message.caption or message.text or "")
            movie_media = media if media and media[0] in {"video", "document"} else None
            if movie_media or source_url:
                code, updated = save_auto_movie(message, movie_media)
                caption_status = (
                    "Kodi va caption maʼlumotlari saqlandi."
                    if message.caption
                    else (
                        "Havola va media maʼlumotlari saqlandi."
                        if source_url
                        else "Caption yuborilmagan, keyin Kino boshqarish orqali to‘ldirishingiz mumkin."
                    )
                )
                await reply_text(
                    update,
                    f"💾 Kino {'yangilandi' if updated else 'avtomatik saqlandi'}.\n"
                    f"🔢 Kodi: {code}\n{caption_status}",
                    reply_markup=admin_keyboard(),
                )
                return
        await reply_text(
            update,
            "Admin paneldan kerakli bo‘limni tanlang.",
            reply_markup=admin_keyboard(),
        )
        return

    if message.text == "/cancel":
        await on_cancel(update, context)
        return
    if not await subscribed_to_required(context.bot, user_id):
        await subscription_prompt(update)
        return
    await handle_user_action(update, context)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data or ""
    chat_id = query.message.chat_id

    if data.startswith("lang:"):
        language = data.split(":", 1)[1]
        if language not in {"uz", "ru"}:
            return
        db.execute(
            "UPDATE users SET language = ? WHERE user_id = ?",
            (language, user_id),
        )
        await send_text(
            context.bot,
            chat_id,
            "✅ Til o‘zgartirildi." if language == "uz" else "✅ Язык изменён.",
            reply_markup=user_keyboard(is_admin(user_id), language),
        )
        return

    if data == "translate_cancel":
        context.user_data.clear()
        await send_text(
            context.bot,
            chat_id,
            "❌ Tarjima bekor qilindi.",
            reply_markup=user_keyboard(is_admin(user_id), user_language(user_id)),
        )
        return

    if data.startswith("translate_lang:"):
        target_code = data.split(":", 1)[1]
        if target_code not in TRANSLATION_LANGUAGES:
            return
        context.user_data["state"] = "translator_wait"
        context.user_data["translate_language"] = target_code
        await send_text(
            context.bot,
            chat_id,
            f"✅ {TRANSLATION_LANGUAGES[target_code][0]} tanlandi.\n"
            "Endi tarjima qilinadigan matn, video, audio yoki voice yuboring.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if data == "subcheck":
        subscribed, failed_channel = await subscription_check(context.bot, user_id)
        if subscribed:
            successes = int(db.setting("subscription_success_count", "0") or "0") + 1
            db.set_setting("subscription_success_count", str(successes))
            await send_text(
                context.bot,
                chat_id,
                "✅ Obuna tasdiqlandi. Endi kino kodini yuborishingiz mumkin.",
                reply_markup=user_keyboard(is_admin(user_id)),
            )
        elif failed_channel:
            await send_text(
                context.bot,
                chat_id,
                f"⚠️ «{failed_channel}» kanalini tekshirib bo‘lmadi. "
                "Botni shu kanalda administrator qiling va qayta tekshiring.",
            )
        else:
            await send_text(context.bot, chat_id, "❌ Hali barcha kanallarga obuna bo‘lmagansiz.")
        return
    if data == "external_subcheck":
        for channel in await required_channels():
            if str(channel["verification_type"] or "telegram") == "external":
                db.execute(
                    """
                    INSERT OR REPLACE INTO external_subscription_checks(user_id, channel_id, checked_at)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, int(channel["id"]), now_text()),
                )
        if await subscribed_to_required(context.bot, user_id):
            successes = int(db.setting("subscription_success_count", "0") or "0") + 1
            db.set_setting("subscription_success_count", str(successes))
            await send_text(
                context.bot,
                chat_id,
                "✅ Tashqi obunalar qayd qilindi. Endi `Tekshirish` tugmasini bosing.",
            )
        else:
            await send_text(
                context.bot,
                chat_id,
                "✅ Tashqi havolalar qayd qilindi. Telegram kanallar bo‘lsa, ularga ham obuna bo‘ling.",
            )
        return
    if data.startswith("vip_approve:") or data.startswith("vip_reject:"):
        if not is_admin(user_id):
            return
        payment_id = int(data.split(":")[1])
        payment = db.execute(
            "SELECT * FROM vip_payments WHERE id = ?", (payment_id,), one=True
        )
        if not payment or payment["status"] != "pending":
            await send_text(context.bot, chat_id, "ℹ️ Bu to‘lov allaqachon ko‘rib chiqilgan.")
            return
        if data.startswith("vip_reject:"):
            db.execute(
                "UPDATE vip_payments SET status = 'rejected', reviewed_at = ? WHERE id = ?",
                (now_text(), payment_id),
            )
            await send_text(context.bot, chat_id, f"❌ VIP to‘lovi #{payment_id} rad etildi.")
            try:
                await context.bot.send_message(
                    int(payment["user_id"]),
                    "❌ VIP to‘lovingiz rad etildi. Chekni tekshirib qayta yuborishingiz mumkin.",
                )
            except TelegramError:
                pass
            return
        current = db.execute(
            "SELECT expires_at FROM vip_users WHERE user_id = ?",
            (int(payment["user_id"]),),
            one=True,
        )
        base = datetime.now()
        if current:
            try:
                base = max(base, datetime.fromisoformat(str(current["expires_at"])))
            except ValueError:
                pass
        expires_at = base + timedelta(days=30)
        db.execute(
            """
            INSERT INTO vip_users(user_id, expires_at) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET expires_at = excluded.expires_at
            """,
            (int(payment["user_id"]), expires_at.isoformat(timespec="minutes")),
        )
        db.execute(
            "UPDATE vip_payments SET status = 'approved', reviewed_at = ? WHERE id = ?",
            (now_text(), payment_id),
        )
        await send_text(
            context.bot,
            chat_id,
            f"✅ VIP to‘lovi #{payment_id} tasdiqlandi.\n⏳ Muddat: {expires_at.isoformat(timespec='minutes')}",
        )
        try:
            await context.bot.send_message(
                int(payment["user_id"]),
                f"🎉 VIP obunangiz faollashtirildi!\n⏳ Amal qilish muddati: {expires_at.isoformat(timespec='minutes')}",
                entities=premium_entities(
                    f"🎉 VIP obunangiz faollashtirildi!\n⏳ Amal qilish muddati: {expires_at.isoformat(timespec='minutes')}"
                ) or None,
                reply_markup=user_keyboard(False),
            )
        except TelegramError:
            pass
        return
    if data.startswith(
        (
            "watch:", "episode:", "fav:", "rate:", "movie:", "music:",
            "music_collection:", "music_collection_page:",
            "prayer:", "translate_lang:",
        )
    ) and not is_admin(user_id):
        if not await subscribed_to_required(context.bot, user_id):
            await send_text(context.bot, chat_id, "📢 Avval majburiy kanallarga obuna bo‘ling.")
            return
    if data.startswith("movie:"):
        movie = movie_by_id(int(data.split(":")[1]))
        if movie:
            await send_movie_card(context.bot, chat_id, movie)
        return
    if data.startswith("watch:"):
        movie_id = int(data.split(":")[1])
        movie = movie_by_id(movie_id)
        if movie:
            if str(movie["content_type"] or "movie") == "serial":
                await send_serial_parts(context.bot, chat_id, movie)
            else:
                db.execute("UPDATE movies SET views = views + 1 WHERE id = ?", (movie_id,))
                await send_movie_media(context.bot, chat_id, movie)
        return
    if data.startswith("episode:"):
        _, movie_id, episode_id = data.split(":")
        movie = movie_by_id(int(movie_id))
        episode = db.execute(
            "SELECT * FROM episodes WHERE id = ? AND movie_id = ?",
            (int(episode_id), int(movie_id)),
            one=True,
        )
        if movie and episode:
            db.execute("UPDATE movies SET views = views + 1 WHERE id = ?", (int(movie_id),))
            await send_episode_media(context.bot, chat_id, episode, movie)
        return
    if data.startswith("music_collection:"):
        try:
            collection_id = int(data.split(":", 1)[1])
        except (TypeError, ValueError):
            await send_text(context.bot, chat_id, "❌ To‘plam tanlovi noto‘g‘ri.")
            return
        await show_music_collection(
            context.bot, chat_id, context, collection_id, offset=0
        )
        return
    if data.startswith("music_collection_page:"):
        try:
            _, collection_id_text, offset_text = data.split(":")
            collection_id = int(collection_id_text)
            offset = int(offset_text)
        except (TypeError, ValueError):
            await send_text(context.bot, chat_id, "❌ To‘plam sahifasi noto‘g‘ri.")
            return
        await show_music_collection(
            context.bot, chat_id, context, collection_id, offset=max(0, offset)
        )
        return
    if data.startswith("music:"):
        audio_path: Path | None = None
        try:
            index = int(data.split(":")[1])
            results = context.user_data.get("music_results") or []
            item = results[index]
            if item.get("library_id"):
                row = db.execute(
                    """
                    SELECT m.*, c.name AS collection_name
                    FROM music_library m
                    LEFT JOIN music_collections c ON c.id = m.collection_id
                    WHERE m.id = ?
                    """,
                    (int(item["library_id"]),),
                    one=True,
                )
                if not row:
                    await send_text(context.bot, chat_id, "❌ Katalogdagi musiqa topilmadi.")
                    return
                await send_library_music(context.bot, chat_id, row)
                context.user_data.pop("music_results", None)
                await send_text(
                    context.bot, chat_id, "Menyu:",
                    reply_markup=user_keyboard(is_admin(user_id)),
                )
                return
            progress_message = await send_text(
                context.bot,
                chat_id,
                progress_text("⏳ Qo‘shiq yuklanmoqda...", 20),
            )
            await update_progress(progress_message, "📥 To‘liq audio yuklanmoqda...", 40)
            download_candidates = [item] + [
                candidate
                for candidate in results
                if candidate is not item and candidate.get("url")
            ][:4]
            last_error: Exception | None = None
            path = ""
            title = ""
            for candidate_index, candidate in enumerate(download_candidates):
                try:
                    path, title = await download_music_audio(str(candidate["url"]))
                    break
                except Exception as error:
                    last_error = error
                    logger.warning(
                        "Musiqa manbasi ishlamadi (%s): %s",
                        candidate.get("url"),
                        error,
                    )
                    if candidate_index < len(download_candidates) - 1:
                        await update_progress(
                            progress_message,
                            "🔁 Boshqa musiqa serveri sinab ko‘rilmoqda...",
                            60,
                        )
            if not path:
                raise last_error or RuntimeError("Musiqa manbalari ishlamadi.")
            audio_path = Path(path)
            await update_progress(progress_message, "🎧 Audio tayyorlanmoqda...", 80)
            if audio_path.stat().st_size > MAX_MUSIC_UPLOAD_BYTES:
                raise ValueError("Audio Telegram limitidan katta.")
            with audio_path.open("rb") as audio_file:
                caption = normalize_emojis(f"🎵 {title[:900]}")
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=title[:255],
                    performer="",
                    caption=caption,
                    caption_entities=premium_entities(caption) or None,
                )
            await update_progress(progress_message, "✅ Audio tayyor!", 100)
            context.user_data.pop("music_results", None)
            await send_text(context.bot, chat_id, "Menyu:", reply_markup=user_keyboard(is_admin(user_id)))
        except Exception:
            logger.exception("Musiqa yuklashda xatolik")
            await send_text(
                context.bot,
                chat_id,
                "❌ Qo‘shiqni yuklab bo‘lmadi. Boshqa natijani tanlab ko‘ring.",
            )
        finally:
            if audio_path:
                shutil.rmtree(audio_path.parent, ignore_errors=True)
        return
    if data.startswith("prayer_menu:"):
        menu_key = data.split(":", 1)[1]
        if menu_key == "main":
            await query.edit_message_text(
                "🕌 Joylashuvni tanlang:", reply_markup=prayer_keyboard()
            )
        elif menu_key == "uz":
            await query.edit_message_text(
                "🇺🇿 O‘zbekiston — viloyatni tanlang:",
                reply_markup=prayer_uzbekistan_keyboard(),
            )
        elif menu_key == "world":
            await query.edit_message_text(
                "🌍 Davlatni tanlang:", reply_markup=prayer_world_keyboard()
            )
        return
    if data.startswith("prayer:"):
        city_key = data.split(":", 1)[1]
        if city_key not in PRAYER_LOCATIONS:
            await send_text(context.bot, chat_id, "❌ Joylashuv topilmadi.")
            return
        try:
            await send_text(context.bot, chat_id, "⏳ Namoz vaqtlari olinmoqda...")
            await send_prayer_times(context.bot, chat_id, city_key)
        except Exception:
            logger.exception("Namoz vaqtlarini olishda xatolik")
            await send_text(
                context.bot,
                chat_id,
                "❌ Namoz vaqtlarini hozir olib bo‘lmadi. Keyinroq qayta urinib ko‘ring.",
            )
        return
    if data.startswith("fav:"):
        movie_id = int(data.split(":")[1])
        exists = db.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id),
            one=True,
        )
        if exists:
            db.execute(
                "DELETE FROM favorites WHERE user_id = ? AND movie_id = ?",
                (user_id, movie_id),
            )
            await send_text(context.bot, chat_id, "💔 Sevimlilardan olib tashlandi.")
        else:
            db.execute(
                "INSERT OR IGNORE INTO favorites(user_id, movie_id) VALUES (?, ?)",
                (user_id, movie_id),
            )
            await send_text(context.bot, chat_id, "😍 Sevimlilarga qo‘shildi.")
        return
    if data.startswith("rate:"):
        try:
            _, movie_id_text, rating_text = data.split(":")
            movie_id = int(movie_id_text)
            rating = int(rating_text)
        except (ValueError, TypeError):
            await send_text(context.bot, chat_id, "❌ Reyting noto‘g‘ri.")
            return
        if rating not in range(1, 6) or not movie_by_id(movie_id):
            await send_text(context.bot, chat_id, "❌ Reyting noto‘g‘ri.")
            return
        db.execute(
            """
            INSERT INTO movie_ratings(user_id, movie_id, rating, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, movie_id) DO UPDATE SET
                rating = excluded.rating, created_at = excluded.created_at
            """,
            (user_id, movie_id, rating, now_text()),
        )
        await send_text(
            context.bot,
            chat_id,
            f"✅ Siz {rating}/5 ⭐ reyting berdingiz. Rahmat!",
        )
        return

    if not is_admin(user_id):
        return
    if data == "admin_home":
        context.user_data.clear()
        await send_text(context.bot, chat_id, "Admin panel:", reply_markup=admin_keyboard())
    elif data == "ai_health_check":
        if is_admin(user_id):
            await run_ai_health_check(context.bot, chat_id)
    elif data == "flow_cancel":
        context.user_data.clear()
        await send_text(context.bot, chat_id, "❌ Bekor qilindi.", reply_markup=admin_keyboard())
    elif data == "database_restore_no":
        import_path = context.user_data.pop("database_import_path", "")
        if import_path:
            Path(import_path).unlink(missing_ok=True)
        context.user_data.clear()
        await send_text(context.bot, chat_id, "❌ Baza tiklash bekor qilindi.", reply_markup=admin_keyboard())
    elif data == "database_restore_yes":
        import_path = str(context.user_data.get("database_import_path") or "")
        if not import_path or not Path(import_path).is_file():
            context.user_data.clear()
            await send_text(context.bot, chat_id, "❌ Yuklangan baza topilmadi. Qayta yuboring.")
            return
        try:
            imported = db.merge_from_file(import_path)
            Path(import_path).unlink(missing_ok=True)
            context.user_data.clear()
            await send_text(
                context.bot,
                chat_id,
                "✅ Eski baza joriy bazaga qo‘shildi, mavjud ma’lumotlar saqlandi.\n"
                f"🎬 Kino: {imported['movies']} | 🎞 Qism: {imported['episodes']} | "
                f"👥 Foydalanuvchi: {imported['users']} | 🎵 Musiqa: {imported['music']}",
                reply_markup=admin_keyboard(),
            )
        except (OSError, sqlite3.Error) as error:
            logger.exception("Baza tiklashda xatolik: %s", error)
            await send_text(context.bot, chat_id, "❌ Bazani tiklashda xatolik yuz berdi.")
    elif data == "movie_save":
        draft = context.user_data.get("draft")
        if not draft:
            await send_text(context.bot, chat_id, "❌ Saqlash uchun draft topilmadi.")
            return
        await send_text(
            context.bot,
            chat_id,
            "⏳ Poster video boshiga va Prime TV watermarkiga qo‘shilmoqda...",
        )
        processed_file_id, processed_media_type = await process_movie_video(
            context.bot,
            poster_file_id=str(draft.get("poster_file_id") or ""),
            video_file_id=str(draft.get("video_file_id") or ""),
            owner_chat_id=chat_id,
        )
        try:
            db.execute(
                """
                INSERT INTO movies(
                    code, title, poster_file_id, video_file_id, media_type, caption,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft["code"],
                    draft["title"],
                    draft.get("poster_file_id"),
                    processed_file_id,
                    processed_media_type,
                    draft.get("caption", ""),
                    now_text(),
                ),
            )
            db.backup(DB_BACKUP_PATH)
        except sqlite3.IntegrityError:
            await send_text(context.bot, chat_id, "❌ Bu kino kodi band.")
            return
        code = draft["code"]
        context.user_data.clear()
        await send_text(
            context.bot,
            chat_id,
            f"🎉 Kino muvaffaqiyatli saqlandi!\n🔢 Kino kodi: {code}",
            reply_markup=admin_keyboard(),
        )
    elif data.startswith("draft_edit:"):
        field = data.split(":")[1]
        context.user_data["state"] = f"draft_{field}"
        prompts = {
            "code": "🔢 Yangi kino kodini yuboring:",
            "title": "📝 Yangi kino nomini yuboring:",
            "poster": "🖼 Yangi poster yuboring:",
            "video": "🎥 Yangi video yuboring:",
            "caption": "📝 Yangi tavsif yuboring yoki skip tugmasini bosing:",
        }
        await send_text(context.bot, chat_id, prompts[field], reply_markup=flow_keyboard(CANCEL_BUTTON))
    elif data.startswith("manage:"):
        movie = movie_by_id(int(data.split(":")[1]))
        if movie:
            context.user_data["state"] = ""
            await show_manage_movie(context.bot, chat_id, movie)
    elif data.startswith("manage_page:"):
        await show_all_movies(
            context.bot,
            chat_id,
            int(data.split(":")[1]),
        )
    elif data.startswith("movie_edit:"):
        _, movie_id, field = data.split(":")
        context.user_data["editing_movie_id"] = int(movie_id)
        context.user_data["state"] = f"movie_edit_{field}"
        prompts = {
            "code": "🔢 Yangi kodni yuboring:",
            "title": "📝 Yangi nomni yuboring:",
            "poster": "🖼 Yangi poster rasm yuboring:",
            "video": "🎥 Yangi video yuboring:",
            "caption": "📝 Yangi tavsif yuboring:",
        }
        await send_text(context.bot, chat_id, prompts[field], reply_markup=flow_keyboard(CANCEL_BUTTON))
    elif data.startswith("movie_delete:"):
        movie_id = int(data.split(":")[1])
        await send_text(
            context.bot,
            chat_id,
            "❗ Bu kinoni butunlay o‘chirishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Ha, o‘chirish", callback_data=f"movie_delete_yes:{movie_id}"),
                        InlineKeyboardButton("❌ Yo‘q", callback_data="admin_home"),
                    ]
                ]
            ),
        )
    elif data.startswith("movie_delete_yes:"):
        movie_id = int(data.split(":")[1])
        db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        db.backup(DB_BACKUP_PATH)
        await send_text(context.bot, chat_id, "🗑 Kino o‘chirildi.", reply_markup=admin_keyboard())
    elif data == "post_preview_watch":
        movie = movie_by_id(int(context.user_data["post_movie_id"]))
        if movie:
            await send_movie_media(context.bot, chat_id, movie)
    elif data == "post_publish":
        if not CHANNEL_ID:
            await send_text(context.bot, chat_id, "❌ CHANNEL_ID sozlanmagan.")
            return
        try:
            movie_id = int(context.user_data["post_movie_id"])
            post_movie = movie_by_id(movie_id)
            post_label = (
                "🎞 Qismlarni ko‘rish"
                if post_movie and str(post_movie["content_type"] or "movie") == "serial"
                else "🎬 Filmni ko‘rish"
            )
            post_code = str(post_movie["code"]) if post_movie else str(movie_id)
            start_link = await movie_start_link(context.bot, post_code)
            post_caption = str(context.user_data.get("caption") or "")
            if post_movie:
                post_caption += f"\n\n👀 Ko‘rishlar: {post_movie['views']}"
            post_button = (
                styled_inline_button(post_label, style="primary", url=start_link)
                if start_link
                else styled_inline_button(
                    post_label, style="primary", callback_data=f"watch:{movie_id}"
                )
            )
            button = InlineKeyboardMarkup([[post_button]])
            await send_media(
                context.bot,
                CHANNEL_ID,
                context.user_data["media_type"],
                context.user_data["media_file_id"],
                post_caption,
                button,
            )
            context.user_data.clear()
            await send_text(context.bot, chat_id, "✅ Post kanalga e'lon qilindi.", reply_markup=admin_keyboard())
        except TelegramError as error:
            await send_text(context.bot, chat_id, f"❌ Kanalga yuborishda xatolik: {error}")
    elif data == "channel_add":
        context.user_data["state"] = "channel_type"
        await send_text(
            context.bot,
            chat_id,
            "📢 Obuna turini tanlang: `telegram` — bot tekshiradigan kanal, "
            "`external` — tashqi sayt/kanal havolasi (foydalanuvchi qo‘lda tasdiqlaydi).",
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
    elif data == "channels_list":
        await channels_menu(chat_id, context.bot)
    elif data.startswith("channel:"):
        await show_channel(context.bot, chat_id, int(data.split(":")[1]))
    elif data.startswith("channel_toggle:"):
        channel_id = int(data.split(":")[1])
        db.execute("UPDATE channels SET active = CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id = ?", (channel_id,))
        await show_channel(context.bot, chat_id, channel_id)
    elif data.startswith("channel_edit:"):
        _, channel_id, field = data.split(":")
        context.user_data["editing_channel_id"] = int(channel_id)
        context.user_data["state"] = f"channel_edit_{field}"
        prompt = {
            "title": "📢 Yangi kanal nomini yuboring:",
            "link": "🔗 Yangi kanal havolasini yuboring:",
            "limit": "🎯 Yangi limitni son bilan yuboring:",
        }[field]
        await send_text(context.bot, chat_id, prompt, reply_markup=flow_keyboard(CANCEL_BUTTON))
    elif data.startswith("channel_reset:"):
        await send_text(context.bot, chat_id, "🔄 Kanal statistikasi Telegram tomonidan boshqariladi; bot tekshiruvini qayta boshlashga tayyor.")
    elif data.startswith("channel_delete:"):
        db.execute("DELETE FROM channels WHERE id = ?", (int(data.split(":")[1]),))
        await send_text(context.bot, chat_id, "🗑 Kanal o‘chirildi.")
        await channels_menu(chat_id, context.bot)
    elif data == "premium_add":
        context.user_data["state"] = "premium_custom"
        await send_text(
            context.bot,
            chat_id,
            "✨ Custom emoji yuboring, emoji ID raqamini yozing yoki custom emoji bor xabarni forward qiling:",
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
    elif data == "premium_toggle":
        current = db.setting("premium_emoji_enabled", "1") == "1"
        db.set_setting("premium_emoji_enabled", "0" if current else "1")
        await send_text(context.bot, chat_id, f"✨ Premium Emoji: {'🔴 O‘chirilgan' if current else '🟢 Yoqilgan'}")
    elif data == "vip_card_edit":
        context.user_data["state"] = "vip_card_number"
        await send_text(
            context.bot,
            chat_id,
            "💳 Karta raqamini yuboring:",
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
    elif data == "vip_price_edit":
        context.user_data["state"] = "vip_price"
        await send_text(
            context.bot,
            chat_id,
            f"💰 Yangi VIP narxini so‘mda yuboring (hozirgi: {db.setting('vip_price', '5000')}):",
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
    elif data.startswith("premium_edit:"):
        context.user_data["editing_premium_id"] = int(data.split(":")[1])
        context.user_data["state"] = "premium_edit"
        await send_text(
            context.bot,
            chat_id,
            "✨ Yangi custom emoji yuboring, ID raqamini yozing yoki xabarni forward qiling:",
            reply_markup=flow_keyboard(CANCEL_BUTTON),
        )
    elif data.startswith("serial_add:"):
        movie_id = int(data.split(":")[1])
        movie = movie_by_id(movie_id)
        if movie and str(movie["content_type"] or "") == "serial":
            context.user_data["serial_movie_id"] = movie_id
            context.user_data.setdefault(
                "serial",
                {
                    "code": movie["code"],
                    "title": movie["title"],
                    "caption": movie["caption"],
                },
            )
            context.user_data["state"] = "serial_episode"
            await send_text(
                context.bot,
                chat_id,
                "🎞 Keyingi serial qismini yuboring. U avtomatik navbatdagi qism bo‘lib saqlanadi:",
                reply_markup=flow_keyboard(CANCEL_BUTTON),
            )
    elif data.startswith("serial_finish:"):
        movie_id = int(data.split(":")[1])
        movie = movie_by_id(movie_id)
        episodes = db.execute(
            "SELECT COUNT(*) AS n FROM episodes WHERE movie_id = ?",
            (movie_id,),
            one=True,
        )
        context.user_data.clear()
        await send_text(
            context.bot,
            chat_id,
            f"🎉 Serial muvaffaqiyatli saqlandi!\n"
            f"🔢 Kodi: {movie['code'] if movie else movie_id}\n"
            f"🎞 Qismlar: {episodes['n']}",
            reply_markup=admin_keyboard(),
        )
    elif data.startswith("premium_delete:"):
        db.execute("DELETE FROM premium_emojis WHERE id = ?", (int(data.split(":")[1]),))
        await send_text(context.bot, chat_id, "🗑 Emoji mapping o‘chirildi.")
    elif data == "premium_menu":
        await premium_menu(
            Update(update.update_id, callback_query=query), context
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, NetworkError):
        logger.warning("Telegram server ulanishi vaqtincha uzildi; polling qayta urinadi.")
        return
    logger.error("Unhandled error: %s", context.error, exc_info=context.error)
    if (
        isinstance(update, Update)
        and update.effective_user
        and update.effective_message
        and not update.channel_post
        and not update.edited_channel_post
    ):
        try:
            error_text = normalize_emojis(
                "❌ Kutilmagan xatolik yuz berdi. Qayta urinib ko‘ring."
            )
            await update.effective_message.reply_text(
                error_text,
                entities=premium_entities(error_text) or None,
            )
        except TelegramError:
            pass


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable'i kiritilmagan. "
            "Botni ishga tushirishdan oldin BOT_TOKEN ni sozlang."
        )
    if not ADMIN_IDS:
        raise RuntimeError(
            "ADMIN_IDS environment variable'i kiritilmagan. "
            "Kamida bitta Telegram admin ID sini sozlang."
        )
    bot_request = HTTPXRequest(
        connection_pool_size=16,
        connect_timeout=30,
        read_timeout=60,
        write_timeout=60,
        pool_timeout=15,
        http_version="1.1",
    )
    updates_request = HTTPXRequest(
        connection_pool_size=4,
        connect_timeout=30,
        read_timeout=90,
        write_timeout=60,
        pool_timeout=15,
        http_version="1.1",
    )
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(bot_request)
        .get_updates_request(updates_request)
        .build()
    )
    application.add_handler(CommandHandler("start", on_start))
    application.add_handler(CommandHandler("cancel", on_cancel))
    application.add_handler(CommandHandler("files", send_project_files))
    application.add_handler(CommandHandler("database", send_database_files))
    application.add_handler(CommandHandler("allmovies", on_message))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, on_message))
    application.add_error_handler(error_handler)
    if application.job_queue:
        application.job_queue.run_repeating(
            database_backup_job,
            interval=6 * 60 * 60,
            first=60,
            name="sqlite-backup",
        )
    return application


if __name__ == "__main__":
    app = build_application()
    logger.info(
        "AI: OpenAI=%s | Gemini=%s | FFmpeg=%s",
        bool(OPENAI_API_KEY),
        bool(GEMINI_API_KEY),
        bool(shutil.which(FFMPEG_BIN)),
    )
    logger.info("Bot polling rejimida ishga tushmoqda.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)