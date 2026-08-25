"""
Postlarni tayyorlovchi qatlam.
Barcha funksiyalar (matn, xato_sababi) emas — (matn, rasm_url) qaytaradi
va HECH QACHON istisno tashlamaydi.
"""
import logging
import random
import urllib.parse
import datetime

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
    try:
        r = requests.get(f"https://wttr.in/{config.CITY}?format=%C+%t", timeout=8)
        if r.status_code == 200 and len(r.text) < 120:
            return f"{config.CITY} ob-havosi: {r.text.strip()}"
    except Exception:
        pass
    return ""


def _tech_news():
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
                return "Bugungi ochiq kodli loyihalar: " + "; ".join(
                    f"{i['name']} — {(i.get('description') or 'tavsifsiz')[:120]}" for i in items)
    except Exception as e:
        log.warning("GitHub xatosi: %s", e)
    # zaxira manba
    try:
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        ids = r.json()[:3]
        titles = []
        for i in ids:
            d = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json", timeout=8).json()
            if d and d.get("title"):
                titles.append(d["title"])
        if titles:
            return "Texnologiya yangiliklari: " + "; ".join(titles)
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

    prompt = f"""Sen {person_name} ismli yigit uchun shaxsiy telegram post yozyapsan.
Bugungi mavzu: "{topic}"

Mavzuni to'liq ochib ber, hayotiy misollar keltir, uni harakatga undaydigan kuchli
va samimiy matn yoz. Postni bevosita unga qaratib yoz. Uzunligi uch to'rt abzats.

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
    topic = topics.pick("antidoping", topics.ANTIDOPING)

    prompt = f"""Sen sport tibbiyoti va antidoping sohasidagi ilmiy tadqiqotchisan.
Telegram kanali uchun CHUQUR ILMIY, ishonchli va batafsil post yozyapsan.

BUGUNGI ILMIY MAVZU: "{topic}"

Postning ilmiy tuzilishi (sarlavhalarsiz, oqar matn shaklida, lekin shu ketma-ketlikda):
1. Muammoning qo'yilishi — bu masala nima uchun sport tibbiyotida dolzarb.
2. Fiziologik va biokimyoviy mexanizm — organizmda aynan nima sodir bo'ladi:
   qaysi hujayra, qaysi ferment, qaysi retseptor, qaysi metabolik yo'l.
3. Analitik yoki tibbiy metodika — qanday o'lchanadi, aniqlanadi yoki baholanadi,
   qanday sezgirlik va aniqlik darajasida.
4. Ilmiy dalillar — Butunjahon antidoping agentligi standartlari, xalqaro
   laboratoriya amaliyoti va tadqiqot natijalariga tayangan aniq faktlar.
5. Sog'liq uchun oqibatlar — qisqa va uzoq muddatli asoratlar, aniq organ tizimlari bo'yicha.
6. Amaliy xulosa — sportchi va murabbiy uchun aniq, bajarilishi mumkin bo'lgan tavsiyalar.

TALABLAR:
- Matn KAMIDA olti yetti abzats va {config.MIN_SCIENCE_CHARS} belgidan uzun bo'lsin.
- Quruq motivatsiya YOZMA. Faqat ilmiy mazmun, aniq atamalar va faktlar.
- Har bir atamani keltirganda uni bir jumlada sodda tushuntirib ket.
- O'ylab topilgan raqam, soxta statistika yoki mavjud bo'lmagan tadqiqotga havola keltirma.
  Aniq bilmasang, umumlashtirib yoz.
- Oxirida bir abzats toza sport g'oyasiga bag'ishlansin.

BIRINCHI QATORGA: shu mavzuga mos, sun'iy intellekt rasm chizishi uchun INGLIZ TILIDA
qisqa prompt yoz (masalan: "modern anti-doping laboratory, mass spectrometer,
scientist analyzing blood sample, blue cinematic lighting"). Faqat promptning o'zi.
IKKINCHI QATORDAN BOSHLAB O'ZBEKCHA ILMIY MATN.
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
    text, img_prompt = _split_prompt_and_text(
        full, "modern anti-doping laboratory, mass spectrometer, scientific, cinematic lighting")

    # SIFAT NAZORATI: post juda qisqa bo'lsa — kengaytirish uchun ikkinchi urinish
    if text and len(text) < config.MIN_SCIENCE_CHARS * 0.7:
        log.info("Post qisqa (%d belgi) — kengaytirilmoqda", len(text))
        expand = (f"Quyidagi ilmiy matnni sifatini saqlagan holda ikki barobar kengaytir. "
                  f"Mexanizmni chuqurroq tushuntir, analitik metodikani batafsil yoz, "
                  f"sog'liq uchun oqibatlarni organ tizimlari bo'yicha och. "
                  f"Yangi soxta raqam qo'shma.\n\nMATN:\n{text}\n\n{STYLE_RULES}")
        bigger = generate(expand, allow_offline=False)
        if bigger and len(bigger) > len(text):
            text = bigger

    return clean_for_channel(text), _image_url(img_prompt)


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
