import re
from pathlib import Path

env_path = Path(".env")
content = env_path.read_text(encoding="utf-8")

new_url = "rediss://default:gQAAAAAAAQZoAAIncDIwNGUyYzAwMzFkOTA0NGY0OGY1ZTBkOTI5ZDNhNmVhYXAyNjcxNzY@ace-mayfly-67176.upstash.io:6379"

if "REDIS_URL" in content:
    content = re.sub(r"REDIS_URL=.*", f"REDIS_URL={new_url}", content)
else:
    content += f"\nREDIS_URL={new_url}"

env_path.write_text(content, encoding="utf-8")
print("REDIS_URL actualizado")
