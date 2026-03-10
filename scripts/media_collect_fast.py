#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def run_cmd(cmd: List[str], timeout: int = 0) -> Dict:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=None if timeout <= 0 else timeout,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "cmd": cmd,
        }
    except Exception as exc:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(exc), "cmd": cmd}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def split_urls(value: str) -> List[str]:
    if not value:
        return []
    raw = [x.strip() for x in value.replace("\n", ",").split(",")]
    return [x for x in raw if x]


def ytdlp_download(url: str, out_dir: Path, archive_file: Path, concurrency: int) -> Dict:
    ytdlp_cmd = ["yt-dlp"] if shutil.which("yt-dlp") else [sys.executable, "-m", "yt_dlp"]
    cmd = [
        *ytdlp_cmd,
        "--no-progress",
        "--concurrent-fragments",
        str(max(1, concurrency)),
        "--download-archive",
        str(archive_file),
        "-o",
        str(out_dir / "%(uploader)s" / "%(title).180B [%(id)s].%(ext)s"),
        "--merge-output-format",
        "mp4",
        "--no-playlist",
        url,
    ]

    aria2 = shutil.which("aria2c")
    if aria2:
        cmd[1:1] = [
            "--downloader",
            "aria2c",
            "--downloader-args",
            "aria2c:-x 8 -s 8 -k 1M",
        ]

    return run_cmd(cmd)


def gallery_dl_x(url: str, out_dir: Path) -> Dict:
    gallery_cmd = ["gallery-dl"] if shutil.which("gallery-dl") else [sys.executable, "-m", "gallery_dl"]
    cmd = [
        *gallery_cmd,
        "--dest",
        str(out_dir),
        "--write-metadata",
        "--download-archive",
        str(out_dir / "gallery-dl-archive.sqlite3"),
        url,
    ]
    return run_cmd(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recolección rápida YouTube/X para contenido autorizado (sin bypass de DRM ni restricciones)."
    )
    parser.add_argument("--youtube-urls", default="", help="URLs YouTube separadas por coma")
    parser.add_argument("--x-urls", default="", help="URLs de posts/perfiles de X separadas por coma")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrencia de workers")
    parser.add_argument("--output", default="documentos/media_intake", help="Directorio salida")
    args = parser.parse_args()

    yt_urls = split_urls(args.youtube_urls)
    x_urls = split_urls(args.x_urls)

    if not yt_urls and not x_urls:
        log.info("No hay URLs para recolectar. Usa --youtube-urls y/o --x-urls")
        return 1

    root = Path(args.output)
    yt_dir = root / "youtube"
    x_dir = root / "x"
    ensure_dir(yt_dir)
    ensure_dir(x_dir)

    archive_file = yt_dir / "yt-dlp-archive.txt"

    jobs = []
    for url in yt_urls:
        jobs.append(("youtube", url))
    for url in x_urls:
        jobs.append(("x", url))

    results: List[Dict] = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
        fut_map = {}
        for source, url in jobs:
            if source == "youtube":
                fut = ex.submit(ytdlp_download, url, yt_dir, archive_file, args.concurrency)
            else:
                fut = ex.submit(gallery_dl_x, url, x_dir)
            fut_map[fut] = (source, url)

        for fut in as_completed(fut_map):
            source, url = fut_map[fut]
            outcome = fut.result()
            results.append({"source": source, "url": url, "result": outcome})

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "jobs": len(results),
        "ok": sum(1 for r in results if r["result"].get("ok")),
        "failed": sum(1 for r in results if not r["result"].get("ok")),
        "output_root": str(root),
        "results": results,
    }

    report_dir = Path("reports/security")
    ensure_dir(report_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"media_collect_fast_{ts}.json"
    report_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"✅ Recolección finalizada. Reporte: {report_file}")
    log.info(json.dumps({"ok": summary["ok"], "failed": summary["failed"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
