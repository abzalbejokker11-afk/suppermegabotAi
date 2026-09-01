"""
Ko'p qatlamli, tinim bilmaydigan AI dvigatel.

Qatlamlar:
  1) Gemini  (bir nechta kalit x bir nechta model)
  2) OpenRouter (bepul modellar)
  3) Groq
  4) Cerebras
  5) OpenAI
  6) Oflayn shablon generatori  <- API umuman ishlamasa ham kanal jim qolmaydi

Har bir (provayder, model, kalit) uchun:
  - eksponensial backoff + jitter bilan qayta urinish
  - 429 / 503 da avtomatik keyingi kalit yoki modelga o'tish
  - "circuit breaker": ketma-ket yiqilgan model vaqtincha chetlab o'tiladi
"""
import json
import logging
import os
import random
import threading
import time

import requests

import config

log = logging.getLogger("ai")

_lock = threading.Lock()
_cooldown = {}      # "provider:model" -> qachongacha chetlab o'tiladi (unix time)
_fail_count = {}
_key_cursor = {}    # provider -> aylanuvchi kalit indeksi
_stats = {"calls": 0, "ok": 0, "fail": 0, "offline": 0, "by_model": {}}


# ---------------------------------------------------------------- utilitalar
def _now():
    return time.time()


def _is_dead(tag):
    with _lock:
        return _cooldown.get(tag, 0) > _now()


def _punish(tag, seconds=None):
    with _lock:
        n = _fail_count.get(tag, 0) + 1
        _fail_count[tag] = n
        if seconds is None:
            seconds = min(600, 20 * (2 ** min(n, 5)))  # 40s -> 10 daqiqa
        _cooldown[tag] = _now() + seconds
    log.warning("Model chetlab o'tilmoqda: %s (%.0f soniya)", tag, seconds)


def _reward(tag):
    with _lock:
        _fail_count[tag] = 0
        _cooldown.pop(tag, None)
        _stats["by_model"][tag] = _stats["by_model"].get(tag, 0) + 1


def _next_key(provider, keys):
    if not keys:
        return None
    with _lock:
        i = _key_cursor.get(provider, 0)
        _key_cursor[provider] = (i + 1) % len(keys)
    return keys[i % len(keys)]


def stats():
    with _lock:
        return json.loads(json.dumps(_stats))


def _retryable(msg):
    m = (msg or "").lower()
    return any(x in m for x in (
        "429", "resource_exhausted", "quota", "rate limit", "rate_limit",
        "503", "unavailable", "overloaded", "500", "502", "504",
        "timeout", "timed out", "connection", "temporarily"
    ))


# ---------------------------------------------------------------- Gemini
_gemini_clients = {}


def _gemini_client(key):
    if key not in _gemini_clients:
        from google import genai
        _gemini_clients[key] = genai.Client(api_key=key)
    return _gemini_clients[key]


def _call_gemini(model, prompt, key, timeout=90):
    client = _gemini_client(key)
    resp = client.models.generate_content(model=model, contents=prompt)
    text = getattr(resp, "text", None)
    if not text:
        raise RuntimeError("Gemini bo'sh javob qaytardi")
    return text


# ---------------------------------------------------------------- OpenAI-mos API
def _call_openai_compatible(base_url, model, prompt, key, timeout=120, extra_headers=None):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 4000,
    }
    r = requests.post(f"{base_url}/chat/completions", headers=headers,
                      json=payload, timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:250]}")
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    if not text or not text.strip():
        raise RuntimeError("Bo'sh javob")
    return text


# ---------------------------------------------------------------- marshrut
def _routes():
    """(provayder, model, kalitlar_ro'yxati, chaqiruvchi) tartibida."""
    out = []
    for m in config.GEMINI_MODELS:
        out.append(("gemini", m, config.GEMINI_KEYS,
                    lambda mm, p, k: _call_gemini(mm, p, k)))
    for m in config.GROQ_MODELS:
        out.append(("groq", m, config.GROQ_KEYS,
                    lambda mm, p, k: _call_openai_compatible(
                        "https://api.groq.com/openai/v1", mm, p, k)))
    for m in config.OPENROUTER_MODELS:
        out.append(("openrouter", m, config.OPENROUTER_KEYS,
                    lambda mm, p, k: _call_openai_compatible(
                        "https://openrouter.ai/api/v1", mm, p, k,
                        extra_headers={"HTTP-Referer": "https://t.me/",
                                       "X-Title": "SuperAgentBot"})))
    for m in config.CEREBRAS_MODELS:
        out.append(("cerebras", m, config.CEREBRAS_KEYS,
                    lambda mm, p, k: _call_openai_compatible(
                        "https://api.cerebras.ai/v1", mm, p, k)))
    for m in config.OPENAI_MODELS:
        out.append(("openai", m, config.OPENAI_KEYS,
                    lambda mm, p, k: _call_openai_compatible(
                        "https://api.openai.com/v1", mm, p, k)))
    return [r for r in out if r[2]]  # kaliti borlarigina


def generate(prompt, attempts_per_route=2, allow_offline=True, offline_fn=None):
    """
    Matn generatsiya qiladi. Hech qachon istisno (exception) tashlamaydi.
    Muvaffaqiyatsiz bo'lsa offline_fn() natijasini yoki None qaytaradi.
    """
    with _lock:
        _stats["calls"] += 1

    routes = _routes()
    if not routes:
        log.error("Hech qanday AI kaliti yo'q!")
        return offline_fn() if (allow_offline and offline_fn) else None

    last_error = "noma'lum xato"

    # 1-bosqich: faqat "sog'lom" marshrutlar. 2-bosqich: hammasi (umidsizlik rejimi)
    for phase in (0, 1):
        for provider, model, keys, fn in routes:
            tag = f"{provider}:{model}"
            if phase == 0 and _is_dead(tag):
                continue
            for attempt in range(attempts_per_route):
                key = _next_key(provider, keys)
                if not key:
                    break
                try:
                    text = fn(model, prompt, key)
                    if text and text.strip():
                        _reward(tag)
                        with _lock:
                            _stats["ok"] += 1
                        log.info("AI OK -> %s", tag)
                        import re
                        clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
                        return clean.strip()
                    raise RuntimeError("bo'sh javob")
                except Exception as e:
                    last_error = str(e)
                    log.warning("AI xato [%s] urinish %d: %s", tag, attempt + 1, last_error[:180])
                    if _retryable(last_error):
                        time.sleep(min(12, (2 ** attempt) + random.random() * 1.5))
                        continue
                    break  # qayta urinib bo'lmaydigan xato -> keyingi model
            _punish(tag)

    with _lock:
        _stats["fail"] += 1
    log.error("Barcha AI marshrutlari yiqildi. Oxirgi xato: %s", last_error[:300])

    if allow_offline and offline_fn:
        with _lock:
            _stats["offline"] += 1
        return offline_fn()
    return None


def health():
    """Qaysi modellar hozir tirik ekanini qaytaradi."""
    rows = []
    for provider, model, keys, _ in _routes():
        tag = f"{provider}:{model}"
        left = max(0, int(_cooldown.get(tag, 0) - _now()))
        rows.append((tag, len(keys), "tirik" if left == 0 else f"tanaffus {left}s"))
    return rows
