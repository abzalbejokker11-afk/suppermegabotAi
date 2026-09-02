import json
import logging
import random
import threading

import kv_storage

log = logging.getLogger("topics")
_lock = threading.Lock()

ANTIDOPING = [
    "Kunlik apteka dorilarining ko'rinmas xavfi va tarkib fojiasi",
    "Murabbiyning qonuniy javobgarligi va umrbod badarg'a",
    "Diskvalifikatsiya: Sport karyerasining o'limi va ijtimoiy izolyatsiya",
    "WADA laboratoriyalarining yangilanishi va yangi texnologiyalar",
    "Ifloslangan oziq-ovqat qo'shimchalari (BAA) va ko'r-ko'rona ishonch tuzog'i",
    "Biologik pasport (ABP) hukmi — Qon aldamaydi",
    "Eritropoetin (EPO) halokati: Qon quyuqlashishi va yurak xuruji",
    "Diuretiklar (Furosemid) va vazn tashlashdagi og'ir jinoyat",
    "Testosteron va gormonal qulash (Endokrin inqiroz)",
    "Musobaqadan tashqari nazorat (ADAMS tizimi) va qochishning bahosi",
    "Meldoniy (Mildronat) qurbonlari: O'zbekistonlik sportchilarning og'ir xatosi",
    "Ifloslangan go'sht va BAA tuzog'i (Klenbuterol) – Real voqealar",
    "Anabolik steroidlar qurbonlari (Metasteron)"
]

def _load():
    try:
        data = kv_storage.kv_get("topics_state", {})
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

def _save(data):
    try:
        kv_storage.kv_set("topics_state", data)
    except Exception:
        pass

def pick(bank_name: str, items: list) -> str:
    with _lock:
        st = _load()
        used = set(st.get(bank_name, []))
        left = [t for t in items if t not in used]
        if not left:
            used, left = set(), list(items)
        choice = random.choice(left)
        used.add(choice)
        st[bank_name] = list(used)
        _save(st)
        return choice

def pick_sequential(bank_name: str, items: list) -> str:
    with _lock:
        st = _load()
        idx = st.get(f"{bank_name}_idx", 0)
        if idx >= len(items):
            idx = 0
        choice = items[idx]
        st[f"{bank_name}_idx"] = idx + 1
        _save(st)
        return choice

def progress(bank_name: str, items: list):
    st = _load()
    idx = st.get(f"{bank_name}_idx", 0)
    return idx, len(items)
