from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_EXTENSIONS = {".py", ".md", ".json", ".txt", ".html", ".js", ".ts", ".css"}
DEFAULT_IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
    "logs",
}
DEFAULT_IGNORED_FILES = {
    ".env",
    "credenciales_google.json",
    "token_google.json",
    "token_google_manage.json",
    "token_youtube_upload.json",
    "boveda.db",
}


@dataclass
class ExtractionResult:
    ok: bool
    output_file: str
    files_scanned: int
    files_included: int
    bytes_written: int
    started_at: str
    finished_at: str


def _iter_source_files(
    root: Path,
    extensions: set[str],
    ignored_dirs: set[str],
    ignored_files: set[str],
) -> Iterable[Path]:
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]

        for filename in filenames:
            if filename in ignored_files:
                continue
            suffix = Path(filename).suffix.lower()
            if suffix in extensions:
                yield Path(current_root) / filename


def extract_project_context(
    *,
    root_dir: str,
    output_file: str,
    extensions: set[str] | None = None,
    ignored_dirs: set[str] | None = None,
    ignored_files: set[str] | None = None,
) -> ExtractionResult:
    root = Path(root_dir).resolve()
    out_path = Path(output_file).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    extensions = {ext.lower() for ext in (extensions or DEFAULT_EXTENSIONS)}
    ignored_dirs = set(ignored_dirs or DEFAULT_IGNORED_DIRS)
    ignored_files = set(ignored_files or DEFAULT_IGNORED_FILES)

    started = datetime.now(timezone.utc).isoformat()
    files_scanned = 0
    files_included = 0
    bytes_written = 0

    with out_path.open("w", encoding="utf-8") as output:
        output.write("# CONTEXTO DE CÓDIGO - NEXO SOBERANO\n")
        output.write("Generado para revisión por otras IA / code review externo.\n\n")
        output.write(f"Raíz: {root}\n")
        output.write(f"Generado: {started}\n\n")

        for file_path in _iter_source_files(root, extensions, ignored_dirs, ignored_files):
            files_scanned += 1
            relative = file_path.relative_to(root)
            output.write("=" * 80 + "\n")
            output.write(f"ARCHIVO: {relative}\n")
            output.write("=" * 80 + "\n")

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                content = f"[ERROR LEYENDO ARCHIVO: {exc}]\n"

            if content.strip():
                files_included += 1
            encoded = (content + "\n\n").encode("utf-8", errors="ignore")
            bytes_written += len(encoded)
            output.write(content + "\n\n")

    finished = datetime.now(timezone.utc).isoformat()

    return ExtractionResult(
        ok=True,
        output_file=str(out_path),
        files_scanned=files_scanned,
        files_included=files_included,
        bytes_written=bytes_written,
        started_at=started,
        finished_at=finished,
    )


def save_result_json(result: ExtractionResult, json_path: str) -> None:
    payload = {
        "ok": result.ok,
        "output_file": result.output_file,
        "files_scanned": result.files_scanned,
        "files_included": result.files_included,
        "bytes_written": result.bytes_written,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }
    target = Path(json_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_output_file(root_dir: str) -> str:
    root = Path(root_dir)
    return str(root / "logs" / "ai_context" / "contexto_nexo_soberano.txt")


def _default_result_file(root_dir: str) -> str:
    root = Path(root_dir)
    return str(root / "logs" / "extractor_report.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extractor de contexto de código para NEXO SOBERANO")
    parser.add_argument("--root", default=".", help="Carpeta raíz del proyecto")
    parser.add_argument("--output", default=None, help="Archivo de salida TXT")
    parser.add_argument("--result-json", default=None, help="Archivo JSON de resultado")
    args = parser.parse_args()

    output = args.output or _default_output_file(args.root)
    result_json = args.result_json or _default_result_file(args.root)

    result = extract_project_context(
        root_dir=args.root,
        output_file=output,
    )
    save_result_json(result, result_json)

    print(json.dumps({
        "ok": result.ok,
        "output_file": result.output_file,
        "files_scanned": result.files_scanned,
        "files_included": result.files_included,
        "bytes_written": result.bytes_written,
    }, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
