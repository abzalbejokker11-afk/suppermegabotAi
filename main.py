"""
SuperAgentBot — mustaqil, tinim bilmaydigan Telegram post agenti.
Ishga tushirish:  python main.py
"""
import asyncio
import logging
import os
import random
import sys
import time
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

import ai_engine
import config
import topics
from ai_handler import (answer_question, generate_antidoping_post,
                        generate_morning_post, generate_person_post, parse_reminder)
from keep_alive import STATUS, keep_alive
from publisher import publish, generate_voice
from textutils import clean_for_channel

# ---------------------------------------------------------------- logging
os.makedirs(config.STATE_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-10s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(os.path.join(config.STATE_DIR, "bot.log"), encoding="utf-8")],
)
log = logging.getLogger("main")

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher()

# Eslatmalar qayta ishga tushgandan keyin ham saqlanadi
scheduler = AsyncIOScheduler(
    timezone=config.TIMEZONE,
    jobstores={"default": SQLAlchemyJobStore(
        url=f"sqlite:///{os.path.join(config.STATE_DIR, 'jobs.sqlite')}")},
    job_defaults={"coalesce": True, "misfire_grace_time": 1800, "max_instances": 1},
)


def is_admin(message: Message) -> bool:
    return message.from_user and message.from_user.id in config.ADMIN_IDS


# ================================================================ VAZIFA HIMOYASI
async def guarded(name: str, coro_fn, retries: int = 3):
    """Rejalashtirilgan vazifani hech qachon yiqilmaydigan qilib o'raydi."""
    for i in range(retries):
        try:
            await coro_fn()
            return True
        except Exception as e:
            STATUS["errors"] += 1
            log.exception("Vazifa xatosi [%s] urinish %d: %s", name, i + 1, e)
            await asyncio.sleep(60 * (i + 1))
    log.error("Vazifa butunlay bajarilmadi: %s", name)
    try:
        for admin in config.ADMIN_IDS:
            await bot.send_message(admin, f"Diqqat: '{name}' vazifasi bajarilmadi. Loglarni tekshiring.")
    except Exception:
        pass
    return False


# ================================================================ POST ISHLAB CHIQARISH
async def do_morning():
    text = await asyncio.to_thread(generate_morning_post)
    await publish(bot, text, None, with_voice=True)


async def do_person(person=None):
    person = person or random.choice(list(topics.PERSON_TRAITS.keys()))
    text, img = await asyncio.to_thread(generate_person_post, person)
    await publish(bot, text, img, with_voice=True)


async def do_antidoping():
    text, img = await asyncio.to_thread(generate_antidoping_post)
    await publish(bot, text, img, with_voice=True)


# Rejalashtirilgan chaqiruvlar (APScheduler ular uchun modul darajasidagi nom talab qiladi)
async def job_morning():
    await guarded("tonggi post", do_morning)


async def job_person(person=None):
    await guarded(f"shaxsiy post {person}", lambda: do_person(person))


async def job_antidoping():
    await guarded("antidoping post", do_antidoping)


# ================================================================ FSM
class AdminStates(StatesGroup):
    waiting_for_voice_text = State()
    waiting_for_reminder = State()


# ================================================================ BUYRUQLAR
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message):
        await message.reply("Assalomu alaykum! Savolingizni yozing, javob beraman.")
        return
    await message.reply(
        "Assalomu alaykum!\n\n"
        "Pastdagi Menu tugmasidan kerakli post turini tanlang.\n"
        "/holat — botning va sun'iy intellekt modellarining hozirgi ahvoli\n"
        "/antidoping — chuqur ilmiy antidoping post"
    )


@dp.message(Command("holat"))
async def status_cmd(message: Message):
    if not is_admin(message):
        return
    s = ai_engine.stats()
    used, total = topics.progress("antidoping", topics.ANTIDOPING)
    lines = [
        f"Ish vaqti: {int((time.time() - STATUS['started']) // 60)} daqiqa",
        f"Joylangan postlar: {STATUS['posts']}   Xatolar: {STATUS['errors']}",
        f"Oxirgi post: {STATUS['last_post'] or 'hali yo`q'}",
        f"AI chaqiruvlar: {s['calls']}, muvaffaqiyat: {s['ok']}, yiqilish: {s['fail']}, "
        f"oflayn rejim: {s['offline']}",
        f"Antidoping mavzulari: {used} / {total} ishlatilgan",
        "",
        "Modellar:",
    ]
    for tag, keys, state in ai_engine.health():
        lines.append(f"  {tag} ({keys} kalit) — {state}")
    await message.reply("\n".join(lines)[:4000])


@dp.message(Command("tonggi_post"))
@dp.message(Command("rahmatillo"))
@dp.message(Command("mirjalol"))
@dp.message(Command("abdullo"))
@dp.message(Command("antidoping"))
async def handle_command_post(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await state.clear()

    cmd = message.text.lstrip("/").split()[0].split("@")[0].lower()
    wait = await message.reply("Post tayyorlanmoqda... Bu bir necha daqiqa olishi mumkin.")

    try:
        if cmd == "tonggi_post":
            text, img = await asyncio.to_thread(generate_morning_post), None
        elif cmd == "antidoping":
            text, img = await asyncio.to_thread(generate_antidoping_post)
        else:
            person = cmd.capitalize()
            text, img = await asyncio.to_thread(generate_person_post, person)
    except Exception as e:
        log.exception("Post yaratishda xato")
        await wait.edit_text(f"Post yaratishda xatolik: {e}")
        return

    if not text or len(text.strip()) < 40:
        await wait.edit_text("Matn juda qisqa chiqdi. Qayta urinib ko'ring.")
        return

    await wait.edit_text(f"Matn tayyor ({len(text)} belgi). Kanalga joylanmoqda...")
    ok, msg = await publish(bot, text, img, with_voice=True)
    await wait.edit_text(("Tayyor! " if ok else "Xatolik: ") + msg + f"\n\n{text[:300]}...")


# ---------------------------------------------------------------- maxsus ovoz
@dp.message(Command("maxsus_ovoz"))
async def custom_voice_prompt(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await message.reply("Ovozga aylantirib kanalga joylamoqchi bo'lgan matnni yuboring:")
    await state.set_state(AdminStates.waiting_for_voice_text)


@dp.message(AdminStates.waiting_for_voice_text)
async def process_custom_voice(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await state.clear()
    wait = await message.reply("Ovoz yaratilmoqda...")
    text = clean_for_channel(message.text or "")
    ok, msg = await publish(bot, text, None, with_voice=True)
    await wait.edit_text("Yuborildi!" if ok else f"Xatolik: {msg}")


# ---------------------------------------------------------------- eslatma
async def send_reminder_post(text_to_post: str):
    await guarded("eslatma", lambda: publish(
        bot, clean_for_channel(text_to_post), None, with_voice=True, header="ESLATMA"))


@dp.message(Command("eslatma"))
async def reminder_prompt(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await message.reply(
        "Eslatmani oddiy tilda yozing.\n"
        "Masalan: Ertaga soat o'nda Mirjalolga moy almashtirishni eslat.")
    await state.set_state(AdminStates.waiting_for_reminder)


@dp.message(AdminStates.waiting_for_reminder)
async def process_reminder(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await state.clear()
    wait = await message.reply("Vaqt hisoblanmoqda...")
    parsed = await asyncio.to_thread(parse_reminder, message.text)

    if "XATO" in parsed.upper() or "|" not in parsed:
        await wait.edit_text("Eslatma vaqtini tushunmadim. Sana va soatni aniqroq yozing.")
        return

    date_str, rem_text = parsed.split("|", 1)
    try:
        run_date = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M")
        if run_date <= datetime.now():
            await wait.edit_text("Bu vaqt allaqachon o'tib ketgan. Kelajakdagi vaqtni yozing.")
            return
        scheduler.add_job(send_reminder_post, "date", run_date=run_date,
                          args=[rem_text.strip()], replace_existing=False)
        await wait.edit_text(
            f"Eslatma o'rnatildi!\nVaqti: {run_date.strftime('%Y-%m-%d %H:%M')}\n"
            f"Vazifa: {rem_text.strip()}")
    except Exception as e:
        await wait.edit_text(f"Vaqtni belgilashda xatolik: {e}")


# ---------------------------------------------------------------- savollar

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

@dp.message(Command("mavzular"))
async def show_topics_menu(message: Message):
    if not is_admin(message):
        return
    import topics
    markup = InlineKeyboardMarkup(inline_keyboard=[])
    for i, t in enumerate(topics.ANTIDOPING):
        markup.inline_keyboard.append([InlineKeyboardButton(text=f"{i+1}. {t[:40]}...", callback_data=f"topic_{i}")])
    
    await message.reply("Quyidagi mavzulardan birini tanlang. Tanlangan mavzu to'g'ridan-to'g'ri kanalga joylanadi:", reply_markup=markup)

@dp.callback_query(lambda c: c.data and c.data.startswith("topic_"))
async def process_topic_callback(callback_query: CallbackQuery):
    if not is_admin(callback_query.message):
        return
    await callback_query.answer("Mavzu tayyorlanmoqda, kuting...")
    
    idx = int(callback_query.data.split("_")[1])
    import topics
    topic_name = topics.ANTIDOPING[idx]
    
    # We set the sequence state to this idx so that ai_handler thinks it's this topic
    import kv_storage
    st = kv_storage.kv_get("topics_state", {})
    st["antidoping_idx"] = idx
    kv_storage.kv_set("topics_state", st)
    
    try:
        from ai_handler import generate_antidoping_post
        import asyncio
        from publisher import publish
        text, img = await asyncio.to_thread(generate_antidoping_post)
        if text:
            await publish(bot, text, img, with_voice=True)
            await bot.send_message(callback_query.from_user.id, f"✅ #{idx+1}-Mavzu kanalga muvaffaqiyatli joylandi!")
        else:
            await bot.send_message(callback_query.from_user.id, "Xatolik: Matn bo'sh chiqdi.")
    except Exception as e:
        await bot.send_message(callback_query.from_user.id, f"Xatolik yuz berdi: {e}")

@dp.message()
async def handle_questions(message: Message):
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    try:
        me = await bot.get_me()
        is_reply = (message.reply_to_message and message.reply_to_message.from_user
                    and message.reply_to_message.from_user.id == me.id)
        mentioned = me.username and f"@{me.username}" in text
        if not (message.chat.type == "private" or "?" in text or is_reply or mentioned):
            return
        try:
            await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        except Exception:
            pass
        answer = await asyncio.to_thread(answer_question, text)
        await message.reply(answer or "Javob tayyorlab bo'lmadi, qayta urinib ko'ring.")
    except Exception as e:
        log.exception("Savolga javob berishda xato: %s", e)


@dp.channel_post()
async def handle_channel_post(message: Message):
    return  # kanaldagi o'z postlarimizga javob bermaymiz


# ================================================================ JADVAL
def setup_schedule():
    j = scheduler.add_job
    j(job_morning, "cron", hour=7, minute=0, id="morning", replace_existing=True)

    j(job_person, "cron", hour=13, minute=0, args=["Mirjalol"], id="p_mirjalol", replace_existing=True)
    j(job_person, "cron", hour=14, minute=0, args=["Rahmatillo"], id="p_rahmatillo", replace_existing=True)
    j(job_person, "cron", hour=15, minute=0, args=["Abdullo"], id="p_abdullo", replace_existing=True)

    j(job_antidoping, "cron", hour="*", minute=0, id="antidoping", replace_existing=True)

    log.info("Jadval o'rnatildi: %d ta vazifa", len(scheduler.get_jobs()))


async def watchdog():
    """Uzoq vaqt post chiqmasa — o'zi tekshirib, zaxira post joylaydi."""
    while True:
        await asyncio.sleep(1800)
        try:
            last = STATUS.get("last_post")
            if last:
                delta = time.time() - time.mktime(time.strptime(last, "%Y-%m-%d %H:%M:%S"))
                hour = datetime.now().hour
                if delta > 5 * 3600 and 8 <= hour <= 22:
                    log.warning("Besh soatdan beri post yo'q — zaxira post joylanmoqda")
                    await guarded("watchdog antidoping", do_antidoping, retries=2)
        except Exception as e:
            log.warning("Watchdog xatosi: %s", e)


# ================================================================ ISHGA TUSHIRISH
async def run_bot():
    problems = config.missing_critical()
    if problems:
        log.error("Sozlamalar to'liq emas: %s", ", ".join(problems))
        if not config.BOT_TOKEN:
            return

    await bot.set_my_commands([
        BotCommand(command="antidoping", description="Ilmiy antidoping post"),
        BotCommand(command="tonggi_post", description="Tonggi post"),
        BotCommand(command="rahmatillo", description="Rahmatillo uchun post"),
        BotCommand(command="mirjalol", description="Mirjalol uchun post"),
        BotCommand(command="abdullo", description="Abdullo uchun post"),
        BotCommand(command="maxsus_ovoz", description="Maxsus ovozli xabar"),
        BotCommand(command="eslatma", description="Aniq vaqtli eslatma"),
        BotCommand(command="holat", description="Bot va AI holati"),
    ])

    if not scheduler.running:
        setup_schedule()
        scheduler.start()

    asyncio.create_task(watchdog())

    log.info("Bot ishga tushdi. Kanal: %s | AI marshrutlari: %d",
             config.CHANNEL_ID, len(ai_engine.health()))
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def supervisor():
    """Polling yiqilsa ham bot o'zini qayta tiklaydi — cheksiz."""
    keep_alive()
    delay = 5
    while True:
        try:
            await run_bot()
            delay = 5
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            log.exception("Bot yiqildi, qayta ishga tushirilmoqda (%s soniya): %s", delay, e)
            await asyncio.sleep(delay)
            delay = min(300, delay * 2)


if __name__ == "__main__":
    try:
        asyncio.run(supervisor())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot to'xtatildi.")
