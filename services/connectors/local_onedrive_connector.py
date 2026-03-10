from __future__ import annotations

import hashlib
import heapq
import mimetypes
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional


def resolve_onedrive_local_root() -> Optional[Path]:
    candidates = [
        os.getenv("NEXO_ONEDRIVE_LOCAL_DIR", "").strip(),
        os.getenv("OneDrive", "").strip(),
        os.getenv("OneDriveConsumer", "").strip(),
        os.getenv("OneDriveCommercial", "").strip(),
        str(Path.home() / "OneDrive"),
    ]

    seen = set()
    for candidate in candidates:
        if not candidate:
            continue
        norm = str(Path(candidate))
        if norm in seen:
            continue
        seen.add(norm)
        path = Path(candidate)
        if path.exists() and path.is_dir():
            return path
    return None


def list_recent_local_onedrive_files(top: int = 20) -> List[Dict]:
    root = resolve_onedrive_local_root()
    if root is None:
        return []

    max_scan = max(200, int(os.getenv("NEXO_ONEDRIVE_LOCAL_MAX_SCAN", "5000")))
    max_depth = max(1, int(os.getenv("NEXO_ONEDRIVE_LOCAL_MAX_DEPTH", "6")))

    scanned = 0
    candidates: List[tuple[float, Path, int]] = []
    stack: List[tuple[Path, int]] = [(root, 0)]

    while stack and scanned < max_scan:
        current, depth = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if scanned >= max_scan:
                        break

                    name = entry.name
                    if name.startswith("."):
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        if depth < max_depth:
                            stack.append((Path(entry.path), depth + 1))
                        continue

                    if not entry.is_file(follow_symlinks=False):
                        continue

                    stat = entry.stat(follow_symlinks=False)
                    candidates.append((float(stat.st_mtime), Path(entry.path), int(stat.st_size)))
                    scanned += 1
        except Exception:
            continue

    top_n = max(0, int(top))
    best = heapq.nlargest(top_n, candidates, key=lambda item: item[0])

    payload: List[Dict] = []
    for mtime, path, size in best:
        rel = path.relative_to(root).as_posix()
        source_id = hashlib.sha1(str(path).encode("utf-8")).hexdigest()
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        payload.append(
            {
                "id": f"local:{source_id}",
                "name": path.name,
                "size": int(size),
                "mimeType": mime_type,
                "modifiedTime": float(mtime),
                "local_path": str(path),
                "relative_path": rel,
                "source": "local_onedrive",
            }
        )
    return payload


def _hydrate_onedrive_file_windows(path: Path) -> None:
    if os.name != "nt":
        return
    subprocess.run(
        ["attrib", "+p", "-u", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _read_bytes_windows_robust(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        if os.name != "nt":
            raise

    raw_path = str(path)
    if not raw_path.startswith("\\\\?\\"):
        raw_path = f"\\\\?\\{path.resolve(strict=False)}"
    with open(raw_path, "rb") as fh:
        return fh.read()


def _is_onedrive_running_windows() -> bool:
    if os.name != "nt":
        return False
    try:
        proc = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq OneDrive.exe"],
            capture_output=True,
            text=True,
            check=False,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return "OneDrive.exe" in output
    except Exception:
        return False


def _start_onedrive_provider_windows() -> bool:
    if os.name != "nt":
        return False
    candidates = [
        Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "OneDrive" / "OneDrive.exe",
        Path("C:/Program Files/Microsoft OneDrive/OneDrive.exe"),
        Path("C:/Program Files (x86)/Microsoft OneDrive/OneDrive.exe"),
    ]
    for exe in candidates:
        if not exe.exists():
            continue
        try:
            subprocess.Popen([str(exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            continue
    return False


def read_local_onedrive_bytes(path: Path, *, hydrate_retries: int = 2, wait_seconds: float = 1.2) -> bytes:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"Archivo local no encontrado: {file_path}")

    attempts = max(0, int(hydrate_retries)) + 1
    wait_for = max(0.2, float(wait_seconds))
    last_exc: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            return _read_bytes_windows_robust(file_path)
        except OSError as exc:
            last_exc = exc
            is_invalid_argument = getattr(exc, "errno", None) == 22
            if not is_invalid_argument or attempt >= attempts:
                raise
            auto_start = (os.getenv("NEXO_ONEDRIVE_AUTO_START", "1") or "1").strip() not in {"0", "false", "False"}
            if auto_start and not _is_onedrive_running_windows():
                started = _start_onedrive_provider_windows()
                if started:
                    time.sleep(3.0)
            _hydrate_onedrive_file_windows(file_path)
            time.sleep(wait_for)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"No fue posible leer archivo local OneDrive: {file_path}")
