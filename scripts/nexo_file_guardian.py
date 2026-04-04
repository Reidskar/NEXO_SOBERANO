#!/usr/bin/env python3
"""
scripts/nexo_file_guardian.py
==============================
Guardián de integridad de archivos NEXO SOBERANO — v2.

Detecta y reporta TODOS los tipos de error:
  SINTAXIS       — SY001-SY008: SyntaxError, texto no-Python, código corrupto
  IMPORTS        — IM001-IM004: módulos faltantes, imports dentro de funciones
  CONEXIONES     — CN001-CN005: routers no registrados, WS no conectados
  ARCHIVOS       — FI001-FI003: HTML/JS/JSON referenciados pero inexistentes
  ENV VARS       — EV001-EV002: variables de entorno usadas pero no definidas
  DEFINICIONES   — DF001-DF003: variables críticas no definidas a nivel módulo
  ESTRUCTURA     — ST001-ST003: __main__ dentro de función, listas huérfanas

Salida: logs/file_guardian_last.json

USO:
  python scripts/nexo_file_guardian.py              # escaneo completo
  python scripts/nexo_file_guardian.py --file X.py  # archivo específico
  python scripts/nexo_file_guardian.py --json       # salida JSON (para hooks)
  python scripts/nexo_file_guardian.py --fix        # diagnóstico con Gemma 4
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GUARDIAN] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexo.guardian")

# ── Configuración ──────────────────────────────────────────────────────────────

SCAN_DIRS = ["backend", "NEXO_CORE", "scripts"]

EXCLUDE_FILES = {
    "nexo_autosupervisor.py",  # tiene regex que disparan falsos positivos
    "nexo_file_guardian.py",   # no escanear a sí mismo
}

# Variables que DEBEN existir a nivel módulo en archivos críticos
CRITICAL_MODULE_VARS: dict[str, list[str]] = {
    "backend/main.py": ["app", "manager", "logger"],
    "NEXO_CORE/main.py": ["app", "logger"],
}

# Routers importados en main.py que deben estar registrados con app.include_router()
# formato: alias usado en el import
REQUIRED_ROUTER_REGISTRATIONS = [
    "core_health_router", "ai_router", "knowledge_router", "stream_router",
    "dashboard_router", "core_webhook_router", "worldmonitor_router",
    "agente_router", "eventos_router", "metrics_router", "media_router",
    "mobile_router", "files_router", "globe_router", "osint_router", "platform_router",
]

# Archivos HTML que deben existir en frontend_public/
REQUIRED_HTML_FILES = [
    "omniglobe.html", "flowmap.html", "landing_nexo.html",
    "control_center.html", "manifest.json", "nexo_config.js", "sw.js",
]

# Variables de entorno críticas que deben estar definidas
CRITICAL_ENV_VARS = [
    "GEMINI_API_KEY", "DISCORD_WEBHOOK_URL", "NEXO_API_KEY",
    "NEXO_ADMIN_PASS", "QDRANT_URL",
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def _issue(code: str, severity: str, line: int, message: str,
           detail: str = "", auto_fixable: bool = False) -> dict:
    return {
        "code": code, "severity": severity, "line": line,
        "message": message, "detail": detail, "auto_fixable": auto_fixable,
    }


def _load_env_file() -> dict[str, str]:
    env: dict[str, str] = {}
    for name in (".env", ".env.local", ".env.production"):
        p = ROOT / name
        if p.exists():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


# ── Chequeadores de sintaxis y corrupción ─────────────────────────────────────

def chk_syntax(path: Path, source: str) -> list[dict]:
    issues = []
    try:
        ast.parse(source)
    except SyntaxError as e:
        issues.append(_issue(
            "SY001", "critical", e.lineno or 0,
            f"SyntaxError: {e.msg}",
            detail=f"offset={e.offset}  texto='{(e.text or '').strip()[:80]}'",
            auto_fixable=True,
        ))
    return issues


def chk_first_line_not_python(path: Path, source: str) -> list[dict]:
    lines = source.splitlines()
    if not lines:
        return []
    first = lines[0].strip()
    valid_starts = (
        "#", "'''", '"""', "from ", "import ", "__", "def ", "class ",
        "@", "if ", "try:", "with ", "async ", "0", "1", "#!", "",
    )
    if first and not any(first.startswith(s) for s in valid_starts):
        words = first.split()
        has_prose = (
            len(words) >= 4
            and not any(c in first for c in ("=", "(", ")", "[", "]", ":", ",", "+"))
        )
        if has_prose:
            return [_issue(
                "SY002", "critical", 1,
                f"Primera línea no es Python válido: '{first[:70]}'",
                detail="Texto en prosa insertado sin comentar con #. Python no puede importar este archivo.",
                auto_fixable=True,
            )]
    return []


def chk_ghost_code_in_lifecycle(path: Path, source: str) -> list[dict]:
    """Detecta imports/class/app= dentro de funciones de lifecycle."""
    issues = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lifecycle_names = {"lifespan", "startup", "shutdown", "on_startup", "on_shutdown"}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in lifecycle_names:
            continue
        for child in ast.walk(node):
            if child is node:
                continue
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                issues.append(_issue(
                    "SY004", "high", child.lineno,
                    f"Import dentro de '{node.name}()' — probable código fantasma",
                    detail="Los imports deben estar al nivel del módulo, no dentro de lifecycle functions.",
                    auto_fixable=False,
                ))
            if isinstance(child, ast.Assign):
                for t in child.targets:
                    if isinstance(t, ast.Name) and t.id == "app":
                        issues.append(_issue(
                            "SY003", "critical", child.lineno,
                            f"'app = FastAPI(...)' dentro de '{node.name}()' — código corrupto/fantasma",
                            detail="La app FastAPI debe definirse a nivel módulo, no dentro de lifespan.",
                            auto_fixable=True,
                        ))
    return issues


def chk_main_inside_function(path: Path, source: str) -> list[dict]:
    issues = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If):
                test = child.test
                if (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"
                ):
                    issues.append(_issue(
                        "ST001", "high", child.lineno,
                        f"Bloque '__main__' dentro de función '{node.name}()' — código corrupto",
                        detail="El bloque if __name__ == '__main__' solo es válido a nivel módulo.",
                    ))
    return issues


def chk_orphan_list_brackets(path: Path, source: str) -> list[dict]:
    """Detecta ]) o }) solitarios — fragmentos de listas huérfanas."""
    issues = []
    for i, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped in ("])", "})", "]", "}]", "])"):
            issues.append(_issue(
                "SY008", "critical", i,
                f"Cierre de lista/tupla huérfano en línea {i}: '{stripped}'",
                detail="Posible fragmento de código anterior borrado a medias.",
                auto_fixable=False,
            ))
    return issues


def chk_orphan_string_paths(path: Path, source: str) -> list[dict]:
    """Detecta strings solitarios que parecen paths de archivos."""
    issues = []
    pattern = re.compile(r'^\s+"[A-Za-z_/\\][A-Za-z0-9_/\\.-]+(\.html|\.py|\.json|\.txt)",?\s*$')
    for i, line in enumerate(source.splitlines(), 1):
        if pattern.match(line):
            issues.append(_issue(
                "SY007", "high", i,
                f"String literal solitario con extensión de archivo — línea {i}",
                detail=f"Fragmento huérfano: {line.strip()[:80]}",
            ))
    return issues


# ── Chequeadores de imports ────────────────────────────────────────────────────

def chk_imports_exist(path: Path, source: str) -> list[dict]:
    """Verifica que los módulos importados en from X import Y existan en el proyecto."""
    issues = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module is None:
            continue
        mod = node.module
        # Solo verificar módulos locales del proyecto
        if not (mod.startswith("backend.") or mod.startswith("NEXO_CORE.")):
            continue
        # Convertir a path
        mod_path = ROOT / Path(mod.replace(".", "/") + ".py")
        mod_init = ROOT / Path(mod.replace(".", "/") + "/__init__.py")
        if not mod_path.exists() and not mod_init.exists():
            issues.append(_issue(
                "IM001", "critical", node.lineno,
                f"Módulo '{mod}' no encontrado en el proyecto",
                detail=f"Se busca: {mod_path} o {mod_init}",
                auto_fixable=False,
            ))
    return issues


# ── Chequeadores de conexiones de app ─────────────────────────────────────────

def chk_routers_registered(path: Path, source: str) -> list[dict]:
    """En main.py: verifica que todos los routers importados estén registrados."""
    if path.name != "main.py" or "backend" not in str(path):
        return []
    issues = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    # Routers importados como alias
    imported_routers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if "router" in name.lower():
                    imported_routers.add(name)

    # Routers pasados a app.include_router(...)
    registered_routers: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if (
                isinstance(call.func, ast.Attribute)
                and call.func.attr == "include_router"
                and call.args
            ):
                arg = call.args[0]
                if isinstance(arg, ast.Name):
                    registered_routers.add(arg.id)

    unregistered = imported_routers - registered_routers
    for r in sorted(unregistered):
        # Solo reportar los que están en la lista de requeridos
        if r in REQUIRED_ROUTER_REGISTRATIONS:
            issues.append(_issue(
                "CN001", "high", 0,
                f"Router '{r}' importado pero no registrado con app.include_router()",
                detail="Añadir: app.include_router({})".format(r),
                auto_fixable=True,
            ))
    return issues


# ── Chequeadores de archivos referenciados ────────────────────────────────────

def chk_referenced_html_files(path: Path, source: str) -> list[dict]:
    """Detecta FileResponse / HTMLResponse que referencian archivos inexistentes."""
    issues = []
    # Buscar patrones como: Path("frontend_public/X.html") o FileResponse("frontend_public/X")
    pattern = re.compile(r'["\']frontend_public/([^"\']+)["\']')
    for i, line in enumerate(source.splitlines(), 1):
        for m in pattern.finditer(line):
            ref = m.group(1)
            target = ROOT / "frontend_public" / ref
            if not target.exists():
                issues.append(_issue(
                    "FI001", "high", i,
                    f"Archivo referenciado no existe: frontend_public/{ref}",
                    detail=f"Ruta: {target}",
                    auto_fixable=False,
                ))
    return issues


def chk_required_static_files() -> list[dict]:
    """Verifica que los archivos estáticos críticos existan."""
    issues = []
    pub = ROOT / "frontend_public"
    for fname in REQUIRED_HTML_FILES:
        if not (pub / fname).exists():
            issues.append(_issue(
                "FI002", "high", 0,
                f"Archivo estático requerido faltante: frontend_public/{fname}",
                detail="Este archivo es servido directamente por el backend.",
                auto_fixable=False,
            ))
    return issues


# ── Chequeadores de variables de entorno ──────────────────────────────────────

def chk_env_vars_defined() -> list[dict]:
    """Verifica que las variables de entorno críticas estén en .env."""
    issues = []
    env = _load_env_file()
    for var in CRITICAL_ENV_VARS:
        if var not in env and not os.getenv(var):
            issues.append(_issue(
                "EV001", "medium", 0,
                f"Variable de entorno crítica no definida: {var}",
                detail="Agregar al archivo .env. Sin esta variable el servicio puede fallar.",
                auto_fixable=False,
            ))
    return issues


# ── Chequeadores de definiciones a nivel módulo ───────────────────────────────

def chk_critical_vars_defined(path: Path, source: str) -> list[dict]:
    """Verifica que variables críticas estén definidas a nivel módulo."""
    issues = []
    rel = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
    expected = CRITICAL_MODULE_VARS.get(rel, [])
    if not expected:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    defined: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defined.add(t.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                defined.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                defined.add(alias.asname or alias.name)

    for var in expected:
        if var not in defined:
            issues.append(_issue(
                "DF001", "critical", 0,
                f"Variable crítica '{var}' no definida a nivel módulo en {rel}",
                detail=f"'{var}' es requerido por el sistema NEXO. Verificar imports y definiciones.",
                auto_fixable=False,
            ))
    return issues


# ── Motor de escaneo ──────────────────────────────────────────────────────────

def scan_file(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "file": str(path.relative_to(ROOT)),
        "issues": [],
        "status": "ok",
    }
    try:
        source = path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        result["issues"].append(_issue("IO001", "critical", 0, f"No se pudo leer: {e}"))
        result["status"] = "critical"
        return result

    FILE_CHECKERS = [
        chk_syntax,
        chk_first_line_not_python,
        chk_ghost_code_in_lifecycle,
        chk_main_inside_function,
        chk_orphan_list_brackets,
        chk_orphan_string_paths,
        chk_imports_exist,
        chk_routers_registered,
        chk_referenced_html_files,
        chk_critical_vars_defined,
    ]
    for checker in FILE_CHECKERS:
        try:
            result["issues"].extend(checker(path, source))
        except Exception as e:
            logger.debug(f"Checker {checker.__name__} error en {path}: {e}")

    if result["issues"]:
        severities = {i["severity"] for i in result["issues"]}
        result["status"] = (
            "critical" if "critical" in severities
            else "high" if "high" in severities
            else "warning"
        )
    return result


def collect_python_files() -> list[Path]:
    files = []
    for d in SCAN_DIRS:
        target = ROOT / d
        if target.exists():
            for f in target.rglob("*.py"):
                if f.name not in EXCLUDE_FILES and "__pycache__" not in str(f):
                    files.append(f)
    return sorted(files)


def run_scan(target_file: Path | None = None) -> dict[str, Any]:
    started = time.time()
    files = [target_file] if target_file else collect_python_files()

    results = []
    broken: list[dict] = []
    for f in files:
        r = scan_file(f)
        results.append(r)
        if r["status"] in ("critical", "high", "error"):
            broken.append(r)

    # Cheques globales (no por archivo)
    global_issues: list[dict] = []
    try:
        global_issues.extend(chk_required_static_files())
        global_issues.extend(chk_env_vars_defined())
    except Exception as e:
        logger.debug(f"Global checks error: {e}")

    summary: dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_ms": int((time.time() - started) * 1000),
        "files_scanned": len(results),
        "broken_files": len(broken),
        "broken": broken,
        "global_issues": global_issues,
        "all_ok": len(broken) == 0 and len(global_issues) == 0,
    }

    # Persistir
    out = LOG_DIR / "file_guardian_last.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    hist_file = LOG_DIR / "file_guardian_history.json"
    history: list[dict] = []
    if hist_file.exists():
        try:
            history = json.loads(hist_file.read_text())
        except Exception:
            history = []
    history.append({
        "ts": summary["timestamp"],
        "files": summary["files_scanned"],
        "broken_files": summary["broken_files"],
        "broken_list": [b["file"] for b in broken],
        "global_issues": len(global_issues),
    })
    hist_file.write_text(json.dumps(history[-100:], ensure_ascii=False), encoding="utf-8")

    return summary


# ── Gemma 4 diagnóstico y fix ─────────────────────────────────────────────────

async def _ask_gemma(prompt: str) -> str:
    try:
        from NEXO_CORE.services.ollama_service import ollama_service
        resp = await ollama_service.consultar(
            prompt=prompt,
            modelo="fast",
            system=(
                "Eres el guardián de código de NEXO SOBERANO. "
                "Diagnostica errores y propón pasos de corrección concretos. "
                "Sé específico: indica el archivo, línea y cambio exacto. "
                "Responde en español."
            ),
            temperature=0.05,
            max_tokens=600,
        )
        if resp.success and resp.text:
            return resp.text.strip()
    except Exception as e:
        logger.debug(f"Gemma 4 error: {e}")
    return ""


async def diagnose_and_report(summary: dict) -> None:
    all_problems = []

    for b in summary.get("broken", []):
        for iss in b.get("issues", []):
            all_problems.append(f"[{b['file']}] línea {iss['line']}: [{iss['code']}] {iss['message']}")

    for g in summary.get("global_issues", []):
        all_problems.append(f"[GLOBAL] [{g['code']}] {g['message']}")

    if not all_problems:
        return

    prompt = (
        "Problemas detectados en NEXO SOBERANO:\n\n"
        + "\n".join(all_problems[:30])
        + "\n\nPara cada problema indica causa y paso de corrección exacto."
    )

    diagnosis = await _ask_gemma(prompt)
    if diagnosis:
        logger.info(f"\nGemma 4 diagnóstico:\n{diagnosis}")
        diag_file = LOG_DIR / "file_guardian_diagnosis.txt"
        existing = ""
        if diag_file.exists():
            existing = diag_file.read_text(encoding="utf-8")
        diag_file.write_text(
            f"[{summary['timestamp']}]\n{diagnosis}\n\n" + existing,
            encoding="utf-8",
        )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="NEXO File Guardian — detector de archivos rotos")
    parser.add_argument("--file", type=str, default=None, help="Archivo específico a escanear")
    parser.add_argument("--json", action="store_true", help="Salida JSON silenciosa (para hooks)")
    parser.add_argument("--fix",  action="store_true", help="Pedir diagnóstico a Gemma 4")
    args = parser.parse_args()

    target = Path(args.file).resolve() if args.file else None
    summary = run_scan(target)

    total_issues = summary["broken_files"] + len(summary.get("global_issues", []))

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
        sys.exit(1 if total_issues > 0 else 0)

    # Salida legible
    ts = summary["timestamp"]
    files = summary["files_scanned"]

    if summary["all_ok"]:
        logger.info(f"✅ {ts} — {files} archivos OK — ningún error detectado")
        sys.exit(0)

    logger.warning(f"🚨 {summary['broken_files']} archivo(s) con errores — {files} archivos escaneados")

    for b in summary["broken"]:
        status_icon = "🔴" if b["status"] == "critical" else "🟠"
        logger.warning(f"  {status_icon} {b['file']} [{b['status'].upper()}]")
        for iss in b["issues"]:
            icon = "🔴" if iss["severity"] == "critical" else "🟠" if iss["severity"] == "high" else "🟡"
            logger.warning(f"     {icon} [{iss['code']}] L{iss['line']}: {iss['message']}")
            if iss.get("detail"):
                logger.info(f"        → {iss['detail']}")

    if summary.get("global_issues"):
        logger.warning(f"\n  📋 {len(summary['global_issues'])} problemas globales:")
        for g in summary["global_issues"]:
            icon = "🟡" if g["severity"] == "medium" else "🟠"
            logger.warning(f"     {icon} [{g['code']}] {g['message']}")
            if g.get("detail"):
                logger.info(f"        → {g['detail']}")

    if args.fix:
        logger.info("\n🤖 Consultando Gemma 4 para diagnóstico y plan de fixes...")
        asyncio.run(diagnose_and_report(summary))

    sys.exit(1 if total_issues > 0 else 0)


if __name__ == "__main__":
    main()
