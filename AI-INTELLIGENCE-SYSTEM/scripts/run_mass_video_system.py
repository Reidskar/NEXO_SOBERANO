from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


log = logging.getLogger(__name__)


@dataclass
class VideoPlan:
    video_path: Path
    profile: str
    prompt_file: Path
    slug: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "video"


def detect_profile(filename: str) -> str:
    name = filename.lower()
    if "enrique" in name or "rocha" in name:
        return "enrique_rocha"
    if "chase" in name:
        return "chase_h_ai"
    if "revolutia" in name:
        return "revolutia_ai"
    if "nico" in name or "pradas" in name:
        return "nico_pradas"
    return "generic"


def profile_to_prompt(prompts_dir: Path, profile: str) -> Path:
    mapping = {
        "enrique_rocha": "01_video_enrique_rocha.md",
        "chase_h_ai": "02_video_chase_h_ai.md",
        "revolutia_ai": "03_video_revolutia_ai.md",
        "nico_pradas": "04_video_nico_pradas.md",
        "generic": "05_super_prompt_reverse_engineering.md",
    }
    return prompts_dir / mapping[profile]


def find_videos(videos_dir: Path) -> list[Path]:
    exts = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".txt", ".md"}
    return sorted([p for p in videos_dir.iterdir() if p.is_file() and p.suffix.lower() in exts])


def ensure_simulated_videos(videos_dir: Path) -> list[Path]:
    simulated = [
        videos_dir / "enrique_rocha_demo.mp4",
        videos_dir / "chase_h_ai_growth_demo.mp4",
        videos_dir / "revolutia_ai_system_demo.mp4",
        videos_dir / "nico_pradas_automation_demo.mp4",
    ]
    for path in simulated:
        if not path.exists():
            path.write_text("SIMULATED_VIDEO_PLACEHOLDER", encoding="utf-8")
    return simulated


def build_plan(videos: Iterable[Path], prompts_dir: Path) -> list[VideoPlan]:
    plans: list[VideoPlan] = []
    for video_path in videos:
        profile = detect_profile(video_path.name)
        prompt_file = profile_to_prompt(prompts_dir, profile)
        slug = slugify(video_path.stem)
        plans.append(VideoPlan(video_path=video_path, profile=profile, prompt_file=prompt_file, slug=slug))
    return plans


def load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_architecture(plan: VideoPlan, root: Path) -> Path:
    target = root / "architectures" / f"{plan.slug}_architecture.md"
    text = f"""# Architecture Blueprint — {plan.video_path.name}

- generated_at: {utc_now()}
- profile: {plan.profile}
- source_video: {plan.video_path.as_posix()}
- prompt_used: {plan.prompt_file.as_posix()}

## System Breakdown
- Tools: n8n, Discord, Google Drive, OpenAI API
- AI Models: configurable provider (OpenAI + optional local)
- Automation: ingest → process → generate → publish → analytics
- Monetization: configurable per workflow (subscription/lead-gen/content ops)
- Data Flow: source video/files -> extraction -> structured outputs -> publication

## Modular Architecture
- Frontend: Next.js/Astro dashboard
- Backend: Python/Node API layer
- Automation: n8n orchestrations
- AI Services: prompt runner + model abstraction
- Storage: PostgreSQL + Drive artifacts

## API Surface
- POST /process-video
- POST /generate
- POST /automation/run
- GET /users
- GET /data/export

## Security Baseline
- API Key auth
- rate limiting
- execution logs
- role-based access
"""
    target.write_text(text, encoding="utf-8")
    return target


def write_knowledge(plan: VideoPlan, root: Path) -> Path:
    target = root / "knowledge" / "systems" / f"{plan.slug}_lesson.md"
    text = f"""# Lesson — {plan.video_path.name}

## Summary
This lesson was generated in simulation mode from video `{plan.video_path.name}`.

## Level 1 (Beginner)
The video shows an automation system that takes content, processes it with AI, and outputs reusable assets.

## Level 2 (Intermediate)
Pipeline stages: trigger, ingestion, AI processing, structured output generation, analytics logging.

## Level 3 (Advanced)
Implement multi-agent orchestration with memory layer, queue-based job execution, and workflow retries.

## Practical Implementation
- Use n8n for trigger + orchestration
- Expose backend endpoints for execution and status
- Persist outputs in PostgreSQL and Google Drive

## Common Mistakes
- Missing API authentication
- No idempotency for repeated runs
- No observability for failed automations
"""
    target.write_text(text, encoding="utf-8")
    return target


def write_workflow(plan: VideoPlan, root: Path) -> Path:
    template_path = root / "workflows" / "n8n_workflow_template.json"
    data = json.loads(load_text(template_path) or "{}")
    data["name"] = f"Video Pipeline - {plan.slug}"
    data["metadata"] = {
        "generated_at": utc_now(),
        "profile": plan.profile,
        "source_video": plan.video_path.as_posix(),
        "prompt": plan.prompt_file.as_posix(),
    }
    target = root / "workflows" / f"{plan.slug}_workflow.json"
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def write_database_note(plan: VideoPlan, root: Path) -> Path:
    target = root / "database" / f"{plan.slug}_migration.sql"
    sql = "\n".join(
        [
            f"-- generated_at: {utc_now()}",
            f"-- source_video: {plan.video_path.name}",
            "",
            "INSERT INTO projects (name, source_type, status)",
            f"VALUES ({sql_literal(plan.slug)}, 'video', 'draft');",
            "",
            "-- Reuse base schema from database/base_schema.sql for core tables.",
            "",
        ]
    )
    target.write_text(sql, encoding="utf-8")
    return target


def update_tools_database(root: Path) -> Path:
    target = root / "tools-database" / "tools_catalog.json"
    catalog = {
        "generated_at": utc_now(),
        "tools": [
            {"name": "n8n", "category": "Automation", "integration": "integrations/n8n"},
            {"name": "Discord Webhooks", "category": "Communication", "integration": "integrations/discord"},
            {"name": "Google Drive API", "category": "Storage", "integration": "integrations/drive"},
            {"name": "OpenAI API", "category": "AI", "integration": "backend/ai-services"},
        ],
    }
    target.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def write_report(root: Path, items: list[dict]) -> Path:
    reports_dir = root / "docs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    target = reports_dir / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    payload = {
        "ok": True,
        "generated_at": utc_now(),
        "total_videos": len(items),
        "items": items,
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def simulate_user_console(plans: list[VideoPlan]) -> None:
    log.info("🧠 [Usuario] Iniciando sistema de ingeniería inversa de videos...")
    log.info(f"📦 [Sistema] Videos detectados: {len(plans)}")
    for index, plan in enumerate(plans, start=1):
        log.info(f"▶️  [{index}/{len(plans)}] Procesando: {plan.video_path.name} | perfil={plan.profile}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch runner for AI-INTELLIGENCE-SYSTEM")
    parser.add_argument("--simulate-user", action="store_true", help="Print user-style simulation logs")
    parser.add_argument("--ensure-sample-videos", action="store_true", help="Create simulated videos if folder is empty")
    parser.add_argument("--max-videos", type=int, default=0, help="Limit number of videos to process")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    videos_dir = root / "videos"
    prompts_dir = root / "prompts"

    videos = find_videos(videos_dir)
    if not videos and args.ensure_sample_videos:
        videos = ensure_simulated_videos(videos_dir)

    plans = build_plan(videos, prompts_dir)
    if args.max_videos and args.max_videos > 0:
        plans = plans[: args.max_videos]

    if args.simulate_user:
        simulate_user_console(plans)

    items: list[dict] = []
    for plan in plans:
        architecture_file = write_architecture(plan, root)
        knowledge_file = write_knowledge(plan, root)
        workflow_file = write_workflow(plan, root)
        migration_file = write_database_note(plan, root)

        items.append(
            {
                "video": plan.video_path.name,
                "profile": plan.profile,
                "prompt": str(plan.prompt_file.relative_to(root)),
                "outputs": {
                    "architecture": str(architecture_file.relative_to(root)),
                    "knowledge": str(knowledge_file.relative_to(root)),
                    "workflow": str(workflow_file.relative_to(root)),
                    "database": str(migration_file.relative_to(root)),
                },
            }
        )

    tools_catalog = update_tools_database(root)
    report = write_report(root, items)

    summary = {
        "ok": True,
        "videos_processed": len(items),
        "report": str(report.relative_to(root)),
        "tools_catalog": str(tools_catalog.relative_to(root)),
    }
    log.info(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
