from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone

import config
from evaluador_ia import evaluate_job
from filtro import apply_rules
from notificacion import notify_ntfy
from postulador import auto_apply
from registro import acquire_cycle_lock, append_csv, append_google_sheet, is_seen, mark_seen, release_cycle_lock
from scraper import fetch_jobs


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.RUN_LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def _write_run_state(payload: dict) -> None:
    config.RUN_STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_cycle() -> dict:
    lock_acquired = acquire_cycle_lock(
        lock_file=config.CYCLE_LOCK_FILE,
        device_id=config.DEVICE_ID,
        stale_minutes=config.LOCK_STALE_MINUTES,
    )
    if not lock_acquired:
        summary = {
            "device_id": config.DEVICE_ID,
            "jobs_scraped": 0,
            "jobs_filtered": 0,
            "jobs_processed": 0,
            "jobs_applied": 0,
            "max_applications_per_cycle": max(1, int(config.MAX_APPLICATIONS_PER_CYCLE)),
            "dry_run": config.DRY_RUN,
            "skipped_reason": "cycle_lock_active",
        }
        return summary

    try:
        jobs = fetch_jobs(config.SEARCH_URL, config.COMPUTRABAJO_URL)
        filtered = apply_rules(
            jobs,
            min_salary_clp=config.MIN_SALARY_CLP,
            max_distance_km=config.MAX_DISTANCE_KM,
            keywords_required=config.KEYWORDS_REQUIRED,
            cv_profile=config.CV_PROFILE,
        )

        rows_for_sheet = []
        processed = 0
        applied = 0
        max_applications = max(1, int(config.MAX_APPLICATIONS_PER_CYCLE))

        for job in filtered:
            if is_seen(config.SEEN_JOBS_FILE, job.id):
                continue

            ev = evaluate_job(
                job=job,
                provider=config.AI_PROVIDER,
                anthropic_api_key=config.ANTHROPIC_API_KEY,
                anthropic_model=config.ANTHROPIC_MODEL,
                openai_api_key=config.OPENAI_API_KEY,
                openai_model=config.OPENAI_MODEL,
                cv_profile=config.CV_PROFILE,
            )
            score = int(ev.get("score", 1))
            status = "rejected_by_ai"

            if score >= config.MIN_AI_SCORE:
                if not config.DRY_RUN and applied >= max_applications:
                    status = "application_limit_reached"
                else:
                    result = auto_apply(
                        job,
                        email=config.COMPUTRABAJO_EMAIL,
                        password=config.COMPUTRABAJO_PASSWORD,
                        dry_run=config.DRY_RUN,
                        headless=config.PLAYWRIGHT_HEADLESS,
                    )
                    status = result.get("status", "unknown")
                    if result.get("ok"):
                        applied += 1

            row = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "device_id": config.DEVICE_ID,
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "score": score,
                "status": status,
                "detail_url": job.detail_url,
                "apply_url": job.apply_url,
                "reason": ev.get("reason", ""),
            }
            append_csv(config.CSV_LOG_FILE, row)
            rows_for_sheet.append(row)
            mark_seen(config.SEEN_JOBS_FILE, job.id, config.DEVICE_ID)
            processed += 1

        append_google_sheet(
            enabled=config.GOOGLE_SHEETS_ENABLED,
            spreadsheet_id=config.GOOGLE_SHEETS_ID,
            service_account_json=config.GOOGLE_SERVICE_ACCOUNT_JSON,
            rows=rows_for_sheet,
        )

        summary = {
            "device_id": config.DEVICE_ID,
            "jobs_scraped": len(jobs),
            "jobs_filtered": len(filtered),
            "jobs_processed": processed,
            "jobs_applied": applied,
            "max_applications_per_cycle": max_applications,
            "dry_run": config.DRY_RUN,
        }

        notify_ntfy(
            server=config.NTFY_SERVER,
            topic=config.NTFY_TOPIC,
            title="Agente de postulación",
            message=(
                f"Device: {summary['device_id']}\n"
                f"Scraped: {summary['jobs_scraped']} | Filtered: {summary['jobs_filtered']}\n"
                f"Processed: {summary['jobs_processed']} | Applied: {summary['jobs_applied']}\n"
                f"DryRun: {summary['dry_run']}"
            ),
            priority="default",
        )

        return summary
    finally:
        release_cycle_lock(config.CYCLE_LOCK_FILE, config.DEVICE_ID)


def run_cycle_with_retries() -> dict:
    retries = max(0, int(config.MAX_CYCLE_RETRIES))
    for attempt in range(retries + 1):
        try:
            return run_cycle()
        except Exception:
            if attempt >= retries:
                raise
            backoff = max(1, int(config.RETRY_BACKOFF_SECONDS)) * (attempt + 1)
            log.warning("Fallo en ciclo (attempt %s/%s). Reintentando en %ss", attempt + 1, retries + 1, backoff)
            time.sleep(backoff)
    raise RuntimeError("run_cycle_with_retries agotó intentos sin retorno")


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente inteligente de postulación")
    parser.add_argument("--once", action="store_true", help="Ejecuta solo un ciclo")
    args = parser.parse_args()

    if args.once:
        started = datetime.now(timezone.utc)
        try:
            result = run_cycle_with_retries()
            payload = {
                "status": "ok",
                "started_at": started.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "summary": result,
            }
            _write_run_state(payload)
            log.info(result)
        except Exception as exc:
            payload = {
                "status": "error",
                "started_at": started.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            }
            _write_run_state(payload)
            notify_ntfy(
                server=config.NTFY_SERVER,
                topic=config.NTFY_TOPIC,
                title="Agente de postulación - error",
                message=f"{config.DEVICE_ID}: {exc}",
                priority="high",
            )
            raise
        return

    while True:
        started = datetime.now(timezone.utc)
        try:
            result = run_cycle_with_retries()
            payload = {
                "status": "ok",
                "started_at": started.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "summary": result,
            }
            _write_run_state(payload)
            log.info(result)
        except Exception as exc:
            payload = {
                "status": "error",
                "started_at": started.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            }
            _write_run_state(payload)
            notify_ntfy(
                server=config.NTFY_SERVER,
                topic=config.NTFY_TOPIC,
                title="Agente de postulación - error",
                message=f"{config.DEVICE_ID}: {exc}",
                priority="high",
            )
        time.sleep(int(config.CYCLE_HOURS * 3600))


if __name__ == "__main__":
    main()
