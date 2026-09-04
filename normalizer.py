import re

_ONES = ["", "bir", "ikki", "uch", "to'rt", "besh", "olti", "yetti", "sakkiz", "to'qqiz"]
_TENS = ["", "o'n", "yigirma", "o'ttiz", "qirq", "ellik", "oltmish", "yetmish", "sakson", "to'qson"]
_LARGE = ["", "ming", "million", "milliard"]

def _int_to_words(n: int) -> str:
    if n == 0: return "nol"
    if n < 0: return "minus " + _int_to_words(-n)
    parts = []
    for word in _LARGE:
        chunk = n % 1000
        n //= 1000
        if chunk == 0: continue
        h, t, o = chunk // 100, (chunk % 100) // 10, chunk % 10
        cps = []
        if h: cps.append(_ONES[h] + " yuz")
        if t: cps.append(_TENS[t])
        if o: cps.append(_ONES[o])
        s = " ".join(cps)
        if word: s += " " + word
        parts.append(s)
    return " ".join(reversed(parts))

_ORDINALS = {1:"birinchi",2:"ikkinchi",3:"uchinchi",4:"to'rtinchi",
             5:"beshinchi",6:"oltinchi",7:"yettinchi",8:"sakkizinchi",
             9:"to'qqizinchi",10:"o'ninchi"}

def _to_ordinal(n: int) -> str:
    if n in _ORDINALS: return _ORDINALS[n]
    base = _int_to_words(n)
    vowels = "aeiouoO'AEIUo'"
    if base and base[-1] in vowels: return base + "nchi"
    return base + "inchi"

_MONTHS = {1:"yanvar",2:"fevral",3:"mart",4:"aprel",5:"may",6:"iyun",
           7:"iyul",8:"avgust",9:"sentyabr",10:"oktyabr",11:"noyabr",12:"dekabr"}

def _date_repl(m: re.Match) -> str:
    try:
        d,mo,y = int(m.group(1)),int(m.group(2)),int(m.group(3))
        return f"{_to_ordinal(d)} {_MONTHS.get(mo, str(mo))}, {_int_to_words(y)} yil"
    except: return m.group(0)

def _time_repl(m: re.Match) -> str:
    try:
        h, mi = int(m.group(1)), int(m.group(2))
        if mi == 0: return f"soat {_int_to_words(h)}"
        return f"soat {_int_to_words(h)} {_int_to_words(mi)}"
    except: return m.group(0)

_ABBREVS = [
    (r'\bWADA\b', "vada"), (r'\bTUE\b', "te-yu-e"), (r'\bEPO\b', "e-pi-o"),
    (r'\bAPI\b', "e-pi-ay"), (r'\bTTS\b', "te-te-es"), (r'\bAI\b', "sun'iy intellekt"),
    (r'\bJSST\b', "jahon sog'liqni saqlash tashkiloti"), (r'\bAQSH\b', "aqsh"),
    (r'\bBMT\b', "birlashgan millatlar tashkiloti"), (r'\bva\s+boshq\.', "va boshqalar"),
]

_MEASURES = [
    (r'(\d+(?:[.,]\d+)?)\s*mkg\b', lambda m: _float_words(m.group(1)) + " mikrogram"),
    (r'(\d+(?:[.,]\d+)?)\s*mg\b', lambda m: _float_words(m.group(1)) + " milligramm"),
    (r'(\d+(?:[.,]\d+)?)\s*kg\b', lambda m: _float_words(m.group(1)) + " kilogramm"),
    (r'(\d+(?:[.,]\d+)?)\s*km\b', lambda m: _float_words(m.group(1)) + " kilometr"),
    (r'(\d+(?:[.,]\d+)?)\s*cm\b', lambda m: _float_words(m.group(1)) + " santimetr"),
    (r'(\d+(?:[.,]\d+)?)\s*mm\b', lambda m: _float_words(m.group(1)) + " millimetr"),
    (r'(\d+(?:[.,]\d+)?)\s*g\b', lambda m: _float_words(m.group(1)) + " gramm"),
]

def _float_words(s: str) -> str:
    s = s.replace(",", ".")
    if "." in s:
        parts = s.split(".")
        left = _int_to_words(int(parts[0]))
        right = _int_to_words(int(parts[1])) if parts[1] else ""
        return left + " butun " + right if right else left
    return _int_to_words(int(s))

def normalize_for_tts(text: str) -> str:
    if not text or not text.strip(): return text

    text = re.sub(r'\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b', _date_repl, text)
    text = re.sub(r'soat\s+([01]?\d|2[0-3]):([0-5]\d)\b', _time_repl, text)
    text = re.sub(r'\b([01]\d|2[0-3]):([0-5]\d)\b', _time_repl, text)
    text = re.sub(r'soat\s+soat\b', 'soat', text)
    text = re.sub(r'(\d),(\w)', r'\1, \2', text)
    text = re.sub(r'(\d+(?:[,\.]\d+)?)\s*%', lambda m: _float_words(m.group(1)) + " foiz", text)
    text = re.sub(r'\$\s*(\d+)(?:[.,](\d{2}))?', lambda m: _int_to_words(int(m.group(1))) + " dollar", text)
    text = re.sub(r'([\d][\d\s\xa0]*)\s+so\'m\b', lambda m: _int_to_words(int(m.group(1).replace(" ","").replace("\xa0",""))) + " so'm", text)
    for pattern, repl in _MEASURES:
        text = re.sub(pattern, repl, text)
    text = re.sub(r'\b(\d+)\s*[-–—]\s*(\d+)\b', lambda m: _int_to_words(int(m.group(1))) + "dan " + _int_to_words(int(m.group(2))) + "gacha", text)
    text = re.sub(r'[№#]\s*(\d+)', lambda m: _to_ordinal(int(m.group(1))), text)
    text = re.sub(r'\b(\d{4})-?yil\b', lambda m: _to_ordinal(int(m.group(1))) + " yil", text)
    for pattern, replacement in _ABBREVS:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r'\b(\d+)\b', lambda m: _int_to_words(int(m.group(1))), text)
    text = re.sub(r'  +', ' ', text).strip()
    return text
