#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  NEXO SOBERANO — Phone AI Installer
#  Instala el cliente de IA en Termux con routing inteligente:
#    LAN disponible  → Torre Gemma 4 27B (GPU, $0, rápido)
#    Off-LAN         → elanarcocapital.com (mismo backend, cloud)
#    Offline         → llama.cpp + Gemma 4 1B local (~700MB)
#
#  Uso:
#    bash install_phone_ai.sh              # solo cliente LAN/dominio
#    bash install_phone_ai.sh --with-local # + modelo 1B offline
# ============================================================

set -e

WITH_LOCAL=false
[[ "$1" == "--with-local" ]] && WITH_LOCAL=true

TOWER_IP="${TOWER_IP:-192.168.100.22}"
TOWER_PORT="${TOWER_PORT:-8000}"
API_KEY="${NEXO_API_KEY:-nexo_dev_key_2025}"
DOMAIN="${NEXO_DOMAIN:-elanarcocapital.com}"
AGENT_ID="${NEXO_AGENT_ID:-telefono}"
NEXO_DIR="$HOME/nexo_agent"
AI_DIR="$NEXO_DIR/ai"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }
info() { echo -e "${CYAN}·${NC} $*"; }
step() { echo -e "\n${BOLD}══ $* ══${NC}"; }

step "NEXO AI — Instalación en teléfono"
echo "  Torre: ${TOWER_IP}:${TOWER_PORT}"
echo "  Dominio: ${DOMAIN}"
echo "  Agente: ${AGENT_ID}"
echo "  Modo local: ${WITH_LOCAL}"

# ─── 1. Paquetes base ────────────────────────────────────────
step "1/5 · Dependencias Termux"
pkg update -y -q 2>/dev/null
pkg install -y -q curl jq python3 python-pip 2>/dev/null || true
ok "curl, jq, python3 instalados"

# ─── 2. Crear directorios ────────────────────────────────────
step "2/5 · Directorios"
mkdir -p "$NEXO_DIR" "$AI_DIR"
ok "Directorios: $AI_DIR"

# ─── 3. Config file ──────────────────────────────────────────
step "3/5 · Configuración"
cat > "$AI_DIR/config.env" << EOF
# NEXO AI — Configuración de routing
TOWER_IP=${TOWER_IP}
TOWER_PORT=${TOWER_PORT}
API_KEY=${API_KEY}
DOMAIN=${DOMAIN}
AGENT_ID=${AGENT_ID}
OLLAMA_URL=http://${TOWER_IP}:11434
BACKEND_URL=http://${TOWER_IP}:${TOWER_PORT}
DOMAIN_URL=https://${DOMAIN}
# Endpoint móvil
MOBILE_AI_ENDPOINT=/api/ai/mobile/query
# Si tienes modelo local instalado:
LOCAL_MODEL_ENABLED=false
LOCAL_MODEL_PORT=8080
EOF
ok "Config guardada en $AI_DIR/config.env"

# ─── 4. Instalar cliente nexo-ai ─────────────────────────────
step "4/5 · Cliente nexo-ai"

cat > "$AI_DIR/nexo_ai.sh" << 'SCRIPT_EOF'
#!/data/data/com.termux/files/usr/bin/bash
# nexo-ai — Cliente IA de NEXO para Termux
# Uso: nexo-ai "tu pregunta aquí"
#      nexo-ai --clear          # limpiar contexto
#      nexo-ai --status         # ver estado backends
#      nexo-ai --models         # modelos disponibles

source "$HOME/nexo_agent/ai/config.env" 2>/dev/null

PROMPT="$*"
TIMEOUT=30

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

# ─── Comandos especiales ──────────────────────────────────────
if [[ "$1" == "--status" ]]; then
    echo -e "${CYAN}Verificando backends AI...${NC}"

    # LAN backend
    LAN_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "${BACKEND_URL}/api/ai/mobile/status" 2>/dev/null)
    if [[ "$LAN_CODE" == "200" ]]; then
        echo -e "${GREEN}✓${NC} Torre LAN (${TOWER_IP}:${TOWER_PORT}) — ONLINE"
        curl -s --connect-timeout 3 "${BACKEND_URL}/api/ai/mobile/status" | jq -r '"  Modelos Ollama: \(.ollama_torre.models | join(", ") // "ninguno")\n  Recomendado: \(.recommended)"' 2>/dev/null
    else
        echo -e "${YELLOW}!${NC} Torre LAN — OFFLINE (código: ${LAN_CODE})"
    fi

    # Dominio
    DOM_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${DOMAIN_URL}/api/ai/mobile/status" 2>/dev/null)
    if [[ "$DOM_CODE" == "200" ]]; then
        echo -e "${GREEN}✓${NC} Dominio (${DOMAIN}) — ONLINE"
    else
        echo -e "${YELLOW}!${NC} Dominio — OFFLINE (código: ${DOM_CODE})"
    fi

    # Local (si instalado)
    if [[ "$LOCAL_MODEL_ENABLED" == "true" ]]; then
        LOC_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://localhost:${LOCAL_MODEL_PORT}/health" 2>/dev/null)
        if [[ "$LOC_CODE" == "200" ]]; then
            echo -e "${GREEN}✓${NC} Modelo local (Gemma 4 1B) — ONLINE"
        else
            echo -e "${YELLOW}!${NC} Modelo local — OFFLINE (inicia con: nexo-ai-local)"
        fi
    fi
    exit 0
fi

if [[ "$1" == "--models" ]]; then
    echo -e "${CYAN}Modelos disponibles en torre:${NC}"
    curl -s --connect-timeout 5 "${BACKEND_URL}/api/ai/mobile/models" | jq -r '.models[]' 2>/dev/null || echo "Torre no disponible"
    exit 0
fi

if [[ "$1" == "--clear" ]]; then
    curl -s -X DELETE \
        "${BACKEND_URL}/api/ai/mobile/context/${AGENT_ID}" \
        -H "X-API-Key: ${API_KEY}" >/dev/null 2>&1 && \
    echo "Contexto limpiado" || echo "Error al limpiar contexto"
    exit 0
fi

if [[ -z "$PROMPT" ]]; then
    echo "Uso: nexo-ai 'tu pregunta'"
    echo "     nexo-ai --status | --models | --clear"
    exit 1
fi

# ─── Selección de endpoint ────────────────────────────────────
ENDPOINT=""

# 1. Intentar LAN (más rápido, Gemma 4 GPU completa)
if ping -c 1 -W 1 "${TOWER_IP}" >/dev/null 2>&1; then
    LAN_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "${BACKEND_URL}/health" 2>/dev/null)
    if [[ "$LAN_HEALTH" == "200" ]]; then
        ENDPOINT="${BACKEND_URL}/api/ai/mobile/query"
        SRC="torre LAN (Gemma 4 27B)"
    fi
fi

# 2. Fallback: modelo local en teléfono (offline)
if [[ -z "$ENDPOINT" && "$LOCAL_MODEL_ENABLED" == "true" ]]; then
    LOC_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://localhost:${LOCAL_MODEL_PORT}/health" 2>/dev/null)
    if [[ "$LOC_HEALTH" == "200" ]]; then
        ENDPOINT="local"
        SRC="local Gemma 4 1B"
    fi
fi

# 3. Fallback: dominio (internet)
if [[ -z "$ENDPOINT" ]]; then
    ENDPOINT="${DOMAIN_URL}/api/ai/mobile/query"
    SRC="dominio (${DOMAIN})"
fi

echo -e "${CYAN}·${NC} Usando: ${SRC}" >&2

# ─── Llamada al modelo local (llama-server) ───────────────────
if [[ "$ENDPOINT" == "local" ]]; then
    RESPONSE=$(curl -s --max-time "$TIMEOUT" \
        "http://localhost:${LOCAL_MODEL_PORT}/completion" \
        -H "Content-Type: application/json" \
        -d "{
            \"prompt\": \"### Instrucción:\\n${PROMPT}\\n### Respuesta:\",
            \"n_predict\": 512,
            \"temperature\": 0.2,
            \"stop\": [\"###\"]
        }" 2>/dev/null)

    TEXT=$(echo "$RESPONSE" | jq -r '.content // "Sin respuesta"' 2>/dev/null)
    echo ""
    echo -e "${GREEN}NEXO [local]:${NC} ${TEXT}"
    exit 0
fi

# ─── Llamada al backend NEXO ─────────────────────────────────
BODY=$(jq -n \
    --arg prompt "$PROMPT" \
    --arg agent_id "$AGENT_ID" \
    '{prompt: $prompt, agent_id: $agent_id, max_tokens: 1024, remember: true}')

RESPONSE=$(curl -s --max-time "$TIMEOUT" \
    "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -d "$BODY" 2>/dev/null)

if [[ -z "$RESPONSE" ]]; then
    echo -e "${YELLOW}Sin respuesta del servidor (timeout o error de red)${NC}"
    exit 1
fi

TEXT=$(echo "$RESPONSE" | jq -r '.text // .detail // "Sin respuesta"' 2>/dev/null)
MODEL=$(echo "$RESPONSE" | jq -r '.model_used // ""' 2>/dev/null)
CTX=$(echo "$RESPONSE" | jq -r '.context_size // 0' 2>/dev/null)

echo ""
echo -e "${GREEN}NEXO${NC} [${MODEL}] (ctx:${CTX}): ${TEXT}"
SCRIPT_EOF

chmod +x "$AI_DIR/nexo_ai.sh"

# Symlink global
ln -sf "$AI_DIR/nexo_ai.sh" "$PREFIX/bin/nexo-ai" 2>/dev/null || \
ln -sf "$AI_DIR/nexo_ai.sh" "$HOME/.local/bin/nexo-ai" 2>/dev/null || true

ok "Cliente nexo-ai instalado → ejecuta: nexo-ai 'hola'"

# ─── 5. Instalación del modelo local (opcional) ──────────────
if [[ "$WITH_LOCAL" == "true" ]]; then
    step "5/5 · Modelo local Gemma 4 1B (offline)"
    info "Esto requiere ~700MB de almacenamiento y 20-40 min de compilación"

    # Instalar herramientas de build
    pkg install -y -q cmake ninja clang git make 2>/dev/null
    ok "Build tools instalados"

    # Clonar llama.cpp
    LLAMACPP_DIR="$AI_DIR/llama.cpp"
    if [[ ! -d "$LLAMACPP_DIR" ]]; then
        info "Clonando llama.cpp (puede tardar)..."
        git clone --depth=1 https://github.com/ggerganov/llama.cpp "$LLAMACPP_DIR" 2>&1 | tail -3
        ok "llama.cpp clonado"
    else
        ok "llama.cpp ya existe"
    fi

    # Build
    info "Compilando llama.cpp (10-40 min en teléfono)..."
    cd "$LLAMACPP_DIR"
    mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=ON -DGGML_NATIVE=OFF 2>&1 | tail -3
    make -j2 llama-server 2>&1 | tail -5
    ok "llama-server compilado"

    # Descargar modelo Gemma 4 1B Q4_K_M
    MODEL_DIR="$AI_DIR/models"
    mkdir -p "$MODEL_DIR"
    MODEL_FILE="$MODEL_DIR/gemma-4-1b-q4.gguf"

    if [[ ! -f "$MODEL_FILE" ]]; then
        info "Descargando Gemma 4 1B Q4_K_M (~700MB)..."
        # Usar Hugging Face Hub — modelo cuantizado ligero
        MODEL_URL="https://huggingface.co/lmstudio-community/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf"
        curl -L --progress-bar -o "$MODEL_FILE" "$MODEL_URL"
        ok "Modelo descargado: $MODEL_FILE"
    else
        ok "Modelo ya descargado: $MODEL_FILE"
    fi

    # Script para iniciar servidor local
    cat > "$AI_DIR/start_local_ai.sh" << LOCALEOF
#!/data/data/com.termux/files/usr/bin/bash
# Inicia llama-server con Gemma 4 1B para uso offline
LLAMACPP_DIR="$LLAMACPP_DIR"
MODEL_FILE="$MODEL_FILE"
PORT="${LOCAL_MODEL_PORT:-8080}"

echo "Iniciando NEXO AI Local (Gemma 4 1B)..."
"\$LLAMACPP_DIR/build/bin/llama-server" \\
    --model "\$MODEL_FILE" \\
    --host 0.0.0.0 \\
    --port "\$PORT" \\
    --ctx-size 2048 \\
    --threads 4 \\
    --n-predict 512 \\
    --temp 0.2 \\
    -ngl 0 &         # -ngl 0 = CPU only (teléfono no tiene GPU accesible)

echo "Servidor local en http://localhost:\$PORT"
echo "PID: \$!"
echo "\$!" > "$NEXO_DIR/local_ai.pid"
LOCALEOF
    chmod +x "$AI_DIR/start_local_ai.sh"
    ln -sf "$AI_DIR/start_local_ai.sh" "$PREFIX/bin/nexo-ai-local" 2>/dev/null || true

    # Actualizar config
    sed -i "s/LOCAL_MODEL_ENABLED=false/LOCAL_MODEL_ENABLED=true/" "$AI_DIR/config.env"
    ok "Modelo local configurado → inicia con: nexo-ai-local"
else
    step "5/5 · Modelo local omitido (usa --with-local para instalarlo)"
    info "Sin modelo local: usará torre LAN o dominio"
fi

# ─── Resumen final ───────────────────────────────────────────
echo ""
echo -e "${BOLD}══════════════════════════════════════════${NC}"
echo -e "${BOLD}  NEXO AI instalado correctamente${NC}"
echo -e "${BOLD}══════════════════════════════════════════${NC}"
echo ""
echo "  Comandos disponibles:"
echo -e "  ${CYAN}nexo-ai 'pregunta'${NC}   → consulta IA (auto-routing)"
echo -e "  ${CYAN}nexo-ai --status${NC}     → ver qué backends están online"
echo -e "  ${CYAN}nexo-ai --models${NC}     → modelos disponibles en torre"
echo -e "  ${CYAN}nexo-ai --clear${NC}      → limpiar contexto compartido"
if [[ "$WITH_LOCAL" == "true" ]]; then
echo -e "  ${CYAN}nexo-ai-local${NC}        → iniciar modelo offline 1B"
fi
echo ""
echo "  Routing automático:"
echo "  1. Torre LAN (${TOWER_IP}:${TOWER_PORT}) → Gemma 4 27B GPU, $0"
if [[ "$WITH_LOCAL" == "true" ]]; then
echo "  2. Local telefono → Gemma 4 1B CPU, $0, offline"
fi
echo "  ${WITH_LOCAL:+3}${WITH_LOCAL:-2}. Dominio (${DOMAIN}) → backend nube, $0"
echo ""
echo "  Test rápido:"
echo -e "  ${CYAN}nexo-ai 'eres NEXO? responde en 1 línea'${NC}"
echo ""
