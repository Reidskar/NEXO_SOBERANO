import time
import requests

URL = "http://elanarcocapital.com"
CHECK_INTERVAL = 60  # segundos

while True:
    try:
        r = requests.get(URL, timeout=10)
        if r.status_code == 200:
            log.info(f"[OK] {URL} responde 200 ✔️")
        else:
            log.info(f"[WARN] {URL} responde {r.status_code}")
    except Exception as e:
        log.info(f"[ERROR] {URL} no responde: {e}")
    time.sleep(CHECK_INTERVAL)
