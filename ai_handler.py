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

def generate_person_post(person_name):
    traits = {
        "Mirjalol": "Moshina haydaydi. Unga doim mashina moyini vaqtida almashtirishni, mashinaga qarab yurishni eslat. Yaxshi haydovchi bo'lish bo'yicha maslahatlar ber va hazil qilib tur.",
        "Rahmatillo": "Yoshi o'tib ketyapti, tezroq uylanishi kerak! Unga qiz topishga harakat qilishni, o'ziga qarab yurishni ayt. Hattoki hazillashib, yaxshi joy bo'lsa 'ichkuyov'likka ham rozi bo'laverishini, asosiysi baxt ekanligini tushuntir.",
        "Abdullo": "O'qishi kerak. Kitob o'qishga, kelajakka va o'qishga (universitetga) tayyorgarlik ko'rish eng muhim vazifasi ekanligini ta'kidla. Chalg'imasdan dars qilishini uqtir."
    }
    
    trait = traits.get(person_name, "Unga pozitiv motivatsiya ber.")

    prompt = f"""
    Sen juda aqlli, quvnoq va do'stona botsan. {person_name} ismli yigit uchun maxsus telegram post tayyorlashing kerak.
    {person_name} haqida muhim ma'lumot: {trait}
    
    Ushbu ma'lumotlarga asoslanib unga juda qiziqarli, o'zbek tilida, do'stona va pozitiv (hazil aralash) ohangda qisqa post yozib ber. 
    Postni shaxsan unga qaratib yoz. Mantiqli, hayotiy va kulgili bo'lsin. Juda cho'zib yuborma.
    """
    return call_gemini(prompt)
