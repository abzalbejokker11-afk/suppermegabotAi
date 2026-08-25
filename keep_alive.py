"""
Doimiy ishlash uchun HTTP server + o'z-o'zini ping qilish (Replit/Render uchun).
"""
import logging
import threading
import time

import requests
from flask import Flask, jsonify

import config

log = logging.getLogger("keepalive")
app = Flask(__name__)

STATUS = {"started": time.time(), "last_post": None, "posts": 0, "errors": 0}


@app.route("/")
def home():
    return "Bot ishlamoqda!"


@app.route("/health")
def health():
    import ai_engine
    return jsonify({
        "ok": True,
        "uptime_seconds": int(time.time() - STATUS["started"]),
        "posts": STATUS["posts"],
        "errors": STATUS["errors"],
        "last_post": STATUS["last_post"],
        "ai": ai_engine.stats(),
        "models": [{"model": m, "keys": k, "holat": s} for m, k, s in ai_engine.health()],
    })


def _run():
    from werkzeug.serving import make_server
    try:
        srv = make_server("0.0.0.0", config.KEEP_ALIVE_PORT, app, threaded=True)
        srv.serve_forever()
    except Exception as e:
        log.error("Keep-alive server xatosi: %s", e)


def _self_ping():
    if not config.SELF_URL:
        return
    while True:
        time.sleep(240)
        try:
            requests.get(config.SELF_URL, timeout=15)
        except Exception:
            pass


def keep_alive():
    threading.Thread(target=_run, daemon=True).start()
    threading.Thread(target=_self_ping, daemon=True).start()
    log.info("Keep-alive ishga tushdi (port %s)", config.KEEP_ALIVE_PORT)
