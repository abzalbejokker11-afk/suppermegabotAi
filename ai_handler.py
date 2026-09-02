"""
Postlarni tayyorlovchi qatlam.
Barcha funksiyalar (matn, xato_sababi) emas — (matn, rasm_url) qaytaradi
va HECH QACHON istisno tashlamaydi.
"""
import logging
import random
import urllib.parse
import datetime
import time
import json
import os

import requests

import config
import topics
from ai_engine import generate
from textutils import clean_for_channel

log = logging.getLogger("handler")

# ---------------------------------------------------------------- umumiy qoidalar
STYLE_RULES = """
QAT'IY QOIDALAR:
1. Matnda hech qanday maxsus belgi ishlatma: yulduzcha, panjara, tire, pastki chiziq, qavs, emoji — YO'Q.
2. Barcha raqamlarni so'z bilan yoz (o'n, yuz, ming).
3. Inglizcha atamalarni birinchi marta keltirganda o'zbekcha o'qilishini ham yoz.
4. Matnni go'zal ovozli diktor qiz o'qib beradi — jumlalar ravon, tinish belgilari to'g'ri bo'lsin.
5. Ro'yxat qilma, oqar matn (abzatslar) shaklida yoz.
""".strip()


def _split_prompt_and_text(full: str, default_img: str):
    """Birinchi qator — rasm prompti, qolgani — matn."""
    if not full:
        return "", default_img
    lines = full.strip().split("\n", 1)
    first = lines[0].strip()
    # birinchi qator inglizcha va qisqa bo'lsa — rasm prompti
    looks_like_prompt = (
        len(lines) >= 2
        and len(first) < 220
        and sum(c.isascii() for c in first) > len(first) * 0.85
    )
    if looks_like_prompt:
        return lines[1].strip(), first
    return full.strip(), default_img


def _image_url(prompt: str) -> str:
    seed = random.randint(1, 10_000_000)
    q = urllib.parse.quote(prompt[:300])
    return (f"https://image.pollinations.ai/prompt/{q}"
            f"?width=1024&height=1024&nologo=true&seed={seed}")


def fetch_image(url: str, tries: int = 3):
    """Rasmni yuklab olib baytlarini qaytaradi. Bo'lmasa None."""
    for i in range(tries):
        try:
            r = requests.get(url, timeout=70)
            ct = r.headers.get("content-type", "")
            if r.status_code == 200 and ct.startswith("image") and len(r.content) > 8000:
                return r.content
            log.warning("Rasm yuklanmadi (%s, %s bayt)", r.status_code, len(r.content))
        except Exception as e:
            log.warning("Rasm xatosi: %s", e)
        url = url.split("?")[0] + f"?width=1024&height=1024&nologo=true&seed={random.randint(1, 9999999)}"
    return None


# ---------------------------------------------------------------- 1. Savol-javob
def answer_question(question: str) -> str:
    prompt = (f"Foydalanuvchi savoli:\n\"{question}\"\n\n"
              "Unga o'zbek tilida, do'stona va aniq javob yoz. "
              "Javob mazmunli bo'lsin, lekin cho'zib yuborma.\n" + STYLE_RULES)
    out = generate(prompt, offline_fn=lambda: (
        "Hozir sun'iy intellekt xizmati bilan aloqa vaqtincha uzildi. "
        "Savolingizni bir necha daqiqadan so'ng qayta yuboring, men albatta javob beraman."))
    return clean_for_channel(out or "")


# ---------------------------------------------------------------- 2. Tonggi post
def _weather():
    cache_file = os.path.join(config.STATE_DIR, "weather_cache.json")
    os.makedirs(config.STATE_DIR, exist_ok=True)
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                c = json.load(f)
                if time.time() - c.get("time", 0) < 14400:
                    return c.get("data", "")
    except Exception:
        pass

    try:
        r = requests.get(f"https://wttr.in/{config.CITY}?format=%C+%t", timeout=8)
        if r.status_code == 200 and len(r.text) < 120:
            result = f"{config.CITY} ob-havosi: {r.text.strip()}"
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"time": time.time(), "data": result}, f)
            except Exception:
                pass
            return result
    except Exception:
        pass
    return ""


def _tech_news():
    cache_file = os.path.join(config.STATE_DIR, "api_cache.json")
    os.makedirs(config.STATE_DIR, exist_ok=True)
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                c = json.load(f)
                if time.time() - c.get("time", 0) < 14400:
                    return c.get("data", "")
    except Exception:
        pass

    try:
        headers = {"Accept": "application/vnd.github+json"}
        if config.GITHUB_PAT:
            headers["Authorization"] = f"token {config.GITHUB_PAT}"
        r = requests.get(
            "https://api.github.com/search/repositories?q=stars:>5000&sort=updated&order=desc&per_page=3",
            headers=headers, timeout=12)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                result = "Bugungi ochiq kodli loyihalar: " + "; ".join(
                    f"{i['name']} — {(i.get('description') or 'tavsifsiz')[:120]}" for i in items)
                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump({"time": time.time(), "data": result}, f)
                except Exception:
                    pass
                return result
    except Exception as e:
        log.warning("GitHub xatosi: %s", e)

    try:
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        ids = r.json()[:3]
        titles = []
        for i in ids:
            d = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json", timeout=8).json()
            if d and d.get("title"):
                titles.append(d["title"])
        if titles:
            result = "Texnologiya yangiliklari: " + "; ".join(titles)
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"time": time.time(), "data": result}, f)
            except Exception:
                pass
            return result
    except Exception:
        pass
    return "Bugun texnologiyalar olamida odatdagidek qizg'in ish kuni."


def generate_morning_post():
    news = _tech_news()
    weather = _weather()
    prompt = f"""Sen tajribali IT blogersan. Telegram kanaling uchun tonggi post yozyapsan.

Bugungi ma'lumotlar:
{news}
{weather}

Shu ma'lumotlarga tayangan holda dasturchilar uchun qiziqarli, aniq faktlarga asoslangan
va ruhlantiruvchi tonggi post yoz. Uzunligi uch to'rt abzats.
{STYLE_RULES}"""

    def offline():
        return (f"Xayrli tong. {weather or ''} Bugungi kun yangi bilim olish uchun ajoyib imkoniyat. "
                f"{news} Kichik bo'lsa ham bir qadam tashlang, kuningiz barakali o'tsin.")

    out = generate(prompt, offline_fn=offline)
    return clean_for_channel(out or offline())


# ---------------------------------------------------------------- 3. Shaxsiy post
def generate_person_post(person_name: str):
    bank = topics.PERSON_TRAITS.get(person_name, ["Unga ijobiy motivatsiya ber"])
    topic = topics.pick(f"person_{person_name}", bank)
    
    styles = [
        "1. Qattiq va jiddiy akalik maslahati uslubi: O'ta realistik, yoshlikni bekorga o'tkazmaslik haqida dakki va qattiq motivatsiya.",
        "2. Falsafiy va o'ylantiradigan uslub: Hayotiy voqealar, xatolar va ulardan olinadigan darslar orqali chuqur ma'noli yondashuv.",
        "3. Suhbat va savol-javob uslubi: Go'yoki u bilan yuzma-yuz o'tirib choy ichib gaplashayotgandek, savollar berib yozish.",
        "4. Kichik hikoya uslubi: Uning bugungi mavzusi doirasida boshqalar qilgan xatolik haqida qisqa hikoya va undan xulosa.",
        "5. Aniq fakt va harakatlar rejasi uslubi: 'Bugun nima qilishing kerak?' degan savolga 3 ta aniq amaliy va kuchli qadam orqali yozish."
    ]
    style = random.choice(styles)

    prompt = f"""Sen {person_name} ismli yigit uchun shaxsiy telegram post yozyapsan.
Bugungi mavzu: "{topic}"

BUGUNGI YOZISH USLUBING VA STRUKTURANG:
{style}

TALABLAR:
- Har kungi postlaring bir xil zerikarli qolipda bo'lmasin. Shuning uchun bugun aynan yuqoridagi uslubni qo'lla.
- Mavzuni to'liq ochib ber, hayotiy misollar keltir, uni harakatga undaydigan kuchli va samimiy matn yoz.
- Ovozli bot o'qishi uchun maxsus belgilar (*, #, _, emoji) ishlatma!
- Uzunligi uch to'rt abzats.

BIRINCHI QATORGA: shu mavzuga mos, sun'iy intellekt rasm chizishi uchun INGLIZ TILIDA
qisqa prompt yoz (faqat promptning o'zi).
IKKINCHI QATORDAN BOSHLAB O'ZBEKCHA MATN.
{STYLE_RULES}"""

    def offline():
        return ("A determined young man working hard, cinematic lighting\n"
                f"Eshityapsanmi {person_name}. Bugungi mavzu shu: {topic}. "
                "Bir daqiqa to'xtab, shu haqda o'ylab ko'r va bugundan kichik bir qadam tashla. "
                "Har kuni tashlangan kichik qadam bir yildan keyin seni tanib bo'lmas darajada o'zgartiradi.")

    full = generate(prompt, offline_fn=offline)
    text, img_prompt = _split_prompt_and_text(
        full, "A motivational portrait of a young man, cinematic lighting, highly detailed")
    return clean_for_channel(text), _image_url(img_prompt)


# ---------------------------------------------------------------- 4. ANTIDOPING (asosiy)
def generate_antidoping_post():
    idx, total = topics.progress("antidoping", topics.ANTIDOPING)
    topic = topics.pick_sequential("antidoping", topics.ANTIDOPING)
    topic_number = idx + 1
    
    styles = [
        "1. Ilmiy-akademik tahlil: Muammo qo'yilishi, biokimyoviy mexanizm, analitik metodika, amaliy xulosa. Jiddiy va sof ilmiy ohangda yoz.",
        "2. Mifni fosh qilish (Mythbusting): Sportchilar orasida shu mavzudagi keng tarqalgan noto'g'ri tushunchani ol va uni faktlar va chuqur tibbiy dalillar bilan chilparchin qil.",
        "3. Qo'rqinchli haqiqat va tibbiy asoratlar: Asosiy urg'uni tanadagi o'zgarishlar, jigar/yurak kabi organlarning aynan hujayra darajasida qanday halokatga yuz tutishiga qarat.",
        "4. Laboratoriya nigohi (Detektiv): Ushbu moddani tekshiradigan zamonaviy antidoping texnologiyalari qanchalik daxshatli darajada sezgir ekanligi (pikogramm aniqlik, yillar davomida tutilishi) nuqtai nazaridan yoz.",
        "5. O'qituvchi-Ekspert nasihati: Ko'proq maslahat ruhida, lekin faqat quruq gap emas, ilmiy tushunchalarni oddiy, ta'sirchan misollar (metabolizm, DNK) bilan yoshlarga yetkazib yoz."
    ]
    style = random.choice(styles)

    prompt = f"""Sen sport tibbiyoti va antidoping sohasidagi ilmiy tadqiqotchisan.
Telegram kanali uchun CHUQUR ILMIY, ishonchli va batafsil post yozyapsan.

BUGUNGI ILMIY MAVZU: "{topic}"

BUGUNGI YOZISH USLUBING VA STRUKTURANG:
{style}

TALABLAR:
- Har bir post bir-biriga umuman o'xshamasligi, monoton bo'lmasligi shart.
- Matn KAMIDA olti yetti abzats va {config.MIN_SCIENCE_CHARS} belgidan uzun bo'lsin.
- O'ylab topilgan raqam, soxta statistika yoki mavjud bo'lmagan tadqiqotga havola keltirma.
- Ovozli bot o'qishi uchun maxsus belgilar (*, #, _, emoji) ishlatma!

BIRINCHI QATORGA: Ushbu mavzuga eng mos keluvchi bitta yoki ikkita INGLIZCHA kalit so'z yoz (masalan: "kidney", "heart", "laboratory", "athlete"). Haqiqiy rasm qidirish uchun kerak. Faqat kalit so'zning o'zi bo'lsin.
IKKINCHI QATORDAN BOSHLAB O'ZBEKCHA O'TA ILMIY MATN Yozing. Kamida 2500-3000 harfdan iborat, batafsil yoritilgan fojiali faktlar bo'lsin.
QAT'IY TAQIQ: Matn boshida uzr so'rash, "Bugungi mavzu:", salomlashish umuman bo'lmasin. Faqat va faqat chuqur ilmiy daxshatli fakt va xulosalardan iborat maqola bo'lsin.
{STYLE_RULES}"""

    def offline():
        return ("modern anti-doping laboratory with mass spectrometer, blue cinematic lighting\n"
                f"Bugungi ilmiy mavzu: {topic}. "
                "Antidoping nazorati zamonaviy sport tibbiyotining eng aniq va eng murakkab "
                "sohalaridan biridir. Har bir namuna xalqaro standartlar asosida, akkreditatsiyalangan "
                "laboratoriyalarda, ikki bosqichli tekshiruvdan o'tkaziladi. Sportchi o'z organizmiga "
                "tushgan har qanday modda uchun shaxsan javobgar. Shuning uchun har bir dori va har bir "
                "oziq-ovqat qo'shimchasi shifokor bilan maslahatlashib qabul qilinishi shart. "
                "Toza sport — bu nafaqat qoida, bu sportchining sog'lig'i va uzoq yillik karyerasi kafolati.")

    full = generate(prompt, offline_fn=offline)
    text, img_prompt = _split_prompt_and_text(full, "laboratory")

    if text and len(text) < config.MIN_SCIENCE_CHARS * 0.7:
        expand = (f"Quyidagi matnni sifatini saqlagan holda kengaytir. "
                  f"Mexanizm va tibbiy asoratlarni qo'sh.\n\nMATN:\n{text}\n\n{STYLE_RULES}")
        bigger = generate(expand, allow_offline=False)
        if bigger and len(bigger) > len(text):
            text = bigger

    final_text = clean_for_channel(text)
    # Rasim tagiga raqamni qoshiyamiz, Madina oqimaydi chunki caption sifatida ketadi.
    final_text = f"#{topic_number}-Dars: {topic}\n\n{final_text}"
    
    return final_text, _image_url(img_prompt)


# ---------------------------------------------------------------- 5. Eslatma tahlili
def parse_reminder(text: str) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    prompt = f"""Sen vaqtni tahlil qiluvchi tizimsan. Hozirgi vaqt: {now}.
Foydalanuvchi yozdi: "{text}"
Matndan sana, soat va eslatma mazmunini aniqla.
"ertaga", "indinga", "bir soatdan keyin" kabi so'zlarni hozirgi vaqtga nisbatan hisobla.
Natijani FAQAT shu formatda qaytar, boshqa hech narsa yozma:
YYYY-MM-DD HH:MM|eslatma mazmuni
Vaqtni aniqlay olmasang faqat XATO deb yoz."""
    out = generate(prompt, allow_offline=False)
    return (out or "XATO").strip().split("\n")[0]
