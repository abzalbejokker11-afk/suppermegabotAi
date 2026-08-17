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
CHANNEL_ID = os.getenv("CHANNEL_ID")

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
    # Faqat ADMIN foydalana oladi
    if message.from_user.id != ADMIN_ID:
        await message.reply("Kechirasiz, sizda ushbu buyruqni ishlatish huquqi yo'q.")
        return
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌅 Tonggi post (Live News)", callback_data="post_morning")],
        [InlineKeyboardButton(text="😎 Rahmatillo uchun", callback_data="post_Rahmatillo")],
        [InlineKeyboardButton(text="🤓 Mirjalol uchun", callback_data="post_Mirjalol")],
        [InlineKeyboardButton(text="🧐 Abdullo uchun", callback_data="post_Abdullo")]
    ])
    await message.reply(f"Assalomu alaykum (Sizning ID: {message.from_user.id}). Boshqaruv paneliga xush kelibsiz! Qaysi postni kanalga tashlaymiz?", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("post_"))
async def handle_admin_post(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    await callback.message.edit_text("⏳ Post yaratilmoqda va ovozlashtirilmoqda (10-15 soniya)... Iltimos kuting.")
    
    if action == "morning":
        text = generate_morning_post()
    else:
        text = generate_person_post(action)
        
    if "Xatolik" in text or "Kechirasiz" in text:
        await callback.message.edit_text(f"Xatolik yuz berdi: {text}")
        return

    voice_filename = "temp_voice.ogg"
    has_voice = await generate_voice(text, voice_filename)
    
    try:
        sent_msg = await bot.send_message(chat_id=CHANNEL_ID, text=text)
        
        if has_voice:
            voice_file = FSInputFile(voice_filename)
            await bot.send_voice(chat_id=CHANNEL_ID, voice=voice_file, reply_to_message_id=sent_msg.message_id)
            os.remove(voice_filename)
            
        await callback.message.edit_text(f"✅ Muvaffaqiyatli kanalga tashlandi!\n\n{text}")
    except Exception as e:
        await callback.message.edit_text(f"❌ Kanalga tashlashda xatolik! Bot kanalda Admin ekanligiga va CHANNEL_ID to'g'riligiga ishonch hosil qiling.\nXato: {str(e)}")

# ----- AVTOMATIK POSTLAR (SCHEDULER) -----
async def send_morning_post():
    text = generate_morning_post()
    voice_filename = "morning.ogg"
    has_voice = await generate_voice(text, voice_filename)
    try:
        sent = await bot.send_message(chat_id=CHANNEL_ID, text=text)
        if has_voice:
            await bot.send_voice(chat_id=CHANNEL_ID, voice=FSInputFile(voice_filename), reply_to_message_id=sent.message_id)
            os.remove(voice_filename)
    except Exception as e:
        logging.error(f"Xatolik: {e}")

async def send_person_post():
    hour = datetime.now().hour
    person = "Rahmatillo"
    if hour % 3 == 1:
        person = "Mirjalol"
    elif hour % 3 == 2:
        person = "Abdullo"
        
    text = generate_person_post(person)
    voice_filename = "person.ogg"
    has_voice = await generate_voice(text, voice_filename)
    try:
        sent = await bot.send_message(chat_id=CHANNEL_ID, text=text)
        if has_voice:
            await bot.send_voice(chat_id=CHANNEL_ID, voice=FSInputFile(voice_filename), reply_to_message_id=sent.message_id)
            os.remove(voice_filename)
    except Exception as e:
        logging.error(f"Xatolik: {e}")

# ----- SAVOLLARGA JAVOB BERISH -----
@dp.message()
async def handle_questions(message: Message):
    text = message.text or ""
    
    bot_me = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot_me.id
    is_mentioned = bot_me.username and f"@{bot_me.username}" in text
    
    # Lyuchkada hammasiga javob beradi, guruhda faqat so'roq belgisiga
    if message.chat.type == 'private' or "?" in text or is_reply_to_bot or is_mentioned:
        try:
            await bot.send_chat_action(chat_id=message.chat.id, action="typing")
            answer = answer_question(text)
            await message.reply(answer)
        except Exception as e:
            logging.error(f"Javob berishda xatolik: {e}")

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
    asyncio.run(main())
