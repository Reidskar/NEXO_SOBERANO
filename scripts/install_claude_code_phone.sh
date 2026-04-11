#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
#  NEXO — Instalador de Claude Code en Termux
#  Instala Claude Code CLI con la misma configuración de la torre
#  Uso: bash install_claude_code_phone.sh
# ============================================================
set -e

REPO_URL="https://github.com/Reidskar/NEXO_SOBERANO.git"
REPO_BRANCH="claude/enhance-3d-visual-layers-ijQhV"
REPO_DIR="$HOME/NEXO_SOBERANO"
TOWER_IP="${TOWER_IP:-192.168.100.22}"
TOWER_PORT="${TOWER_PORT:-8000}"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }
info() { echo -e "${CYAN}·${NC} $*"; }
step() { echo -e "\n${BOLD}══ $* ══${NC}"; }

echo -e "\n${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   NEXO SOBERANO — Claude Code Phone  ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}\n"

# ─── 1. Dependencias base ────────────────────────────────────
step "1/6 · Dependencias Termux"
pkg update -y -q 2>/dev/null
pkg install -y -q nodejs git python3 jq curl 2>/dev/null
ok "Node.js $(node --version), git, python3 instalados"

# ─── 2. Instalar Claude Code CLI ─────────────────────────────
step "2/6 · Claude Code CLI"
if command -v claude >/dev/null 2>&1; then
    ok "Claude Code ya instalado: $(claude --version 2>/dev/null | head -1)"
else
    info "Instalando @anthropic-ai/claude-code..."
    npm install -g @anthropic-ai/claude-code 2>&1 | tail -3
    ok "Claude Code instalado: $(claude --version 2>/dev/null | head -1)"
fi

# ─── 3. Clonar / actualizar el repo ──────────────────────────
step "3/6 · Repositorio NEXO SOBERANO"
if [[ -d "$REPO_DIR/.git" ]]; then
    info "Repo ya existe, actualizando..."
    git -C "$REPO_DIR" fetch origin "$REPO_BRANCH" 2>/dev/null
    git -C "$REPO_DIR" checkout "$REPO_BRANCH" 2>/dev/null
    git -C "$REPO_DIR" pull origin "$REPO_BRANCH" 2>/dev/null || true
    ok "Repo actualizado en $REPO_DIR"
else
    info "Clonando $REPO_URL (rama: $REPO_BRANCH)..."
    git clone --depth=1 -b "$REPO_BRANCH" "$REPO_URL" "$REPO_DIR" 2>&1 | tail -3
    ok "Repo clonado en $REPO_DIR"
fi

# ─── 4. Configurar ANTHROPIC_API_KEY ─────────────────────────
step "4/6 · API Key de Anthropic"

PROFILE="$HOME/.bashrc"
[[ -f "$HOME/.zshrc" ]] && PROFILE="$HOME/.zshrc"

if grep -q "ANTHROPIC_API_KEY" "$PROFILE" 2>/dev/null; then
    ok "ANTHROPIC_API_KEY ya configurada en $PROFILE"
else
    echo ""
    echo -e "${YELLOW}  Necesitas tu Anthropic API Key para usar Claude Code.${NC}"
    echo -e "  Obtén una en: https://console.anthropic.com/settings/keys"
    echo ""
    read -p "  Pega tu API Key (sk-ant-...): " ANTHROPIC_KEY

    if [[ "$ANTHROPIC_KEY" == sk-ant-* ]]; then
        echo "" >> "$PROFILE"
        echo "# NEXO — Anthropic Claude Code" >> "$PROFILE"
        echo "export ANTHROPIC_API_KEY=\"$ANTHROPIC_KEY\"" >> "$PROFILE"
        export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
        ok "API Key guardada en $PROFILE"
    else
        warn "API Key no reconocida — agrégala manualmente:"
        warn "  echo 'export ANTHROPIC_API_KEY=\"sk-ant-...\"' >> $PROFILE"
    fi
fi

# ─── 5. Configuración .claude/ adaptada para teléfono ────────
step "5/6 · Configuración Claude Code (adaptada para Termux)"

CLAUDE_DIR="$REPO_DIR/.claude"
mkdir -p "$CLAUDE_DIR/rules" "$CLAUDE_DIR/commands" "$CLAUDE_DIR/skills"

# settings.json — adaptado para Termux (sin .venv, sin Windows paths)
cat > "$CLAUDE_DIR/settings.local.json" << 'JSON_EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 scripts/nexo_file_guardian.py --file \"$CLAUDE_TOOL_INPUT_file_path\" --json 2>/dev/null || true",
            "timeout": 15000,
            "blocking": false
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "curl -s http://TOWER_IP:TOWER_PORT/api/tower/ping 2>/dev/null && echo '[NEXO] Torre online' || echo '[NEXO] Torre offline'",
            "timeout": 5000,
            "blocking": false
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(python3 scripts/*)",
      "Bash(git diff*)",
      "Bash(git status*)",
      "Bash(git add*)",
      "Bash(git commit*)",
      "Bash(git push*)",
      "Bash(curl*)",
      "Bash(nexo-ai*)"
    ],
    "deny": []
  }
}
JSON_EOF

# Reemplazar placeholders
sed -i "s/TOWER_IP/$TOWER_IP/g" "$CLAUDE_DIR/settings.local.json"
sed -i "s/TOWER_PORT/$TOWER_PORT/g" "$CLAUDE_DIR/settings.local.json"

ok "settings.local.json creado (adaptado para Termux)"

# .mcp.json — sin playwright (necesita browser), con memory y sequential-thinking
cat > "$REPO_DIR/.mcp.local.json" << 'MCP_EOF'
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory@2026.1.26"],
      "description": "Memoria persistente entre sesiones"
    },
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@2025.12.18"],
      "description": "Razonamiento paso a paso para análisis complejos"
    }
  }
}
MCP_EOF

ok ".mcp.local.json creado (memory + sequential-thinking, sin playwright)"

# ─── 6. Instalar nexo-ai si no existe ────────────────────────
step "6/6 · Cliente nexo-ai"
if command -v nexo-ai >/dev/null 2>&1; then
    ok "nexo-ai ya instalado"
else
    NEXO_AI_DIR="$HOME/nexo_agent/ai"
    if [[ -f "$NEXO_AI_DIR/nexo_ai.sh" ]]; then
        ln -sf "$NEXO_AI_DIR/nexo_ai.sh" "$PREFIX/bin/nexo-ai" 2>/dev/null || true
        ok "nexo-ai vinculado"
    else
        info "nexo-ai no instalado todavía — corre: bash $REPO_DIR/scripts/install_phone_ai.sh"
    fi
fi

# ─── Resumen final ───────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        Instalación completa          ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
echo "  Repo:      $REPO_DIR"
echo "  Config:    $CLAUDE_DIR/settings.local.json"
echo "  MCP:       $REPO_DIR/.mcp.local.json"
echo ""
echo -e "${BOLD}Cómo usar Claude Code desde el teléfono:${NC}"
echo ""
echo -e "  ${CYAN}cd ~/NEXO_SOBERANO${NC}"
echo -e "  ${CYAN}claude${NC}                    # modo interactivo"
echo -e "  ${CYAN}claude -p 'tu pregunta'${NC}   # pregunta directa"
echo -e "  ${CYAN}claude --resume${NC}           # retomar sesión anterior"
echo ""
echo -e "${BOLD}Con acceso a la torre:${NC}"
echo -e "  ${CYAN}nexo-ai 'pregunta'${NC}        # Gemma 4 torre (rápido, $0)"
echo ""
echo -e "${YELLOW}Nota: Recarga el perfil primero:${NC}"
echo -e "  ${CYAN}source $PROFILE${NC}"
echo ""
