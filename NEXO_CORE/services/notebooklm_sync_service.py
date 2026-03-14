import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuración
EXPORT_DIR = Path("exports")
NOTEBOOKLM_FILE = EXPORT_DIR / "nexo_master_context.txt"
CAMILO_DIR = Path("camilo el bkn")
CAMILO_FILE = CAMILO_DIR / "nexo_soberano_para_otra_ia.txt"
OBSIDIAN_VAULT = Path(r"C:\Users\Admn\Documents\Obsidian Vault\NEXO SOBERANO")
OBSIDIAN_FILE = OBSIDIAN_VAULT / "NEXO_MASTER_CONTEXT.md" # Cambiado a .md para Obsidian

# Extensiones a incluir
EXTENSIONES = {'.py', '.md', '.txt', '.js', '.ts', '.toml', '.yaml', '.yml'}

# Directorios a ignorar
EXCLUIR_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', 'exports', 'camilo el bkn', '.pytest_cache'}

def exportar_contexto_maestro():
    """Recorre el proyecto y genera un archivo consolidado para NotebookLM."""
    print("Iniciando exportacion de contexto maestro...")
    
    # Asegurar directorios
    EXPORT_DIR.mkdir(exist_ok=True)
    CAMILO_DIR.mkdir(exist_ok=True)
    OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)

    repo_root = Path(".")
    archivos_procesados = 0
    buffer = []

    # Cabecera del documento
    buffer.append(f"NEXO SOBERANO — CONTEXTO MAESTRO PARA ANÁLISIS")
    buffer.append(f"Generado: {datetime.now().isoformat()}")
    buffer.append(f"Repositorio: https://github.com/Reidskar/NEXO_SOBERANO")
    buffer.append("=" * 60 + "\n")

    # Recorrido recursivo usando Path.rglob
    print("Escaneando archivos...")
    for file_path in repo_root.rglob("*"):
        # Ignorar directorios excluidos
        if any(part in EXCLUIR_DIRS for part in file_path.parts):
            continue
        
        # Ignorar si es un directorio
        if file_path.is_dir():
            continue

        # Filtrar por extensión
        if file_path.suffix.lower() not in EXTENSIONES:
            continue
        
        # Ignorar archivos demasiado grandes (> 100KB) para evitar ruido
        if file_path.stat().st_size > 100000:
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Formato de cabecera por archivo
            buffer.append(f"=== Archivo: {file_path} ===")
            buffer.append(content)
            buffer.append("-" * 40 + "\n")
            
            archivos_procesados += 1
            if archivos_procesados % 10 == 0:
                print(f"   Processed {archivos_procesados} files...")
        except Exception as e:
            logger.error(f"Error leyendo {file_path}: {e}")

    final_content = "\n".join(buffer)

    # Guardar en destino principal
    NOTEBOOKLM_FILE.write_text(final_content, encoding='utf-8')
    
    # Sincronizar con "camilo el bkn"
    CAMILO_FILE.write_text(final_content, encoding='utf-8')
    
    # Sincronizar con Obsidian
    OBSIDIAN_FILE.write_text(final_content, encoding='utf-8')

    print("Exportacion completada!")
    print(f"   Archivos incluidos: {archivos_procesados}")
    print(f"   Destino 1: {NOTEBOOKLM_FILE}")
    print(f"   Destino 2: {CAMILO_FILE}")
    print(f"   Destino 3: {OBSIDIAN_FILE}")
    
    return {
        "ok": True,
        "archivos": archivos_procesados,
        "tamaño_kb": len(final_content) // 1024
    }

if __name__ == "__main__":
    exportar_contexto_maestro()
