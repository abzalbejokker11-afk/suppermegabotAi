import requests
import json
import logging
import base64

log = logging.getLogger('kv_storage')

# Base64 encoded credentials for SUPERAGENT_BOT_DB
_A = base64.b64decode('OGViMmNlNGQ3MGJiZGVkMjFjYTM0YTQxOTc3MjA4ZGY=').decode()
_N = base64.b64decode('ZTFlODY3NzVkYjk4NDcxNTg3NWY3MWY0YTc3MTA4M2E=').decode()
_T = base64.b64decode('Y2ZhdF8yYWNWRzdOT0g3dzVmWm1mZEhyeXJXdEpzTGphMFJOcjVlSVhtcnFBZTA4MWZjZWI=').decode()

BASE_URL = f'https://api.cloudflare.com/client/v4/accounts/{_A}/storage/kv/namespaces/{_N}/values'
HEADERS = {'Authorization': f'Bearer {_T}'}

def kv_get(key: str, default=None):
    try:
        r = requests.get(f'{BASE_URL}/{key}', headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            return default
    except Exception as e:
        log.warning(f'KV Get error: {e}')
    return default

def kv_set(key: str, value):
    try:
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        r = requests.put(f'{BASE_URL}/{key}', headers=HEADERS, data=value.encode('utf-8'), timeout=10)
        return r.status_code == 200
    except Exception as e:
        log.warning(f'KV Set error: {e}')
        return False
