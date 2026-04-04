#!/usr/bin/env python3
# ============================================================
# NEXO SOBERANO — Clasificador de Complejidad de Tareas v1.0
# © 2026 elanarcocapital.com
#
# Usado por hooks de Claude Code para decidir quién ejecuta cada tarea:
#   NIVEL 1 (simple)  → VS Code / nexo_autosupervisor --fix
#   NIVEL 2 (medio)   → Antigravity (skills automatizadas)
#   NIVEL 3 (complejo)→ Claude Code (requiere autorización)
#
# Salida (stdout JSON):
#   {"nivel": 1, "label": "simple", "razon": "...", "herramienta": "vscode"}
#
# Uso:
#   python scripts/clasificar_tarea.py --tarea "formatea el archivo X"
#   python scripts/clasificar_tarea.py --tarea "agrega autenticación OAuth" --archivo "backend/routes/auth.py"
#   python scripts/clasificar_tarea.py --diff "$(git diff --staged)"
# ============================================================
from __future__ import annotations
import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── REGLAS DETERMINISTAS (sin IA, instantáneas) ───────────────────────────────

PATRONES_SIMPLE = [
    r"\b(format|formatea|lint|linting|black|ruff|isort|import)\b",
    r"\b(typo|typos|ortograf|espacio|whitespace|indent|indenta)\b",
    r"\b(docstring|comentario|comment|type hint|anotaci[oó]n)\b",
    r"\b(rename|renombra|variable name|nombre de variable)\b",
    r"\b(log|logging|print|debug|agrega log)\b",
    r"\b(test unit|unittest|pytest unit)\b",
    r"\badd\s+\w+\s+import\b",
    r"\bfix syntax\b",
    r"\bformato\b",
]

PATRONES_COMPLEJO = [
    r"\b(arquitectura|architecture|refactor completo|rewrite|reescribir)\b",
    r"\b(autenticaci[oó]n|oauth|jwt|auth|permisos|rbac)\b",
    r"\b(base de datos|database|migration|schema|modelo de datos)\b",
    r"\b(integrar|integration|nuevo servicio|new service|api externa)\b",
    r"\b(seguridad|security|vulnerabilidad|vulnerability|cve)\b",
    r"\b(multi.?file|m[uú]ltiples archivos|varios archivos)\b",
    r"\b(websocket|streaming|async architecture)\b",
    r"\b(deploy|desplegar|railway|docker|k8s|kubernetes)\b",
    r"\b(algoritmo complejo|complex algorithm|ml|machine learning)\b",
    r"\b(redise[ñn]ar|redesign|cambio mayor|major change)\b",
]

PATRONES_MEDIO = [
    r"\b(endpoint|ruta|route|handler)\b",
    r"\b(validaci[oó]n|validation|pydantic|schema)\b",
    r"\b(error handling|manejo de errores|exception)\b",
    r"\b(test integrac|integration test|e2e)\b",
    r"\b(cache|caché|redis)\b",
    r"\b(helper|utility|util|función auxiliar)\b",
]


def clasificar_reglas(tarea: str, archivo: str = "", diff: str = "") -> dict | None:
    """
    Clasificación rápida basada en regex.
    Retorna dict si hay match claro, None si necesita IA.
    """
    texto = (tarea + " " + archivo + " " + diff[:500]).lower()

    # Chequeo de tamaño del diff
    if diff:
        lineas = len([l for l in diff.splitlines() if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))])
        if lineas > 200:
            return {"nivel": 3, "label": "complejo", "razon": f"Diff grande ({lineas} líneas cambiadas)", "herramienta": "claude_code"}
        if lineas <= 15:
            # Diff pequeño — si no hay patrón complejo, es simple
            if not any(re.search(p, texto) for p in PATRONES_COMPLEJO):
                return {"nivel": 1, "label": "simple", "razon": f"Diff pequeño ({lineas} líneas)", "herramienta": "vscode"}

    # Patrones explícitos
    for p in PATRONES_COMPLEJO:
        if re.search(p, texto):
            return {"nivel": 3, "label": "complejo", "razon": f"Detectado patrón complejo: {p}", "herramienta": "claude_code"}

    for p in PATRONES_SIMPLE:
        if re.search(p, texto):
            return {"nivel": 1, "label": "simple", "razon": f"Detectado patrón simple: {p}", "herramienta": "vscode"}

    for p in PATRONES_MEDIO:
        if re.search(p, texto):
            return {"nivel": 2, "label": "medio", "razon": f"Detectado patrón medio: {p}", "herramienta": "antigravity"}

    return None   # Necesita IA para clasificar


async def clasificar_con_gemma(tarea: str, archivo: str = "", diff: str = "") -> dict:
    """Clasificación semántica con Gemma 4 cuando las reglas no son suficientes."""
    try:
        from NEXO_CORE.services.ollama_service import ollama_service

        system = (
            "Eres un clasificador de tareas de programación para NEXO SOBERANO. "
            "Clasifica la tarea en UNO de estos niveles:\n"
            "NIVEL 1 (simple): formateo, lint, typos, docstrings, renombrar variables, "
            "agregar logs, imports, cambios de 1-15 líneas sin lógica nueva.\n"
            "NIVEL 2 (medio): endpoint nuevo sencillo, validación, error handling, "
            "helper functions, tests unitarios, refactor de función individual.\n"
            "NIVEL 3 (complejo): arquitectura, autenticación, integraciones externas, "
            "seguridad, cambios multi-archivo, algoritmos, migraciones, despliegue.\n\n"
            "Responde ÚNICAMENTE con este JSON exacto (sin markdown):\n"
            '{"nivel": N, "label": "simple|medio|complejo", "razon": "explicacion breve"}'
        )

        contexto = f"Tarea: {tarea}"
        if archivo:
            contexto += f"\nArchivo: {archivo}"
        if diff:
            contexto += f"\nDiff (primeras 300 líneas):\n{diff[:1200]}"

        resp = await ollama_service.consultar(
            prompt=contexto, modelo="fast", system=system, temperature=0.0, max_tokens=100
        )

        if resp.success:
            text = resp.text.strip()
            # Extraer JSON del response
            m = re.search(r'\{[^}]+\}', text)
            if m:
                data = json.loads(m.group())
                nivel = int(data.get("nivel", 2))
                herramientas = {1: "vscode", 2: "antigravity", 3: "claude_code"}
                data["herramienta"] = herramientas.get(nivel, "claude_code")
                data["clasificador"] = "gemma4"
                return data
    except Exception as e:
        pass

    # Fallback: nivel 2 si no hay IA disponible
    return {
        "nivel": 2,
        "label": "medio",
        "razon": "Clasificación por defecto (Gemma 4 no disponible)",
        "herramienta": "antigravity",
        "clasificador": "fallback",
    }


async def clasificar(tarea: str, archivo: str = "", diff: str = "") -> dict:
    """Clasificación completa: reglas rápidas primero, Gemma 4 si necesario."""
    # 1. Intento con reglas (sin latencia)
    resultado = clasificar_reglas(tarea, archivo, diff)
    if resultado:
        resultado["clasificador"] = "reglas"
        return resultado
    # 2. Gemma 4 para casos ambiguos
    return await clasificar_con_gemma(tarea, archivo, diff)


def main():
    parser = argparse.ArgumentParser(description="Clasificador de complejidad de tareas NEXO")
    parser.add_argument("--tarea",  "-t", default="", help="Descripción de la tarea")
    parser.add_argument("--archivo","-f", default="", help="Archivo involucrado")
    parser.add_argument("--diff",   "-d", default="", help="Git diff del cambio")
    parser.add_argument("--json",   action="store_true", help="Solo output JSON (para hooks)")
    args = parser.parse_args()

    if not args.tarea and not args.diff:
        print(json.dumps({"nivel": 2, "label": "medio", "herramienta": "antigravity", "razon": "sin descripción"}))
        sys.exit(0)

    result = asyncio.run(clasificar(args.tarea, args.archivo, args.diff))

    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, ensure_ascii=False))
    else:
        nivel_icons = {1: "🟢", 2: "🟡", 3: "🔴"}
        herramienta_desc = {
            "vscode":      "VS Code / nexo_autosupervisor (automático)",
            "antigravity": "Antigravity skills (semiautomático)",
            "claude_code": "Claude Code (requiere autorización)",
        }
        icon = nivel_icons.get(result["nivel"], "⚪")
        tool = herramienta_desc.get(result["herramienta"], result["herramienta"])
        print(f"\n{icon}  NIVEL {result['nivel']} — {result['label'].upper()}")
        print(f"   Herramienta: {tool}")
        print(f"   Razón: {result['razon']}")
        print(f"   Clasificador: {result.get('clasificador', '?')}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
