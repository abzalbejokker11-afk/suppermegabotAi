"""
Mavzular banki + takrorlanmaslik tizimi.
Har bir mavzu bir marta ishlatiladi, hammasi tugagach navbat yangilanadi.
"""
import json
import os
import random
import threading

import config

_lock = threading.Lock()
_STATE = os.path.join(config.STATE_DIR, "topic_state.json")

# ---------------------------------------------------------------------------
# ANTIDOPING — chuqur ilmiy mavzular (har biri alohida post uchun yetarli)
# ---------------------------------------------------------------------------
ANTIDOPING = [
    "Yuqori samarali suyuqlik xromatografiyasi va tandem mass-spektrometriya (LC-MS/MS): namunadagi metabolitlarni pikogramm darajasida aniqlash mexanizmi, ionlanish va parchalanish spektrlari",
    "Gaz xromatografiyasi va yonish izotop nisbati mass-spektrometriyasi (GC-C-IRMS): tanadagi tabiiy testosteron bilan sintetik testosteronni uglerod o'n uch izotopi nisbati orqali ajratish",
    "Sportchining biologik pasporti (ABP): gematologik modul, adaptiv Bayes statistikasi va uzoq muddatli individual chegaralar",
    "Biologik pasportning steroid moduli: testosteron va epitestosteron nisbati, uning genetik o'zgaruvchanligi va UGT2B17 fermenti polimorfizmi",
    "Qat'iy javobgarlik prinsipi: Butunjahon antidoping kodeksining huquqiy asosi va sportchining o'z organizmiga tushgan har bir modda uchun javobgarligi",
    "Anabolik androgen steroidlarning gipotalamus-gipofiz-gonada o'qiga ta'siri: ichki gormon ishlab chiqarishning bostirilishi va tiklanish muddati",
    "Anabolik steroidlar va yurak: chap qorincha gipertrofiyasi, diastolik disfunksiya va lipid profilining buzilishi",
    "Eritropoetin va qon dopingi: gematokritning ko'tarilishi, qon quyuqlashishi, tromboz va o'lim xavfi",
    "Avtogen va gomologik qon transfuziyasi: eritrotsitlar membranasidagi antigenlar orqali begona qonni aniqlash usullari",
    "Rekombinant EPO ni izoelektrik fokuslash va SAR-PAGE usullari bilan tabiiy EPO dan ajratish",
    "O'sish gormoni (hGH): izoformalar testi va biomarker testi (IGF-1 hamda P-III-NP) ning ilmiy asoslari",
    "Gen dopingi: transgen kiritish, CRISPR asosidagi tahrirlash va qon plazmasidagi ekzogen DNK izlarini polimeraza zanjir reaksiyasi bilan aniqlash",
    "Miostatin ingibitorlari va follistatin: mushak o'sishini sun'iy kuchaytirishning molekulyar yo'llari va noma'lum uzoq muddatli xavflari",
    "Diuretiklar va niqoblovchi moddalar: siydik konsentratsiyasini suyultirish orqali yashirish urinishlari va solishtirma zichlik nazorati",
    "Plazma kengaytiruvchilar (gidroksietilkraxmal, albumin): qon hajmini sun'iy oshirish va uni aniqlash metodikasi",
    "Beta-2 agonistlar: salbutamol va formoterol uchun belgilangan chegaraviy konsentratsiyalar hamda farmakokinetik tadqiqotlar",
    "Beta-blokatorlar: qo'l titrashini kamaytirish orqali otishma va kamondan otish sportida beg'araz ustunlik olish muammosi",
    "Psixostimulyatorlar (amfetamin, modafinil): markaziy asab tizimidagi dofamin transporterining blokadasi va poygadan keyingi charchoq hamda kayfiyat pasayishi",
    "Kokain va narkotik analgetiklar: og'riq signalini bostirish natijasida jarohatni sezmaslik va o'ta og'ir travma xavfi",
    "Meldoniy (mildronat) tarixi: karnitin biosintezini bloklash mexanizmi va uning taqiqlanish sabablari",
    "Selektiv androgen retseptor modulatorlari (SARM): tadqiqot bosqichidagi moddalarning nazoratsiz iste'moli va jigar shikastlanishi",
    "Insulin va o'sish omillari: sport tibbiyotidagi noqonuniy qo'llanishi va gipoglikemik koma xavfi",
    "Gipoksiya induksiyalovchi omil (HIF) stabilizatorlari: eritropoezni dorivor yo'l bilan qo'zg'atish va uni aniqlash",
    "Oziq-ovqat qo'shimchalari (BAA) tarkibidagi deklaratsiya qilinmagan taqiqlangan moddalar: xalqaro tadqiqotlardagi ifloslanish darajasi",
    "Terapevtik istisno ruxsatnomasi (TUE): tibbiy hujjatlar, mustaqil ekspert komissiyasi va qat'iy shartlar tizimi",
    "Namuna olish jarayoni: chaperon nazorati, A va B kolbalari, zanjirli hujjatlashtirish va namuna butunligini muhrlash",
    "Musobaqadan tashqari nazorat va uch oylik joylashuv ma'lumotlari (whereabouts): o'n ikki oy ichida uchta o'tkazib yuborish oqibatlari",
    "Uzoq muddatli metabolitlar: metandienon va stanozololning oyning davomida siydikda saqlanadigan izlari va aniqlash oynasining kengayishi",
    "Namunalarni o'n yil saqlash va yangi texnologiyalar paydo bo'lgach qayta tahlil qilish amaliyoti",
    "Quruq qon tomchisi (DBS) usuli: yangi avlod namuna olish texnologiyasining afzalliklari va analitik cheklovlari",
    "Antidoping laboratoriyalarini akkreditatsiya qilish: xalqaro standartlar, ISO talablari va yillik nazorat testlari",
    "Aniqlashning minimal talab qilinadigan darajasi (MRPL) va noaniqlik chegaralari: analitik natijaning ilmiy ishonchliligi",
    "Yolg'on ijobiy natijalar muammosi: ifloslangan go'sht (klenbuterol), dori-darmon o'zaro ta'siri va ilmiy ekspertiza",
    "Doping va endokrin buzilishlar: qalqonsimon bez, buyrak usti bezi va reproduktiv tizimga uzoq muddatli ta'sir",
    "Ayol sportchilarda anabolik moddalar: virilizatsiya, hayz siklining buzilishi va suyak zichligiga ta'siri",
    "O'smir sportchilar: epifizar o'sish plastinkalarining erta yopilishi va bo'y o'sishining to'xtashi",
    "Doping psixologiyasi: guruh bosimi, natijaga bo'lgan bosim va axloqiy qaror qabul qilish modellari",
    "Sof sport ta'limi: yosh sportchilar uchun profilaktik dasturlar samaradorligini baholovchi tadqiqotlar",
    "Farmakokinetika asoslari: yarim parchalanish davri, klirens va moddaning organizmdan chiqish oynasini hisoblash",
    "Metabolizm yo'llari: sitoxrom P450 fermentlari, faza bir va faza ikki konyugatsiya jarayonlari",
    "Antidoping va sun'iy intellekt: katta ma'lumotlar tahlili orqali shubhali profillarni bashorat qilish",
    "Sport arbitraji sudi (CAS): doping ishlarini ko'rish tartibi, dalillar standarti va nufuzli qarorlar",
    "Ehtiyotkorlik chorasi (provisional suspension) va jazo muddatlarini belgilash mezonlari",
    "Mikrodozalash strategiyasi: kichik dozalar bilan aniqlanishdan qochish urinishlari va biologik pasport ularni qanday fosh etadi",
    "Sun'iy kislorod tashuvchilar (HBOC va perftorkarbonlar): kislorod tashishni oshirish va o'pka hamda buyrak asoratlari",
    "Kortikosteroidlar: tizimli qabul qilinganda taqiq, mahalliy qo'llashda ruxsat va ularning chegarasi",
    "Antidoping nazorati va sportchining shaxsiy hayoti: ma'lumotlar himoyasi hamda huquqiy muvozanat",
    "Ovqatlanish va qonuniy ergogen vositalar: kreatin, kofein, nitrat va beta-alaninning isbotlangan ilmiy samarasi",
    "Balandlik tayyorgarligi va gipoksik chodirlar: tabiiy adaptatsiya bilan dopingning axloqiy chegarasi",
    "Toza sportchi uchun tiklanish fiziologiyasi: uyqu, periodizatsiya va yuklamani boshqarish dopingga muqobil sifatida",
]

PERSON_TRAITS = {
    "Mirjalol": [
        "Shineray T o'ttiz va T ellik yuk mashinalarining texnik ko'rsatkichlarini puxta o'rganish, boshliq so'raganda aniq javob bera olish",
        "Shineray va Labo mashinalarini yuk ko'tarish, tejamkorlik va ishonchlilik bo'yicha taqqoslash",
        "Motor moyini va filtrlarni o'z vaqtida almashtirish, texnik xizmat jadvalini yuritish",
        "Yo'l harakati qoidalari, tezlik rejimi va xavfsiz masofa haqida jiddiy eslatma",
        "Mashinani toza tutish va tashqi ko'rinish ishonch keltirishi haqida",
        "Yoqilg'ini tejab haydash usullari va oylik xarajatni hisoblab borish",
        "Ish kunini rejalashtirish, buyurtmalarni tartibga solish va vaqtni tejash",
        "Mijoz bilan muomala madaniyati va doimiy mijoz orttirish",
        "Kelajakda o'z tijorat transportiga ega bo'lish uchun jamg'arma rejasi",
        "Rulda hushyorlik, charchoqni sezish va dam olish muhimligi",
    ],
    "Rahmatillo": [
        "Sun'iy intellekt bilan har kuni amaliy mashq qilish, kichik loyihalar yaratish",
        "Kichik qadamlar katta natijaga olib borishi, yangi vositalarni sinab ko'rish",
        "Sayt yaratish ko'nikmasini oshirish, interfeys va foydalanuvchi tajribasiga e'tibor",
        "Dasturlashda asoslarni mustahkamlash: algoritmlar, ma'lumotlar tuzilmasi",
        "Portfolio yig'ish va o'z ishini odamlarga ko'rsata olish",
        "Sport va sog'lom rejim ish unumdorligini oshirishi",
        "Moliyaviy savodxonlik: daromadni rejalashtirish va jamg'arish",
        "Vaqtni boshqarish va chalg'ituvchi narsalardan himoyalanish",
        "Muloqot ko'nikmasi va jamoada ishlash",
        "Uzoq muddatli maqsad qo'yish va mustaqil mutaxassisga aylanish",
    ],
    "Abdullo": [
        "Harakatsizlikni yengish, hayotga real qarash va omad mehnat bilan kelishi",
        "Ishda shoshmasdan, o'ylab harakat qilish va tovarlarda xatoga yo'l qo'ymaslik",
        "Og'ir yukni to'g'ri ko'tarish texnikasi va umurtqa sog'lig'ini asrash",
        "Ota-onani qadrlash va ularning duosini olish",
        "Zararli odatlardan yiroq bo'lish va sog'lom turmush tarzi",
        "Kitob o'qish, ilm olish va universitetga tayyorgarlik",
        "Ijtimoiy tarmoq va o'yinlardan chalg'imay darsga jamlanish",
        "Vaqtni to'g'ri taqsimlash va kunlik reja tuzish",
        "Imtihonga tayyorgarlikda dangasalikni yengish usullari",
        "Halol mehnat, sog'lom fikrlash va kelajakka ishonch",
    ],
}


# ---------------------------------------------------------------------------
def _load():
    try:
        with open(_STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    os.makedirs(config.STATE_DIR, exist_ok=True)
    tmp = _STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _STATE)


def pick(bank_name: str, items: list) -> str:
    """Takrorlanmaydigan mavzu tanlash (hammasi tugagach navbat yangilanadi)."""
    with _lock:
        st = _load()
        used = set(st.get(bank_name, []))
        left = [t for t in items if t not in used]
        if not left:
            used, left = set(), list(items)
        choice = random.choice(left)
        used.add(choice)
        st[bank_name] = list(used)
        try:
            _save(st)
        except Exception:
            pass
        return choice


def progress(bank_name: str, items: list):
    st = _load()
    return len(set(st.get(bank_name, []))), len(items)
