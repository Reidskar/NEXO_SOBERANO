from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
KEY_VALUE_RE = re.compile(r"^([A-Za-z0-9_\-]+)\s*:\s*(.+)$")
BUNDLE_HINTS = {
    "engineering": ["engineering", "architect", "debug", "clean-architecture", "devops", "backend"],
    "marketing": ["marketing", "seo", "growth", "prospecting", "lead", "outreach", "copywriting"],
    "research": ["research", "rag", "notebooklm", "analysis", "geopolit", "econom", "report"],
    "operations": ["automation", "workflow", "n8n", "make", "sync", "connector", "integration"],
    "content": ["youtube", "script", "guion", "content", "editorial", "storytelling"],
}


@dataclass
class SkillRecord:
    id: str
    name: str
    description: str
    bundle: str
    source_file: str
    tags: list[str]
    command: str
    confidence: float


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def sanitize(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    block = match.group(1)
    out: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        kv = KEY_VALUE_RE.match(line)
        if kv:
            out[kv.group(1).strip().lower()] = kv.group(2).strip().strip('"').strip("'")
    return out


def infer_bundle(text: str, source_path: Path, tags: Iterable[str]) -> tuple[str, float]:
    haystack = " ".join([source_path.as_posix().lower(), text.lower(), " ".join(t.lower() for t in tags)])
    best_bundle = "general"
    best_score = 0

    for bundle, hints in BUNDLE_HINTS.items():
        score = sum(1 for hint in hints if hint in haystack)
        if score > best_score:
            best_bundle = bundle
            best_score = score

    confidence = min(1.0, 0.35 + (best_score * 0.15)) if best_score else 0.25
    return best_bundle, round(confidence, 2)


def extract_name_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines()[:40]:
        clean = line.strip()
        if clean.startswith("#"):
            return sanitize(clean.lstrip("#").strip())
    return sanitize(fallback.replace("_", "-").replace(".md", ""))


def extract_description(text: str) -> str:
    lines = [sanitize(line) for line in text.splitlines() if sanitize(line)]
    for line in lines:
        if line.startswith("#"):
            continue
        if len(line) >= 20:
            return line[:280]
    return "Skill description not provided"


def extract_command(text: str, source_path: Path) -> str:
    command_patterns = [
        re.compile(r"`(npx\s+[^`]+)`", re.IGNORECASE),
        re.compile(r"`(python\s+[^`]+)`", re.IGNORECASE),
        re.compile(r"`(@[a-z0-9_\-]+)`", re.IGNORECASE),
    ]
    for pattern in command_patterns:
        match = pattern.search(text)
        if match:
            return sanitize(match.group(1))
    stem = source_path.stem
    return f"@{stem}"


def extract_tags(frontmatter: dict[str, str], source_path: Path, text: str) -> list[str]:
    tags: list[str] = []
    for key in ("tags", "tag", "categories", "category"):
        raw = frontmatter.get(key, "")
        if raw:
            parts = re.split(r"[,|]", raw)
            tags.extend(sanitize(p).lower() for p in parts if sanitize(p))

    path_parts = [part.lower() for part in source_path.parts]
    tags.extend([p for p in path_parts if p not in {"skills", "skill", "prompts", "docs"}][-3:])

    for term in ["rag", "notebooklm", "seo", "debug", "clean architecture", "youtube", "apify", "vibe"]:
        if term in text.lower():
            tags.append(term.replace(" ", "-"))

    unique = sorted({tag for tag in tags if tag and len(tag) <= 40})
    return unique[:12]


def parse_markdown_skill(path: Path) -> SkillRecord:
    text = read_text(path)
    frontmatter = parse_frontmatter(text)

    fallback_name = path.stem
    name = sanitize(frontmatter.get("name") or frontmatter.get("title") or extract_name_from_text(text, fallback_name))
    description = sanitize(frontmatter.get("description") or extract_description(text))
    tags = extract_tags(frontmatter, path, text)
    bundle, confidence = infer_bundle(" ".join([name, description]), path, tags)
    command = sanitize(frontmatter.get("command") or extract_command(text, path))

    skill_id = sanitize(frontmatter.get("id") or path.stem).lower().replace(" ", "-")

    return SkillRecord(
        id=skill_id,
        name=name,
        description=description,
        bundle=bundle,
        source_file=path.as_posix(),
        tags=tags,
        command=command,
        confidence=confidence,
    )


def parse_json_skill(path: Path) -> SkillRecord | None:
    text = read_text(path)
    if not text.strip():
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    name = sanitize(str(data.get("name") or data.get("title") or path.stem))
    description = sanitize(str(data.get("description") or data.get("summary") or "Skill description not provided"))
    raw_tags = data.get("tags") or data.get("categories") or []
    tags = [sanitize(str(t)).lower() for t in raw_tags if sanitize(str(t))] if isinstance(raw_tags, list) else []
    bundle = sanitize(str(data.get("bundle") or ""))

    if not bundle:
        bundle, confidence = infer_bundle(" ".join([name, description]), path, tags)
    else:
        confidence = 0.95

    command = sanitize(str(data.get("command") or data.get("trigger") or f"@{path.stem}"))
    skill_id = sanitize(str(data.get("id") or path.stem)).lower().replace(" ", "-")

    return SkillRecord(
        id=skill_id,
        name=name,
        description=description,
        bundle=bundle,
        source_file=path.as_posix(),
        tags=sorted({t for t in tags})[:12],
        command=command,
        confidence=round(confidence, 2),
    )


def discover_skill_files(root: Path) -> list[Path]:
    patterns = [
        "**/*skill*.md",
        "**/skills/**/*.md",
        "**/prompts/**/*.md",
        "**/*skill*.json",
        "**/skills/**/*.json",
    ]
    found: list[Path] = []
    for pattern in patterns:
        found.extend(root.glob(pattern))

    unique = sorted({path.resolve() for path in found if path.is_file()})
    return [Path(p) for p in unique]


def build_catalog(source_root: Path, skills: list[SkillRecord]) -> dict:
    bundles: dict[str, list[str]] = {}
    for skill in skills:
        bundles.setdefault(skill.bundle, []).append(skill.id)

    return {
        "ok": True,
        "generated_at": now_iso(),
        "source_root": source_root.as_posix(),
        "total_skills": len(skills),
        "bundles": {k: sorted(v) for k, v in sorted(bundles.items(), key=lambda item: item[0])},
        "skills": [asdict(skill) for skill in skills],
    }


def run(source_root: Path, output_path: Path, min_confidence: float = 0.0) -> Path:
    skill_files = discover_skill_files(source_root)
    skills: list[SkillRecord] = []

    for path in skill_files:
        if path.suffix.lower() == ".json":
            parsed = parse_json_skill(path)
            if parsed and parsed.confidence >= min_confidence:
                skills.append(parsed)
            continue

        parsed = parse_markdown_skill(path)
        if parsed.confidence >= min_confidence:
            skills.append(parsed)

    catalog = build_catalog(source_root, sorted(skills, key=lambda item: (item.bundle, item.name.lower())))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Catalogador masivo de skills (Antigravity/NEXO)")
    parser.add_argument("--source", default=".", help="Ruta raíz del repositorio de skills")
    parser.add_argument(
        "--output",
        default="logs/antigravity_skills_catalog.json",
        help="Archivo JSON de salida para Make/NEXO",
    )
    parser.add_argument("--min-confidence", type=float, default=0.35, help="Confianza mínima para incluir skill")
    args = parser.parse_args()

    source_root = Path(args.source).resolve()
    output_path = Path(args.output).resolve()

    out = run(source_root=source_root, output_path=output_path, min_confidence=max(0.0, min(1.0, args.min_confidence)))
    log.info(json.dumps({"ok": True, "output": out.as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
