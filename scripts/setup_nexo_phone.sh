#!/data/data/com.termux/files/usr/bin/bash
# ================================================================
#  NEXO SOBERANO — Setup Completo del Teléfono
#  Instala y configura TODO lo necesario:
#    1. Tailscale (VPN soberana → acceso a la torre desde cualquier lugar)
#    2. Claude Code CLI (IA remota con acceso al repo)
#    3. nexo-ai CLI (Gemma 4 con routing inteligente)
#    4. Config de acceso remoto OBS, stream, torre
#
#  Uso: bash setup_nexo_phone.sh
#       bash setup_nexo_phone.sh --tailscale-ip 100.x.x.x
# ================================================================
set -e

# ─── Args ────────────────────────────────────────────────────
TAILSCALE_IP=""
TOWER_LAN_IP="${TOWER_IP:-192.168.100.22}"
TOWER_PORT="${TOWER_PORT:-8000}"
REPO_URL="https://github.com/Reidskar/NEXO_SOBERANO.git"
REPO_BRANCH="claude/enhance-3d-visual-layers-ijQhV"
REPO_DIR="$HOME/NEXO_SOBERANO"
NEXO_DIR="$HOME/nexo_agent"
PROFILE="$HOME/.bashrc"
[[ -f "$HOME/.zshrc" ]] && PROFILE="$HOME/.zshrc"

for i in "$@"; do
    case $i in
        --tailscale-ip=*) TAILSCALE_IP="${i#*=}" ;;
        --tailscale-ip)   shift; TAILSCALE_IP="$1" ;;
    esac
done

# ─── Colors ──────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
fail() { echo -e "  ${RED}✗${NC} $*"; }
info() { echo -e "  ${CYAN}·${NC} $*"; }
warn() { echo -e "  ${YELLOW}!${NC} $*"; }
step() { echo -e "\n${BOLD}┌─ $* ─────────────────────────────${NC}"; }

echo -e "\n${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   NEXO SOBERANO — Setup Teléfono NEXO    ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════╝${NC}"
echo -e "  Torre LAN: ${TOWER_LAN_IP}:${TOWER_PORT}"
[[ -n "$TAILSCALE_IP" ]] && echo -e "  Torre Tailscale: ${TAILSCALE_IP}:${TOWER_PORT}"

# ════════════════════════════════════════════════════════════
# PASO 1 — Dependencias base
# ════════════════════════════════════════════════════════════
step "1/6  Dependencias Termux"
pkg update -y -q 2>/dev/null
pkg install -y -q curl wget git nodejs python3 python-pip jq openssh 2>/dev/null
ok "Base packages instalados (curl, git, node $(node -v), python3)"

# ════════════════════════════════════════════════════════════
# PASO 2 — Tailscale
# ════════════════════════════════════════════════════════════
step "2/6  Tailscale — VPN Soberana"

echo ""
echo -e "  ${BOLD}Tailscale necesita instalarse como APP Android:${NC}"
echo -e "  ${CYAN}→ Play Store:${NC} busca 'Tailscale' e instálala"
echo -e "  ${CYAN}→ F-Droid:${NC}    https://f-droid.org/packages/com.tailscale.ipn.android"
echo ""

# Tailscale CLI en Termux (si hay root o userspace networking)
if command -v tailscale >/dev/null 2>&1; then
    ok "tailscale CLI detectado en Termux"
    TAILSCALE_IP_DETECTED=$(tailscale ip --4 2>/dev/null | head -1)
    [[ -n "$TAILSCALE_IP_DETECTED" ]] && ok "IP local Tailscale: $TAILSCALE_IP_DETECTED"
else
    # Intentar instalar desde pkg
    pkg install -y -q tailscale 2>/dev/null && ok "tailscale instalado via pkg" || \
    warn "tailscale no disponible en pkg — usa la app Android"
fi

# Pedir Tailscale IP de la torre si no se pasó como arg
if [[ -z "$TAILSCALE_IP" ]]; then
    echo ""
    echo -e "  ${BOLD}IP Tailscale de la Torre:${NC}"
    echo -e "  Para obtenerla, ejecuta en la torre:  tailscale ip"
    echo -e "  Formato esperado: 100.x.x.x"
    echo ""
    read -p "  Pega la IP Tailscale de la torre (Enter para omitir): " TAILSCALE_IP
fi

if [[ "$TAILSCALE_IP" =~ ^100\. ]]; then
    ok "Torre Tailscale configurada: $TAILSCALE_IP"
    TOWER_PRIMARY="$TAILSCALE_IP"
    TOWER_FALLBACK="$TOWER_LAN_IP"
else
    warn "Tailscale IP no configurada — usando LAN como primary"
    TOWER_PRIMARY="$TOWER_LAN_IP"
    TOWER_FALLBACK=""
fi

# ════════════════════════════════════════════════════════════
# PASO 3 — Clonar / actualizar repo
# ════════════════════════════════════════════════════════════
step "3/6  Repositorio NEXO SOBERANO"
if [[ -d "$REPO_DIR/.git" ]]; then
    info "Actualizando repo existente..."
    git -C "$REPO_DIR" fetch -q origin "$REPO_BRANCH" 2>/dev/null && \
    git -C "$REPO_DIR" checkout -q "$REPO_BRANCH" 2>/dev/null && \
    git -C "$REPO_DIR" pull -q origin "$REPO_BRANCH" 2>/dev/null || true
    ok "Repo actualizado → $REPO_DIR"
else
    info "Clonando repo (rama: $REPO_BRANCH)..."
    git clone --depth=1 -b "$REPO_BRANCH" "$REPO_URL" "$REPO_DIR" 2>&1 | tail -2
    ok "Repo clonado → $REPO_DIR"
fi

# ════════════════════════════════════════════════════════════
# PASO 4 — Claude Code CLI
# ════════════════════════════════════════════════════════════
step "4/6  Claude Code CLI"
if command -v claude >/dev/null 2>&1; then
    ok "Claude Code ya instalado: $(claude --version 2>/dev/null | head -1 || echo 'ok')"
else
    info "Instalando @anthropic-ai/claude-code..."
    npm install -g @anthropic-ai/claude-code 2>&1 | tail -3
    ok "Claude Code instalado"
fi

# API Key
if grep -q "ANTHROPIC_API_KEY" "$PROFILE" 2>/dev/null; then
    ok "ANTHROPIC_API_KEY ya en $PROFILE"
else
    echo ""
    warn "Necesitas tu Anthropic API Key"
    echo -e "  Obtén una en: https://console.anthropic.com/settings/keys"
    read -p "  API Key (sk-ant-...): " ANT_KEY
    if [[ "$ANT_KEY" == sk-ant-* ]]; then
        echo "" >> "$PROFILE"
        echo "export ANTHROPIC_API_KEY=\"$ANT_KEY\"" >> "$PROFILE"
        export ANTHROPIC_API_KEY="$ANT_KEY"
        ok "API Key guardada en $PROFILE"
    else
        warn "Formato incorrecto — agrégala después: echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> $PROFILE"
    fi
fi

# Claude settings.local.json adaptado para Termux + Tailscale
CLAUDE_DIR="$REPO_DIR/.claude"
mkdir -p "$CLAUDE_DIR"
cat > "$CLAUDE_DIR/settings.local.json" << JSON_EOF
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "python3 scripts/nexo_file_guardian.py --file \"\$CLAUDE_TOOL_INPUT_file_path\" --json 2>/dev/null || true",
          "timeout": 15000,
          "blocking": false
        }]
      }
    ],
    "SessionStart": [
      {
        "hooks": [{
          "type": "command",
          "command": "bash -c 'TS=\"${TOWER_PRIMARY}\"; LAN=\"${TOWER_LAN_IP}\"; for H in \"\$TS\" \"\$LAN\"; do [ -z \"\$H\" ] && continue; R=\$(curl -s --connect-timeout 2 \"http://\$H:${TOWER_PORT}/api/tower/ping\" 2>/dev/null); [ -n \"\$R\" ] && echo \"[NEXO] Torre online via \$H\" && exit 0; done; echo \"[NEXO] Torre offline\"'",
          "timeout": 8000,
          "blocking": false
        }]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(python3 scripts/*)",
      "Bash(curl http://${TOWER_PRIMARY}:${TOWER_PORT}/*)",
      "Bash(curl http://${TOWER_LAN_IP}:${TOWER_PORT}/*)",
      "Bash(curl https://elanarcocapital.com/*)",
      "Bash(nexo-ai*)",
      "Bash(git diff*)", "Bash(git status*)", "Bash(git add*)",
      "Bash(git commit*)", "Bash(git push*)", "Bash(git pull*)"
    ],
    "deny": []
  }
}
JSON_EOF
ok "Claude Code configurado (.claude/settings.local.json)"

# MCP sin playwright
cat > "$REPO_DIR/.mcp.local.json" << 'MCP_EOF'
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory@2026.1.26"]
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@2025.12.18"]
    }
  }
}
MCP_EOF
ok "MCP configurado (memory + sequential-thinking)"

# ════════════════════════════════════════════════════════════
# PASO 5 — nexo-ai con routing Tailscale
# ════════════════════════════════════════════════════════════
step "5/6  nexo-ai — Routing inteligente via Tailscale"
mkdir -p "$NEXO_DIR/ai"

cat > "$NEXO_DIR/ai/config.env" << CONF_EOF
# NEXO AI — Configuración de routing
TOWER_TAILSCALE_IP=${TOWER_PRIMARY}
TOWER_LAN_IP=${TOWER_LAN_IP}
TOWER_PORT=${TOWER_PORT}
API_KEY=nexo_dev_key_2025
DOMAIN=elanarcocapital.com
AGENT_ID=telefono
# Routing priority: tailscale > lan > domain
BACKEND_URL=http://${TOWER_PRIMARY}:${TOWER_PORT}
BACKEND_URL_LAN=http://${TOWER_LAN_IP}:${TOWER_PORT}
DOMAIN_URL=https://elanarcocapital.com
MOBILE_AI_ENDPOINT=/api/ai/mobile/query
LOCAL_MODEL_ENABLED=false
LOCAL_MODEL_PORT=8080
CONF_EOF
ok "Config nexo-ai con Tailscale IP: ${TOWER_PRIMARY}"

# Script nexo-ai actualizado con routing Tailscale
cat > "$NEXO_DIR/ai/nexo_ai.sh" << 'NEXO_AI_EOF'
#!/data/data/com.termux/files/usr/bin/bash
# nexo-ai — Cliente IA NEXO con routing Tailscale > LAN > Domain

source "$HOME/nexo_agent/ai/config.env" 2>/dev/null

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'

_try_endpoint() {
    local url="$1"
    local r
    r=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "${url%/api/*}/health" 2>/dev/null)
    [[ "$r" == "200" ]] && echo "$url" || echo ""
}

_resolve_endpoint() {
    local e
    # 1. Tailscale (desde cualquier lugar, privado y seguro)
    [[ -n "$TOWER_TAILSCALE_IP" ]] && \
        e=$(_try_endpoint "http://$TOWER_TAILSCALE_IP:$TOWER_PORT/api/ai/mobile/query") && \
        [[ -n "$e" ]] && { echo "$e"; echo "tailscale ($TOWER_TAILSCALE_IP)" >&3; return; }
    # 2. LAN (cuando está en casa)
    [[ -n "$TOWER_LAN_IP" ]] && \
        e=$(_try_endpoint "http://$TOWER_LAN_IP:$TOWER_PORT/api/ai/mobile/query") && \
        [[ -n "$e" ]] && { echo "$e"; echo "LAN ($TOWER_LAN_IP)" >&3; return; }
    # 3. Dominio público
    e=$(_try_endpoint "https://elanarcocapital.com/api/ai/mobile/query") && \
        [[ -n "$e" ]] && { echo "$e"; echo "dominio (elanarcocapital.com)" >&3; return; }
    echo ""
    echo "sin conexión" >&3
}

case "$1" in
    --status)
        echo -e "${BOLD}Estado backends NEXO:${NC}"
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://$H:$TOWER_PORT/health" 2>/dev/null)
            [[ "$CODE" == "200" ]] && echo -e "  ${GREEN}✓${NC} $H:$TOWER_PORT" || echo -e "  ${YELLOW}✗${NC} $H:$TOWER_PORT"
        done
        CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 4 "https://elanarcocapital.com/health" 2>/dev/null)
        [[ "$CODE" == "200" ]] && echo -e "  ${GREEN}✓${NC} elanarcocapital.com" || echo -e "  ${YELLOW}✗${NC} elanarcocapital.com"
        exit 0 ;;
    --stream-status)
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            R=$(curl -s --connect-timeout 3 "http://$H:$TOWER_PORT/api/tower/stream/status" 2>/dev/null)
            [[ -n "$R" ]] && echo "$R" | jq . 2>/dev/null && exit 0
        done; echo "Torre no disponible"; exit 1 ;;
    --stream-start)
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            R=$(curl -s -X POST "http://$H:$TOWER_PORT/api/tower/stream" \
                -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
                -d '{"action":"start"}' --connect-timeout 5 2>/dev/null)
            [[ -n "$R" ]] && echo "$R" | jq . 2>/dev/null && exit 0
        done; echo "Torre no disponible"; exit 1 ;;
    --stream-stop)
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            R=$(curl -s -X POST "http://$H:$TOWER_PORT/api/tower/stream" \
                -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
                -d '{"action":"stop"}' --connect-timeout 5 2>/dev/null)
            [[ -n "$R" ]] && echo "$R" | jq . 2>/dev/null && exit 0
        done; exit 1 ;;
    --obs-scene)
        SCENE="${2:-globe}"
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            R=$(curl -s -X POST "http://$H:$TOWER_PORT/api/integrations/obs/scene" \
                -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
                -d "{\"scene_name\":\"$SCENE\"}" --connect-timeout 5 2>/dev/null)
            [[ -n "$R" ]] && echo "$R" | jq . 2>/dev/null && exit 0
        done; exit 1 ;;
    --tower-status)
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            R=$(curl -s --connect-timeout 3 "http://$H:$TOWER_PORT/api/tower/status" 2>/dev/null)
            [[ -n "$R" ]] && echo "$R" | jq . 2>/dev/null && exit 0
        done; echo "Torre no disponible"; exit 1 ;;
    --discord-register)
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            R=$(curl -s -X POST "http://$H:$TOWER_PORT/api/tower/discord/register" \
                -H "X-API-Key: $API_KEY" --connect-timeout 10 2>/dev/null)
            [[ -n "$R" ]] && echo "$R" | jq . 2>/dev/null && exit 0
        done; echo "Torre no disponible"; exit 1 ;;
    --clear)
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            curl -s -X DELETE "http://$H:$TOWER_PORT/api/ai/mobile/context/$AGENT_ID" \
                -H "X-API-Key: $API_KEY" >/dev/null 2>&1 && echo "Contexto limpiado" && exit 0
        done; exit 1 ;;
    --models)
        for H in "$TOWER_TAILSCALE_IP" "$TOWER_LAN_IP"; do
            [[ -z "$H" ]] && continue
            R=$(curl -s --connect-timeout 5 "http://$H:$TOWER_PORT/api/ai/mobile/models" 2>/dev/null)
            [[ -n "$R" ]] && echo "$R" | jq -r '.models[]' 2>/dev/null && exit 0
        done; exit 1 ;;
    "")
        echo -e "Uso: ${CYAN}nexo-ai 'pregunta'${NC}"
        echo "Comandos: --status | --tower-status | --stream-status | --stream-start | --stream-stop"
        echo "          --obs-scene [nombre] | --discord-register | --models | --clear"
        exit 0 ;;
esac

# ─── Query AI ────────────────────────────────────────────────
PROMPT="$*"
exec 3>&1
ENDPOINT=$(_resolve_endpoint 2>&3)
SRC=$(cat /tmp/nexo_src 2>/dev/null || echo "desconocido")

exec 3>&-
[[ -z "$ENDPOINT" ]] && { echo -e "${YELLOW}Sin conexión a la torre${NC}"; exit 1; }

echo -e "${CYAN}·${NC} ${SRC}" >&2

BODY=$(jq -n --arg p "$PROMPT" --arg a "$AGENT_ID" \
    '{prompt:$p, agent_id:$a, max_tokens:1024, remember:true}')

RESP=$(curl -s --max-time 90 "$ENDPOINT" \
    -H "Content-Type: application/json" -d "$BODY" 2>/dev/null)

TEXT=$(echo "$RESP" | jq -r '.text // .detail // "Sin respuesta"' 2>/dev/null)
MODEL=$(echo "$RESP" | jq -r '.model_used // ""' 2>/dev/null)
CTX=$(echo "$RESP" | jq -r '.context_size // 0' 2>/dev/null)

echo ""
echo -e "${GREEN}NEXO${NC} [${MODEL}] ctx:${CTX}: ${TEXT}"
NEXO_AI_EOF

chmod +x "$NEXO_DIR/ai/nexo_ai.sh"
ln -sf "$NEXO_DIR/ai/nexo_ai.sh" "$PREFIX/bin/nexo-ai" 2>/dev/null || \
    mkdir -p "$HOME/.local/bin" && ln -sf "$NEXO_DIR/ai/nexo_ai.sh" "$HOME/.local/bin/nexo-ai" 2>/dev/null || true
ok "nexo-ai instalado con routing Tailscale"

# ════════════════════════════════════════════════════════════
# PASO 6 — Variables de entorno globales
# ════════════════════════════════════════════════════════════
step "6/6  Variables de entorno"

add_env() {
    local key="$1" val="$2"
    grep -q "^export $key=" "$PROFILE" 2>/dev/null && \
        sed -i "s|^export $key=.*|export $key=\"$val\"|" "$PROFILE" || \
        echo "export $key=\"$val\"" >> "$PROFILE"
}

echo "" >> "$PROFILE"
echo "# NEXO SOBERANO — Phone Config" >> "$PROFILE"
add_env "NEXO_REPO"     "$REPO_DIR"
add_env "TOWER_IP"      "$TOWER_PRIMARY"
add_env "TOWER_LAN_IP"  "$TOWER_LAN_IP"
add_env "TOWER_PORT"    "$TOWER_PORT"
[[ -n "$TAILSCALE_IP" ]] && add_env "TAILSCALE_TOWER_IP" "$TAILSCALE_IP"
add_env "NEXO_API_KEY"  "nexo_dev_key_2025"

ok "Variables guardadas en $PROFILE"

# ════════════════════════════════════════════════════════════
# RESUMEN
# ════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║          Setup NEXO — Completo           ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Comandos disponibles:${NC}"
echo -e "  ${CYAN}nexo-ai 'pregunta'${NC}           → IA (Gemma 4, routing auto)"
echo -e "  ${CYAN}nexo-ai --status${NC}             → estado de todos los backends"
echo -e "  ${CYAN}nexo-ai --tower-status${NC}        → estado completo de la torre"
echo -e "  ${CYAN}nexo-ai --stream-start${NC}        → iniciar stream OBS remotamente"
echo -e "  ${CYAN}nexo-ai --stream-stop${NC}         → detener stream"
echo -e "  ${CYAN}nexo-ai --stream-status${NC}       → ver si está transmitiendo"
echo -e "  ${CYAN}nexo-ai --obs-scene globe${NC}     → cambiar escena OBS"
echo -e "  ${CYAN}nexo-ai --discord-register${NC}    → registrar slash commands Discord"
echo ""
echo -e "  ${BOLD}Claude Code:${NC}"
echo -e "  ${CYAN}cd ~/NEXO_SOBERANO && claude${NC}  → sesión interactiva completa"
echo -e "  ${CYAN}claude -p 'pregunta'${NC}           → pregunta rápida"
echo ""
echo -e "  ${BOLD}Routing activo:${NC}"
[[ -n "$TAILSCALE_IP" ]] && \
echo -e "  1. ${GREEN}Tailscale${NC} $TAILSCALE_IP (desde cualquier lugar, seguro)"
echo -e "  2. ${CYAN}LAN${NC} $TOWER_LAN_IP (cuando estés en casa)"
echo -e "  3. ${YELLOW}Dominio${NC} elanarcocapital.com (internet público)"
echo ""
echo -e "  ${YELLOW}Recarga el perfil:${NC} source $PROFILE"
echo ""

# Tailscale pasos finales
if [[ -z "$TAILSCALE_IP" ]]; then
echo -e "${BOLD}Pendiente — Tailscale:${NC}"
echo -e "  1. Instala la app Tailscale en Android (Play Store / F-Droid)"
echo -e "  2. Inicia sesión con la misma cuenta de la torre"
echo -e "  3. Obtén la IP Tailscale de la torre: ${CYAN}tailscale ip${NC} (en la torre)"
echo -e "  4. Actualiza la config: ${CYAN}sed -i 's/TOWER_TAILSCALE_IP=/TOWER_TAILSCALE_IP=100.x.x.x/' ~/nexo_agent/ai/config.env${NC}"
echo ""
fi
