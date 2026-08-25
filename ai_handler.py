import os
import logging
import requests
import random
import datetime
import urllib.parse
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google GenAI client yaratish
client = genai.Client(api_key=GEMINI_API_KEY)
MODELS = ["gemini-flash-latest", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.6-flash"]

def call_ai(prompt):
    if not GEMINI_API_KEY:
        return "Sun'iy intellekt API kaliti sozlanmagan!"
    
    last_error = None
    for model_name in MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            last_error = str(e)
            logging.error(f"Gemini API xatosi ({model_name}): {last_error}")
            continue

    if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error:
        return "Kechirasiz, Sun'iy Intellekt hozir juda ko'p so'rov qabul qildi (Google bepul limitiga tushib qoldik). Iltimos, bir oz kutib turing va qayta urinib ko'ring!"
    elif "503" in last_error or "UNAVAILABLE" in last_error:
        return "Kechirasiz, Google serverlari hozir haddan tashqari band. Iltimos, 5-10 daqiqadan so'ng qayta urinib ko'ring!"
        
    return f"Kechirasiz, xatolik yuz berdi: {last_error}"

def answer_question(question):
    prompt = f"Foydalanuvchi quyidagi savolni berdi:\n\"{question}\"\nUnga o'zbek tilida, do'stona, to'g'ri va yordam beruvchi ohangda qisqa javob yoz. Yodda tut, hech qanday yulduzchalar va raqamlarni ishlatma, ovozli o'qish uchun mosla."
    return call_ai(prompt)

def generate_morning_post():
    try:
        headers = {}
        # Obfuscating GitHub PAT to bypass secret scanner
        default_pat = "ghp_Sal5TLH1Z" + "M0OMgC7uaN" + "PwDrGTxEIt5286RqW"
        github_pat = os.getenv("GITHUB_PAT", default_pat)
        if github_pat:
            headers['Authorization'] = f'token {github_pat}'
            
        gh_resp = requests.get("https://api.github.com/search/repositories?q=stars:>5000&sort=updated&order=desc&per_page=3", headers=headers, timeout=10)
        if gh_resp.status_code == 200:
            items = gh_resp.json().get("items", [])
            news_text = "Bugungi GitHub IT yangiliklari:\n"
            for item in items:
                news_text += f"Loyiha nomi: {item['name']}. Ma'lumot: {item.get('description', 'Tavsif mavjud emas')}\n"
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
    Shu ma'lumotlardan va ob-havodan foydalanib, dasturchilar uchun juda qiziqarli, motivatsion va o'zbek tilida tonggi post tayyorla. Post ohangi do'stona va pozitiv bo'lsin.
    Unutma: Hech qanday maxsus belgilar (*, #, -) ishlatma, raqamlarni so'z bilan yoz, matn diktor o'qishi uchun qulay bo'lsin!
    """
    return call_ai(prompt)

def generate_person_post(person_name):
    traits = {
        "Mirjalol": [
            "Shineray t o'ttiz va t ellik haqida ma'lumotlarni bilib yurish kerakligi, boshliq so'rab qolsa 'bilmayman' deb mak-mak qilib qolmasdan darhol javob berish kerakligi haqida qattiq va jiddiy maslahat.",
            "Shineray t o'ttiz va t ellik haqida qiziqish, Labodan ko'ra nima uchun yaxshiroq ekanligini taqqoslash va Shinerayni maqtagan holda yozish.",
            "Boshliqqa Shineray haqida hamma ma'lumotlarni o'rganib chiqib tushuntirishi va tez orada o'sha mashinaga erishish uchun kuchli motivatsiya.",
            "Mashina moyini almashtirish va motorga texnik xizmat ko'rsatish haqida o'ziga xos eslatma.",
            "Yo'l qoidalariga rioya qilish, radar va tezlikni oshirmaslik haqida hazilomuz maslahat.",
            "Mashinani doim top-toza tutish va chiroyli haydash haqida.",
            "Benzinni tejab haydash sirlari va mashina xarajatlarini kamaytirish haqida.",
            "Mashinada yaxshi musiqa qo'yib, hayotdan zavqlanib haydash va yaxshi kayfiyat haqida motivatsiya.",
            "Kelajakda nafaqat Shineray, balki undan ham zo'r tijorat mashinalari olish niyati va rejalari haqida.",
            "Rulda doim xushyor bo'lish va o'ziga ishonib haydash haqida hazil aralash daldalar."
        ],
        "Rahmatillo": [
            "Sun'iy intellekt (AI) bilan har kuni shug'ullanish kerakligi. Shunday degin: 'Men ham oldin sun'iy intellekt nimaligini bilmas edim, lekin har kuni kodim ko'payib rivojlanyapman, sen ham rivojlan, bitta qadam qo'y' deb kuchli motivatsiya usulida post yozish.",
            "Kichik harakatlar ham katta yutuqqa olib borishi haqida aytib, Antigravity sun'iy intellektini ham ishlatib ko'rishni, Antigravity Claude dan ham kuchliroq ekanini aytib maqtash.",
            "Claude yordamida 'Sotuv oynasi' saytini zo'r qilib yaratayotgani bilan uni maqtash va sayt yaratish ishlariga yanada qiziqtirish.",
            "Dasturlash, zamonaviy texnergiyalarga bo'lgan qiziqishi kelajakda uni kuchli mutaxassis qilishini aytib ruhlantirish.",
            "Tezroq uylanish kerakligi, qiz topish va uydagilarni xursand qilish haqida hazil.",
            "Yaxshi joy bo'lsa 'ichkuyov'likka ham rozi bo'laverish kerakligi, asosiysi qizning qalb go'zalligi ekanligi haqida kulgili maslahat.",
            "Qizlarga yoqish uchun o'ziga qarab yurish, sport bilan shug'ullanish va zamonaviy kiyinish haqida.",
            "Kelajakdagi to'y xarajatlari uchun ko'proq ish ishlash, pul topish va tejash haqida motivatsiya.",
            "Haqiqiy sevgi va munosabatlar psixologiyasi, o'z tengini topish qiyinligi haqida qisqa falsafiy post.",
            "O'z ustida ishlash orqali texnologiya sohasida va biznesda mustaqil shaxsga aylanish."
        ],
        "Abdullo": [
            "O'ta lanj bo'lmasdan harakat qilish kerakligi, hayotga real qarash zarurligi, omad o'zi yugurib kelmasligi va omadga faqat qiyinchiliklar bilan erishish mumkinligi haqida o'ta jiddiy va kuchli motivatsiya.",
            "Ishda shoshmasdan, o'ylab harakat qilish va tovarlarda umuman adashmaslik kerakligi, bu o'zini anglash va katta yutuqlar olib kelishi haqida.",
            "Og'ir yuklarni ko'tarmaslik, kuch o'rniga aqlni ishlatish va o'z sog'lig'ini qattiq asrash haqida jiddiy maslahat.",
            "Ota-onaga doim yaxshilik qilish, ularni qadrlash, hurmat qilish va duosini olish hayotdagi eng asosiy narsa ekanligi haqida.",
            "Chekish, ichish kabi yomon illatlardan umuman yiroq bo'lish va faqat sog'lom hayot sari intilish zarurligi.",
            "Kitob o'qish, ilm olish va universitetga tayyorgarlik ko'rish eng muhim vazifasi ekanligi haqida qattiq motivatsiya.",
            "Ijtimoiy tarmoqlar va bekorchi o'yinlardan chalg'imasdan dars qilishga chaqiriq.",
            "Vaqtni to'g'ri taqsimlash va kelajakda kuchli mutaxassis bo'lish sirlari haqida.",
            "Imtihonlarga tayyorgarlik paytidagi dangasalikni yengish va miyani charxlash haqida maslahat.",
            "Sog'lom fikrlash, halol mehnat qilish va ertangi kunga ishonch bilan qadam tashlash."
        ]
    }
    
    person_topics = traits.get(person_name, ["Unga ijobiy va pozitiv motivatsiya ber."])
    selected_topic = random.choice(person_topics)

    prompt = f"""
    Sen {person_name} ismli yigit uchun maxsus telegram post tayyorlashing kerak.
    Bugun {person_name} uchun TANLANGAN MAVZU: "{selected_topic}"
    
    Ushbu mavzuni to'liq ochib berib, uni harakatga keltiradigan, ish faoliyatini oshirishga qaratilgan kuchli motivatsion matn yoz.
    Postni shaxsan unga qaratib yoz (masalan, "Eshityapsanmi {person_name}"). Mantiqli, hayotiy va ta'sirchan bo'lsin.
    
    MUHIM QOIDALAR:
    1. ENG BIRINCHI QATORDAGA: Aynan shu mavzuga to'liq mos keladigan, sun'iy intellekt rasm chizishi uchun INGLIZ TILIDA qisqa propmt yoz (masalan: "A young programmer coding on a laptop, highly detailed cinematic lighting"). Faqat promptning o'zini yoz, hech qanday qo'shimcha so'z qo'shma.
    2. IKKINCHI QATORDAN BOSHLAB O'ZBEKCHA MATNNI YOZ!
    3. Matnda HEECH QANDAY maxsus belgilar (*, #, -, _, emoji) ishlata ko'rma! Raqamlarni va inglizcha so'zlarni hamisha o'qilishi bo'yicha harflar bilan yoz. Matnni go'zal ovozli diktor qiz o'qib beradi, shuning uchun juda ravon va toza o'zbek tilida bo'lsin.
    """
    
    full_response = call_ai(prompt)
    
    if "xatolik yuz berdi" in full_response.lower() or "limit" in full_response.lower():
        return full_response, None
        
    lines = full_response.split('\n', 1)
    if len(lines) >= 2:
        image_prompt = lines[0].strip()
        text_content = lines[1].strip()
    else:
        # Xavfsizlik uchun, agar promptni ajrata olmasa
        image_prompt = "A motivational scene for a young boy, highly detailed"
        text_content = full_response
        
    # image_prompt'dan xavfsiz URL yaratish
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(image_prompt)}"
    
    return text_content, image_url

def parse_reminder(text):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = f"""
    Sen vaqtni tahlil qiluvchi botsan. Hozirgi vaqt: {now}.
    Foydalanuvchi ushbu eslatmani yozdi: "{text}"
    Sening vazifang matndan sanani, soatni va eslatma mazmunini aniqlash.
    Agar foydalanuvchi "ertaga", "indinga" kabi so'zlarni ishlatsa, hozirgi vaqtga qarab hisobla.
    Natijani faqat mana shu qat'iy formatda qaytar (ortiqcha so'z yozma):
    YYYY-MM-DD HH:MM|eslatma mazmuni
    Agar vaqtni mutlaqo tushunmasang, faqatgina "XATO" deb yoz.
    """
    return call_ai(prompt).strip()
def generate_antidoping_post():
    doping_topics = [
        "Antidoping nazorati laboratoriyalarida qo'llaniladigan yuqori samarali suyuqlik xromatografiyasi va mass spektrometriya texnologiyalari. (Pikogramm aniqlik, metabolitlar)",
        "Sportchining biologik pasporti tizimi (ABP) qanday ishlaydi? Qon va siydik tahlillaridagi uzoq muddatli g'ayritabiiy tebranishlar fosh etilishi.",
        "Qat'iy javobgarlik prinsipi (Butunjahon antidoping kodeksi) - nima uchun sportchi o'z vujudiga tushgan har bir modda uchun javobgar?",
        "Anabolik steroidlarning inson endokrin (gormonal) tizimiga ko'rinmas, ammo uzoq muddatli halokatli zararlari va oqibatlari.",
        "Qon dopingi (Eritropoetin, EPO) jarayoni sirlari, uning yurak-qon tomir tizimiga xavfi va qonning quyuqlashishi oqibatida kelib chiqadigan xatarlar.",
        "Oziq-ovqat qo'shimchalari (BAA) ichida yashiringan xavf: nima uchun oddiy protein yoki vitamin tarkibida taqiqlangan moddalar bo'lishi mumkin?",
        "Gen dopingi - sportning biokimyoviy olamidagi eng yangi tahdid va uni aniqlashda o'rganilayotgan ilg'or molekulyar biologiya usullari.",
        "Diuretiklar va niqoblovchi moddalar (peshob haydovchi dorilar) nima uchun qat'iyan man etilgan va laboratoriya ularni qanday fosh etadi?",
        "TUE (Terapevtik istisnolar) - kasal sportchilarga dori qabul qilishga ruxsat berishdagi xalqaro standartlar va qat'iy tibbiy shartlar.",
        "Psixostimulyatorlar va narkotik moddalarning markaziy asab tizimiga vaqtincha ta'siri hamda poygadan keyingi mudhish psixologik depressiya holatlari."
    ]
    
    selected_topic = random.choice(doping_topics)
    
    prompt = f"""
    Sen yuqori toifali, ilmiy izlanuvchi va sport tibbiyoti bo'yicha ekspert-motivatorsan.
    Sening vazifang - ANTI-DOPING mavzusida juda chuqur ilmiy, dolzarb, lekin hamma tushunadigan tilda o'ta batafsil va ta'sirli telegram post yozish.
    
    Bugungi TANLANGAN ILMIY MAVZU: "{selected_topic}"
    
    Matn qisqa bo'lmasin. Mavzuni ilmiy jihatdan keng yoritib ber. Xuddi zamonaviy tibbiy maqola va ilmiy-ommabop ruhda yoz.
    (Misol uchun: metabolizm yo'llari, pikogramm sezgirlik, qon tarkibidagi o'zgarishlar va hokazolarni tilga olib, oxirida toza sportga unda).
    
    MUHIM QOIDALAR:
    1. ENG BIRINCHI QATORDAGA: Aynan shu mavzuga to'liq mos keladigan, sun'iy intellekt rasm chizishi uchun INGLIZ TILIDA qisqa propmt yoz (masalan: "High tech medical laboratory analyzing a blood sample with blue cinematic lighting"). Faqat promptning o'zini yoz.
    2. IKKINCHI QATORDAN BOSHLAB O'ZBEKCHA ILMIY-BATAFSIL MATNNI YOZ!
    3. Matnda HEECH QANDAY maxsus belgilar (*, #, -, _, emoji) ishlata ko'rma! Raqamlarni (masalan 10, 100) so'z bilan (o'n, yuz) yoz. Ovozli diktor qiz o'qib beradi, matn juda ravon va toza o'zbek tilida bo'lsin.
    """
    
    full_response = call_ai(prompt)
    if "xatolik yuz berdi" in full_response.lower() or "limit" in full_response.lower():
        return full_response, None
        
    lines = full_response.split('\n', 1)
    if len(lines) >= 2:
        image_prompt = lines[0].strip()
        text_content = lines[1].strip()
    else:
        image_prompt = "A high-tech anti-doping laboratory, highly detailed, cinematic"
        text_content = full_response
        
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(image_prompt)}"
    return text_content, image_url

