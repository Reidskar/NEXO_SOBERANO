from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def repair_catalog_script(repo_root: Path) -> dict:
    expected = repo_root / "scripts" / "catalog_antigravity_skills.py"
    backups = [
        repo_root / "camilo_el_bkn" / "scripts" / "catalog_antigravity_skills.py",
        repo_root / "NEXO_SOBERANO" / "scripts" / "catalog_antigravity_skills.py",
    ]

    actions: list[str] = []

    if not expected.exists():
        for candidate in backups:
            if candidate.exists():
                expected.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, expected)
                actions.append(f"restored_from:{candidate.as_posix()}")
                break

    if not expected.exists():
        return {
            "ok": False,
            "target": expected.as_posix(),
            "actions": actions,
            "error": "catalog_antigravity_skills.py missing and no backup found",
        }

    text = expected.read_text(encoding="utf-8", errors="replace")
    old = "log.info(json.dumps({\"ok\": True, \"output\": out.as_posix()}, ensure_ascii=False))"
    new = "log.info(json.dumps({\"ok\": True, \"output\": out.as_posix()}, ensure_ascii=False))"

    if old in text:
        expected.write_text(text.replace(old, new), encoding="utf-8")
        actions.append("patched_undefined_log")

    return {
        "ok": True,
        "target": expected.as_posix(),
        "actions": actions or ["already_healthy"],
    }


def ensure_runtime_dirs(repo_root: Path) -> dict:
    logs = repo_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return {"ok": True, "logs": logs.as_posix()}


def run_doctor() -> dict:
    repo_root = root_dir()
    catalog = repair_catalog_script(repo_root)
    runtime = ensure_runtime_dirs(repo_root)
    return {
        "ok": bool(catalog.get("ok")) and bool(runtime.get("ok")),
        "repo_root": repo_root.as_posix(),
        "catalog": catalog,
        "runtime": runtime,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-repair for Antigravity local runner")
    parser.add_argument("--quiet", action="store_true", help="Only emit JSON summary")
    args = parser.parse_args()

    result = run_doctor()
    log.info(json.dumps(result, ensure_ascii=False))

    if args.quiet:
        return 0 if result.get("ok") else 1
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
