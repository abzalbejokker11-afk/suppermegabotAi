import os
import logging
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google GenAI client yaratish
os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY or ""
client = genai.Client()
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
        logging.error(f"Gemini API xatosi: {e}")
        return f"Kechirasiz, xatolik yuz berdi: {str(e)}"

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

    prompt = f"""
    Sen tajribali va xarizmatik IT blogersan. Telegram kanalingda ertalabki postni yozyapsan.
    Hozirgi yangiliklar:
    {news_text}
    Shu yangiliklardan foydalanib, dasturchilar uchun juda qiziqarli, motivatsion va o'zbek tilida tonggi post tayyorla. Post ohangi do'stona va pozitiv bo'lsin. Emoji'lar ishlating.
    """
    return call_gemini(prompt)

def generate_person_post(person_name):
    prompt = f"""
    Sen juda aqlli va quvnoq botsan. {person_name} ismli yigit uchun maxsus telegram post tayyorlashing kerak.
    Unga juda qiziqarli, o'zbek tilida, do'stona va pozitiv ohangda bitta qisqa voqea, hazil yoki motivatsiya yozib ber. 
    Postni shaxsan unga qaratib yoz. Mantiqli va hayotiy bo'lsin.
    """
    return call_gemini(prompt)
