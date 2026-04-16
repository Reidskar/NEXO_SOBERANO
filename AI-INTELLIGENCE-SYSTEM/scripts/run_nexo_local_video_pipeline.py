from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "video"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def find_videos(videos_dir: Path) -> list[Path]:
    exts = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
    return sorted([p for p in videos_dir.iterdir() if p.is_file() and p.suffix.lower() in exts])


def format_output_path(template: str, slug: str) -> Path:
    return Path(template.format(slug=slug))


def build_prompt(video_name: str, template: str, config: dict[str, Any]) -> str:
    return (
        template.replace("{{video_file}}", video_name)
        .replace("{{language}}", str(config.get("language", "es")))
        .replace("{{confidence_threshold}}", str(config.get("confidence_threshold", 0.7)))
    )


def http_json(
    method: str,
    url: str,
    timeout_seconds: int,
    api_key: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-NEXO-API-KEY"] = api_key
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = request.Request(url=url, method=method, headers=headers, data=data)
    try:
        with request.urlopen(req, timeout=timeout_seconds) as resp:
            payload = resp.read().decode("utf-8", errors="ignore")
            return {
                "ok": True,
                "status": resp.status,
                "data": json.loads(payload) if payload.strip() else {},
            }
    except error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
        return {
            "ok": False,
            "status": exc.code,
            "error": payload or str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "error": str(exc),
        }


def run_runtime_checks(config: dict[str, Any], api_key: str) -> dict[str, Any]:
    runtime = config.get("runtime", {})
    base_url = str(runtime.get("base_url", "http://127.0.0.1:8080")).rstrip("/")
    timeout_seconds = int(runtime.get("timeout_seconds", 20))

    checks = {
        "health": ("GET", f"{base_url}/health", None),
        "analytics": ("GET", f"{base_url}/analytics", None),
        "warroom_ai_control": ("GET", f"{base_url}/warroom/ai-control", None),
        "foda_low_cost": (
            "POST",
            f"{base_url}/api/ai/foda-critical",
            {
                "objective": "Evaluar viabilidad técnica y económica del sistema extraído del video",
                "decisor_final": config.get("final_decider", "claude"),
                "modo_ahorro": bool(config.get("modo_ahorro", True)),
            },
        ),
    }

    results: dict[str, Any] = {}
    for name, (method, url, body) in checks.items():
        results[name] = http_json(method=method, url=url, timeout_seconds=timeout_seconds, api_key=api_key, body=body)
    return results


def generate_artifacts(root: Path, video_path: Path, config: dict[str, Any], prompt_template: str) -> dict[str, str]:
    slug = slugify(video_path.stem)
    output_manifest = config.get("output_manifest", {})

    target_knowledge = root / format_output_path(output_manifest["knowledge"], slug)
    target_architecture = root / format_output_path(output_manifest["architecture"], slug)
    target_workflow = root / format_output_path(output_manifest["workflow"], slug)
    target_prompts = root / format_output_path(output_manifest["prompts"], slug)
    target_sql = root / format_output_path(output_manifest["sql"], slug)
    target_implementation = root / format_output_path(output_manifest["implementation"], slug)

    prompt_content = build_prompt(video_path.name, prompt_template, config)
    write_text(target_prompts, f"# Prompt Pack — {video_path.name}\n\n{prompt_content}\n")

    write_text(
        target_knowledge,
        "\n".join(
            [
                f"# System Knowledge — {video_path.name}",
                "",
                f"- generated_at: {utc_now()}",
                f"- mode: {config.get('mode', 'fast')}",
                f"- final_decider: {config.get('final_decider', 'claude')}",
                f"- modo_ahorro: {config.get('modo_ahorro', True)}",
                "",
                "## Summary",
                "Documento generado localmente para integración en NEXO sin Make.",
                "",
                "## Output Contract",
                "A-I + plan de validación runtime J.",
            ]
        ),
    )

    write_text(
        target_architecture,
        "\n".join(
            [
                f"# NEXO Architecture — {video_path.name}",
                "",
                "## Components",
                "- Local video ingest",
                "- Prompt generation (low-cost policy)",
                "- Knowledge + architecture + workflow + SQL outputs",
                "- Runtime checks against NEXO API",
                "",
                "## Runtime Endpoints",
                "- GET /health",
                "- GET /analytics",
                "- GET /warroom/ai-control",
                "- POST /api/ai/foda-critical (claude + modo_ahorro=true)",
            ]
        ),
    )

    workflow_payload = {
        "name": f"nexo-local-video-{slug}",
        "mode": config.get("mode", "fast"),
        "cost_policy": {
            "final_decider": config.get("final_decider", "claude"),
            "modo_ahorro": bool(config.get("modo_ahorro", True)),
            "fallback": config.get("providers", {}).get("fallback", "gemini"),
        },
        "steps": [
            "detect_video",
            "generate_prompt_pack",
            "generate_knowledge_artifacts",
            "run_nexo_runtime_checks",
            "persist_report",
        ],
    }
    write_json(target_workflow, workflow_payload)

    write_text(
        target_sql,
        "\n".join(
            [
                "CREATE TABLE IF NOT EXISTS video_system_runs (",
                "  id SERIAL PRIMARY KEY,",
                "  slug TEXT NOT NULL,",
                "  source_video TEXT NOT NULL,",
                "  mode TEXT NOT NULL,",
                "  final_decider TEXT NOT NULL,",
                "  modo_ahorro BOOLEAN NOT NULL DEFAULT TRUE,",
                "  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
                ");",
            ]
        ),
    )

    write_text(
        target_implementation,
        "\n".join(
            [
                f"# 72h Roadmap — {video_path.name}",
                "",
                "## 0-6h",
                "- Ejecutar pipeline local",
                "- Validar endpoints runtime",
                "",
                "## 6-24h",
                "- Ajustar outputs y prompts por evidencia",
                "- Reprocesar en modo standard si es necesario",
                "",
                "## 24-72h",
                "- Integración completa con catálogo y documentación",
                "- Endurecer validaciones y checklists",
            ]
        ),
    )

    return {
        "slug": slug,
        "knowledge": str(target_knowledge.relative_to(root)),
        "architecture": str(target_architecture.relative_to(root)),
        "workflow": str(target_workflow.relative_to(root)),
        "prompts": str(target_prompts.relative_to(root)),
        "sql": str(target_sql.relative_to(root)),
        "implementation": str(target_implementation.relative_to(root)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local NEXO video pipeline without Make")
    parser.add_argument("--video", default="", help="Specific video filename to process")
    parser.add_argument("--max-videos", type=int, default=0, help="Limit number of videos")
    parser.add_argument("--skip-runtime-checks", action="store_true", help="Skip endpoint checks")
    parser.add_argument("--api-key", default="", help="NEXO API key override")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    config_path = root / "integrations" / "local_nexo" / "nexo_local_video_pipeline_config.json"
    prompt_template_path = root / "integrations" / "local_nexo" / "prompt_template_local.txt"
    videos_dir = root / "videos"

    config = load_json(config_path)
    prompt_template = read_text(prompt_template_path)
    videos = find_videos(videos_dir)

    if args.video:
        videos = [v for v in videos if v.name == args.video]

    if args.max_videos > 0:
        videos = videos[: args.max_videos]

    api_key = args.api_key
    if not api_key:
        api_key = ""

    items: list[dict[str, Any]] = []
    for video_path in videos:
        artifacts = generate_artifacts(root=root, video_path=video_path, config=config, prompt_template=prompt_template)
        runtime_checks = {}
        if not args.skip_runtime_checks and config.get("runtime", {}).get("validate_endpoints", True):
            runtime_checks = run_runtime_checks(config=config, api_key=api_key)

        items.append(
            {
                "video": video_path.name,
                "generated_at": utc_now(),
                "policy": {
                    "mode": config.get("mode", "fast"),
                    "final_decider": config.get("final_decider", "claude"),
                    "modo_ahorro": bool(config.get("modo_ahorro", True)),
                },
                "artifacts": artifacts,
                "runtime_checks": runtime_checks,
            }
        )

    report_path = root / "docs" / "reports" / f"local_video_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    write_json(
        report_path,
        {
            "ok": True,
            "project": config.get("project_name", "NEXO_SOBERANO"),
            "generated_at": utc_now(),
            "videos_processed": len(items),
            "items": items,
        },
    )

    print(
        json.dumps(
            {
                "ok": True,
                "videos_processed": len(items),
                "report": str(report_path.relative_to(root)),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
