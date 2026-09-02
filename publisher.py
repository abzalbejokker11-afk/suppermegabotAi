"""
Kanalga chop etish qatlami: rasm + matn + ovoz.
Har bir bosqich alohida himoyalangan — biri yiqilsa qolgani baribir chiqadi.
"""
import asyncio
import logging
import os
import tempfile

from aiogram.types import BufferedInputFile, FSInputFile

import config
from ai_handler import fetch_image
from textutils import chunks
from keep_alive import STATUS

log = logging.getLogger("publisher")

_post_lock = asyncio.Lock()  # bir vaqtda faqat bitta post — takrorlanishning oldini oladi


async def generate_voice(text: str, filename: str) -> bool:
    """edge-tts orqali ovoz. Bir nechta ovoz varianti bilan qayta uriniladi."""
    import edge_tts
    voices = [config.VOICE_NAME] + [v for v in config.VOICE_FALLBACKS if v != config.VOICE_NAME]
    # Telegram ovozli xabari uchun matn juda uzun bo'lsa qisqartiramiz
    speech = text if len(text) <= 8000 else text[:8000].rsplit(".", 1)[0] + "."
    for voice in voices:
        for attempt in range(2):
            try:
                communicate = edge_tts.Communicate(speech, voice)
                await asyncio.wait_for(communicate.save(filename), timeout=180)
                if os.path.exists(filename) and os.path.getsize(filename) > 2000:
                    return True
            except Exception as e:
                log.warning("Ovoz xatosi [%s] urinish %d: %s", voice, attempt + 1, e)
                await asyncio.sleep(2 + attempt * 3)
    return False


async def _retry(coro_fn, tries=3, label=""):
    last = None
    for i in range(tries):
        try:
            return await coro_fn()
        except Exception as e:
            last = e
            log.warning("Telegram xatosi [%s] urinish %d: %s", label, i + 1, e)
            await asyncio.sleep(3 * (i + 1))
    log.error("Telegram bosqichi yiqildi [%s]: %s", label, last)
    return None


async def publish(bot, text: str, image_url: str | None = None,
                  with_voice: bool = True, header: str | None = None):
    """
    Kanalga to'liq post joylaydi. Natija: (muvaffaqiyat: bool, xabar: str)
    """
    if not text or not text.strip():
        return False, "Matn bo'sh"

    async with _post_lock:
        body = (header + "\n\n" + text) if header else text
        parts = chunks(body, config.MAX_TG_TEXT)

        first_msg_id = None

        # 1) Rasm
        if image_url:
            img_bytes = await asyncio.to_thread(fetch_image, image_url)
            if img_bytes:
                photo = BufferedInputFile(img_bytes, filename="post.jpg")
                sent = await _retry(
                    lambda: bot.send_photo(chat_id=config.CHANNEL_ID, photo=photo),
                    label="photo")
                if sent:
                    first_msg_id = sent.message_id

        # 2) Matn (bo'laklab)
        reply_to = first_msg_id
        for part in parts:
            sent = await _retry(
                lambda p=part, r=reply_to: bot.send_message(
                    chat_id=config.CHANNEL_ID, text=p, reply_to_message_id=r),
                label="text")
            if sent is None:
                # reply_to noto'g'ri bo'lishi mumkin — reply'siz qayta urinish
                sent = await _retry(
                    lambda p=part: bot.send_message(chat_id=config.CHANNEL_ID, text=p),
                    label="text-plain")
            if sent:
                if first_msg_id is None:
                    first_msg_id = sent.message_id
                reply_to = sent.message_id

        if first_msg_id is None:
            STATUS["errors"] += 1
            return False, "Kanalga matn yuborilmadi"

        # 3) Ovoz
        if with_voice:
            fd, path = tempfile.mkstemp(suffix=".ogg")
            os.close(fd)
            try:
                # Ovozdan #Dars degan bosh qismini kesib tashlaymiz, Madina o'qimasligi uchun
                voice_text = text
                if voice_text.startswith("#"):
                    parts = voice_text.split("\n\n", 1)
                    if len(parts) == 2:
                        voice_text = parts[1]
                        
                if await generate_voice(voice_text, path):
                    await _retry(
                        lambda: bot.send_voice(chat_id=config.CHANNEL_ID,
                                               voice=FSInputFile(path),
                                               reply_to_message_id=first_msg_id),
                        label="voice")
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass

        STATUS["posts"] += 1
        import time
        STATUS["last_post"] = time.strftime("%Y-%m-%d %H:%M:%S")
        import keep_alive
        keep_alive.save_status()
        return True, "Muvaffaqiyatli joylandi"
