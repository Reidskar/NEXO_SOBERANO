from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as urlrequest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from backend.services.unified_sync_service import run_unified_sync
from scripts.ai_context_tracker import update_ai_context_state


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

LOGS = ROOT / "logs"
LOCK_PATH = LOGS / "sync_unified.lock"
STATUS_PATH = LOGS / "sync_unified_status.json"
REPORT_PATH = LOGS / "sync_unified_last.json"
ALERTS_PATH = LOGS / "sync_unified_alerts.jsonl"
INDICATORS_PATH = LOGS / "sync_unified_indicators.json"
GRAPH_DIR = LOGS / "sync_unified_graphs"
APPROVAL_PATH = LOGS / "system_approval.json"


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "") or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_channels() -> list[str]:
    raw = (os.getenv("NEXO_FULL_YOUTUBE_CHANNELS", "") or "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_alert(payload: dict) -> None:
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _notify_webhook(payload: dict) -> None:
    webhook = (os.getenv("NEXO_ALERT_WEBHOOK", "") or "").strip()
    if not webhook:
        return
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urlrequest.Request(webhook, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urlrequest.urlopen(req, timeout=8):
            pass
        try:
            from backend.services.unified_cost_tracker import get_cost_tracker

            get_cost_tracker().track_service_call(
                servicio="discord_webhook",
                operaciones=1,
                tipo_operacion="sync_alert_webhook",
                metadata={"source": "scripts.run_unified_sync_full", "channel": "NEXO_ALERT_WEBHOOK"},
            )
        except Exception:
            pass
    except Exception:
        pass


def _summary(result: dict) -> dict:
    gp = result.get("google_photos", {})
    gd = result.get("google_drive", {})
    od = result.get("onedrive", {})
    yt = result.get("youtube", {})
    return {
        "google_photos": {
            "imported": gp.get("imported", 0),
            "skipped": gp.get("skipped", 0),
            "errors": gp.get("errors", 0),
        },
        "google_drive": {
            "analyzed": gd.get("analyzed", 0),
            "classified": gd.get("classified", 0),
            "skipped": gd.get("skipped", 0),
            "errors": gd.get("errors", 0),
        },
        "onedrive": {
            "imported": od.get("imported", 0),
            "skipped": od.get("skipped", 0),
            "errors": od.get("errors", 0),
        },
        "youtube": {
            "processed": yt.get("processed", 0),
            "skipped": yt.get("skipped", 0),
            "errors": yt.get("errors", 0),
        },
    }


def _has_errors(summary: dict) -> bool:
    return any(int((section or {}).get("errors", 0) or 0) > 0 for section in summary.values())


def _llm_provider_status() -> dict:
    provider = (os.getenv("NEXO_LLM_PROVIDER", "auto") or "auto").strip().lower()
    available = {
        "anthropic": bool((os.getenv("ANTHROPIC_API_KEY", "") or "").strip()),
        "grok": bool((os.getenv("XAI_API_KEY", "") or "").strip()),
        "openai_copilot": bool((os.getenv("OPENAI_API_KEY", "") or "").strip()),
        "gemini": bool((os.getenv("GEMINI_API_KEY", "") or "").strip()),
    }
    return {
        "selected": provider,
        "available": available,
        "ready_count": sum(1 for v in available.values() if v),
    }


def _provider_comparison(llm_status: dict) -> list[dict]:
    availability = llm_status.get("available", {}) or {}
    providers = [
        {
            "provider": "gemini",
            "available": bool(availability.get("gemini")),
            "best_for": ["clasificación multimodal", "OCR/contexto imagen", "coste contenido"],
            "risks": ["scope/credenciales Google", "cuotas API"],
        },
        {
            "provider": "anthropic_claude",
            "available": bool(availability.get("anthropic")),
            "best_for": ["análisis largo", "razonamiento estructurado", "síntesis de riesgo"],
            "risks": ["API key faltante", "coste por token"],
        },
        {
            "provider": "grok_xai",
            "available": bool(availability.get("grok")),
            "best_for": ["señales X/Twitter", "tiempo real", "contexto social"],
            "risks": ["API key faltante", "dependencia fuente externa"],
        },
        {
            "provider": "openai_copilot",
            "available": bool(availability.get("openai_copilot")),
            "best_for": ["QA RAG general", "orquestación", "fallback robusto"],
            "risks": ["API key/base_url", "coste variable"],
        },
    ]
    return providers


def _credentials_status() -> dict:
    root = ROOT
    credential_candidates = {
        "google_credentials": [
            root / "credenciales_google.json",
            root / "backend" / "auth" / "credenciales_google.json",
        ],
        "microsoft_credentials": [
            root / "credenciales_microsoft.json",
            root / "backend" / "auth" / "credenciales_microsoft.json",
        ],
        "drive_client_secrets": [
            root / "backend" / "auth" / "drive_client_secrets.json",
            root / "backend" / "auth" / "credenciales_google.json",
        ],
    }
    env_keys = {
        "GEMINI_API_KEY": bool((os.getenv("GEMINI_API_KEY", "") or "").strip()),
        "OPENAI_API_KEY": bool((os.getenv("OPENAI_API_KEY", "") or "").strip()),
        "ANTHROPIC_API_KEY": bool((os.getenv("ANTHROPIC_API_KEY", "") or "").strip()),
        "XAI_API_KEY": bool((os.getenv("XAI_API_KEY", "") or "").strip()),
    }
    files = {
        name: any(path.exists() for path in candidates)
        for name, candidates in credential_candidates.items()
    }
    return {
        "files": files,
        "env_keys": env_keys,
    }


def _build_approval(summary: dict, indicators: dict) -> dict:
    llm = indicators.get("llm_coordination", {}) or {}
    creds = _credentials_status()
    blockers: list[str] = []
    warnings: list[str] = []

    if int(llm.get("ready_count", 0) or 0) == 0:
        blockers.append("Sin proveedor IA activo (GEMINI/OPENAI/ANTHROPIC/XAI)")

    files = creds.get("files", {}) or {}
    if not bool(files.get("google_credentials")):
        blockers.append("Falta credenciales_google.json")
    if not bool(files.get("microsoft_credentials")):
        blockers.append("Falta credenciales_microsoft.json")

    gp_errors = int((summary.get("google_photos") or {}).get("errors", 0) or 0)
    od_errors = int((summary.get("onedrive") or {}).get("errors", 0) or 0)
    gd_errors = int((summary.get("google_drive") or {}).get("errors", 0) or 0)
    if gp_errors > 0:
        warnings.append(f"Google Photos con errores: {gp_errors}")
    if od_errors > 0:
        warnings.append(f"OneDrive con errores: {od_errors}")
    if gd_errors > 0:
        warnings.append(f"Google Drive con errores: {gd_errors}")

    approved = len(blockers) == 0 and (gp_errors + od_errors + gd_errors) == 0
    grade = "A" if approved else ("B" if len(blockers) == 0 else "C")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "approved": approved,
        "grade": grade,
        "blockers": blockers,
        "warnings": warnings,
        "credentials": creds,
        "llm": llm,
        "provider_comparison": _provider_comparison(llm),
        "next_actions": [
            "Autorizar Drive/Photos via endpoint /agente/drive/authorize y /agente/photos/authorize",
            "Configurar credenciales Microsoft válidas para Graph o fallback local",
            "Configurar al menos una API key LLM para aprobación completa",
        ],
    }


def _build_indicators(result: dict) -> dict:
    source_status = {}
    category_counter = Counter()
    bucket_counter = Counter()
    status_counter = Counter()

    for source in ("google_photos", "google_drive", "onedrive", "youtube"):
        section = result.get(source, {}) or {}
        source_status[source] = {
            "imported": int(section.get("imported", 0) or 0),
            "classified": int(section.get("classified", 0) or 0),
            "processed": int(section.get("processed", 0) or 0),
            "analyzed": int(section.get("analyzed", 0) or 0),
            "skipped": int(section.get("skipped", 0) or 0),
            "errors": int(section.get("errors", 0) or 0),
        }
        for item in (section.get("items") or []):
            status_counter[str(item.get("status") or "unknown")] += 1
            category = item.get("category")
            if category:
                category_counter[str(category)] += 1
            bucket = item.get("conflict_bucket")
            if bucket:
                bucket_counter[str(bucket)] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm_coordination": _llm_provider_status(),
        "source_status": source_status,
        "category_distribution": dict(sorted(category_counter.items(), key=lambda x: (-x[1], x[0]))),
        "conflict_bucket_distribution": dict(sorted(bucket_counter.items(), key=lambda x: (-x[1], x[0]))),
        "item_status_distribution": dict(sorted(status_counter.items(), key=lambda x: (-x[1], x[0]))),
    }


def _render_graphs(indicators: dict) -> list[str]:
    try:
        import matplotlib  # pyright: ignore[reportMissingModuleSource]
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # pyright: ignore[reportMissingModuleSource]
    except Exception as exc:
        log.warning("No se generaron gráficos (matplotlib no disponible): %s", exc)
        return []

    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    generated = []

    source_status = indicators.get("source_status", {})
    labels = list(source_status.keys())
    processed = [
        int(source_status.get(s, {}).get("imported", 0))
        + int(source_status.get(s, {}).get("classified", 0))
        + int(source_status.get(s, {}).get("processed", 0))
        for s in labels
    ]
    errors = [int(source_status.get(s, {}).get("errors", 0)) for s in labels]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(labels, processed, label="procesado")
    ax.bar(labels, errors, bottom=processed, label="errores")
    ax.set_title("Sync unificado: procesado y errores por fuente")
    ax.set_ylabel("items")
    ax.legend()
    fig.tight_layout()
    out_a = GRAPH_DIR / "sync_sources.png"
    fig.savefig(str(out_a), dpi=140)
    plt.close(fig)
    generated.append(str(out_a))

    cat_dist = indicators.get("category_distribution", {}) or {}
    if cat_dist:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.bar(list(cat_dist.keys()), list(cat_dist.values()))
        ax.set_title("Distribución por categoría")
        ax.set_ylabel("items")
        fig.tight_layout()
        out_b = GRAPH_DIR / "sync_categories.png"
        fig.savefig(str(out_b), dpi=140)
        plt.close(fig)
        generated.append(str(out_b))

    bucket_dist = indicators.get("conflict_bucket_distribution", {}) or {}
    if bucket_dist:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.bar(list(bucket_dist.keys()), list(bucket_dist.values()))
        ax.set_title("Distribución geopolítica por bucket")
        ax.set_ylabel("items")
        fig.tight_layout()
        out_c = GRAPH_DIR / "sync_conflict_buckets.png"
        fig.savefig(str(out_c), dpi=140)
        plt.close(fig)
        generated.append(str(out_c))

    return generated


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)

    try:
        lock_fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(lock_fd, str(os.getpid()).encode("utf-8"))
        os.close(lock_fd)
    except FileExistsError:
        _write_json(
            STATUS_PATH,
            {
                "status": "already_running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Ya existe una sincronización unificada en ejecución",
            },
        )
        log.info("already_running")
        return 2

    request_payload = {
        "dry_run": _env_bool("NEXO_FULL_DRY_RUN", False),
        "photos_limit": _env_int("NEXO_FULL_PHOTOS_LIMIT", 50),
        "drive_limit": _env_int("NEXO_FULL_DRIVE_LIMIT", 300),
        "onedrive_limit": _env_int("NEXO_FULL_ONEDRIVE_LIMIT", 100),
        "onedrive_max_mb": _env_int("NEXO_FULL_ONEDRIVE_MAX_MB", 50),
        "youtube_per_channel": _env_int("NEXO_FULL_YT_PER_CHANNEL", 10),
        "youtube_channels": _env_channels(),
        "drive_include_trashed": _env_bool("NEXO_FULL_DRIVE_INCLUDE_TRASHED", True),
        "drive_full_scan": _env_bool("NEXO_FULL_DRIVE_FULL_SCAN", True),
        "drive_auto_rename": _env_bool("NEXO_FULL_DRIVE_AUTO_RENAME", True),
        "retry_attempts": _env_int("NEXO_FULL_RETRY_ATTEMPTS", 3),
        "retry_backoff_seconds": _env_float("NEXO_FULL_RETRY_BACKOFF_SECONDS", 1.2),
    }
    full_run_attempts = max(1, _env_int("NEXO_FULL_RUN_ATTEMPTS", 2))

    try:
        last_exc = None
        result = None
        used_attempt = 0
        for run_attempt in range(1, full_run_attempts + 1):
            used_attempt = run_attempt
            _write_json(
                STATUS_PATH,
                {
                    "status": "running",
                    "pid": os.getpid(),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "run_attempt": run_attempt,
                    "max_run_attempts": full_run_attempts,
                    "request": request_payload,
                },
            )
            try:
                result = run_unified_sync(
                    dry_run=request_payload["dry_run"],
                    photos_limit=request_payload["photos_limit"],
                    drive_limit=request_payload["drive_limit"],
                    onedrive_limit=request_payload["onedrive_limit"],
                    onedrive_max_mb=request_payload["onedrive_max_mb"],
                    youtube_per_channel=request_payload["youtube_per_channel"],
                    youtube_channels=request_payload["youtube_channels"],
                    drive_include_trashed=request_payload["drive_include_trashed"],
                    drive_full_scan=request_payload["drive_full_scan"],
                    drive_auto_rename=request_payload["drive_auto_rename"],
                    retry_attempts=request_payload["retry_attempts"],
                    retry_backoff_seconds=request_payload["retry_backoff_seconds"],
                )
                break
            except Exception as exc:
                last_exc = exc
                alert = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "sync_unified_runner_retry",
                    "run_attempt": run_attempt,
                    "max_run_attempts": full_run_attempts,
                    "error": str(exc),
                }
                _append_alert(alert)
                _notify_webhook(alert)
                if run_attempt >= full_run_attempts:
                    raise

        if result is None and last_exc is not None:
            raise last_exc
        if result is None:
            raise RuntimeError("run_unified_sync no retornó resultado")

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ok": bool(result.get("ok", False)),
            "request": request_payload,
            "summary": _summary(result),
            "result": result,
        }
        indicators = _build_indicators(result)
        chart_paths = _render_graphs(indicators)
        indicators["graph_files"] = chart_paths
        approval = _build_approval(payload["summary"], indicators)
        payload["indicators"] = indicators
        payload["approval"] = approval
        _write_json(REPORT_PATH, payload)
        _write_json(INDICATORS_PATH, indicators)
        _write_json(APPROVAL_PATH, approval)
        if payload["summary"] and _has_errors(payload["summary"]):
            alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "sync_unified_completed_with_errors",
                "summary": payload["summary"],
                "report_path": str(REPORT_PATH),
            }
            _append_alert(alert)
            _notify_webhook(alert)

        for item in (result.get("alerts") or []):
            _append_alert(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "type": "sync_unified_internal_alert",
                    "payload": item,
                }
            )

        _write_json(
            STATUS_PATH,
            {
                "status": "done",
                "pid": os.getpid(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "run_attempt": used_attempt,
                "max_run_attempts": full_run_attempts,
                "summary": payload["summary"],
                "report_path": str(REPORT_PATH),
            },
        )
        try:
            update_ai_context_state()
        except Exception as ctx_exc:
            log.warning("No fue posible actualizar contexto IA automático: %s", ctx_exc)
        log.info(json.dumps(payload["summary"], ensure_ascii=False))
        log.info(f"Reporte: {REPORT_PATH}")
        return 0
    except Exception as exc:
        _write_json(
            STATUS_PATH,
            {
                "status": "error",
                "pid": os.getpid(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "sync_unified_runner_error",
            "error": str(exc),
        }
        _append_alert(alert)
        _notify_webhook(alert)
        try:
            update_ai_context_state()
        except Exception as ctx_exc:
            log.warning("No fue posible actualizar contexto IA automático tras error: %s", ctx_exc)
        raise
    finally:
        try:
            LOCK_PATH.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
