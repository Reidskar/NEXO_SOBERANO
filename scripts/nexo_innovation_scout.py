"""
scripts/nexo_innovation_scout.py
=================================
Escáner de innovación de NEXO SOBERANO.
Detecta paquetes faltantes, oportunidades de integración y genera
recomendaciones priorizadas usando IA.

Salida: logs/innovation_scout_last.json
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nexo.innovation_scout")

# Paquetes conocidos que potencian el sistema
RECOMMENDED_PACKAGES = {
    "aiofiles": "I/O asíncrono de archivos (reduce bloqueos en RAG)",
    "httpx": "Cliente HTTP async moderno (reemplaza aiohttp en algunos módulos)",
    "pydantic-settings": "Gestión de configuración tipada (mejora config.py)",
    "tenacity": "Reintentos con backoff exponencial (resiliencia de APIs)",
    "rich": "Output de terminal mejorado (logs más legibles)",
    "orjson": "Serialización JSON 5-10x más rápida (APIs de alta frecuencia)",
    "structlog": "Logging estructurado (mejor observabilidad)",
    "prometheus_client": "Métricas Prometheus (monitoreo avanzado)",
    "redis": "Cliente Redis nativo (caché de embeddings)",
    "chromadb": "Base de datos vectorial local (alternativa a Qdrant para dev)",
    "sentence-transformers": "Embeddings locales (independencia de APIs)",
    "tiktoken": "Conteo preciso de tokens OpenAI/Anthropic",
}

# Integraciones recomendadas según estado del sistema
INTEGRATION_OPPORTUNITIES = [
    {
        "name": "Webhook de Telegram",
        "description": "Canal alternativo de alertas cuando Discord falla",
        "env_key": "TELEGRAM_BOT_TOKEN",
        "priority": "medium",
    },
    {
        "name": "Caché de embeddings en Redis",
        "description": "Evita regenerar embeddings costosos para documentos ya indexados",
        "env_key": "UPSTASH_REDIS_URL",
        "priority": "high",
    },
    {
        "name": "Exportación a Notion",
        "description": "Sincronización de reportes FODA a workspace de Notion",
        "env_key": "NOTION_API_KEY",
        "priority": "low",
    },
    {
        "name": "Monitoreo de costos en tiempo real",
        "description": "Dashboard de tokens/$ consumidos por sesión (ya existe tracker, falta UI)",
        "env_key": None,
        "priority": "medium",
    },
]


def _check_installed_packages() -> dict[str, bool]:
    """Verifica qué paquetes recomendados están instalados."""
    installed: dict[str, bool] = {}
    for pkg in RECOMMENDED_PACKAGES:
        pkg_import = pkg.replace("-", "_")
        try:
            __import__(pkg_import)
            installed[pkg] = True
        except ImportError:
            installed[pkg] = False
    return installed


def _check_active_integrations() -> dict[str, bool]:
    """Verifica qué integraciones están configuradas via env vars."""
    active: dict[str, bool] = {}
    for integ in INTEGRATION_OPPORTUNITIES:
        key = integ.get("env_key")
        if key:
            active[integ["name"]] = bool(os.getenv(key, "").strip())
        else:
            active[integ["name"]] = True  # No requiere config externa
    return active


def _count_py_files() -> int:
    """Cuenta archivos Python en el proyecto."""
    count = 0
    for d in [ROOT / "backend", ROOT / "NEXO_CORE", ROOT / "scripts"]:
        if d.exists():
            count += len(list(d.rglob("*.py")))
    return count


def _check_recent_errors() -> list[str]:
    """Lee el log más reciente del supervisor para encontrar errores activos."""
    errors: list[str] = []
    try:
        log_dir = ROOT / "logs" / "supervisor"
        if log_dir.exists():
            logs = sorted(log_dir.glob("supervisor_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if logs:
                lines = logs[0].read_text(encoding="utf-8", errors="replace").splitlines()
                for line in lines[-50:]:
                    if "ERROR" in line or "CRITICAL" in line:
                        errors.append(line.strip()[-200:])
    except Exception:
        pass
    return errors[:10]


def _generate_recommendations_with_ai(
    missing_pkgs: list[str],
    inactive_integrations: list[str],
    errors: list[str],
) -> list[str]:
    """
    Genera recomendaciones con Gemma 4 local ($0).
    Fallback: Gemini Flash → lista estática.
    """
    import asyncio

    context = (
        f"Sistema: NEXO SOBERANO (FastAPI + Gemma 4 local + Qdrant + OmniGlobe 3D + TheBigBrother OSINT).\n"
        f"Paquetes recomendados no instalados: {missing_pkgs[:8]}\n"
        f"Integraciones inactivas: {inactive_integrations[:5]}\n"
        f"Errores recientes: {errors[:3]}\n\n"
        "Lista 5 recomendaciones técnicas priorizadas (impacto alto primero). "
        "Cada ítem en una sola línea, sin markdown. Español."
    )

    # Intentar Gemma 4 primero ($0)
    async def _try_gemma() -> list[str]:
        try:
            from NEXO_CORE.services.ollama_service import ollama_service
            resp = await ollama_service.consultar(
                prompt=context,
                modelo="fast",
                system="Eres el optimizador técnico de NEXO SOBERANO. Da recomendaciones concretas.",
                temperature=0.1,
                max_tokens=300,
            )
            if resp.success and resp.text:
                return [l.strip() for l in resp.text.strip().splitlines() if l.strip()][:5]
        except Exception as e:
            logger.debug(f"Gemma 4 recommendations failed: {e}")
        return []

    try:
        recs = asyncio.run(_try_gemma())
        if recs:
            logger.info("Recomendaciones generadas con Gemma 4 ($0)")
            return recs
    except RuntimeError:
        pass   # event loop already running

    # Fallback: Gemini Flash
    try:
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            resp = model.generate_content(context)
            if resp.text:
                logger.info("Recomendaciones generadas con Gemini Flash")
                return [line.strip() for line in resp.text.strip().splitlines() if line.strip()][:5]
    except Exception as e:
        logger.debug(f"Gemini recommendations failed: {e}")

    # Fallback estático
    recs = []
    if missing_pkgs:
        recs.append(f"Instalar paquetes de alto impacto: {', '.join(missing_pkgs[:3])}")
    recs.append("Ejecutar nexo_evolution.py para búsqueda autónoma de mejoras")
    recs.append("Revisar logs/evolution_proposals.json para propuestas pendientes")
    if errors:
        recs.append(f"Resolver error recurrente: {errors[0][:100]}")
    return recs[:5]


def _compute_innovation_score(
    pkg_coverage: float,
    integration_coverage: float,
    errors_count: int,
) -> float:
    """Score 0-100 de madurez de innovación del sistema."""
    score = (pkg_coverage * 0.35) + (integration_coverage * 0.35) + (max(0, 1 - errors_count / 10) * 30)
    return round(min(100.0, max(0.0, score)), 1)


def run_scout() -> dict[str, Any]:
    """Ejecuta el escaneo de innovación completo."""
    started = time.time()
    logger.info("Iniciando NEXO Innovation Scout...")

    installed = _check_installed_packages()
    active_integrations = _check_active_integrations()

    missing_pkgs = [p for p, ok in installed.items() if not ok]
    inactive_integrations = [n for n, ok in active_integrations.items() if not ok]
    errors = _check_recent_errors()
    py_files = _count_py_files()

    pkg_coverage = ((len(installed) - len(missing_pkgs)) / len(installed) * 100) if installed else 0
    integ_coverage = ((len(active_integrations) - len(inactive_integrations)) / len(active_integrations) * 100) if active_integrations else 0

    recommendations = _generate_recommendations_with_ai(missing_pkgs, inactive_integrations, errors)
    innovation_score = _compute_innovation_score(pkg_coverage, integ_coverage, len(errors))

    result: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_ms": int((time.time() - started) * 1000),
        "innovation_score": innovation_score,
        "recommendations": recommendations,
        "integrations": {
            "missing_packages": missing_pkgs,
            "inactive_integrations": inactive_integrations,
            "package_coverage_percent": round(pkg_coverage, 1),
            "integration_coverage_percent": round(integ_coverage, 1),
        },
        "updates": {
            "count": len(missing_pkgs),
            "packages_detail": {p: RECOMMENDED_PACKAGES[p] for p in missing_pkgs},
        },
        "codebase": {
            "python_files": py_files,
            "recent_errors_count": len(errors),
        },
    }

    output_path = LOG_DIR / "innovation_scout_last.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "Scout completado: score=%.1f  paquetes_faltantes=%d  recomendaciones=%d",
        innovation_score,
        len(missing_pkgs),
        len(recommendations),
    )
    return result


if __name__ == "__main__":
    result = run_scout()
    logger.info(json.dumps(result, ensure_ascii=False, indent=2))
