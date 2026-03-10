from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from NEXO_CORE import config

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class WebAISupervisorStatus:
    running: bool = False
    last_tick_at: Optional[float] = None
    last_context_update_at: Optional[float] = None
    last_web_monitor_at: Optional[float] = None
    last_innovation_scan_at: Optional[float] = None
    last_visual_guard_at: Optional[float] = None
    last_error: Optional[str] = None
    context_updates_ok: int = 0
    context_updates_failed: int = 0
    web_checks_ok: int = 0
    web_checks_failed: int = 0
    innovation_checks_ok: int = 0
    innovation_checks_failed: int = 0
    visual_checks_ok: int = 0
    visual_checks_failed: int = 0
    providers: dict[str, bool] | None = None
    context_summary: dict[str, Any] | None = None
    web_summary: dict[str, Any] | None = None
    innovation_summary: dict[str, Any] | None = None
    visual_summary: dict[str, Any] | None = None
    data_freshness: dict[str, Any] | None = None


class WebAISupervisor:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._status = WebAISupervisorStatus(
            providers={
                "gemini": bool((os.getenv("GEMINI_API_KEY", "") or "").strip()),
                "openai": bool((os.getenv("OPENAI_API_KEY", "") or "").strip()),
                "anthropic": bool((os.getenv("ANTHROPIC_API_KEY", "") or "").strip()),
                "grok_xai": bool((os.getenv("XAI_API_KEY", "") or "").strip()),
            }
        )
        self._last_context_run = 0.0
        self._last_web_run = 0.0
        self._last_innovation_run = 0.0
        self._last_visual_guard_run = 0.0
        self._base_url = self._resolve_base_url()

    def snapshot(self) -> dict[str, Any]:
        data = asdict(self._status)
        data["providers_ready"] = sum(1 for value in (self._status.providers or {}).values() if value)
        data["provider_total"] = len(self._status.providers or {})
        data["enabled"] = bool(config.AI_WEB_INTELLIGENCE_ENABLED)
        data["visual_guard_enabled"] = bool(config.AI_VISUAL_GUARD_ENABLED)
        data["visual_guard_interval_seconds"] = float(config.AI_VISUAL_GUARD_SECONDS)
        data["data_freshness_slo_seconds"] = float(config.AI_DATA_FRESHNESS_MAX_AGE_SECONDS)
        return data

    def _resolve_base_url(self) -> str:
        explicit = (os.getenv("NEXO_SUPERVISOR_BASE_URL", "") or "").strip()
        if explicit:
            return explicit.rstrip("/")
        host = (config.HOST or "127.0.0.1").strip()
        if host in {"0.0.0.0", "::", ""}:
            host = "127.0.0.1"
        return f"http://{host}:{int(config.PORT)}"

    def _http_get_json(self, path: str, protected: bool = False) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = {"Accept": "application/json", "User-Agent": "NEXO-WebAI-Supervisor/1.0"}
        if protected and (config.NEXO_API_KEY or "").strip():
            headers["X-NEXO-API-KEY"] = config.NEXO_API_KEY
            headers["X-NEXO-KEY"] = config.NEXO_API_KEY
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=max(1.0, float(config.AI_VISUAL_HTTP_TIMEOUT))) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body) if body else {}

    @staticmethod
    def _age_seconds(reference: Optional[float], now: float) -> Optional[float]:
        if reference is None:
            return None
        try:
            return max(0.0, now - float(reference))
        except Exception:
            return None

    async def _update_ai_context(self) -> None:
        try:
            from scripts.ai_context_tracker import update_ai_context_state

            status = await asyncio.to_thread(update_ai_context_state)
            self._status.context_updates_ok += 1
            self._status.last_context_update_at = time.time()
            self._status.context_summary = {
                "rag_loaded": ((status.get("rag") or {}).get("rag_loaded", False)),
                "total_documentos": ((status.get("rag") or {}).get("total_documentos", 0)),
                "total_chunks": ((status.get("rag") or {}).get("total_chunks", 0)),
                "google_photos_imported": ((status.get("google_photos") or {}).get("imported", 0)),
            }
        except Exception as exc:
            self._status.context_updates_failed += 1
            self._status.last_error = f"AI context update failed: {exc}"
            logger.warning("AI context update failed: %s", exc)

    async def _run_web_monitor_once(self) -> None:
        if not config.AI_WEB_MONITOR_ENABLED:
            return
        try:
            script = ROOT / "scripts" / "run_x_monitor.py"
            if not script.exists():
                raise FileNotFoundError(f"No existe {script}")

            cmd = [
                sys.executable,
                str(script),
                "--once",
                "--limit",
                str(config.AI_WEB_MONITOR_LIMIT),
            ]
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                timeout=config.AI_WEB_MONITOR_TIMEOUT,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError((result.stderr or "monitor failed")[:300])

            parsed: dict[str, Any] | None = None
            output = (result.stdout or "").strip()
            if output:
                try:
                    parsed = json.loads(output)
                except Exception:
                    parsed = {"raw": output[:500]}

            self._status.web_checks_ok += 1
            self._status.last_web_monitor_at = time.time()
            self._status.web_summary = parsed or {"ok": True}
        except Exception as exc:
            self._status.web_checks_failed += 1
            self._status.last_error = f"Web monitor failed: {exc}"
            logger.warning("Web monitor failed: %s", exc)

    async def _run_visual_data_guard_once(self) -> None:
        if not config.AI_VISUAL_GUARD_ENABLED:
            return

        now = time.time()
        endpoint_checks: dict[str, dict[str, Any]] = {}
        health_payload: dict[str, Any] | None = None
        analytics_payload: dict[str, Any] | None = None

        try:
            health_payload = await asyncio.to_thread(self._http_get_json, "/api/health/", False)
            endpoint_checks["health"] = {"ok": True}
        except Exception as exc:
            endpoint_checks["health"] = {"ok": False, "error": str(exc)[:180]}

        try:
            analytics_payload = await asyncio.to_thread(self._http_get_json, "/agente/control-center/analytics", True)
            endpoint_checks["analytics"] = {"ok": True}
        except Exception as exc:
            endpoint_checks["analytics"] = {"ok": False, "error": str(exc)[:180]}

        raw_ai_web = (health_payload or {}).get("ai_web") if isinstance(health_payload, dict) else {}
        reference_ai_web = raw_ai_web if isinstance(raw_ai_web, dict) else {}
        context_reference = reference_ai_web.get("last_context_update_at") or self._status.last_context_update_at
        web_reference = reference_ai_web.get("last_web_monitor_at") or self._status.last_web_monitor_at

        context_age = self._age_seconds(context_reference, now)
        web_age = self._age_seconds(web_reference, now)

        context_max_age = max(30.0, float(config.AI_DATA_FRESHNESS_MAX_AGE_SECONDS))
        web_max_age = max(context_max_age, float(config.AI_WEB_MONITOR_SECONDS) * 2.0)
        context_fresh = context_age is not None and context_age <= context_max_age
        web_fresh = web_age is not None and web_age <= web_max_age

        sync_values = (((analytics_payload or {}).get("charts") or {}).get("drive_sync") or {}).get("values") or []
        analyzed = int(sync_values[0]) if len(sync_values) > 0 else 0
        classified = int(sync_values[1]) if len(sync_values) > 1 else 0
        sync_errors = int(sync_values[3]) if len(sync_values) > 3 else 0
        rag_queries = int((analytics_payload or {}).get("metrics", {}).get("rag_queries_today", 0) or 0)

        total_checks = len(endpoint_checks)
        passed_checks = sum(1 for item in endpoint_checks.values() if item.get("ok"))
        coverage_percent = round((passed_checks / total_checks) * 100.0, 1) if total_checks else 0.0

        has_key = bool((config.NEXO_API_KEY or "").strip())
        analytics_ok = bool((endpoint_checks.get("analytics") or {}).get("ok"))
        analytics_condition = analytics_ok if has_key else True
        freshness_ok = bool(context_fresh and web_fresh and analytics_condition)

        self._status.last_visual_guard_at = now
        self._status.data_freshness = {
            "fresh": freshness_ok,
            "context_age_seconds": round(context_age, 1) if context_age is not None else None,
            "web_monitor_age_seconds": round(web_age, 1) if web_age is not None else None,
            "context_slo_seconds": context_max_age,
            "web_monitor_slo_seconds": web_max_age,
            "context_fresh": context_fresh,
            "web_monitor_fresh": web_fresh,
            "analytics_fresh": analytics_condition,
        }
        self._status.visual_summary = {
            "guard_ok": freshness_ok,
            "coverage_percent": coverage_percent,
            "endpoints": endpoint_checks,
            "metrics": {
                "drive_analyzed": analyzed,
                "drive_classified": classified,
                "sync_errors": sync_errors,
                "rag_queries_today": rag_queries,
            },
            "checked_at": now,
        }

        if freshness_ok:
            self._status.visual_checks_ok += 1
        else:
            self._status.visual_checks_failed += 1
            self._status.last_error = "Visual/Data guard detectó datos potencialmente desactualizados"

    async def _run_innovation_scout_once(self) -> None:
        if not config.AI_INNOVATION_SCOUT_ENABLED:
            return
        try:
            script = ROOT / "scripts" / "nexo_innovation_scout.py"
            if not script.exists():
                raise FileNotFoundError(f"No existe {script}")

            cmd = [sys.executable, str(script)]
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                timeout=120,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError((result.stderr or "innovation scout failed")[:300])

            scout_path = ROOT / "logs" / "innovation_scout_last.json"
            summary: dict[str, Any] = {"ok": True}
            if scout_path.exists():
                try:
                    summary = json.loads(scout_path.read_text(encoding="utf-8"))
                except Exception:
                    summary = {"ok": True, "raw": (result.stdout or "")[:500]}

            self._status.innovation_checks_ok += 1
            self._status.last_innovation_scan_at = time.time()
            self._status.innovation_summary = {
                "innovation_score": summary.get("innovation_score"),
                "recommendations": summary.get("recommendations", [])[:5],
                "updates_count": ((summary.get("updates") or {}).get("count", 0)),
                "missing_packages": ((summary.get("integrations") or {}).get("missing_packages", [])),
            }
        except Exception as exc:
            self._status.innovation_checks_failed += 1
            self._status.last_error = f"Innovation scout failed: {exc}"
            logger.warning("Innovation scout failed: %s", exc)

    async def loop(self) -> None:
        logger.info("Web AI Supervisor iniciado")
        self._status.running = True
        while True:
            try:
                now = time.time()
                self._status.last_tick_at = now

                if now - self._last_context_run >= config.AI_CONTEXT_UPDATE_SECONDS:
                    await self._update_ai_context()
                    self._last_context_run = now

                if now - self._last_web_run >= config.AI_WEB_MONITOR_SECONDS:
                    await self._run_web_monitor_once()
                    self._last_web_run = now

                if now - self._last_innovation_run >= config.AI_INNOVATION_SCOUT_SECONDS:
                    await self._run_innovation_scout_once()
                    self._last_innovation_run = now

                if now - self._last_visual_guard_run >= config.AI_VISUAL_GUARD_SECONDS:
                    await self._run_visual_data_guard_once()
                    self._last_visual_guard_run = now

                await asyncio.sleep(max(5.0, config.AI_SUPERVISOR_POLL_SECONDS))
            except asyncio.CancelledError:
                self._status.running = False
                logger.info("Web AI Supervisor detenido")
                raise
            except Exception as exc:
                self._status.last_error = str(exc)
                logger.error("Error en Web AI Supervisor: %s", exc)
                await asyncio.sleep(10)

    def start(self) -> None:
        if not config.AI_WEB_INTELLIGENCE_ENABLED:
            logger.info("Web AI Supervisor deshabilitado por configuración")
            return
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.loop())

    async def shutdown(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


web_ai_supervisor = WebAISupervisor()
