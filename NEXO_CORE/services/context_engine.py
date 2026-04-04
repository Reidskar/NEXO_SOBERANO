# ============================================================
# NEXO SOBERANO — Context Engine v1.0
# © 2026 elanarcocapital.com
#
# Motor de comprensión de contexto para la IA.
# Antes de CUALQUIER cambio, la IA lee y entiende el código
# relevante: dependencias, patrones, historia, impacto.
#
# Funciones:
#   build_context(files)        → mapa semántico del código
#   get_context_for_task(desc)  → código relevante para una tarea
#   get_related_files(file)     → qué otros archivos usa/importa
#   store_learning(change)      → aprende de cambios pasados
# ============================================================
from __future__ import annotations
import ast
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("NEXO.context_engine")

ROOT       = Path(__file__).resolve().parents[2]
CACHE_DIR  = ROOT / "logs" / "context_cache"
LEARN_FILE = ROOT / "logs" / "context_learnings.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ── DATA MODELS ───────────────────────────────────────────────────────────────

@dataclass
class FileContext:
    path: str
    imports: list[str]         = field(default_factory=list)
    classes: list[str]         = field(default_factory=list)
    functions: list[str]       = field(default_factory=list)
    patterns: list[str]        = field(default_factory=list)   # "fastapi_route", "ollama_call", etc.
    complexity: str            = "low"                          # low | medium | high
    last_modified: str         = ""
    hash: str                  = ""
    summary: str               = ""                             # Gemma 4 generated

@dataclass
class TaskContext:
    task: str
    relevant_files: list[str]  = field(default_factory=list)
    related_patterns: list[str]= field(default_factory=list)
    impact_estimate: str       = "low"
    suggested_approach: str    = ""
    warnings: list[str]        = field(default_factory=list)

@dataclass
class ChangeRecord:
    ts: str
    file: str
    task: str
    before_hash: str
    after_hash: str
    success: bool
    gemma4_review: str         = ""
    lines_changed: int         = 0


# ── PARSER ────────────────────────────────────────────────────────────────────

NEXO_PATTERNS = {
    "fastapi_route":    r"@router\.(get|post|put|patch|delete)",
    "ollama_call":      r"ollama_service\.(consultar|analizar|revisar|sugerir)",
    "ai_router_call":   r"ai_router\.consultar",
    "globe_broadcast":  r"broadcast_command\(",
    "pydantic_model":   r"class\s+\w+\(BaseModel\)",
    "auth_guard":       r"_require_key\(",
    "websocket":        r"WebSocket|websocket",
    "qdrant":           r"qdrant|QdrantClient",
    "async_def":        r"async def ",
    "cost_tracking":    r"cost_manager|cost_usd|track_cost",
    "osint":            r"big_brother|BigBrother|osint",
    "gemma4":           r"ollama_service|OllamaService",
}


def _parse_file(path: Path) -> FileContext:
    """Extrae metadatos semánticos de un archivo Python."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return FileContext(path=str(path))

    ctx = FileContext(
        path=str(path.relative_to(ROOT)),
        hash=hashlib.md5(source.encode()).hexdigest()[:12],
        last_modified=datetime.fromtimestamp(path.stat().st_mtime).isoformat()[:16],
    )

    # AST parsing
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    ctx.imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    ctx.imports.append(node.module.split(".")[0])
            elif isinstance(node, ast.ClassDef):
                ctx.classes.append(node.name)
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                ctx.functions.append(node.name)
    except SyntaxError:
        pass

    ctx.imports = list(dict.fromkeys(ctx.imports))[:20]

    # Pattern detection
    for pattern_name, pattern_re in NEXO_PATTERNS.items():
        if re.search(pattern_re, source):
            ctx.patterns.append(pattern_name)

    # Complexity estimate
    lines = source.count("\n")
    num_fns = len(ctx.functions)
    if lines > 400 or num_fns > 20:
        ctx.complexity = "high"
    elif lines > 150 or num_fns > 8:
        ctx.complexity = "medium"

    return ctx


# ── CONTEXT ENGINE ────────────────────────────────────────────────────────────

class ContextEngine:
    """
    Motor de comprensión de contexto para IA.

    La IA usa esto antes de hacer cambios para entender:
    - Qué hace cada archivo (funciones, clases, patrones)
    - Qué otros archivos dependen de él
    - Qué cambios se han hecho antes y con qué resultado
    - Cuál es el enfoque más seguro para la tarea actual
    """

    def __init__(self):
        self._cache: dict[str, FileContext] = {}
        self._learnings: list[ChangeRecord] = self._load_learnings()
        self._initialized = False

    # ── BUILD / SCAN ──────────────────────────────────────────────────────────

    def scan_project(self, dirs: list[str] | None = None) -> dict[str, FileContext]:
        """Escanea el proyecto y construye mapa de contexto completo."""
        scan_dirs = dirs or ["backend", "NEXO_CORE", "scripts", "frontend/src"]
        scanned = {}
        for d in scan_dirs:
            target = ROOT / d
            if not target.exists():
                continue
            for py_file in target.rglob("*.py"):
                rel = str(py_file.relative_to(ROOT))
                if any(skip in rel for skip in ["__pycache__", ".venv", "node_modules"]):
                    continue
                ctx = _parse_file(py_file)
                scanned[rel] = ctx
                self._cache[rel] = ctx

        self._initialized = True
        logger.info(f"Context Engine: {len(scanned)} archivos escaneados")
        return scanned

    def get_file_context(self, filepath: str) -> FileContext | None:
        """Contexto de un archivo específico."""
        rel = str(Path(filepath).relative_to(ROOT)) if Path(filepath).is_absolute() else filepath
        if rel not in self._cache:
            full = ROOT / rel
            if full.exists():
                ctx = _parse_file(full)
                self._cache[rel] = ctx
                return ctx
            return None
        return self._cache[rel]

    def get_related_files(self, filepath: str) -> list[str]:
        """
        Encuentra qué archivos importan o usan el archivo dado.
        Esencial para entender el impacto de un cambio.
        """
        if not self._initialized:
            self.scan_project()

        rel = str(Path(filepath).relative_to(ROOT)) if Path(filepath).is_absolute() else filepath
        target_ctx = self._cache.get(rel)
        if not target_ctx:
            return []

        # Buscar quién importa los módulos de este archivo
        target_module = Path(rel).stem
        related = []
        for path, ctx in self._cache.items():
            if path == rel:
                continue
            if target_module in ctx.imports:
                related.append(path)
            # También buscar uso directo de clases/funciones
            if target_ctx.classes:
                # (simplificado: si comparten patrones clave)
                common_patterns = set(ctx.patterns) & set(target_ctx.patterns)
                if len(common_patterns) >= 2 and path not in related:
                    related.append(path)

        return related[:10]

    async def get_context_for_task(
        self,
        task: str,
        target_file: str = "",
    ) -> TaskContext:
        """
        Construye contexto completo para una tarea específica.
        La IA usa esto para entender qué toca y qué podría romper.
        """
        if not self._initialized:
            self.scan_project()

        tc = TaskContext(task=task)

        if target_file:
            rel = str(Path(target_file).relative_to(ROOT)) if Path(target_file).is_absolute() else target_file
            tc.relevant_files.append(rel)
            related = self.get_related_files(target_file)
            tc.relevant_files.extend(related)

            ctx = self._cache.get(rel)
            if ctx:
                tc.related_patterns = ctx.patterns
                if ctx.complexity == "high":
                    tc.impact_estimate = "high"
                    tc.warnings.append(f"Archivo de alta complejidad ({len(ctx.functions)} funciones)")
                if "fastapi_route" in ctx.patterns and "auth_guard" not in ctx.patterns:
                    tc.warnings.append("Archivo tiene rutas FastAPI sin auth guard detectado")

        # Detectar patrones de la tarea
        task_lower = task.lower()
        if any(k in task_lower for k in ["seguridad", "auth", "security", "clave", "key"]):
            tc.impact_estimate = "high"
            tc.warnings.append("Tarea relacionada con seguridad — nivel 3 recomendado")
        if any(k in task_lower for k in ["base de datos", "schema", "migration", "migrate"]):
            tc.impact_estimate = "high"
            tc.warnings.append("Tarea afecta esquema de datos — revisar migraciones")

        # Historial de cambios relevantes
        past = [r for r in self._learnings if target_file and r.file == target_file]
        if past:
            last = past[-1]
            if not last.success:
                tc.warnings.append(f"Último cambio en este archivo falló ({last.ts[:10]}): {last.task[:60]}")

        # Sugerencia de enfoque con Gemma 4
        if tc.impact_estimate == "high" or tc.warnings:
            tc.suggested_approach = await self._suggest_approach(task, tc)

        return tc

    async def _suggest_approach(self, task: str, tc: TaskContext) -> str:
        """Gemma 4 sugiere el enfoque más seguro para una tarea."""
        try:
            from NEXO_CORE.services.ollama_service import ollama_service
            context_summary = {
                "tarea": task,
                "archivos_afectados": tc.relevant_files[:5],
                "patrones_detectados": tc.related_patterns,
                "advertencias": tc.warnings,
                "historial_fallos": [r.task for r in self._learnings if not r.success][-3:],
            }
            resp = await ollama_service.consultar(
                prompt=f"Contexto:\n{json.dumps(context_summary, ensure_ascii=False)}\n\nSugiere el enfoque más seguro para la tarea en máximo 3 pasos.",
                modelo="fast",
                system="Eres el arquitecto técnico de NEXO SOBERANO. Da orientación técnica concisa.",
                temperature=0.1,
                max_tokens=300,
            )
            return resp.text if resp.success else ""
        except Exception:
            return ""

    # ── LEARNING ─────────────────────────────────────────────────────────────

    def store_learning(
        self,
        file: str,
        task: str,
        before_content: str,
        after_content: str,
        success: bool,
        review: str = "",
    ):
        """Registra el resultado de un cambio para aprender de él."""
        record = ChangeRecord(
            ts=datetime.now(timezone.utc).isoformat(),
            file=str(Path(file).relative_to(ROOT)) if Path(file).is_absolute() else file,
            task=task[:120],
            before_hash=hashlib.md5(before_content.encode()).hexdigest()[:12],
            after_hash=hashlib.md5(after_content.encode()).hexdigest()[:12],
            success=success,
            gemma4_review=review[:500],
            lines_changed=abs(len(after_content.splitlines()) - len(before_content.splitlines())),
        )
        self._learnings.append(record)
        # Guardar (últimas 500 entradas)
        self._learnings = self._learnings[-500:]
        try:
            LEARN_FILE.write_text(
                json.dumps([asdict(r) for r in self._learnings], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Error guardando learnings: {e}")

    def _load_learnings(self) -> list[ChangeRecord]:
        try:
            if LEARN_FILE.exists():
                data = json.loads(LEARN_FILE.read_text(encoding="utf-8"))
                return [ChangeRecord(**r) for r in data]
        except Exception:
            pass
        return []

    def get_stats(self) -> dict:
        total = len(self._learnings)
        successful = sum(1 for r in self._learnings if r.success)
        return {
            "total_changes_tracked": total,
            "success_rate": f"{successful/total*100:.0f}%" if total else "N/A",
            "files_in_context": len(self._cache),
            "patterns_known": list(NEXO_PATTERNS.keys()),
        }


# Instancia global
context_engine = ContextEngine()
