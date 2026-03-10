"""Utility to verify that cloud connectors are configured and working.

Usage: python backend/check_connectors.py

The script performs the following checks and records results under backend/checks/:

  - Google Drive credentials exist and connection succeeds
  - Microsoft OneDrive credentials exist and connection succeeds
  - It dumps a small JSON sample from each service
  - Reports missing files or errors in a human-readable checklist

The output directory is created automatically; it is gitignored.
"""
import os
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

log.info("[check_connectors] starting")
BASE = Path(__file__).parent
# ensure project root is importable
PROJECT_ROOT = BASE.parent
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CHECK_DIR = BASE / "checks"
CHECK_DIR.mkdir(exist_ok=True)

results = []

# helper

def write(name, data):
    with open(CHECK_DIR / f"{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# 1. Google Drive
try:
    from services.connectors.google_connector import list_recent_files
    results.append("Google connector import: OK")
    try:
        files = list_recent_files(5)
        write("google_files", files)
        results.append(f"Google Drive access: OK ({len(files)} items)" if files is not None else "Google Drive access: returned None")
    except Exception as e:
        results.append(f"Google Drive access: ERROR ({e})")
except Exception as e:
    results.append(f"Google connector import failed: {e}")

# 2. Microsoft OneDrive
try:
    from services.connectors.microsoft_connector import MicrosoftConnector
    results.append("Microsoft connector import: OK")
    try:
        mc = MicrosoftConnector()
        root = mc.list_drive_root(top=5)
        recent = mc.list_recent_files(top=5)
        write("onedrive_root", root)
        write("onedrive_recent", recent)
        results.append("OneDrive access: OK")
    except Exception as e:
        results.append(f"OneDrive access: ERROR ({e})")
except Exception as e:
    results.append(f"Microsoft connector import failed: {e}")

# 3. Token/credentials presence
for provider, path in [("google", BASE / "auth" / "credenciales_google.json"),
                       ("microsoft", BASE / "auth" / "credenciales_microsoft.json")]:
    if path.exists():
        results.append(f"{provider.capitalize()} credentials file present: {path}")
    else:
        # look on desktop as fallback
        desktop_path = Path.home() / "Desktop" / path.name
        if desktop_path.exists():
            import shutil
            shutil.copy(desktop_path, path)
            results.append(f"{provider.capitalize()} credentials copied from desktop to {path}")
        else:
            # look in Downloads too
            downloads_path = Path.home() / "Downloads" / path.name
            if downloads_path.exists():
                import shutil
                shutil.copy(downloads_path, path)
                results.append(f"{provider.capitalize()} credentials copied from Downloads to {path}")
            else:
                results.append(f"{provider.capitalize()} credentials file missing: {path} (also not on Desktop/Downloads)")

# 4. report
log.info("Checklist status:\n" + "\n".join(f"- {r}" for r in results))
log.info(f"Details dumped to {CHECK_DIR}")
