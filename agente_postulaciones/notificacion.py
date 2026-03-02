from __future__ import annotations

import requests


def notify_ntfy(server: str, topic: str, title: str, message: str, priority: str = "default") -> bool:
    if not topic:
        return False

    url = f"{server.rstrip('/')}/{topic}"
    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": "robot_face,briefcase",
    }
    try:
        resp = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=12)
        return resp.status_code < 400
    except Exception:
        return False
