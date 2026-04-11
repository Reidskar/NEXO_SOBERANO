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

# ════════════════════════════════════════════════════════════
# PASO 7 — Phone Agent NEXO (bidireccional + herramientas Termux)
# ════════════════════════════════════════════════════════════
step "7/9  Phone Agent NEXO (Termux tools + comando bidireccional)"

# Intentar descargar el agente desde la torre (ya generado dinámicamente)
AGENT_INSTALLED=false
for H in "$TOWER_PRIMARY" "$TOWER_LAN_IP"; do
    [[ -z "$H" ]] && continue
    info "Intentando descargar agente desde $H..."
    if curl -sf --connect-timeout 5 "http://$H:$TOWER_PORT/phone/setup.sh" -o /tmp/nexo_agent_setup.sh 2>/dev/null; then
        bash /tmp/nexo_agent_setup.sh
        AGENT_INSTALLED=true
        ok "Agente instalado desde la torre ($H)"
        break
    fi
done

# Fallback: instalar agente desde el repo clonado
if [[ "$AGENT_INSTALLED" == "false" ]]; then
    warn "Torre no disponible — instalando agente desde repo local"
    mkdir -p "$NEXO_DIR" "$NEXO_DIR/logs"

    # Instalar dependencias Python del agente
    pip install --quiet requests psutil 2>/dev/null || true
    pkg install -y -q termux-api 2>/dev/null || true

    # Copiar agente si existe en el repo
    AGENT_SRC="$REPO_DIR/nexo_agent/nexo_mobile_agent.py"
    if [[ ! -f "$AGENT_SRC" ]]; then
        # Crear agente mínimo funcional
        cat > "$NEXO_DIR/nexo_mobile_agent.py" << 'PYEOF'
#!/usr/bin/env python3
"""NEXO Phone Agent — ejecuta cuando la torre lo descargue"""
import json, os, subprocess, time, requests, psutil
from datetime import datetime, timezone

BASE     = os.path.expanduser("~/nexo_agent")
PIDFILE  = os.path.join(BASE, "nexo_agent.pid")
LOGFILE  = os.path.join(BASE, "logs/agent.log")

def _load_env():
    for p in [os.path.join(BASE, ".env"), os.path.expanduser("~/.bashrc")]:
        if os.path.exists(p):
            for line in open(p):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip().strip("export "), v.strip().strip('"'))
_load_env()

BACKENDS = [b for b in [
    os.getenv("BACKEND_URL",     "http://192.168.100.22:8000"),
    os.getenv("TAILSCALE_TOWER_IP", "") and f"http://{os.getenv('TAILSCALE_TOWER_IP')}:{os.getenv('TOWER_PORT','8000')}",
] if b]
AGENT_ID = os.getenv("AGENT_ID", "telefono")
API_KEY  = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
HDR      = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def get_backend():
    for url in BACKENDS:
        try:
            if requests.get(f"{url}/health", timeout=3).status_code < 500:
                return url
        except: pass
    return BACKENDS[0]

BACKEND = get_backend()

def metrics():
    m = {"agent_id": AGENT_ID, "timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        m["cpu_pct"] = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        m["ram_pct"] = mem.percent
        m["ram_total_mb"] = round(mem.total / 1e6, 1)
    except: pass
    for cmd, key in [("termux-battery-status", "bat"), ("termux-wifi-connectioninfo", "wifi")]:
        try:
            r = subprocess.run([cmd], capture_output=True, text=True, timeout=4)
            if r.returncode == 0:
                d = json.loads(r.stdout)
                if key == "bat":
                    m["bateria_pct"] = d.get("percentage", -1)
                    m["bateria_estado"] = d.get("status", "unknown")
                else:
                    m["wifi_ssid"] = d.get("ssid", "unknown")
        except: pass
    return m

def exec_cmd(cmd):
    t = cmd.get("type","")
    p = cmd.get("payload", {})
    def run(*a): subprocess.run(list(a), timeout=10)
    if t == "notify":    run("termux-notification","--title",p.get("title","NEXO"),"--content",p.get("content",""))
    elif t == "torch":   run("termux-torch","on" if p.get("on",True) else "off")
    elif t == "vibrate": run("termux-vibrate","-d",str(p.get("duration_ms",500)),"-f")
    elif t == "volume":  run("termux-volume",p.get("stream","music"),str(p.get("volume",5)))
    elif t == "location":
        r = subprocess.run(["termux-location","-p","gps","-r","once"], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            loc = json.loads(r.stdout)
            requests.post(f"{BACKEND}/api/webhooks/ingest",
                json={"tenant_slug":"globe","type":"phone_location","title":f"{AGENT_ID} GPS",
                      "body":json.dumps({"lat":loc.get("latitude"),"lng":loc.get("longitude")}),"severity":0.3},
                headers=HDR, timeout=8)
    elif t == "screenshot":
        out = os.path.join(BASE, "screenshot.png")
        subprocess.run(["termux-screenshot","-f",out], timeout=10)
    elif t == "exec":
        out = subprocess.run(["bash","-c",p.get("command","echo ok")], capture_output=True, text=True, timeout=30)
        subprocess.run(["termux-notification","--title","NEXO exec","--content",out.stdout[:100] or out.stderr[:100]])
    elif t == "tts":
        run("termux-tts-speak", p.get("text",""))
    elif t == "sms":
        run("termux-sms-send","-n",p.get("number",""),p.get("message","NEXO"))
    elif t == "open_url":
        run("termux-open-url", p.get("url",""))

with open(PIDFILE, "w") as f: f.write(str(os.getpid()))
subprocess.run(["termux-wake-lock"], timeout=5)
subprocess.run(["termux-notification","--title","◎ NEXO SOBERANO","--content","Agente iniciado","--id","99","--ongoing"])

# Detectar herramientas Termux y registrar
tools_all = ["termux-battery-status","termux-sensor","termux-torch","termux-vibrate","termux-volume",
             "termux-wifi-connectioninfo","termux-wifi-scaninfo","termux-location","termux-camera-info",
             "termux-camera-photo","termux-microphone-record","termux-notification","termux-dialog",
             "termux-toast","termux-open-url","termux-clipboard-get","termux-clipboard-set",
             "termux-screenshot","termux-wake-lock","termux-alarm","termux-sms-send","termux-sms-list",
             "termux-call-log","termux-contact-list","termux-tts-speak","termux-fingerprint"]
detected = [t for t in tools_all if subprocess.run(["which",t],capture_output=True).returncode == 0]
try:
    requests.post(f"{BACKEND}/api/mobile/tools/{AGENT_ID}", json={"tools": detected}, headers=HDR, timeout=8)
    print(f"[NEXO] {len(detected)} herramientas Termux registradas")
except Exception as e: print(f"[NEXO] tools registro falló: {e}")

last_hb = 0
last_cmd = 0
while True:
    now = time.time()
    if now - last_hb >= 30:
        try:
            m = metrics()
            r = requests.post(f"{BACKEND}/api/mobile/heartbeat", json=m, headers=HDR, timeout=8)
            cmds = r.json().get("commands", [])
            for c in cmds: exec_cmd(c)
        except Exception as e: print(f"[NEXO] heartbeat error: {e}")
        last_hb = now
    if now - last_cmd >= 10:
        try:
            r = requests.get(f"{BACKEND}/api/mobile/commands/{AGENT_ID}", headers=HDR, timeout=5)
            for c in r.json().get("commands", []): exec_cmd(c)
        except: pass
        last_cmd = now
    time.sleep(5)
PYEOF
    fi

    ok "Agente instalado desde repo"
fi

# Start script
cat > "$NEXO_DIR/start.sh" << 'STARTEOF'
#!/data/data/com.termux/files/usr/bin/bash
AGENT_DIR="$HOME/nexo_agent"
PIDFILE="$AGENT_DIR/nexo_agent.pid"
if [[ -f "$PIDFILE" ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "Agente ya corriendo (PID $(cat $PIDFILE))"
    exit 0
fi
nohup python3 "$AGENT_DIR/nexo_mobile_agent.py" >> "$AGENT_DIR/logs/agent.log" 2>&1 &
echo "Agente NEXO iniciado (PID $!)"
STARTEOF
chmod +x "$NEXO_DIR/start.sh"

# Termux:Boot
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/nexo-agent.sh" << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
sleep 10
termux-wake-lock
bash "$HOME/nexo_agent/start.sh"
BOOTEOF
chmod +x "$HOME/.termux/boot/nexo-agent.sh"
ok "Termux:Boot configurado (auto-inicio al encender)"

# Arrancar agente ahora
bash "$NEXO_DIR/start.sh" 2>/dev/null || true
ok "Agente NEXO iniciado"

# ════════════════════════════════════════════════════════════
# PASO 8 — Ollama local (Gemma 4 1B — opcional)
# ════════════════════════════════════════════════════════════
step "8/9  Ollama / IA local en teléfono"

WITH_LOCAL=false
[[ "$*" == *"--with-local"* ]] && WITH_LOCAL=true

if [[ "$WITH_LOCAL" == "true" ]]; then
    info "Instalando llama.cpp + Gemma 4 1B (~700MB, 20-40 min)..."
    pkg install -y -q cmake ninja clang make 2>/dev/null
    LLAMACPP="$HOME/nexo_agent/ai/llama.cpp"
    MODEL_DIR="$HOME/nexo_agent/ai/models"
    mkdir -p "$MODEL_DIR"

    if [[ ! -d "$LLAMACPP" ]]; then
        git clone --depth=1 https://github.com/ggerganov/llama.cpp "$LLAMACPP" 2>&1 | tail -2
    fi
    cd "$LLAMACPP" && mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF 2>&1 | tail -2
    make -j2 llama-server 2>&1 | tail -3
    ok "llama-server compilado"

    MODEL_FILE="$MODEL_DIR/gemma-1b-q4.gguf"
    if [[ ! -f "$MODEL_FILE" ]]; then
        info "Descargando Gemma 3 1B Q4_K_M (~700MB)..."
        curl -L --progress-bar \
            "https://huggingface.co/lmstudio-community/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf" \
            -o "$MODEL_FILE"
        ok "Modelo descargado"
    fi

    cat > "$HOME/nexo_agent/ai/start_local_ai.sh" << LOCALEOF
#!/data/data/com.termux/files/usr/bin/bash
$LLAMACPP/build/bin/llama-server \\
    --model $MODEL_FILE --host 0.0.0.0 --port 8080 \\
    --ctx-size 2048 --threads 4 --n-predict 512 -ngl 0 &
echo "IA local iniciada en http://localhost:8080"
LOCALEOF
    chmod +x "$HOME/nexo_agent/ai/start_local_ai.sh"
    ln -sf "$HOME/nexo_agent/ai/start_local_ai.sh" "$PREFIX/bin/nexo-ai-local" 2>/dev/null || true
    sed -i "s/LOCAL_MODEL_ENABLED=false/LOCAL_MODEL_ENABLED=true/" "$HOME/nexo_agent/ai/config.env" 2>/dev/null || true
    ok "Gemma 4 1B configurada — inicia con: nexo-ai-local"
else
    info "Saltando IA local — para instalarla: bash $0 --with-local"
    info "La IA usa la torre (Gemma 4 27B GPU) via Tailscale/LAN"
fi

# ════════════════════════════════════════════════════════════
# PASO 9 — Registro final en la torre
# ════════════════════════════════════════════════════════════
step "9/9  Registro en la torre"

for H in "$TOWER_PRIMARY" "$TOWER_LAN_IP"; do
    [[ -z "$H" ]] && continue
    # Registrar Discord commands
    R=$(curl -s -X POST "http://$H:$TOWER_PORT/api/tower/discord/register" \
        -H "X-API-Key: nexo_dev_key_2025" --connect-timeout 8 2>/dev/null)
    if echo "$R" | grep -q '"ok":true'; then
        ok "Slash commands Discord registrados"
    fi

    # Verificar estado IA
    STATUS=$(curl -s --connect-timeout 5 "http://$H:$TOWER_PORT/api/ai/mobile/status" 2>/dev/null)
    if echo "$STATUS" | grep -q '"available":true'; then
        MODEL=$(echo "$STATUS" | grep -o '"models":\[[^]]*\]' | head -1)
        ok "Torre Gemma 4 disponible"
    fi
    break
done

echo ""
echo -e "${BOLD}╔═══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║      NEXO Phone — Setup 100% Completo        ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Acceso remoto desde Discord:${NC}"
echo -e "  ${CYAN}/ai pregunta: 'toma una foto'${NC}     → NEXO envía cmd al teléfono"
echo -e "  ${CYAN}/ai pregunta: 'muestra ubicación'${NC}  → GPS → OmniGlobe"
echo ""
echo -e "  ${BOLD}Control desde Termux:${NC}"
echo -e "  ${CYAN}nexo-ai 'pregunta'${NC}                → IA Gemma 4 torre"
echo -e "  ${CYAN}nexo-ai --stream-start${NC}            → OBS stream"
echo -e "  ${CYAN}nexo-ai --obs-scene globe${NC}         → cambiar escena"
echo -e "  ${CYAN}nexo-ai --tower-status${NC}            → estado torre completo"
echo ""
echo -e "  ${BOLD}Agente en segundo plano:${NC}"
echo -e "  ${CYAN}bash ~/nexo_agent/start.sh${NC}        → iniciar agente"
echo -e "  ${CYAN}tail -f ~/nexo_agent/logs/agent.log${NC} → ver logs"
echo ""
[[ "$WITH_LOCAL" == "true" ]] && \
echo -e "  ${CYAN}nexo-ai-local${NC}                     → Gemma 4 1B offline"
echo ""
