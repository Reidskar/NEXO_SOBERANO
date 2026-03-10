#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   NEXO SOBERANO — AGENTE SUPERVISOR v1.0                                   ║
║   Supervisa código, auto-repara y cifra reportes y secretos detectados     ║
╚══════════════════════════════════════════════════════════════════════════════╝

MODO DE USO:
    python agente_supervisor.py --watch          # Supervisión continua con cifrado
    python agente_supervisor.py --scan           # Escaneo único
    python agente_supervisor.py --fix            # Escaneo + auto-reparación
    python agente_supervisor.py --report         # Mostrar último reporte
    python agente_supervisor.py --genkey         # Generar/rotar clave de cifrado
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ─── Rutas base ──────────────────────────────────────────────────────────────

_AGENT_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _AGENT_DIR.parent.parent

# Añadir raíz al path para poder importar nexo_autosupervisor
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from nexo_autosupervisor import (  # noqa: E402
    NexoSupervisor,
    SupervisorReport,
    FileMetrics,
)

# ─── Cifrado ─────────────────────────────────────────────────────────────────

_KEY_FILE = _AGENT_DIR / ".supervisor.key"
_ENCRYPTED_REPORT_DIR = _AGENT_DIR / "reportes_cifrados"
_ENCRYPTED_REPORT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("nexo.agente_supervisor")


def _try_secure_chmod(path: Path) -> None:
    """Intenta restringir permisos del archivo de clave (best effort)."""
    try:
        path.chmod(0o600)
    except Exception as exc:
        log.debug("No se pudo aplicar chmod 600 en %s: %s", path, exc)


def _load_or_create_key() -> bytes:
    """Carga la clave Fernet existente o genera una nueva."""
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError(
            "Instala 'cryptography': pip install cryptography"
        ) from exc

    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes().strip()

    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    _try_secure_chmod(_KEY_FILE)
    log.info("🔑 Nueva clave de cifrado generada: %s", _KEY_FILE)
    return key


def _get_fernet():
    from cryptography.fernet import Fernet
    return Fernet(_load_or_create_key())


def rotate_key() -> Path:
    """Genera una nueva clave Fernet (rotación); la clave anterior se archiva."""
    from cryptography.fernet import Fernet

    if _KEY_FILE.exists():
        archive = _KEY_FILE.with_suffix(
            f".{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.bak"
        )
        _KEY_FILE.rename(archive)
        log.info("🗄  Clave anterior archivada: %s", archive)

    new_key = Fernet.generate_key()
    _KEY_FILE.write_bytes(new_key)
    _try_secure_chmod(_KEY_FILE)
    log.info("🔑 Clave rotada y guardada: %s", _KEY_FILE)
    return _KEY_FILE


# ─── Cifrado de reportes ──────────────────────────────────────────────────────

def encrypt_report(report: SupervisorReport, metrics: List[FileMetrics]) -> Path:
    """Cifra el reporte completo con Fernet y lo guarda en reportes_cifrados/."""
    fernet = _get_fernet()

    payload = {
        "report": {
            "timestamp": report.timestamp,
            "files_scanned": report.files_scanned,
            "total_issues": report.total_issues,
            "critical": report.critical,
            "high": report.high,
            "medium": report.medium,
            "low": report.low,
            "auto_fixed": report.auto_fixed,
            "quality_score": report.quality_score,
            "improvements": report.improvements,
            "metrics": report.metrics,
        },
        "files_with_critical": [
            {
                "path": m.path,
                "issues": [
                    {"line": i.line, "code": i.code, "message": i.message, "severity": i.severity}
                    for i in m.issues
                    if i.severity in ("critical", "high")
                ],
            }
            for m in metrics
            if any(i.severity in ("critical", "high") for i in m.issues)
        ],
    }

    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode()
    token = fernet.encrypt(raw)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = _ENCRYPTED_REPORT_DIR / f"reporte_{ts}.enc"
    out_path.write_bytes(token)
    log.info("🔒 Reporte cifrado guardado: %s", out_path)
    return out_path


def decrypt_report(enc_path: Path) -> Dict:
    """Descifra y devuelve el contenido de un reporte cifrado."""
    fernet = _get_fernet()
    raw = fernet.decrypt(enc_path.read_bytes())
    return json.loads(raw.decode())


# ─── Cifrado de secretos detectados ──────────────────────────────────────────

_SECRETS_FILE = _ENCRYPTED_REPORT_DIR / "secretos_detectados.enc"


def save_detected_secrets(secrets: List[Dict]) -> None:
    """Añade secretos detectados al almacén cifrado."""
    if not secrets:
        return

    fernet = _get_fernet()
    existing: List[Dict] = []

    if _SECRETS_FILE.exists():
        try:
            existing = json.loads(fernet.decrypt(_SECRETS_FILE.read_bytes()).decode())
        except Exception:
            existing = []

    existing.extend(secrets)

    token = fernet.encrypt(json.dumps(existing, ensure_ascii=False, indent=2).encode())
    _SECRETS_FILE.write_bytes(token)
    log.info("🔒 %d secretos detectados guardados cifrados.", len(secrets))


def _extract_secrets_from_metrics(metrics: List[FileMetrics]) -> List[Dict]:
    """Extrae los issues de tipo 'credencial hardcodeada' del reporte."""
    result = []
    for m in metrics:
        for issue in m.issues:
            if issue.code in ("SV008", "SV009", "SV010"):
                result.append({
                    "file": m.path,
                    "line": issue.line,
                    "code": issue.code,
                    "message": issue.message,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })
    return result


# ─── Agente Supervisor ────────────────────────────────────────────────────────

class AgenteSupervisor:
    """
    Agente autónomo que envuelve NexoSupervisor y añade:
    - Cifrado Fernet de reportes y secretos detectados
    - Notificaciones en consola para issues críticos
    - Ciclo watch continuo con auto-reparación
    """

    def __init__(self, target_dir: Optional[Path] = None, workers: int = 4, max_files: int = 0):
        self.target_dir = target_dir or _ROOT_DIR
        self.supervisor = NexoSupervisor(target_dir=self.target_dir, max_workers=workers)
        self.max_files = max_files if max_files > 0 else 0
        log.info("🤖 AgenteSupervisor iniciado — dir: %s", self.target_dir)
        if self.max_files:
            log.info("📏 Límite de archivos por scan: %d", self.max_files)

    def scan(self, auto_fix: bool = False) -> SupervisorReport:
        report, all_metrics = self._run_scan(auto_fix=auto_fix)
        return report

    def _run_scan(self, auto_fix: bool = False):
        # Recolectar y analizar archivos directamente desde el supervisor
        files = self.supervisor.collect_files()
        from concurrent.futures import ThreadPoolExecutor, as_completed

        files_to_scan = files[:self.max_files] if self.max_files else files
        if self.max_files and len(files) > self.max_files:
            log.warning(
                "⚠️ Se aplicó límite max_files=%d (descubiertos=%d, escaneados=%d)",
                self.max_files,
                len(files),
                len(files_to_scan),
            )

        all_metrics: List[FileMetrics] = []
        with ThreadPoolExecutor(max_workers=self.supervisor.max_workers) as ex:
            futures = {ex.submit(self.supervisor.analyze_file, f): f for f in files_to_scan}
            for fut in as_completed(futures):
                try:
                    all_metrics.append(fut.result())
                except Exception as exc:
                    log.error("Error analizando archivo: %s", exc)

        total = critical = high = medium = low = auto_fixed = 0
        quality_scores: List[float] = []
        improvements: List[str] = []

        for m in all_metrics:
            total += len(m.issues)
            critical += sum(1 for i in m.issues if i.severity == "critical")
            high += sum(1 for i in m.issues if i.severity == "high")
            medium += sum(1 for i in m.issues if i.severity == "medium")
            low += sum(1 for i in m.issues if i.severity == "low")
            quality_scores.append(m.quality_score)

            if auto_fix and m.issues:
                n, applied = self.supervisor.fixer.fix_file(m)
                auto_fixed += n
                improvements.extend(applied)

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 100.0

        report = SupervisorReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            files_scanned=len(all_metrics),
            total_issues=total,
            critical=critical,
            high=high,
            medium=medium,
            low=low,
            auto_fixed=auto_fixed,
            quality_score=round(avg_quality, 2),
            improvements=improvements,
            metrics={
                "files_with_critical": [
                    m.path for m in all_metrics
                    if any(i.severity == "critical" for i in m.issues)
                ],
            },
        )

        # Cifrar reporte
        try:
            encrypt_report(report, all_metrics)
        except Exception as exc:
            log.warning("No se pudo cifrar el reporte: %s", exc)

        # Cifrar secretos detectados
        secrets = _extract_secrets_from_metrics(all_metrics)
        if secrets:
            try:
                save_detected_secrets(secrets)
            except Exception as exc:
                log.warning("No se pudo cifrar secretos: %s", exc)

        log.info(
            "📊 Scan completado — %d archivos, score: %.1f/100, críticos: %d",
            report.files_scanned, report.quality_score, report.critical,
        )
        if report.critical > 0:
            log.warning("⚠️  %d ISSUES CRÍTICOS — revisar reportes_cifrados/", report.critical)

        return report, all_metrics

    def watch(self, interval: int = 30, auto_fix: bool = True) -> None:
        """Ciclo de supervisión continua con cifrado automático."""
        log.info("👁  Modo WATCH activo — intervalo: %ds  auto_fix=%s", interval, auto_fix)
        log.info("   [Ctrl+C para detener]")

        scan_count = 0
        try:
            while True:
                changed = self.supervisor._detect_changes()
                if changed or scan_count == 0:
                    if changed:
                        log.info("🔄 %d archivos cambiados — re-analizando...", len(changed))
                    self._run_scan(auto_fix=auto_fix)
                    scan_count += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            log.info("⏹  Watch detenido por el usuario")

    def show_report(self) -> None:
        """Muestra el último reporte cifrado descifrado en consola."""
        files = sorted(_ENCRYPTED_REPORT_DIR.glob("reporte_*.enc"), reverse=True)
        if not files:
            log.info("No hay reportes cifrados. Ejecuta --scan primero.")
            return

        latest = files[0]
        try:
            data = decrypt_report(latest)
            r = data.get("report", {})
            log.info("\n%s", "═" * 60)
            log.info("  NEXO AGENTE SUPERVISOR — ÚLTIMO REPORTE CIFRADO")
            log.info("%s", "═" * 60)
            log.info("  Fecha     : %s", r.get("timestamp", "—"))
            log.info("  Score     : %.1f/100", r.get("quality_score", 0))
            log.info("  Archivos  : %d", r.get("files_scanned", 0))
            log.info("  Issues    : %d  (🔴%d  🟠%d  🟡%d  🟢%d)",
                     r.get("total_issues", 0),
                     r.get("critical", 0), r.get("high", 0),
                     r.get("medium", 0), r.get("low", 0))
            log.info("  Reparados : %d", r.get("auto_fixed", 0))
            log.info("%s\n", "═" * 60)
        except Exception as exc:
            log.error("No se pudo descifrar el reporte: %s", exc)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NEXO SOBERANO — Agente Supervisor con cifrado",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dir", type=Path, default=None, help="Directorio a supervisar")
    parser.add_argument("--watch", action="store_true", help="Supervisión continua")
    parser.add_argument("--scan", action="store_true", help="Escaneo único")
    parser.add_argument("--fix", action="store_true", help="Escaneo + auto-reparación")
    parser.add_argument("--report", action="store_true", help="Mostrar último reporte cifrado")
    parser.add_argument("--genkey", action="store_true", help="Generar/rotar clave de cifrado")
    parser.add_argument("--interval", type=int, default=30, help="Intervalo watch (segundos)")
    parser.add_argument("--workers", type=int, default=4, help="Workers paralelos")
    parser.add_argument("--max-files", type=int, default=0, help="Máximo de archivos por scan (0 = sin límite)")
    args = parser.parse_args()

    if args.genkey:
        rotate_key()
        return

    env_max_files = int(os.getenv("NEXO_SUPERVISOR_MAX_FILES", "0") or "0")
    max_files = args.max_files if args.max_files > 0 else env_max_files
    agente = AgenteSupervisor(target_dir=args.dir, workers=args.workers, max_files=max_files)

    if args.watch:
        agente.watch(interval=args.interval, auto_fix=args.fix)
    elif args.scan or args.fix:
        agente.scan(auto_fix=args.fix)
    elif args.report:
        agente.show_report()
    else:
        agente.scan(auto_fix=False)


if __name__ == "__main__":
    main()
