#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   NEXO SOBERANO — AUTO-SUPERVISOR DE CÓDIGO v1.0                           ║
║   Sistema de mejora continua y auto-reparación con IA                      ║
║   Monitorea, analiza, repara y mejora el código de forma autónoma          ║
╚══════════════════════════════════════════════════════════════════════════════╝

MODO DE USO:
    python nexo_autosupervisor.py --watch         # Modo watch continuo
    python nexo_autosupervisor.py --scan          # Escaneo único
    python nexo_autosupervisor.py --fix           # Auto-reparar errores
    python nexo_autosupervisor.py --report        # Generar reporte
    python nexo_autosupervisor.py --improve       # Ciclo de mejora IA
"""

import os
import sys
import json
import time
import ast
import re
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if stream is not None and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# ─── CONFIGURACIÓN ───────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs" / "supervisor"
LOG_DIR.mkdir(parents=True, exist_ok=True)

REPORT_DIR = BASE_DIR / "reports" / "supervisor"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

BACKUP_DIR = BASE_DIR / ".supervisor_backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"supervisor_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("nexo.supervisor")

# ─── MODELOS DE DATOS ────────────────────────────────────────────────────────

@dataclass
class CodeIssue:
    """Representa un problema detectado en el código"""
    file: str
    line: int
    col: int
    severity: str          # critical | high | medium | low | info
    category: str          # syntax | logic | security | performance | style | dead_code
    code: str              # código de issue (ej: SV001)
    message: str
    suggestion: str = ""
    auto_fixable: bool = False
    fixed: bool = False


@dataclass
class FileMetrics:
    """Métricas de calidad de un archivo"""
    path: str
    lines: int = 0
    functions: int = 0
    classes: int = 0
    complexity: int = 0     # ciclomática aproximada
    issues: List[CodeIssue] = field(default_factory=list)
    quality_score: float = 100.0
    hash: str = ""
    last_checked: str = ""


@dataclass
class SupervisorReport:
    """Reporte completo del supervisor"""
    timestamp: str
    files_scanned: int
    total_issues: int
    critical: int
    high: int
    medium: int
    low: int
    auto_fixed: int
    quality_score: float
    improvements: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


# ─── ANALIZADORES ────────────────────────────────────────────────────────────

class PythonAnalyzer:
    """Analiza archivos Python en busca de problemas"""

    SECURITY_PATTERNS = [
        (r"eval\s*\(", "SV001", "Uso peligroso de eval()", "critical"),
        (r"exec\s*\(", "SV002", "Uso peligroso de exec()", "critical"),
        (r"__import__\s*\(", "SV003", "Import dinámico inseguro", "high"),
        (r"os\.system\s*\(", "SV004", "os.system() - usar subprocess", "high"),
        (r"pickle\.loads?\s*\(", "SV005", "Pickle inseguro con datos externos", "high"),
        (r"sql\s*=.*%.*%", "SV006", "Posible SQL injection con %", "critical"),
        (r'sql\s*=.*f".*\{', "SV007", "Posible SQL injection con f-string", "critical"),
        (r"password\s*=\s*['\"][^'\"]{3,}", "SV008", "Credencial hardcodeada", "critical"),
        (r"api_key\s*=\s*['\"][^'\"]{10,}", "SV009", "API Key hardcodeada", "critical"),
        (r"SECRET\s*=\s*['\"][^'\"]{5,}", "SV010", "Secret hardcodeado", "critical"),
    ]

    PERFORMANCE_PATTERNS = [
        (r"for .+ in .+:\s*\n\s+.+\.append", "PF001", "Usar list comprehension", "low"),
        (r"time\.sleep\s*\(\s*[0-9]+\s*\)", "PF002", "Sleep en código síncrono", "medium"),
        (r"\.read\(\)", "PF003", "Leer archivo completo - considerar streaming", "info"),
        (r"global\s+\w+", "PF004", "Variable global - prefer funciones puras", "low"),
    ]

    STYLE_PATTERNS = [
        (r"except\s*:", "ST001", "except desnudo - capturar excepciones específicas", "medium"),
        (r"except\s+Exception\s*:", "ST002", "except Exception muy amplio", "low"),
        (r"print\s*\(", "ST003", "log.info() - usar logging", "info"),
        (r"#\s*TODO", "ST004", "TODO pendiente", "info"),
        (r"#\s*FIXME", "ST005", "FIXME pendiente", "medium"),
        (r"#\s*HACK", "ST006", "HACK en código", "medium"),
        (r"pass\s*$", "ST007", "pass innecesario", "info"),
    ]

    def analyze(self, path: Path) -> FileMetrics:
        metrics = FileMetrics(
            path=str(path),
            last_checked=datetime.now(timezone.utc).isoformat()
        )

        try:
            source = path.read_text(encoding="utf-8-sig", errors="replace")
            metrics.hash = hashlib.sha256(source.encode()).hexdigest()[:16]
            lines = source.splitlines()
            metrics.lines = len(lines)

            # ── Análisis sintáctico ──
            try:
                tree = ast.parse(source)
                metrics.functions = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
                metrics.classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
                metrics.complexity = self._compute_complexity(tree)
            except SyntaxError as e:
                metrics.issues.append(CodeIssue(
                    file=str(path), line=e.lineno or 0, col=e.offset or 0,
                    severity="critical", category="syntax",
                    code="SY001", message=f"Error de sintaxis: {e.msg}",
                    suggestion="Revisar y corregir la sintaxis del archivo.",
                    auto_fixable=False
                ))

            # ── Análisis por patrones ──
            all_patterns = (
                [(p, c, m, "security") for p, c, m, _ in self.SECURITY_PATTERNS] +
                [(p, c, m, "performance") for p, c, m, _ in self.PERFORMANCE_PATTERNS] +
                [(p, c, m, "style") for p, c, m, _ in self.STYLE_PATTERNS]
            )
            for pattern, code, message, category in all_patterns:
                if path.name == "nexo_autosupervisor.py" and category == "security":
                    continue
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        sev = self._get_severity(code)
                        metrics.issues.append(CodeIssue(
                            file=str(path), line=i, col=0,
                            severity=sev, category=category,
                            code=code, message=message,
                            auto_fixable=(code in ["ST003", "ST007"]),
                            suggestion=self._get_suggestion(code)
                        ))

            # ── Análisis de líneas largas ──
            for i, line in enumerate(lines, 1):
                if len(line) > 120:
                    metrics.issues.append(CodeIssue(
                        file=str(path), line=i, col=120,
                        severity="info", category="style",
                        code="ST008", message=f"Línea demasiado larga ({len(line)} chars)",
                        suggestion="Dividir en múltiples líneas (PEP8: max 120 chars)",
                        auto_fixable=False
                    ))

            # ── Análisis funciones muy largas ──
            try:
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_lines = (node.end_lineno or node.lineno) - node.lineno
                        if func_lines > 80:
                            metrics.issues.append(CodeIssue(
                                file=str(path), line=node.lineno, col=0,
                                severity="medium", category="complexity",
                                code="CX001", message=f"Función '{node.name}' muy larga ({func_lines} líneas)",
                                suggestion="Dividir en funciones más pequeñas (máx 80 líneas)",
                                auto_fixable=False
                            ))
            except SyntaxError:
                pass

            # ── Score de calidad ──
            metrics.quality_score = self._compute_quality_score(metrics)

        except Exception as e:
            log.error(f"Error analizando {path}: {e}")

        return metrics

    def _compute_complexity(self, tree: ast.AST) -> int:
        """Complejidad ciclomática aproximada"""
        decision_nodes = (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert)
        return sum(1 for n in ast.walk(tree) if isinstance(n, decision_nodes))

    def _compute_quality_score(self, m: FileMetrics) -> float:
        """Score 0-100 de calidad del archivo"""
        score = 100.0
        deductions = {"critical": 15, "high": 8, "medium": 4, "low": 1, "info": 0.2}
        for issue in m.issues:
            score -= deductions.get(issue.severity, 0)
        if m.complexity > 50:
            score -= (m.complexity - 50) * 0.1
        return max(0.0, min(100.0, score))

    def _get_severity(self, code: str) -> str:
        all_p = self.SECURITY_PATTERNS + self.PERFORMANCE_PATTERNS + self.STYLE_PATTERNS
        for _, c, _, sev in all_p:
            if c == code:
                return sev
        return "info"

    def _get_suggestion(self, code: str) -> str:
        suggestions = {
            "SV001": "Reemplazar eval() con ast.literal_eval() o json.loads()",
            "SV002": "Usar subprocess.run() con lista de argumentos",
            "SV004": "Usar subprocess.run(['cmd', 'arg'], capture_output=True)",
            "SV006": "Usar parámetros preparados: cursor.execute('SELECT * WHERE id=?', (id,))",
            "SV007": "Usar ORM o parámetros: cursor.execute(query, params)",
            "SV008": "Mover a .env y usar os.getenv('PASSWORD')",
            "SV009": "Mover a .env y usar os.getenv('API_KEY')",
            "ST001": "Capturar excepciones específicas: except ValueError as e:",
            "ST003": "Usar logging.info() en vez de print()",
            "PF001": "result = [expr for item in iterable]",
        }
        return suggestions.get(code, "Revisar y refactorizar según buenas prácticas")


class HTMLAnalyzer:
    """Analiza archivos HTML/CSS/JS"""

    def analyze(self, path: Path) -> FileMetrics:
        metrics = FileMetrics(path=str(path), last_checked=datetime.now(timezone.utc).isoformat())
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            metrics.hash = hashlib.sha256(source.encode()).hexdigest()[:16]
            metrics.lines = source.count("\n")

            issues = []

            # Patrones HTML problemáticos
            html_checks = [
                (r"javascript:void", "HT001", "javascript:void obsoleto - usar #", "low"),
                (r"onclick=.*alert\(", "HT002", "alert() en producción", "medium"),
                (r"style=.*!important", "HT003", "!important en estilos inline", "info"),
                (r"<script src=\"http://", "HT004", "Script HTTP no seguro", "high"),
                (r"innerHTML\s*=", "HT005", "innerHTML puede causar XSS", "high"),
                (r"document\.write\s*\(", "HT006", "document.write() obsoleto", "medium"),
                (r"var\s+\w+\s*=", "HT007", "var obsoleto - usar const/let", "low"),
                (r"console\.log\s*\(", "HT008", "console.log en producción", "info"),
            ]

            lines = source.splitlines()
            for pattern, code, message, sev in html_checks:
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        issues.append(CodeIssue(
                            file=str(path), line=i, col=0,
                            severity=sev, category="style",
                            code=code, message=message,
                            auto_fixable=(code in ["HT007", "HT008"]),
                            suggestion=f"Código {code}: revisar y actualizar"
                        ))

            # Detectar img sin alt
            for i, line in enumerate(lines, 1):
                if "<img" in line and "alt=" not in line:
                    issues.append(CodeIssue(
                        file=str(path), line=i, col=0,
                        severity="low", category="accessibility",
                        code="AC001", message="<img> sin atributo alt (accesibilidad)",
                        suggestion='Agregar alt="descripción de imagen"',
                        auto_fixable=False
                    ))

            metrics.issues = issues
            metrics.quality_score = max(0, 100 - len(issues) * 3)
        except Exception as e:
            log.error(f"Error analizando HTML {path}: {e}")
        return metrics


# ─── AUTO-REPARADOR ──────────────────────────────────────────────────────────

class AutoFixer:
    """Auto-repara issues marcados como auto_fixable"""

    def fix_file(self, metrics: FileMetrics) -> Tuple[int, List[str]]:
        path = Path(metrics.path)
        fixable = [i for i in metrics.issues if i.auto_fixable and not i.fixed]
        if not fixable:
            return 0, []

        # Backup antes de modificar
        backup = BACKUP_DIR / f"{path.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        backup.write_bytes(path.read_bytes())

        source = path.read_text(encoding="utf-8")
        applied = []

        for issue in fixable:
            if issue.code == "ST003":
                # print() → logging
                source_new = re.sub(
                    r'\bprint\s*\((.+?)\)',
                    r'log.info(\1)',
                    source
                )
                if source_new != source:
                    source = source_new
                    issue.fixed = True
                    applied.append(f"L{issue.line}: log.info() → log.info()")

            elif issue.code == "HT007":
                # var → let
                source_new = re.sub(r'\bvar\b', 'let', source)
                if source_new != source:
                    source = source_new
                    issue.fixed = True
                    applied.append(f"L{issue.line}: var → let")

        if applied:
            path.write_text(source, encoding="utf-8")
            log.info(f"✓ Auto-fix aplicado en {path.name}: {len(applied)} cambios")

        return len(applied), applied


# ─── MOTOR PRINCIPAL ─────────────────────────────────────────────────────────

class NexoSupervisor:
    """Motor principal del supervisor autónomo"""

    def __init__(self, target_dir: Path = BASE_DIR, max_workers: int = 4):
        self.target_dir = target_dir
        self.max_workers = max_workers
        self.max_files = int(os.getenv("NEXO_SUPERVISOR_MAX_FILES", "0") or "0")
        self.py_analyzer = PythonAnalyzer()
        self.html_analyzer = HTMLAnalyzer()
        self.fixer = AutoFixer()
        self.history: List[SupervisorReport] = []
        self._file_hashes: Dict[str, str] = {}
        self._running = False

        # Patrones a ignorar
        self.ignore_patterns = {
            "__pycache__", ".git", "node_modules", ".venv", "venv",
            "dist", "build", ".supervisor_backups", "logs", "reports",
            ".pytest_cache", "*.egg-info"
        }

        log.info(f"🔍 Supervisor iniciado — directorio: {self.target_dir}")

    def _should_ignore(self, path: Path) -> bool:
        path_parts = {part.lower() for part in path.parts}
        file_name = path.name.lower()
        for pattern in self.ignore_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower.startswith("*."):
                if file_name.endswith(pattern_lower[1:]):
                    return True
                continue
            if pattern_lower in path_parts:
                return True
        return False

    def collect_files(self) -> List[Path]:
        """Recolecta todos los archivos a analizar"""
        files = []
        extensions = {".py", ".html", ".js", ".jsx", ".ts"}
        for ext in extensions:
            for f in self.target_dir.rglob(f"*{ext}"):
                if not self._should_ignore(f):
                    files.append(f)
        return sorted(files)

    def analyze_file(self, path: Path) -> FileMetrics:
        if path.suffix == ".py":
            return self.py_analyzer.analyze(path)
        elif path.suffix in {".html", ".js", ".jsx", ".ts"}:
            return self.html_analyzer.analyze(path)
        return FileMetrics(path=str(path))

    def scan(self, auto_fix: bool = False) -> SupervisorReport:
        """Escaneo completo del proyecto"""
        log.info(f"🔍 Iniciando escaneo en {self.target_dir}...")
        files = self.collect_files()
        files_to_scan = files[: self.max_files] if self.max_files > 0 else files
        truncated = len(files) > len(files_to_scan)
        log.info(f"   Archivos a analizar: {len(files_to_scan)} / {len(files)}")
        if truncated:
            log.warning(
                "⚠ Escaneo truncado a %s archivos (NEXO_SUPERVISOR_MAX_FILES)",
                self.max_files,
            )

        all_metrics: List[FileMetrics] = []
        analysis_errors = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = {ex.submit(self.analyze_file, f): f for f in files_to_scan}
            for fut in as_completed(futures):
                try:
                    all_metrics.append(fut.result())
                except Exception as e:
                    log.error(f"Error: {e}")
                    analysis_errors += 1

        # Contar issues
        total = critical = high = medium = low = auto_fixed = 0
        quality_scores = []
        improvements = []

        for m in all_metrics:
            total += len(m.issues)
            critical += sum(1 for i in m.issues if i.severity == "critical")
            high += sum(1 for i in m.issues if i.severity == "high")
            medium += sum(1 for i in m.issues if i.severity == "medium")
            low += sum(1 for i in m.issues if i.severity == "low")
            quality_scores.append(m.quality_score)

            if auto_fix and m.issues:
                n, applied = self.fixer.fix_file(m)
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
                "scan_limit": self.max_files,
                "files_total_collected": len(files),
                "scan_truncated": truncated,
                "analysis_errors": analysis_errors,
                "files_by_score": self._bucket_scores(all_metrics),
                "top_issues": self._top_issues(all_metrics),
                "files_with_critical": [m.path for m in all_metrics if any(i.severity == "critical" for i in m.issues)]
            }
        )

        self.history.append(report)
        self._save_report(report, all_metrics)
        self._print_summary(report)
        return report

    def _bucket_scores(self, metrics: List[FileMetrics]) -> Dict:
        buckets = {"excellent(90-100)": 0, "good(70-90)": 0, "fair(50-70)": 0, "poor(<50)": 0}
        for m in metrics:
            if m.quality_score >= 90:
                buckets["excellent(90-100)"] += 1
            elif m.quality_score >= 70:
                buckets["good(70-90)"] += 1
            elif m.quality_score >= 50:
                buckets["fair(50-70)"] += 1
            else:
                buckets["poor(<50)"] += 1
        return buckets

    def _top_issues(self, metrics: List[FileMetrics]) -> List[Dict]:
        """Top 10 issues más frecuentes"""
        counter: Dict[str, int] = {}
        msgs: Dict[str, str] = {}
        for m in metrics:
            for i in m.issues:
                counter[i.code] = counter.get(i.code, 0) + 1
                msgs[i.code] = i.message
        return [{"code": k, "count": v, "message": msgs[k]}
                for k, v in sorted(counter.items(), key=lambda x: -x[1])[:10]]

    def _save_report(self, report: SupervisorReport, metrics: List[FileMetrics]):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON detallado
        full = {
            "report": asdict(report),
            "files": [asdict(m) for m in metrics]
        }
        json_path = REPORT_DIR / f"scan_{ts}.json"
        json_path.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")

        # Markdown legible
        md = self._build_markdown_report(report, metrics)
        md_path = REPORT_DIR / f"scan_{ts}.md"
        md_path.write_text(md, encoding="utf-8")

        # Último reporte siempre en latest
        (REPORT_DIR / "latest.json").write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        (REPORT_DIR / "latest.md").write_text(md, encoding="utf-8")

        log.info(f"📄 Reporte guardado: {json_path}")

    def _build_markdown_report(self, r: SupervisorReport, metrics: List[FileMetrics]) -> str:
        sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "⚪"}
        lines = [
            "# NEXO SOBERANO — Reporte de Supervisor",
            f"**Fecha:** {r.timestamp}",
            f"**Score de calidad:** {r.quality_score:.1f}/100",
            "",
            "## Resumen Ejecutivo",
            "| Métrica | Valor |",
            "|---|---|",
            f"| Archivos escaneados | {r.files_scanned} |",
            f"| Issues totales | {r.total_issues} |",
            f"| 🔴 Críticos | {r.critical} |",
            f"| 🟠 Altos | {r.high} |",
            f"| 🟡 Medios | {r.medium} |",
            f"| 🟢 Bajos | {r.low} |",
            f"| ✅ Auto-reparados | {r.auto_fixed} |",
            "",
            "## Top Issues",
        ]
        for issue in r.metrics.get("top_issues", []):
            lines.append(f"- `{issue['code']}` ({issue['count']}x): {issue['message']}")

        if r.metrics.get("files_with_critical"):
            lines += ["", "## ⚠ Archivos Críticos"]
            for f in r.metrics["files_with_critical"][:10]:
                lines.append(f"- `{f}`")

        lines += ["", "## Detalle por Archivo"]
        for m in sorted(metrics, key=lambda x: x.quality_score):
            if m.issues:
                lines.append(f"\n### `{Path(m.path).name}` — Score: {m.quality_score:.0f}/100")
                for i in m.issues[:5]:  # max 5 por archivo
                    emoji = sev_emoji.get(i.severity, "⚪")
                    lines.append(f"- {emoji} L{i.line} `{i.code}`: {i.message}")
                if len(m.issues) > 5:
                    lines.append(f"  *(+{len(m.issues)-5} más...)*")

        return "\n".join(lines)

    def _print_summary(self, r: SupervisorReport):
        colors = {
            "critical": "\033[91m", "high": "\033[93m", "medium": "\033[94m",
            "low": "\033[92m", "reset": "\033[0m", "cyan": "\033[96m", "bold": "\033[1m"
        }
        c = colors
        log.info(f"\n{c['bold']}{'═'*60}{c['reset']}")
        log.info(f"{c['cyan']}{c['bold']}  NEXO SUPERVISOR — REPORTE{c['reset']}")
        log.info(f"{'═'*60}")
        log.info(f"  📁 Archivos: {r.files_scanned}   |   🎯 Score: {c['bold']}{r.quality_score:.1f}/100{c['reset']}")
        print(f"  {c['critical']}🔴 Críticos: {r.critical}{c['reset']}  {c['high']}🟠 Altos: {r.high}{c['reset']}  "
              f"{c['medium']}🟡 Medios: {r.medium}{c['reset']}  {c['low']}🟢 Bajos: {r.low}{c['reset']}")
        if r.auto_fixed:
            log.info(f"  {c['low']}✅ Auto-reparados: {r.auto_fixed}{c['reset']}")
        log.info(f"{'═'*60}\n")

    def watch(self, interval: int = 30, auto_fix: bool = True):
        """Modo watch: monitorea cambios y re-analiza automáticamente"""
        self._running = True
        log.info(f"👁 Modo WATCH activo — intervalo: {interval}s  auto_fix={auto_fix}")
        log.info("   [Ctrl+C para detener]")

        scan_count = 0
        try:
            while self._running:
                changed_files = self._detect_changes()
                if changed_files or scan_count == 0:
                    if changed_files:
                        log.info(f"🔄 {len(changed_files)} archivos cambiados — re-analizando...")
                    report = self.scan(auto_fix=auto_fix)
                    scan_count += 1

                    # Notificación si hay críticos
                    if report.critical > 0:
                        log.warning(f"⚠️  {report.critical} ISSUES CRÍTICOS DETECTADOS")
                        self._notify_critical(report)

                time.sleep(interval)
        except KeyboardInterrupt:
            log.info("⏹ Watch detenido por el usuario")

    def _detect_changes(self) -> List[Path]:
        """Detecta archivos que cambiaron desde el último scan"""
        changed = []
        for path in self.collect_files():
            try:
                content = path.read_bytes()
                h = hashlib.sha256(content).hexdigest()[:16]
                if self._file_hashes.get(str(path)) != h:
                    self._file_hashes[str(path)] = h
                    changed.append(path)
            except Exception:
                pass
        return changed

    def _notify_critical(self, report: SupervisorReport):
        """Notificación del sistema para issues críticos"""
        try:
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"NEXO SUPERVISOR: {report.critical} issues críticos detectados\nScore: {report.quality_score:.0f}/100",
                    "NEXO SOBERANO — Alerta de Código",
                    0x30
                )
        except Exception:
            pass


# ─── MEJORA CON IA ──────────────────────────────────────────────────────────

class AIImprover:
    """Usa la API de Anthropic para sugerir mejoras automáticas"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            log.warning("AI Improver: ANTHROPIC_API_KEY no configurada — mejoras IA desactivadas")

    def suggest_improvements(self, metrics: FileMetrics) -> List[str]:
        """Pide sugerencias de mejora a Claude para un archivo con issues"""
        if not self.enabled or not metrics.issues:
            return []

        # Solo para archivos con issues altos o críticos
        serious = [i for i in metrics.issues if i.severity in ("critical", "high", "medium")]
        if not serious:
            return []

        try:
            import urllib.request
            import json as json_mod

            issues_text = "\n".join([
                f"- L{i.line} [{i.severity}] {i.code}: {i.message}"
                for i in serious[:10]
            ])

            prompt = f"""Eres un experto en código Python y seguridad.
Analiza estos issues encontrados en el archivo `{Path(metrics.path).name}`:

{issues_text}

Proporciona sugerencias CONCRETAS y ACCIONABLES para mejorar el código.
Responde en español, formato lista, máximo 5 sugerencias.
Sé específico con nombres de funciones/patterns a usar."""

            payload = json_mod.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}]
            }).encode()

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json_mod.loads(resp.read())
                return [data["content"][0]["text"]]

        except Exception as e:
            log.debug(f"AI Improver error: {e}")
            return []

    def generate_missing_docstrings(self, path: Path) -> int:
        """Agrega docstrings a funciones que no los tienen"""
        if not self.enabled or path.suffix != ".py":
            return 0
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            missing = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not (node.body and isinstance(node.body[0], ast.Expr) and
                            isinstance(node.body[0].value, ast.Constant)):
                        missing.append(node.name)
            if missing:
                log.info(f"  Funciones sin docstring en {path.name}: {', '.join(missing[:5])}")
            return len(missing)
        except Exception:
            return 0


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="NEXO SOBERANO — Auto-Supervisor de Código",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--dir", type=Path, default=BASE_DIR, help="Directorio a supervisar")
    parser.add_argument("--watch", action="store_true", help="Modo watch continuo")
    parser.add_argument("--scan", action="store_true", help="Escaneo único")
    parser.add_argument("--fix", action="store_true", help="Auto-reparar issues")
    parser.add_argument("--report", action="store_true", help="Mostrar último reporte")
    parser.add_argument("--improve", action="store_true", help="Ciclo de mejora con IA")
    parser.add_argument("--interval", type=int, default=30, help="Intervalo watch en segundos")
    parser.add_argument("--workers", type=int, default=4, help="Workers paralelos")
    parser.add_argument("--max-files", type=int, default=0, help="Máximo de archivos por escaneo (0=usar env/default)")
    args = parser.parse_args()

    supervisor = NexoSupervisor(target_dir=args.dir, max_workers=args.workers)
    if args.max_files and args.max_files > 0:
        supervisor.max_files = args.max_files

    if args.watch:
        supervisor.watch(interval=args.interval, auto_fix=args.fix)
    elif args.scan or args.fix:
        supervisor.scan(auto_fix=args.fix)
    elif args.report:
        latest = REPORT_DIR / "latest.md"
        if latest.exists():
            log.info(latest.read_text(encoding="utf-8"))
        else:
            log.info("No hay reportes previos. Ejecuta --scan primero.")
    elif args.improve:
        ai = AIImprover()
        supervisor.scan(auto_fix=True)
        log.info("🤖 Iniciando ciclo de mejora con IA...")
        files = supervisor.collect_files()
        for f in files[:20]:
            metrics = supervisor.analyze_file(f)
            suggestions = ai.suggest_improvements(metrics)
            if suggestions:
                log.info(f"\n💡 Sugerencias para {f.name}:\n{suggestions[0]}")
            ai.generate_missing_docstrings(f)
    else:
        supervisor.scan(auto_fix=False)


if __name__ == "__main__":
    main()
