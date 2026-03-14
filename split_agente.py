import os
from pathlib import Path

agente_path = r"c:\Users\Admn\Desktop\NEXO_SOBERANO\backend\routes\agente.py"
with open(agente_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

header_lines = lines[0:313]  # includes imports, helpers mostly up to the first endpoint

def create_router(file_path, router_name, line_ranges):
    # Change the router logic in header to match new tag
    file_content = ""
    for line in header_lines:
        if "router = APIRouter(prefix=\"/agente\"" in line:
            line = f'router = APIRouter(prefix="/api/{router_name}", tags=["{router_name}"])\n'
        file_content += line
    
    file_content += "\n# ════════════════════════════════════════════════════════════════════\n"
    file_content += f"# RUTAS EXTRAÍDAS: {router_name}\n"
    file_content += "# ════════════════════════════════════════════════════════════════════\n\n"
    
    for start, end in line_ranges:
        file_content += "".join(lines[start-1:end]) + "\n"
        
    # Write to destination
    p = Path(r"c:\Users\Admn\Desktop\NEXO_SOBERANO") / file_path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(file_content)

# 1. NEXO_CORE/api/rag.py
create_router("NEXO_CORE/api/rag.py", "rag", [
    (347, 386), # /consultar
    (389, 420), # /consultar-rag
    (522, 537), # /health
    (540, 548), # /presupuesto
    (612, 620), # /historial-costos
])

# 2. NEXO_CORE/api/sync.py
create_router("NEXO_CORE/api/sync.py", "sync", [
    (810, 848), # /sync/unificado
    (1192, 1205), # /drive/recent
    (568, 581), # /photos/recent
    (584, 609), # /onedrive/recent
    (851, 868), # /youtube/recent
    (871, 891), # /youtube/transcript
])

# 3. NEXO_CORE/api/media_auth.py
create_router("NEXO_CORE/api/media_auth.py", "media_auth", [
    (1005, 1018), # /drive/authorize
    (957, 970), # /youtube/authorize
    (989, 1002), # /drive/create-client-secrets
    (973, 986), # /youtube/create-client-secrets
])

# 4. NEXO_CORE/api/contrib.py
create_router("NEXO_CORE/api/contrib.py", "contrib", [
    (452, 519), # /drive/upload-aporte
])

# Moderation file doesn't need all headers, just the function is fine
mod_path = Path(r"c:\Users\Admn\Desktop\NEXO_SOBERANO\NEXO_CORE\services\moderation.py")
mod_path.parent.mkdir(parents=True, exist_ok=True)
with open(mod_path, "w", encoding="utf-8") as f:
    f.write("import logging\n")
    f.write("logger = logging.getLogger(__name__)\n\n")
    f.write("".join(lines[422:449])) # _detect_direct_harm
