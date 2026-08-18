import os
import logging
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google GenAI client yaratish
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-3.6-flash"

def call_gemini(prompt):
    if not GEMINI_API_KEY:
        return "Sun'iy intellekt API kaliti sozlanmagan!"
    
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Gemini API xatosi: {error_msg}")
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return "Kechirasiz, Sun'iy Intellekt hozir juda ko'p so'rov qabul qildi (Google bepul limitiga tushib qoldik). Iltimos, 1 daqiqa kutib turing va qayta urinib ko'ring!"
        return f"Kechirasiz, xatolik yuz berdi: {error_msg}"

def answer_question(question):
    prompt = f"Sen Telegram kanaldagi aqlli va pozitiv yordamchisan. Foydalanuvchi quyidagi savolni berdi:\n\"{question}\"\nUnga o'zbek tilida, do'stona, to'g'ri va yordam beruvchi ohangda qisqa javob yoz."
    return call_gemini(prompt)

def generate_morning_post():
    try:
        gh_resp = requests.get("https://api.github.com/search/repositories?q=stars:>5000&sort=updated&order=desc&per_page=3", timeout=10)
        if gh_resp.status_code == 200:
            items = gh_resp.json().get("items", [])
            news_text = "Bugungi GitHub IT yangiliklari:\n"
            for item in items:
                news_text += f"- {item['name']}: {item.get('description', 'Tavsif mavjud emas')}\n"
        else:
            news_text = "Bugun IT olamida juda ko'p qiziqarli yangiliklar bo'lyapti."
    except Exception:
        news_text = "Bugun texnologiyalar olamida katta kashfiyotlar kuni bo'lishi kutilmoqda."

    weather_text = ""
    try:
        w_resp = requests.get("https://wttr.in/Tashkent?format=%C+%t", timeout=5)
        if w_resp.status_code == 200:
            weather_text = f"Toshkentda hozirgi ob-havo: {w_resp.text.strip()}"
    except Exception:
        pass

    prompt = f"""
    Sen tajribali va xarizmatik IT blogersan. Telegram kanalingda ertalabki postni yozyapsan.
    Hozirgi yangiliklar:
    {news_text}
    {weather_text}
    Shu ma'lumotlardan va ob-havodan foydalanib, dasturchilar uchun juda qiziqarli, motivatsion va o'zbek tilida tonggi post tayyorla. Post ohangi do'stona va pozitiv bo'lsin. Emoji'lar ishlating.
    """
    return call_gemini(prompt)

import random

def generate_person_post(person_name):
    traits = {
        "Mirjalol": [
            "Mashina moyini almashtirish va motorga texnik xizmat ko'rsatish haqida o'ziga xos eslatma.",
            "Yo'l qoidalariga rioya qilish, radar va tezlikni oshirmaslik haqida hazilomuz maslahat.",
            "Mashinani doim top-toza tutish (moykaga tez-tez kirish) va chiroyli haydash haqida.",
            "Benzinni tejab haydash sirlari va moshina xarajatlarini kamaytirish haqida.",
            "Mashinada yaxshi musiqa qo'yib, hayotdan zavqlanib haydash va yaxshi kayfiyat haqida motivatsiya."
        ],
        "Rahmatillo": [
            "Tezroq uylanish kerakligi, qiz topish va uydagilarni xursand qilish haqida hazil.",
            "Yaxshi joy bo'lsa 'ichkuyov'likka ham rozi bo'laverish kerakligi, asosiysi qizning qalb go'zalligi ekanligi haqida kulgili maslahat.",
            "Qizlarga yoqish uchun o'ziga qarab yurish, sport bilan shug'ullanish va zamonaviy kiyinish haqida.",
            "Kelajakdagi to'y xarajatlari uchun ko'proq ish ishlash, pul topish va tejash haqida motivatsiya.",
            "Haqiqiy sevgi va munosabatlar psixologiyasi, o'z tengini topish qiyinligi haqida qisqa falsafiy post."
        ],
        "Abdullo": [
            "Kitob o'qish, ilm olish va universitetga tayyorgarlik ko'rish eng muhim vazifasi ekanligi haqida qattiq motivatsiya.",
            "Ijtimoiy tarmoqlar (Insta, TikTok) va o'yinlardan chalg'imasdan dars qilishga chaqiriq.",
            "Vaqtni to'g'ri taqsimlash va kelajakda kuchli mutaxassis bo'lish sirlari haqida.",
            "Imtihonlarga tayyorgarlik paytidagi dangasalikni yengish va miyani charxlash haqida maslahat.",
            "Universitetdagi qiziqarli hayot va talabalikning oltin davri haqida ilhomlantiruvchi post."
        ]
    }
    
    person_topics = traits.get(person_name, ["Unga ijobiy va pozitiv motivatsiya ber."])
    selected_topic = random.choice(person_topics)

    prompt = f"""
    Sen juda aqlli, quvnoq va do'stona botsan. {person_name} ismli yigit uchun maxsus telegram post tayyorlashing kerak.
    
    Bugun {person_name} uchun TANLANGAN MAVZU: "{selected_topic}"
    
    Ushbu MAVZUDAN chiqmagan holatda, aynan shu narsa haqida qaratib unga juda qiziqarli, o'zbek tilida, do'stona va pozitiv (hazil aralash) ohangda qisqa post yozib ber. 
    Postni shaxsan unga qaratib yoz (masalan, "Qalay {person_name}", "Eshityapsanmi {person_name}" kabi). Mantiqli, hayotiy va kulgili bo'lsin. Juda cho'zib yuborma.
    """
    return call_gemini(prompt)

import datetime
def parse_reminder(text):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = f"""
    Sen vaqtni tahlil qiluvchi aqlli botsan. Hozirgi vaqt: {now}.
    Foydalanuvchi ushbu eslatmani yozdi: "{text}"
    Sening vazifang matndan sanani, soatni va eslatma mazmunini aniqlash.
    Agar foydalanuvchi "ertaga", "indinga" kabi so'zlarni ishlatsa, hozirgi vaqtga qarab hisobla. Agar faqat soat berilsa va u o'tib ketgan bo'lsa, ertangi kunga o'tkaz.
    Natijani faqat mana shu qat'iy formatda qaytar (ortiqcha so'z yozma):
    YYYY-MM-DD HH:MM|eslatma mazmuni
    Masalan: 2026-08-19 10:00|Mirjalolga moshina moyini almashtirishni eslatish
    Agar vaqtni mutlaqo tushunmasang, faqatgina "XATO" deb yoz.
    """
    return call_gemini(prompt).strip()
