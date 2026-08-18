import asyncio
import logging
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from ai_handler import answer_question, generate_morning_post, generate_person_post, parse_reminder
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

# ----- FSM STATES -----
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class AdminStates(StatesGroup):
    waiting_for_voice_text = State()
    waiting_for_reminder = State()

# ----- ADMIN PANEL -----
ADMIN_ID = 90581324
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.reply("Assalomu alaykum! Pastki chap burchakdagi **Menu** tugmasini bosing va o'zingizga kerakli post turini tanlang. Men zudlik bilan ishga tushaman!", parse_mode="Markdown")

# ----- POST YARATISH BUYRUQLARI -----
@dp.message(Command("tonggi_post"))
@dp.message(Command("rahmatillo"))
@dp.message(Command("mirjalol"))
@dp.message(Command("abdullo"))
async def handle_command_post(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    cmd = message.text.replace("/", "").split()[0].lower()
    action_map = {
        "tonggi_post": "morning",
        "rahmatillo": "Rahmatillo",
        "mirjalol": "Mirjalol",
        "abdullo": "Abdullo"
    }
    action = action_map.get(cmd)
    if not action: return

    wait_msg = await message.reply("⏳ Kanalga tayyorlanmoqda (10 soniya)... Iltimos kuting.")

    try:
        if action == "morning":
            text = generate_morning_post()
        else:
            text = generate_person_post(action)
    except Exception as e:
        await wait_msg.edit_text(f"❌ AI xatosi: {str(e)}")
        return

    if not text or "xatolik" in text.lower():
        await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {text}")
        return

    voice_filename = f"temp_voice_{action}.ogg"
    has_voice = await generate_voice(text, voice_filename)

    try:
        sent_msg = await bot.send_message(chat_id=CHANNEL_ID, text=text)

        if has_voice and os.path.exists(voice_filename):
            voice_file = FSInputFile(voice_filename)
            await bot.send_voice(chat_id=CHANNEL_ID, voice=voice_file, reply_to_message_id=sent_msg.message_id)
            os.remove(voice_filename)

        await wait_msg.edit_text(f"✅ Muvaffaqiyatli kanalga tashlandi!\n\n{text[:200]}...")
    except Exception as e:
        await wait_msg.edit_text(f"❌ Kanalga tashlashda xatolik!\nXato: {str(e)}")

# ----- MAXSUS OVOZ YARATISH -----
@dp.message(Command("maxsus_ovoz"))
async def custom_voice_prompt(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.reply("✍️ **Ovozga aylantirib, kanalga tashlamoqchi bo'lgan matningizni yozib yuboring:**\n\n*(Bekor qilish uchun Menu'dan boshqa narsa tanlang)*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_voice_text)

@dp.message(AdminStates.waiting_for_voice_text)
async def process_custom_voice(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    
    wait_msg = await message.reply("⏳ Ovoz yaratilmoqda... Iltimos kuting.")
    voice_filename = "custom_voice.ogg"
    has_voice = await generate_voice(message.text, voice_filename)
    
    if has_voice and os.path.exists(voice_filename):
        try:
            voice_file = FSInputFile(voice_filename)
            await bot.send_voice(chat_id=CHANNEL_ID, voice=voice_file, caption=f"🎙 Maxsus xabar:\n\n{message.text[:900]}")
            os.remove(voice_filename)
            await wait_msg.edit_text("✅ Ovozli xabar kanalingizga muvaffaqiyatli yuborildi!")
        except Exception as e:
            await wait_msg.edit_text(f"❌ Kanalga tashlashda xatolik: {e}")
    else:
        await wait_msg.edit_text("❌ Ovoz yaratishda xatolik yuz berdi.")

# ----- ESLATMA YARATISH (SMART REMINDERS) -----
async def send_reminder_post(text_to_post):
    try:
        voice_filename = f"reminder_{datetime.now().strftime('%H%M%S')}.ogg"
        has_voice = await generate_voice(text_to_post, voice_filename)
        caption = f"⏰ **ESLATMA!**\n\n{text_to_post}"
        
        if has_voice and os.path.exists(voice_filename):
            await bot.send_voice(chat_id=CHANNEL_ID, voice=FSInputFile(voice_filename), caption=caption)
            os.remove(voice_filename)
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=caption)
    except Exception as e:
        logging.error(f"Eslatma yuborishda xatolik: {e}")

@dp.message(Command("eslatma"))
async def reminder_prompt(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.reply("⏰ **Eslatmani yozing!**\nSana, vaqt va eslatma qilinishi kerak bo'lgan vazifani oddiy tilda yozavering.\n\n_Masalan: Ertaga soat 10:00 da Mirjalolga moy almashtirishni kanalga tashla._", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_reminder)

@dp.message(AdminStates.waiting_for_reminder)
async def process_reminder(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    
    wait_msg = await message.reply("⏳ Vaqt hisoblanmoqda... Kuting.")
    parsed = parse_reminder(message.text)
    
    if "XATO" in parsed or "|" not in parsed:
        await wait_msg.edit_text("❌ Kechirasiz, eslatma vaqtini tushunmadim. Iltimos, soat va kunni aniqroq yozing.")
        return
        
    date_str, rem_text = parsed.split("|", 1)
    try:
        run_date = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M")
        scheduler.add_job(send_reminder_post, 'date', run_date=run_date, args=[rem_text.strip()])
        await wait_msg.edit_text(f"✅ **Eslatma o'rnatildi!**\n📅 Vaqti: {run_date.strftime('%Y-%m-%d %H:%M')}\n📝 Vazifa: {rem_text.strip()}")
    except Exception as e:
        await wait_msg.edit_text(f"❌ Vaqtni belgilashda xatolik: {e}")

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

import random

async def send_person_post():
    try:
        person = random.choice(["Rahmatillo", "Mirjalol", "Abdullo"])

        text = generate_person_post(person)
        voice_filename = "person.ogg"
        has_voice = await generate_voice(text, voice_filename)
        sent = await bot.send_message(chat_id=CHANNEL_ID, text=text)
        if has_voice and os.path.exists(voice_filename):
            await bot.send_voice(chat_id=CHANNEL_ID, voice=FSInputFile(voice_filename), reply_to_message_id=sent.message_id)
            os.remove(voice_filename)
    except Exception as e:
        logging.error(f"Shaxsiy post xatolik: {e}")

from aiogram.types import BotCommand

async def main():
    logging.basicConfig(level=logging.INFO)
    keep_alive()

    # Telegram'ning pastki chap burchagidagi Menu tugmasini sozlash
    await bot.set_my_commands([
        BotCommand(command="tonggi_post", description="🌅 Tonggi post yaratish"),
        BotCommand(command="rahmatillo", description="😎 Rahmatillo uchun post"),
        BotCommand(command="mirjalol", description="🤓 Mirjalol uchun post"),
        BotCommand(command="abdullo", description="🧐 Abdullo uchun post"),
        BotCommand(command="maxsus_ovoz", description="🎙 Maxsus ovozli xabar"),
        BotCommand(command="eslatma", description="⏰ Aniq vaqtli eslatma qo'shish")
    ])

    scheduler.add_job(send_morning_post, 'cron', hour=7, minute=0)
    # Sinov uchun har soatda (8:00 dan 22:00 gacha) avtomatik post tashlaydi
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
