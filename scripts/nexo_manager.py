#!/usr/bin/env python3
# ============================================================
# NEXO SOBERANO — Gestor Inteligente v1.0
# © 2026 elanarcocapital.com
#
# Motor: Gemma 4 local ($0/consulta)
#
# Comandos:
#   review    — Revisa código con Gemma 4 (git diff o archivo)
#   security  — Auditoría de seguridad profunda
#   fix       — Auto-corrige issues detectados
#   diagnose  — Diagnóstico completo del sistema
#   supervise — Monitoreo continuo (servicios + código)
#   status    — Estado rápido de todos los servicios
#
# Uso:
#   python scripts/nexo_manager.py review
#   python scripts/nexo_manager.py review --file backend/routes/osint.py
#   python scripts/nexo_manager.py security --file backend/services/big_brother_bridge.py
#   python scripts/nexo_manager.py fix --file backend/routes/osint.py --issue "missing auth guard"
#   python scripts/nexo_manager.py diagnose
#   python scripts/nexo_manager.py supervise --interval 120
#   python scripts/nexo_manager.py status
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
from datetime import datetime, timezone
from pathlib import Path

# Agrega el root al path para importar NEXO_CORE
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [MANAGER] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexo.manager")

NEXO_URL     = os.getenv("NEXO_URL",     "http://localhost:8000")
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
BB_URL       = os.getenv("BIGBROTHER_URL","http://localhost:8888")
NEXO_API_KEY = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")

PYTHON = os.getenv("NEXO_PYTHON", sys.executable)

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _banner(title: str, char: str = "━"):
    w = 62
    print(f"\n{char * w}")
    print(f"  {title}")
    print(f"{char * w}")


def _run_cmd(cmd: list[str], cwd: str = None) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=60, cwd=cwd or str(ROOT)
        )
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, "", str(e)


def _git_diff(staged_only: bool = False) -> str:
    args = ["git", "diff"]
    if staged_only:
        args.append("--cached")
    args.extend(["--", "*.py"])
    _, out, _ = _run_cmd(args)
    return out or ""


def _git_diff_file(filepath: str) -> str:
    _, out, _ = _run_cmd(["git", "diff", "HEAD", "--", filepath])
    if not out:
        # Si no hay diff (archivo nuevo o sin cambios), devuelve el contenido
        try:
            return Path(filepath).read_text(encoding="utf-8")[:12000]
        except Exception:
            return ""
    return out


def _read_file(filepath: str) -> str:
    try:
        return Path(filepath).read_text(encoding="utf-8")[:12000]
    except Exception as e:
        return f"Error leyendo archivo: {e}"


async def _get_ollama():
    from NEXO_CORE.services.ollama_service import ollama_service
    return ollama_service


# ── STATUS ────────────────────────────────────────────────────────────────────

async def cmd_status(args):
    import aiohttp

    _banner("NEXO SOBERANO — Estado de Servicios")

    services = {
        "nexo_backend":  f"{NEXO_URL}/health",
        "ollama":        f"{OLLAMA_URL}/api/tags",
        "bigbrother":    f"{BB_URL}/health",
    }

    results = {}
    async with aiohttp.ClientSession() as s:
        for name, url in services.items():
            try:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=4)) as r:
                    results[name] = {"ok": r.status == 200, "code": r.status}
            except Exception as e:
                results[name] = {"ok": False, "error": str(e)[:60]}

    # Modelos Ollama
    ollama = await _get_ollama()
    check = await ollama.supervisor_check()

    for name, r in results.items():
        icon = "✓" if r.get("ok") else "✗"
        status = "OK" if r.get("ok") else f"FAIL ({r.get('error', r.get('code', '?'))})"
        print(f"  {icon} {name:<20} {status}")

    print(f"\n  Gemma 4 (general): {check.get('active_general', 'N/A')}")
    print(f"  Gemma 4 (código):  {check.get('active_code',    'N/A')}")
    print(f"  Modelos Ollama:    {check.get('models_count',   0)}")
    print(f"  Costo/consulta:    $0.00 (local)\n")


# ── CODE REVIEW ───────────────────────────────────────────────────────────────

async def cmd_review(args):
    _banner("NEXO MANAGER — Revisión de Código (Gemma 4)")

    # Obtener diff / contenido
    if args.file:
        print(f"  Archivo: {args.file}")
        diff = _git_diff_file(args.file)
        contexto = f"Revisando archivo {args.file}"
    else:
        print("  Analizando git diff (cambios actuales)...")
        diff = _git_diff(staged_only=args.staged)
        contexto = "Revisión de git diff"

    if not diff or len(diff.strip()) < 10:
        print("  ⚠  Sin cambios detectados para revisar.")
        return

    print(f"  Diff: {len(diff)} caracteres → enviando a Gemma 4...\n")

    # 1. Bandit (estático)
    bandit_issues = []
    if args.file:
        rc, out, _ = _run_cmd([PYTHON, "-m", "bandit", "-r", args.file, "-ll", "-q"])
        if out.strip():
            bandit_issues = [l for l in out.splitlines() if l.strip()]

    # 2. Ruff (linting)
    ruff_issues = []
    target = args.file if args.file else "backend/ NEXO_CORE/"
    rc, out, _ = _run_cmd([PYTHON, "-m", "ruff", "check"] + (
        [args.file] if args.file else ["backend", "NEXO_CORE"]
    ))
    if out.strip():
        ruff_issues = [l for l in out.splitlines() if l.strip()][:20]

    # 3. Gemma 4 review
    ollama = await _get_ollama()
    resp = await ollama.revisar_codigo(diff[:8000], contexto=contexto)

    print("─" * 62)
    if resp.success:
        print(resp.text)
    else:
        print(f"  ⚠  Gemma 4 no disponible: {resp.error}")
        print("  Ejecutando solo análisis estático...")

    # Mostrar issues de herramientas estáticas si los hay
    if bandit_issues:
        print("\n━━ BANDIT (análisis estático) ━━")
        for line in bandit_issues[:15]:
            print(f"  {line}")

    if ruff_issues:
        print("\n━━ RUFF (linting) ━━")
        for line in ruff_issues[:15]:
            print(f"  {line}")

    # Resultado final
    review_text = resp.text if resp.success else ""
    has_critical = "RECHAZADO" in review_text or "🔴" in review_text
    has_bandit   = any("HIGH" in l or "CRITICAL" in l for l in bandit_issues)

    print("\n" + "─" * 62)
    if has_critical or has_bandit:
        print("  ❌ RESULTADO: RECHAZADO — corregir issues críticos antes de merge")
        return 1
    else:
        print("  ✅ RESULTADO: APROBADO")
        return 0


# ── SECURITY AUDIT ───────────────────────────────────────────────────────────

async def cmd_security(args):
    _banner("NEXO MANAGER — Auditoría de Seguridad (Gemma 4)")

    # Determinar archivos a auditar
    if args.file:
        files = [args.file]
    else:
        # Auditar todos los archivos Python modificados
        _, out, _ = _run_cmd(["git", "diff", "--cached", "--name-only"])
        files = [f for f in out.splitlines() if f.endswith(".py") and Path(f).exists()]
        if not files:
            # Fallback: archivos críticos del proyecto
            files = [
                "backend/routes/osint.py",
                "backend/routes/globe_control.py",
                "backend/services/big_brother_bridge.py",
                "NEXO_CORE/services/ollama_service.py",
                "NEXO_CORE/services/ai_router.py",
            ]
            files = [f for f in files if Path(ROOT / f).exists()]

    ollama = await _get_ollama()
    total_critical = 0

    for filepath in files:
        full_path = ROOT / filepath if not Path(filepath).is_absolute() else Path(filepath)
        if not full_path.exists():
            continue

        print(f"\n  Auditando: {filepath}")
        codigo = full_path.read_text(encoding="utf-8")[:10000]

        resp = await ollama.revisar_seguridad(codigo, archivo=filepath)

        print("─" * 62)
        if resp.success:
            print(resp.text)
            if "CRÍTICO" in resp.text or "ALTO" in resp.text:
                total_critical += 1
        else:
            print(f"  ⚠  Gemma 4 no disponible: {resp.error}")

    # Bandit en todo el proyecto
    print("\n━━ BANDIT — escaneo completo ━━")
    rc, out, err = _run_cmd([PYTHON, "-m", "bandit", "-r", "backend", "NEXO_CORE", "-ll"])
    if out.strip():
        for line in out.splitlines()[:25]:
            print(f"  {line}")
    else:
        print("  ✓ Bandit: sin issues de alta severidad")

    print("\n" + "─" * 62)
    if total_critical > 0 or rc != 0:
        print(f"  ❌ AUDITORÍA: {total_critical} archivo(s) con issues de seguridad")
    else:
        print("  ✅ AUDITORÍA: Sin vulnerabilidades críticas detectadas")


# ── AUTO-FIX ─────────────────────────────────────────────────────────────────

async def cmd_fix(args):
    _banner("NEXO MANAGER — Auto-Fix (Gemma 4)")

    if not args.file:
        print("  Error: --file requerido para auto-fix")
        print("  Uso: python scripts/nexo_manager.py fix --file backend/routes/mi_ruta.py --issue 'descripción'")
        return 1

    if not args.issue:
        # Primero hacer review para detectar issues
        print(f"  Sin --issue especificado, ejecutando review de {args.file} primero...")
        ollama = await _get_ollama()
        codigo = _read_file(args.file)
        rev = await ollama.revisar_codigo(codigo, contexto=f"Auto-detección de issues en {args.file}")
        if rev.success:
            print(rev.text)
            # Extraer primer issue crítico automáticamente
            lines = rev.text.splitlines()
            issue_lines = [l for l in lines if "🔴" in l or "🟡" in l or ("- [" in l and "]" in l)]
            if issue_lines:
                args.issue = issue_lines[0].strip("- ").strip()
                print(f"\n  Issue detectado: {args.issue}")
            else:
                print("  ✅ Sin issues críticos detectados — nada que corregir.")
                return 0
        else:
            print(f"  ⚠  Gemma 4 no disponible: {rev.error}")
            return 1

    filepath = Path(args.file) if Path(args.file).is_absolute() else ROOT / args.file
    if not filepath.exists():
        print(f"  Error: archivo no encontrado: {args.file}")
        return 1

    codigo_original = filepath.read_text(encoding="utf-8")
    print(f"\n  Archivo: {args.file}")
    print(f"  Issue:   {args.issue}")
    print(f"  Enviando a Gemma 4 para corrección...")

    ollama = await _get_ollama()
    resp = await ollama.sugerir_fix(
        issue=args.issue,
        codigo_original=codigo_original[:8000],
        lenguaje="python",
    )

    if not resp.success:
        print(f"  ⚠  Gemma 4 no disponible: {resp.error}")
        return 1

    codigo_corregido = resp.text

    # Limpiar markdown si Gemma lo envuelve en ```
    if "```python" in codigo_corregido:
        m = re.search(r"```python\n(.*?)```", codigo_corregido, re.DOTALL)
        if m:
            codigo_corregido = m.group(1)
    elif "```" in codigo_corregido:
        m = re.search(r"```\n?(.*?)```", codigo_corregido, re.DOTALL)
        if m:
            codigo_corregido = m.group(1)

    print("\n━━ CÓDIGO CORREGIDO ━━")
    print(codigo_corregido[:2000])

    if args.apply:
        # Backup del original
        backup = filepath.with_suffix(".py.bak")
        backup.write_text(codigo_original, encoding="utf-8")
        # Aplicar corrección
        filepath.write_text(codigo_corregido, encoding="utf-8")
        print(f"\n  ✅ Corrección aplicada. Backup en: {backup}")
        print(f"  Verificando con ruff...")
        rc, out, _ = _run_cmd([PYTHON, "-m", "ruff", "check", str(filepath)])
        if rc == 0:
            print("  ✅ Ruff OK — código sintácticamente correcto")
        else:
            print(f"  ⚠  Ruff reporta issues:\n{out[:500]}")
            print(f"  Restaurando backup...")
            filepath.write_text(codigo_original, encoding="utf-8")
            print(f"  ⚠  Corrección revertida — revisar manualmente")
    else:
        print(f"\n  (Usa --apply para aplicar la corrección automáticamente)")

    return 0


# ── DIAGNOSE ─────────────────────────────────────────────────────────────────

async def cmd_diagnose(args):
    import aiohttp
    _banner("NEXO MANAGER — Diagnóstico del Sistema (Gemma 4)")

    estado = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "servicios": {},
        "ollama": {},
        "config": {},
    }

    # Verificar servicios
    checks = {
        "nexo_backend":  f"{NEXO_URL}/health",
        "ollama":        f"{OLLAMA_URL}/api/tags",
        "bigbrother":    f"{BB_URL}/health",
    }

    async with aiohttp.ClientSession() as s:
        for name, url in checks.items():
            try:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    estado["servicios"][name] = {
                        "ok": r.status == 200,
                        "http_code": r.status,
                    }
            except Exception as e:
                estado["servicios"][name] = {"ok": False, "error": str(e)[:80]}

    # Ollama detail
    ollama = await _get_ollama()
    estado["ollama"] = await ollama.supervisor_check()

    # Config rápida
    env_keys = [
        "NEXO_MODE", "NEXO_LLM_PROVIDER", "OLLAMA_ENABLED",
        "DISCORD_ENABLED", "QDRANT_URL", "NEXO_MAX_TOKENS_DIA",
    ]
    for k in env_keys:
        v = os.getenv(k, "")
        estado["config"][k] = "SET" if v else "NOT SET"

    # Logs de errores recientes
    log_file = ROOT / "logs" / "nexo.log"
    if log_file.exists():
        try:
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            error_lines = [l for l in lines if "ERROR" in l or "CRITICAL" in l][-10:]
            estado["errores_recientes"] = error_lines
        except Exception:
            pass

    # Tests rápidos
    print("  Ejecutando tests...")
    rc_test, out_test, _ = _run_cmd(
        [PYTHON, "-m", "pytest", "tests/", "-q", "--tb=no", "-x"],
        cwd=str(ROOT),
    )
    estado["tests"] = {
        "passed": rc_test == 0,
        "output": out_test.strip()[-200:] if out_test else "sin tests",
    }

    # Análisis con Gemma 4
    print("  Analizando con Gemma 4...")
    resp = await ollama.diagnosticar_sistema(estado)

    print("\n" + "─" * 62)
    if resp.success:
        print(resp.text)
    else:
        # Fallback: reporte manual sin AI
        print("  (Gemma 4 no disponible — reporte manual)")
        for svc, r in estado["servicios"].items():
            icon = "✓" if r.get("ok") else "✗"
            print(f"  {icon} {svc}: {'OK' if r.get('ok') else r.get('error', 'FAIL')}")
        print(f"\n  Ollama: {estado['ollama'].get('status', 'N/A')}")
        print(f"  Tests: {'OK' if estado['tests']['passed'] else 'FAIL'}")

    # Guardar reporte
    report_path = ROOT / "logs" / "diagnostico.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(
        json.dumps({
            "estado": estado,
            "analisis_gemma4": resp.text if resp.success else None,
            "ts": datetime.now(timezone.utc).isoformat(),
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n  Reporte guardado: logs/diagnostico.json")


# ── SUPERVISE (bucle continuo) ────────────────────────────────────────────────

async def cmd_supervise(args):
    _banner("NEXO MANAGER — Supervisión Continua (Gemma 4)")
    print(f"  Intervalo: {args.interval}s | Ctrl+C para detener\n")

    while True:
        try:
            await cmd_status(args)
            # Si hay diff nuevo → review automático
            diff = _git_diff()
            if diff and len(diff.strip()) > 50:
                print("\n  → Cambios detectados en código, ejecutando review...")
                class FakeArgs:
                    file = None
                    staged = False
                await cmd_review(FakeArgs())
        except KeyboardInterrupt:
            print("\n  Supervisión detenida.")
            break
        except Exception as e:
            logger.error(f"Supervisor error: {e}")
        await asyncio.sleep(args.interval)


# ── CLI ENTRYPOINT ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="NEXO SOBERANO — Gestor Inteligente (Gemma 4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/nexo_manager.py status
  python scripts/nexo_manager.py review
  python scripts/nexo_manager.py review --file backend/routes/osint.py
  python scripts/nexo_manager.py security
  python scripts/nexo_manager.py security --file backend/services/big_brother_bridge.py
  python scripts/nexo_manager.py fix --file backend/routes/osint.py --issue "endpoint sin auth guard" --apply
  python scripts/nexo_manager.py diagnose
  python scripts/nexo_manager.py supervise --interval 120
        """
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # status
    sub.add_parser("status", help="Estado rápido de todos los servicios")

    # review
    p_rev = sub.add_parser("review", help="Revisión de código con Gemma 4")
    p_rev.add_argument("--file", "-f", help="Archivo específico a revisar")
    p_rev.add_argument("--staged", action="store_true", help="Solo cambios staged")

    # security
    p_sec = sub.add_parser("security", help="Auditoría de seguridad profunda")
    p_sec.add_argument("--file", "-f", help="Archivo específico a auditar")

    # fix
    p_fix = sub.add_parser("fix", help="Auto-corrección de issues con Gemma 4")
    p_fix.add_argument("--file", "-f", required=False, help="Archivo a corregir")
    p_fix.add_argument("--issue", "-i", help="Descripción del issue a corregir")
    p_fix.add_argument("--apply", action="store_true", help="Aplicar la corrección automáticamente")

    # diagnose
    sub.add_parser("diagnose", help="Diagnóstico completo del sistema")

    # supervise
    p_sup = sub.add_parser("supervise", help="Monitoreo continuo")
    p_sup.add_argument("--interval", type=int, default=120, help="Segundos entre checks")

    args = parser.parse_args()

    cmd_map = {
        "status":   cmd_status,
        "review":   cmd_review,
        "security": cmd_security,
        "fix":      cmd_fix,
        "diagnose": cmd_diagnose,
        "supervise": cmd_supervise,
    }

    rc = asyncio.run(cmd_map[args.cmd](args))
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
