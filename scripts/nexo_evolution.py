#!/usr/bin/env python3
# ============================================================
# NEXO SOBERANO — Motor de Evolución Autónoma v1.0
# © 2026 elanarcocapital.com
#
# El sistema busca, evalúa y aplica mejoras de forma continua
# con iniciativa propia, usando Gemma 4 como cerebro.
#
# Ciclos automáticos:
#   CICLO RÁPIDO (cada 6h)   — errores, fixes nivel 1, salud
#   CICLO DIARIO (cada 24h)  — búsqueda de repos/herramientas,
#                              propuestas de mejora
#   CICLO SEMANAL (cada 7d)  — evolución profunda, arquitectura,
#                              reporte de progreso
#
# Uso:
#   python scripts/nexo_evolution.py            # ciclo manual completo
#   python scripts/nexo_evolution.py --fast     # solo ciclo rápido
#   python scripts/nexo_evolution.py --search   # solo búsqueda de repos
#   python scripts/nexo_evolution.py --report   # reporte de evolución
#   python scripts/nexo_evolution.py --watch    # modo continuo
# ============================================================
from __future__ import annotations
import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [EVOLUCIÓN] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexo.evolution")

EVOLUTION_LOG   = ROOT / "logs" / "evolution_history.json"
PROPOSALS_FILE  = ROOT / "logs" / "evolution_proposals.json"
STATE_FILE      = ROOT / "logs" / "evolution_state.json"

PYTHON = os.getenv("NEXO_PYTHON", sys.executable)

# ── REPOS/HERRAMIENTAS DE BÚSQUEDA INICIAL ────────────────────────────────────
# Gemma 4 ampliará esta lista con sus propios hallazgos
SEED_SEARCHES = [
    # OSINT / Inteligencia
    "awesome osint python site:github.com",
    "geopolitical intelligence fastapi",
    "real-time threat intelligence api python",
    "osint automation tool 2025 site:github.com",
    # AI / Local models
    "ollama fastapi integration python",
    "local llm agent python autonomous",
    "gemma fine-tuning osint",
    # Visualización
    "globe.gl real-time data visualization",
    "3d geospatial python fastapi websocket",
    # Sistemas
    "autonomous agent supervisor python",
    "self-healing microservice python",
    "progressive code improvement ai",
]

# Categorías de mejora que busca proactivamente
IMPROVEMENT_CATEGORIES = {
    "osint":         "Herramientas OSINT, rastreo, inteligencia de fuentes abiertas",
    "ai_local":      "Modelos locales, fine-tuning, inference optimization",
    "visualization": "Visualización 3D, mapas, globos interactivos",
    "security":      "Seguridad, auditoría, protección de agentes",
    "performance":   "Optimización, caché, async patterns",
    "automation":    "Automatización, workflows, self-healing",
    "integration":   "Conectores, bridges, APIs nuevas relevantes",
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _run(cmd: list, timeout: int = 30) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)


def _load_json(path: Path) -> list | dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        return []


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _banner(msg: str):
    print(f"\n{'━'*64}\n  {msg}\n{'━'*64}")


async def _gemma(prompt: str, system: str = "", modelo: str = "general", max_tokens: int = 1024) -> str:
    """Llama a Gemma 4 directamente. Costo: $0."""
    try:
        from NEXO_CORE.services.ollama_service import ollama_service
        resp = await ollama_service.consultar(
            prompt=prompt, modelo=modelo, system=system,
            temperature=0.2, max_tokens=max_tokens,
        )
        return resp.text if resp.success else ""
    except Exception as e:
        logger.warning(f"Gemma no disponible: {e}")
        return ""


# ── CICLO RÁPIDO: salud + auto-fixes ─────────────────────────────────────────

async def ciclo_rapido() -> dict:
    """
    Cada 6h:
    - Verifica salud de servicios
    - Aplica auto-fixes de nivel 1 (ruff, black) sin preguntar
    - Detecta errores recientes en logs y los analiza con Gemma 4
    - Guarda estado
    """
    _banner("CICLO RÁPIDO — Salud + Auto-fixes nivel 1")
    resultado = {"ts": datetime.now(timezone.utc).isoformat(), "tipo": "rapido", "acciones": []}

    # 1. Ruff auto-fix (nivel 1, sin intervención)
    rc, out = _run([PYTHON, "-m", "ruff", "check", "--fix", "backend", "NEXO_CORE", "-q"])
    if rc == 0:
        print("  ✓ Ruff auto-fix: OK")
        resultado["acciones"].append("ruff_autofix: OK")
    else:
        print(f"  ⚠ Ruff: {out[:100]}")
        resultado["acciones"].append(f"ruff_autofix: issues — {out[:80]}")

    # 2. Leer errores de logs recientes
    errores = []
    log_file = ROOT / "logs" / "nexo.log"
    if log_file.exists():
        lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        errores = [l for l in lines if "ERROR" in l or "CRITICAL" in l][-15:]

    if errores:
        print(f"  → {len(errores)} errores recientes detectados, analizando con Gemma 4...")
        analisis = await _gemma(
            prompt=f"Errores del sistema NEXO SOBERANO (últimas 24h):\n{''.join(errores)}",
            system=(
                "Analiza estos errores de sistema y responde en formato:\n"
                "CAUSA PROBABLE: ...\n"
                "ACCIÓN INMEDIATA: ...\n"
                "PRIORIDAD: ALTA/MEDIA/BAJA"
            ),
            max_tokens=300,
        )
        if analisis:
            print(f"  Gemma 4:\n{analisis}")
            resultado["analisis_errores"] = analisis
    else:
        print("  ✓ Sin errores críticos en logs")

    # 3. Verificar servicios básicos
    import aiohttp
    checks = {"ollama": "http://localhost:11434/api/tags", "nexo": "http://localhost:8000/health"}
    for name, url in checks.items():
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=3)) as r:
                    status = "✓ OK" if r.status == 200 else f"⚠ HTTP {r.status}"
        except Exception:
            status = "✗ Offline"
        print(f"  {status}  {name}")
        resultado["acciones"].append(f"health_{name}: {status}")

    # 4. Context Engine: actualizar caché
    try:
        from NEXO_CORE.services.context_engine import context_engine
        files = context_engine.scan_project()
        print(f"  ✓ Context Engine: {len(files)} archivos indexados")
        resultado["context_files"] = len(files)
    except Exception as e:
        logger.warning(f"Context scan: {e}")

    _save_json(STATE_FILE, resultado)
    return resultado


# ── BÚSQUEDA DE REPOS / HERRAMIENTAS ─────────────────────────────────────────

async def buscar_herramientas(categoria: str | None = None) -> list[dict]:
    """
    Gemma 4 genera búsquedas relevantes, evalúa resultados y
    propone integraciones. Completamente autónomo.
    """
    _banner(f"BÚSQUEDA DE HERRAMIENTAS — {categoria or 'todas las categorías'}")

    cats = {categoria: IMPROVEMENT_CATEGORIES[categoria]} if categoria else IMPROVEMENT_CATEGORIES
    propuestas = list(_load_json(PROPOSALS_FILE))

    for cat_key, cat_desc in cats.items():
        print(f"\n  Categoría: {cat_key} — {cat_desc}")

        # Gemma 4 genera términos de búsqueda específicos para el estado actual del sistema
        terminos_prompt = f"""
Sistema: NEXO SOBERANO (FastAPI + Gemma 4 local + Qdrant + OmniGlobe 3D + TheBigBrother OSINT)
Categoría de mejora: {cat_key} — {cat_desc}
Stack actual: Python 3.11, FastAPI, React 18, Gemma 4, Ollama, Qdrant, aiohttp

Genera 3 queries específicos para buscar en GitHub repos relevantes para mejorar NEXO.
Responde SOLO las 3 queries, una por línea, sin numeración ni markdown.
"""
        queries_text = await _gemma(terminos_prompt, max_tokens=150)
        queries = [q.strip() for q in (queries_text or "").splitlines() if q.strip()][:3]
        if not queries:
            queries = [f"{cat_key} python fastapi 2025"]

        for query in queries:
            print(f"  Buscando: {query}")
            # Gemma 4 evalúa si la herramienta es relevante y cómo integrarla
            eval_prompt = f"""
Contexto NEXO SOBERANO:
- Backend FastAPI Python con Gemma 4 local (Ollama)
- OSINT con TheBigBrother
- Visualización 3D OmniGlobe (globe.gl)
- Router IA: Gemma 4 → Gemini Flash → Claude Sonnet
- Búsqueda actual: "{query}"

Basándote en tu conocimiento de repos de GitHub y herramientas Python de 2024-2026,
sugiere 1-2 repositorios o librerías concretas que mejoren esta categoría del sistema.

Para cada uno, responde en formato JSON array:
[{{"nombre": "...", "github": "...", "descripcion": "...", "integracion": "...", "nivel_complejidad": 1|2|3, "prioridad": "alta|media|baja"}}]

Solo el JSON, sin markdown.
"""
            eval_text = await _gemma(eval_prompt, max_tokens=400)

            # Parsear propuestas de Gemma 4
            try:
                m = re.search(r'\[.*\]', eval_text, re.DOTALL)
                if m:
                    nuevas = json.loads(m.group())
                    for p in nuevas:
                        p["categoria"] = cat_key
                        p["ts"] = datetime.now(timezone.utc).isoformat()
                        p["estado"] = "pendiente"
                        p["fuente"] = "gemma4_autonomous"
                        # Evitar duplicados por nombre
                        if not any(ex.get("nombre") == p.get("nombre") for ex in propuestas):
                            propuestas.append(p)
                            print(f"  + {p.get('nombre')} [{p.get('prioridad', '?')} prioridad]")
            except Exception:
                pass

        await asyncio.sleep(1)  # No saturar Ollama

    _save_json(PROPOSALS_FILE, propuestas)
    print(f"\n  Total propuestas acumuladas: {len(propuestas)}")
    return propuestas


# ── APLICAR MEJORAS PROGRESIVAS ───────────────────────────────────────────────

async def aplicar_mejoras_progresivas(solo_nivel: int | None = None) -> dict:
    """
    Toma propuestas pendientes y las aplica en orden de prioridad.
    Solo aplica automáticamente nivel 1 y 2.
    Nivel 3 → lista para aprobación humana.
    """
    _banner("APLICAR MEJORAS PROGRESIVAS")

    propuestas: list[dict] = _load_json(PROPOSALS_FILE)
    pendientes = [p for p in propuestas if p.get("estado") == "pendiente"]

    if not pendientes:
        print("  Sin propuestas pendientes.")
        return {"aplicadas": 0, "pendientes_aprobacion": 0}

    # Ordenar por prioridad
    prio_map = {"alta": 0, "media": 1, "baja": 2}
    pendientes.sort(key=lambda p: (prio_map.get(p.get("prioridad", "media"), 1), p.get("nivel_complejidad", 2)))

    aplicadas = 0
    esperan_aprobacion = []

    from NEXO_CORE.services.context_engine import context_engine
    context_engine.scan_project()

    for prop in pendientes[:10]:  # Máximo 10 por ciclo
        nivel = prop.get("nivel_complejidad", 2)
        nombre = prop.get("nombre", "?")

        if solo_nivel and nivel != solo_nivel:
            continue

        print(f"\n  → {nombre} (nivel {nivel}, {prop.get('prioridad')} prioridad)")
        print(f"    {prop.get('descripcion', '')[:80]}")

        if nivel == 1:
            # NIVEL 1: Aplicar automáticamente (solo dependencias/config)
            integracion = prop.get("integracion", "")
            if "pip install" in integracion.lower() or "requirements" in integracion.lower():
                # Extraer nombre del paquete
                pkg_match = re.search(r'pip install ([\w\-]+)', integracion, re.I)
                if pkg_match:
                    pkg = pkg_match.group(1)
                    print(f"    Instalando {pkg}...")
                    rc, out = _run([PYTHON, "-m", "pip", "install", pkg, "-q"])
                    if rc == 0:
                        prop["estado"] = "aplicada"
                        prop["aplicada_ts"] = datetime.now(timezone.utc).isoformat()
                        aplicadas += 1
                        print(f"    ✓ Instalado: {pkg}")
                    else:
                        print(f"    ⚠ Error: {out[:80]}")
            else:
                prop["estado"] = "aplica_manual"
                print(f"    → Integración manual: {integracion[:100]}")

        elif nivel == 2:
            # NIVEL 2: Generar plan de implementación con Gemma 4 y pedir confirmación
            plan = await _gemma(
                prompt=f"Herramienta: {nombre}\nDescripción: {prop.get('descripcion')}\nGitHub: {prop.get('github', 'N/A')}\n"
                       f"Integración sugerida: {prop.get('integracion', '')}\n\n"
                       f"Genera un plan de implementación de 3 pasos concretos para integrar esto en NEXO SOBERANO. "
                       f"Considerar que ya existe: FastAPI, Gemma 4 local, Qdrant, OmniGlobe, BigBrother bridge.",
                system="Arquitecto técnico de NEXO SOBERANO. Da pasos concretos y verificables.",
                max_tokens=400,
            )
            prop["plan_implementacion"] = plan
            prop["estado"] = "listo_para_implementar"
            esperan_aprobacion.append(prop)
            print(f"    Plan generado — esperando aprobación")

        else:
            # NIVEL 3: Solo documentar y notificar
            prop["estado"] = "requiere_aprobacion_manual"
            esperan_aprobacion.append(prop)
            print(f"    [NIVEL 3] Requiere aprobación manual de Claude Code")

    # Guardar estado actualizado
    for prop in propuestas:
        next_prop = next((p for p in pendientes if p.get("nombre") == prop.get("nombre")), None)
        if next_prop:
            prop.update(next_prop)
    _save_json(PROPOSALS_FILE, propuestas)

    print(f"\n  Aplicadas automáticamente: {aplicadas}")
    print(f"  Esperan aprobación: {len(esperan_aprobacion)}")
    return {"aplicadas": aplicadas, "pendientes_aprobacion": len(esperan_aprobacion)}


# ── REPORTE DE EVOLUCIÓN ──────────────────────────────────────────────────────

async def generar_reporte() -> str:
    """
    Reporte completo de la evolución del sistema.
    Gemma 4 analiza tendencias y propone la dirección estratégica.
    """
    _banner("REPORTE DE EVOLUCIÓN NEXO SOBERANO")

    history: list[dict] = _load_json(EVOLUTION_LOG)
    proposals: list[dict] = _load_json(PROPOSALS_FILE)

    # Estadísticas
    total_props = len(proposals)
    aplicadas   = len([p for p in proposals if p.get("estado") == "aplicada"])
    pendientes  = len([p for p in proposals if "pendiente" in p.get("estado", "")])
    alta_prio   = [p for p in proposals if p.get("prioridad") == "alta" and p.get("estado") in ("pendiente", "listo_para_implementar")]

    try:
        from NEXO_CORE.services.context_engine import context_engine
        ctx_stats = context_engine.get_stats()
    except Exception:
        ctx_stats = {}

    resumen = {
        "propuestas_total": total_props,
        "aplicadas": aplicadas,
        "pendientes": pendientes,
        "alta_prioridad": [p.get("nombre") for p in alta_prio[:5]],
        "categorias": list({p.get("categoria") for p in proposals}),
        "context_stats": ctx_stats,
        "ciclos_ejecutados": len(history),
    }

    print(f"  Total propuestas: {total_props}")
    print(f"  Aplicadas: {aplicadas}")
    print(f"  Pendientes: {pendientes}")
    if alta_prio:
        print(f"\n  Alta prioridad:")
        for p in alta_prio[:5]:
            print(f"    - {p.get('nombre')} [{p.get('categoria')}]: {p.get('descripcion', '')[:60]}")

    # Análisis estratégico con Gemma 4
    analisis = await _gemma(
        prompt=json.dumps(resumen, ensure_ascii=False, indent=2),
        system=(
            "Eres el estratega de NEXO SOBERANO. Analiza el estado de evolución del sistema y genera:\n"
            "## Análisis de evolución\n"
            "**Estado actual:** ...\n"
            "**Tendencias detectadas:** ...\n"
            "**Próximas 3 acciones prioritarias:**\n"
            "1. ...\n2. ...\n3. ...\n"
            "**Visión 30 días:** ...\n"
            "Responde en español, sé directo y estratégico."
        ),
        max_tokens=600,
    )

    if analisis:
        print(f"\n{analisis}")

    # Guardar reporte
    reporte = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stats": resumen,
        "analisis_gemma4": analisis,
    }
    report_path = ROOT / "logs" / f"evolution_report_{datetime.now().strftime('%Y%m%d')}.json"
    _save_json(report_path, reporte)
    print(f"\n  Reporte guardado: {report_path.name}")
    return analisis or ""


# ── CICLO COMPLETO ────────────────────────────────────────────────────────────

async def ciclo_completo():
    """Ciclo de evolución completo: rápido + búsqueda + aplicar + reporte."""
    history = list(_load_json(EVOLUTION_LOG))

    ts_inicio = datetime.now(timezone.utc)
    r_rapido   = await ciclo_rapido()
    r_busqueda = await buscar_herramientas()
    r_mejoras  = await aplicar_mejoras_progresivas()
    r_reporte  = await generar_reporte()

    entry = {
        "ts": ts_inicio.isoformat(),
        "duracion_s": (datetime.now(timezone.utc) - ts_inicio).seconds,
        "rapido":   r_rapido.get("acciones", []),
        "busqueda": len(r_busqueda),
        "mejoras":  r_mejoras,
    }
    history.append(entry)
    history = history[-100:]
    _save_json(EVOLUTION_LOG, history)
    _banner("EVOLUCIÓN COMPLETADA")


# ── MODO CONTINUO ─────────────────────────────────────────────────────────────

async def modo_watch(interval_rapido: int = 21600, interval_completo: int = 86400):
    """
    Bucle de evolución autónoma.
    Ciclo rápido cada 6h, completo cada 24h.
    """
    _banner("NEXO EVOLUTION — Modo Watch Autónomo")
    print(f"  Ciclo rápido: cada {interval_rapido//3600}h")
    print(f"  Ciclo completo: cada {interval_completo//3600}h")

    last_full = 0.0
    while True:
        try:
            now = time.time()
            if now - last_full >= interval_completo:
                await ciclo_completo()
                last_full = now
            else:
                await ciclo_rapido()
        except KeyboardInterrupt:
            print("\n  Evolution watch detenido.")
            break
        except Exception as e:
            logger.error(f"Evolution error: {e}")
        await asyncio.sleep(interval_rapido)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NEXO — Motor de Evolución Autónoma")
    parser.add_argument("--fast",   action="store_true", help="Solo ciclo rápido (salud + fixes)")
    parser.add_argument("--search", help="Solo búsqueda [categoria: osint|ai_local|visualization|...]")
    parser.add_argument("--apply",  action="store_true", help="Aplicar mejoras pendientes")
    parser.add_argument("--report", action="store_true", help="Generar reporte de evolución")
    parser.add_argument("--watch",  action="store_true", help="Modo continuo autónomo")
    parser.add_argument("--full",   action="store_true", help="Ciclo completo (default)")
    args = parser.parse_args()

    if args.watch:
        asyncio.run(modo_watch())
    elif args.fast:
        asyncio.run(ciclo_rapido())
    elif args.search:
        cat = args.search if args.search in IMPROVEMENT_CATEGORIES else None
        asyncio.run(buscar_herramientas(cat))
    elif args.apply:
        asyncio.run(aplicar_mejoras_progresivas())
    elif args.report:
        asyncio.run(generar_reporte())
    else:
        asyncio.run(ciclo_completo())


if __name__ == "__main__":
    main()
