"""
NEXO SOBERANO — NotebookLM Sync Service
Mantiene actualizado el export del código para análisis en NotebookLM/Gemini.
Se ejecuta automáticamente cuando hay cambios en el repo.
"""
import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

EXPORT_PATH = Path("nexo_soberano_para_notebooklm.txt")
EXTENSIONES = {'.py', '.js', '.ts', '.md', '.toml', '.yaml'}
EXCLUIR = {'node_modules', '__pycache__', '.git', 'venv', 'dist', 'build', 'logs'}


def exportar_repo() -> dict:
    """Exporta el repositorio completo en formato legible para NotebookLM."""
    repo_root = Path('.')
    archivos = []
    
    for ext in EXTENSIONES:
        for f in repo_root.rglob(f'*{ext}'):
            if any(ex in f.parts for ex in EXCLUIR):
                continue
            if f.stat().st_size > 80_000:
                continue
            try:
                content = f.read_text(encoding='utf-8', errors='ignore')
                archivos.append((str(f), content))
            except Exception:
                pass

    output = f'NEXO SOBERANO — Snapshot de código\n'
    output += f'Repo: https://github.com/Reidskar/NEXO_SOBERANO\n'
    output += f'Generado: {datetime.now().isoformat()}\n'
    output += f'Archivos: {len(archivos)}\n'
    output += '=' * 60 + '\n\n'

    for ruta, content in sorted(archivos):
        output += f'\n### {ruta} ###\n{content}\n{"-"*40}\n'

    EXPORT_PATH.write_text(output, encoding='utf-8')
    size_kb = len(output) // 1024
    logger.info(f"[NOTEBOOKLM] Export actualizado: {size_kb}KB, {len(archivos)} archivos")
    
    return {
        'ok': True,
        'archivos': len(archivos),
        'tamaño_kb': size_kb,
        'ruta': str(EXPORT_PATH)
    }


def get_ultimo_commit() -> str:
    """Obtiene el hash del último commit."""
    try:
        r = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True
        )
        return r.stdout.strip()
    except Exception:
        return 'unknown'


if __name__ == '__main__':
    resultado = exportar_repo()
    print(f"Export listo: {resultado['ruta']} ({resultado['tamaño_kb']}KB)")
    print(f"Commit: {get_ultimo_commit()}")
    print("\nSUBE ESTOS ARCHIVOS A NOTEBOOKLM:")
    print(f"  1. {EXPORT_PATH}")
