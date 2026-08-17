import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from ai_handler import answer_question, generate_morning_post, generate_person_post
from keep_alive import keep_alive
import edge_tts

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
_raw_channel = os.getenv("CHANNEL_ID", "")
if _raw_channel and not _raw_channel.startswith("-"):
    CHANNEL_ID = f"-100{_raw_channel}"
else:
    CHANNEL_ID = _raw_channel

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone='Asia/Tashkent')

async def generate_voice(text, filename="voice.ogg"):
    try:
        communicate = edge_tts.Communicate(text, "uz-UZ-MadinaNeural")
        await communicate.save(filename)
        return True
    except Exception as e:
        logging.error(f"Voice generation failed: {e}")
        return False

# ----- ADMIN PANEL -----
ADMIN_ID = 90581324

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("Kechirasiz, sizda ushbu buyruqni ishlatish huquqi yo'q.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌅 Tonggi post (Live News)", callback_data="post_morning")],
        [InlineKeyboardButton(text="😎 Rahmatillo uchun", callback_data="post_Rahmatillo")],
        [InlineKeyboardButton(text="🤓 Mirjalol uchun", callback_data="post_Mirjalol")],
        [InlineKeyboardButton(text="🧐 Abdullo uchun", callback_data="post_Abdullo")]
    ])
    await message.reply("Boshqaruv paneliga xush kelibsiz! Qaysi postni kanalga tashlaymiz?", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("post_"))
async def handle_admin_post(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Sizda ruxsat yo'q!", show_alert=True)
        return

    action = callback.data.split("_", 1)[1]
    await callback.message.edit_text("⏳ Post yaratilmoqda (10-15 soniya)... Iltimos kuting.")

    try:
        if action == "morning":
            text = generate_morning_post()
        else:
            text = generate_person_post(action)
    except Exception as e:
        await callback.message.edit_text(f"❌ AI xatosi: {str(e)}")
        return

    if not text or "xatolik" in text.lower():
        await callback.message.edit_text(f"❌ Xatolik yuz berdi: {text}")
        return

    voice_filename = "temp_voice.ogg"
    has_voice = await generate_voice(text, voice_filename)

    try:
        sent_msg = await bot.send_message(chat_id=CHANNEL_ID, text=text)

        if has_voice and os.path.exists(voice_filename):
            voice_file = FSInputFile(voice_filename)
            await bot.send_voice(chat_id=CHANNEL_ID, voice=voice_file, reply_to_message_id=sent_msg.message_id)
            os.remove(voice_filename)

        await callback.message.edit_text(f"✅ Muvaffaqiyatli kanalga tashlandi!\n\n{text[:500]}")
    except Exception as e:
        await callback.message.edit_text(f"❌ Kanalga tashlashda xatolik!\nXato: {str(e)}")

# ----- SAVOLLARGA JAVOB BERISH -----
@dp.message()
@dp.channel_post()
async def handle_questions(message: Message):
    text = message.text or ""
    if not text.strip():
        return

    bot_me = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == bot_me.id
    is_mentioned = bot_me.username and f"@{bot_me.username}" in text

    # Agar u shaxsiy chat bo'lsa, YOKI ichida so'roq belgisi bo'lsa, YOKI unga reply qilingan bo'lsa
    if message.chat.type == 'private' or "?" in text or is_reply_to_bot or is_mentioned:
        try:
            # Kanalda chat action yuborish ba'zan xato berishi mumkin, shuning uchun try/except
            try:
                await bot.send_chat_action(chat_id=message.chat.id, action="typing")
            except Exception:
                pass
            answer = answer_question(text)
            await message.reply(answer)
        except Exception as e:
            logging.error(f"Javob berishda xatolik: {e}")

# ----- AVTOMATIK POSTLAR -----
async def send_morning_post():
    try:
        text = generate_morning_post()
        voice_filename = "morning.ogg"
        has_voice = await generate_voice(text, voice_filename)
        sent = await bot.send_message(chat_id=CHANNEL_ID, text=text)
        if has_voice and os.path.exists(voice_filename):
            await bot.send_voice(chat_id=CHANNEL_ID, voice=FSInputFile(voice_filename), reply_to_message_id=sent.message_id)
            os.remove(voice_filename)
    except Exception as e:
        logging.error(f"Tonggi post xatolik: {e}")

async def send_person_post():
    try:
        hour = datetime.now().hour
        person = "Rahmatillo"
        if hour % 3 == 1:
            person = "Mirjalol"
        elif hour % 3 == 2:
            person = "Abdullo"

        text = generate_person_post(person)
        voice_filename = "person.ogg"
        has_voice = await generate_voice(text, voice_filename)
        sent = await bot.send_message(chat_id=CHANNEL_ID, text=text)
        if has_voice and os.path.exists(voice_filename):
            await bot.send_voice(chat_id=CHANNEL_ID, voice=FSInputFile(voice_filename), reply_to_message_id=sent.message_id)
            os.remove(voice_filename)
    except Exception as e:
        logging.error(f"Shaxsiy post xatolik: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    keep_alive()

    scheduler.add_job(send_morning_post, 'cron', hour=7, minute=0)
    for hour in range(8, 23):
        scheduler.add_job(send_person_post, 'cron', hour=hour, minute=0)

    scheduler.start()
    logging.info("Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
