"""
Matnni tozalash: maxsus belgilar, emoji, markdown olib tashlanadi;
raqamlar o'zbekcha so'zga aylantiriladi (diktor ovozi uchun).
"""
import re

_ONES = ["nol", "bir", "ikki", "uch", "to'rt", "besh", "olti", "yetti", "sakkiz", "to'qqiz"]
_TENS = ["", "o'n", "yigirma", "o'ttiz", "qirq", "ellik", "oltmish", "yetmish", "sakson", "to'qson"]


def num_to_uz(n: int) -> str:
    if n < 0:
        return "minus " + num_to_uz(-n)
    if n < 10:
        return _ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return _TENS[t] + ("" if o == 0 else " " + _ONES[o])
    if n < 1000:
        h, r = divmod(n, 100)
        s = (_ONES[h] + " yuz") if h > 1 else "yuz"
        return s + ("" if r == 0 else " " + num_to_uz(r))
    if n < 1_000_000:
        th, r = divmod(n, 1000)
        s = (num_to_uz(th) + " ming") if th > 1 else "ming"
        return s + ("" if r == 0 else " " + num_to_uz(r))
    if n < 1_000_000_000:
        m, r = divmod(n, 1_000_000)
        return num_to_uz(m) + " million" + ("" if r == 0 else " " + num_to_uz(r))
    b, r = divmod(n, 1_000_000_000)
    return num_to_uz(b) + " milliard" + ("" if r == 0 else " " + num_to_uz(r))


_EMOJI = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF" "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF" "\U0000FE00-\U0000FE0F" "]+",
    flags=re.UNICODE,
)

_REPLACE = {
    "%": " foiz ", "&": " va ", "№": " raqam ", "°": " daraja ",
    "+": " plyus ", "=": " teng ", "@": " ", "€": " yevro ", "$": " dollar ",
}


def clean_for_voice(text: str) -> str:
    """Diktor o'qishi uchun to'liq toza matn."""
    if not text:
        return ""
    t = _EMOJI.sub("", text)
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"[*#_`~>\[\]\{\}\\|^]", " ", t)
    t = re.sub(r"(?m)^\s*[-•–—]\s*", "", t)          # ro'yxat belgilarini olib tashlash
    t = re.sub(r"(?<=\w)[-–—](?=\w)", " ", t)
    t = re.sub(r"\s[-–—]\s", ", ", t)
    for k, v in _REPLACE.items():
        t = t.replace(k, v)
    # kasr sonlar: 2.5 -> ikki butun besh
    t = re.sub(r"\b(\d+)[.,](\d+)\b",
               lambda m: f"{num_to_uz(int(m.group(1)))} butun {num_to_uz(int(m.group(2)))}", t)
    # oddiy sonlar
    t = re.sub(r"\d+", lambda m: num_to_uz(int(m.group(0))) if len(m.group(0)) <= 12 else m.group(0), t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"\s+([,.!?;:])", r"\1", t)
    return t.strip()


def clean_for_channel(text: str) -> str:
    """Kanal matni: markdown va emoji yo'q, lekin raqamlar so'z bilan (bir xil uslub)."""
    return clean_for_voice(text)


def chunks(text: str, limit: int = 4000):
    """Telegram limitiga mos bo'laklarga bo'lish (abzatslarni buzmasdan)."""
    text = text.strip()
    if len(text) <= limit:
        return [text]
    out, cur = [], ""
    for para in text.split("\n"):
        if len(cur) + len(para) + 1 > limit:
            if cur.strip():
                out.append(cur.strip())
            while len(para) > limit:
                cut = para.rfind(" ", 0, limit)
                cut = cut if cut > 0 else limit
                out.append(para[:cut].strip())
                para = para[cut:]
            cur = para + "\n"
        else:
            cur += para + "\n"
    if cur.strip():
        out.append(cur.strip())
    return out
