"""
Markaziy sozlamalar. Hamma kalitlar .env dan olinadi.
Bir nechta API kalit qo'ysangiz — bot ularni navbat bilan aylantiradi.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _multi(prefix: str):
    """GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3 ... hammasini yig'adi."""
    keys = []
    base = os.getenv(prefix, "").strip()
    if base:
        keys.append(base)
    i = 2
    while True:
        v = os.getenv(f"{prefix}_{i}", "").strip()
        if not v:
            break
        keys.append(v)
        i += 1
    # vergul bilan ham berish mumkin: GEMINI_API_KEY=key1,key2
    out = []
    for k in keys:
        out.extend([x.strip() for x in k.split(",") if x.strip()])
    # takrorlarni olib tashlash, tartibni saqlash
    seen, uniq = set(), []
    for k in out:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

_raw_channel = os.getenv("CHANNEL_ID", "").strip()
if _raw_channel.startswith("@") or _raw_channel.startswith("-"):
    CHANNEL_ID = _raw_channel
elif _raw_channel:
    CHANNEL_ID = f"-100{_raw_channel}"
else:
    CHANNEL_ID = ""

ADMIN_IDS = set()
for _a in os.getenv("ADMIN_ID", "90581324").replace(",", " ").split():
    try:
        ADMIN_IDS.add(int(_a))
    except ValueError:
        pass

TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")
CITY = os.getenv("CITY", "Tashkent")

# ---------- AI provayderlar ----------
GEMINI_KEYS = _multi("GEMINI_API_KEY")
OPENROUTER_KEYS = _multi("OPENROUTER_API_KEY")
GROQ_KEYS = _multi("GROQ_API_KEY")
CEREBRAS_KEYS = _multi("CEREBRAS_API_KEY")
OPENAI_KEYS = _multi("OPENAI_API_KEY")

# Faqat haqiqatda mavjud model nomlari (eskisida yo'q modellar bor edi)
GEMINI_MODELS = [
    m.strip() for m in os.getenv(
        "GEMINI_MODELS",
        "gemini-2.5-flash,gemini-flash-latest,gemini-2.0-flash,gemini-2.5-flash-lite,gemini-2.0-flash-lite"
    ).split(",") if m.strip()
]

OPENROUTER_MODELS = [
    m.strip() for m in os.getenv(
        "OPENROUTER_MODELS",
        "anthropic/claude-sonnet-5,"
        "meta-llama/llama-3.3-70b-instruct,"
        "deepseek/deepseek-chat,"
        "qwen/qwen-2.5-72b-instruct"
    ).split(",") if m.strip()
]

GROQ_MODELS = [
    m.strip() for m in os.getenv(
        "GROQ_MODELS",
        "llama-3.3-70b-versatile,llama-3.1-8b-instant"
    ).split(",") if m.strip()
]

CEREBRAS_MODELS = [
    m.strip() for m in os.getenv("CEREBRAS_MODELS", "llama-3.3-70b").split(",") if m.strip()
]

OPENAI_MODELS = [
    m.strip() for m in os.getenv("OPENAI_MODELS", "gpt-4o-mini").split(",") if m.strip()
]

GITHUB_PAT = os.getenv("GITHUB_PAT", "").strip()  # ixtiyoriy, kodda hardcode YO'Q

VOICE_NAME = os.getenv("VOICE_NAME", "uz-UZ-MadinaNeural")
VOICE_FALLBACKS = ["uz-UZ-MadinaNeural", "uz-UZ-SardorNeural", "ru-RU-SvetlanaNeural"]

STATE_DIR = os.getenv("STATE_DIR", "state")
KEEP_ALIVE_PORT = int(os.getenv("PORT", "8080"))
SELF_URL = os.getenv("SELF_URL", "").strip()  # Replit/Render URL — o'zini o'zi ping qiladi

# Post uzunligi talablari (antidoping ilmiy post uchun)
MIN_SCIENCE_CHARS = int(os.getenv("MIN_SCIENCE_CHARS", "2600"))
MAX_TG_TEXT = 4000


def missing_critical():
    problems = []
    if not BOT_TOKEN:
        problems.append("BOT_TOKEN")
    if not CHANNEL_ID:
        problems.append("CHANNEL_ID")
    if not (GEMINI_KEYS or OPENROUTER_KEYS or GROQ_KEYS or CEREBRAS_KEYS or OPENAI_KEYS):
        problems.append("hech qanday AI API kaliti")
    return problems
