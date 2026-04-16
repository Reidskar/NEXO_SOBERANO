#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# NEXO SOBERANO — Setup del Agente Móvil en Termux (Xiaomi)
# Controla y es controlado por la Torre vía Tailscale/LAN
#
# Uso: curl http://192.168.100.22:8080/phone/setup.sh | bash
#   o: curl http://[IP_TAILSCALE_TORRE]:8080/phone/setup.sh | bash
# ============================================================

set -e

TORRE_LAN="192.168.100.22"
TORRE_TAILSCALE="100.112.238.97"
BACKEND_PORT="8080"
AGENT_ID="xiaomi-14t-pro-1"
API_KEY="NEXO_LOCAL_2026_OK"
REPO_URL="https://github.com/Reidskar/NEXO_SOBERANO.git"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   NEXO SOBERANO — Mobile Agent Setup     ║"
echo "║   Xiaomi 14T Pro ↔ Torre                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Paquetes base ─────────────────────────────────────────
echo "[1/6] Actualizando Termux y paquetes base..."
pkg update -y -q
pkg install -y python git curl openssh termux-api 2>/dev/null

# ── 2. Dependencias Python ───────────────────────────────────
echo "[2/6] Instalando dependencias Python..."
pip install --quiet --upgrade pip
pip install --quiet requests psutil

# ── 3. Clonar o actualizar el agente ─────────────────────────
echo "[3/6] Obteniendo agente NEXO..."
AGENT_DIR="$HOME/nexo_agent"

if [ -d "$AGENT_DIR" ]; then
    echo "   Directorio existente — actualizando..."
    cd "$AGENT_DIR"
    git pull --quiet origin main 2>/dev/null || true
else
    echo "   Clonando repo (solo agente móvil)..."
    git clone --quiet --depth 1 --filter=blob:none \
        --sparse "$REPO_URL" "$AGENT_DIR" 2>/dev/null || {
        # Fallback: descarga solo el archivo del agente
        mkdir -p "$AGENT_DIR/mobile_agent"
        curl -s "http://${TORRE_LAN}:${BACKEND_PORT}/api/mobile/agent-script" \
            -o "$AGENT_DIR/mobile_agent/nexo_mobile_agent.py" 2>/dev/null || \
        curl -s "http://${TORRE_TAILSCALE}:${BACKEND_PORT}/api/mobile/agent-script" \
            -o "$AGENT_DIR/mobile_agent/nexo_mobile_agent.py" || true
    }
    cd "$AGENT_DIR"
fi

# ── 4. Archivo de configuración ──────────────────────────────
echo "[4/6] Configurando variables de entorno..."
ENV_FILE="$HOME/.nexo_env"
cat > "$ENV_FILE" <<EOF
export NEXO_AGENT_ID="${AGENT_ID}"
export NEXO_API_KEY="${API_KEY}"
export NEXO_POLL=15
export NEXO_BACKEND_LAN="http://${TORRE_LAN}:${BACKEND_PORT}"
export NEXO_BACKEND_TAILSCALE="http://${TORRE_TAILSCALE}:${BACKEND_PORT}"
EOF

# Agregar al .bashrc si no está
grep -q "nexo_env" "$HOME/.bashrc" 2>/dev/null || \
    echo "source $HOME/.nexo_env" >> "$HOME/.bashrc"

source "$ENV_FILE"

# ── 5. Script de inicio rápido ───────────────────────────────
echo "[5/6] Creando script de inicio..."
cat > "$HOME/nexo_start.sh" <<'STARTSCRIPT'
#!/data/data/com.termux/files/usr/bin/bash
source $HOME/.nexo_env
echo "🚀 Iniciando NEXO Mobile Agent..."
echo "   Torre LAN:      $NEXO_BACKEND_LAN"
echo "   Torre Tailscale: $NEXO_BACKEND_TAILSCALE"
echo "   Agent ID:        $NEXO_AGENT_ID"
echo ""
cd $HOME/nexo_agent
python mobile_agent/nexo_mobile_agent.py
STARTSCRIPT
chmod +x "$HOME/nexo_start.sh"

# Script de parada
cat > "$HOME/nexo_stop.sh" <<'STOPSCRIPT'
#!/data/data/com.termux/files/usr/bin/bash
pkill -f nexo_mobile_agent.py && echo "✅ Agente detenido" || echo "No había agente corriendo"
STOPSCRIPT
chmod +x "$HOME/nexo_stop.sh"

# ── 6. Habilitar ADB vía WiFi (para scrcpy desde la Torre) ───
echo "[6/6] Habilitando ADB inalámbrico para control desde Torre..."
echo ""
echo "   Para que la Torre pueda controlarte por ADB/scrcpy:"
echo "   1. En el celu: Ajustes → Opciones de desarrollo → Depuración inalámbrica"
echo "   2. Anota el puerto que aparece (ej: 45678)"
echo "   3. En la Torre ejecuta:"
echo "      adb connect [IP_CELU]:45678"
echo "      adb pair [IP_CELU]:[PUERTO_PAR]"
echo ""

# Intentar activar ADB sobre TCP automáticamente (requiere root o permisos)
termux-open-url "intent://com.android.settings.APPLICATION_DEVELOPMENT_SETTINGS" 2>/dev/null || true

# ── Verificar conectividad con la Torre ─────────────────────
echo "══════════════════════════════════════════"
echo "Verificando conexión con la Torre..."
echo ""

BACKEND=""
if curl -sf "http://${TORRE_LAN}:${BACKEND_PORT}/health" > /dev/null 2>&1; then
    BACKEND="http://${TORRE_LAN}:${BACKEND_PORT}"
    echo "✅ Torre LAN:      $BACKEND (CONECTADO)"
elif curl -sf "http://${TORRE_TAILSCALE}:${BACKEND_PORT}/health" > /dev/null 2>&1; then
    BACKEND="http://${TORRE_TAILSCALE}:${BACKEND_PORT}"
    echo "✅ Torre Tailscale: $BACKEND (CONECTADO)"
else
    echo "⚠️  Torre no alcanzable ahora — verifica que el backend esté corriendo"
    echo "   LAN:       http://${TORRE_LAN}:${BACKEND_PORT}"
    echo "   Tailscale: http://${TORRE_TAILSCALE}:${BACKEND_PORT}"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║         Setup completado ✅               ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Comandos disponibles:"
echo "  ~/nexo_start.sh  → Iniciar agente (conecta a la Torre)"
echo "  ~/nexo_stop.sh   → Detener agente"
echo ""
echo "Iniciando agente ahora..."
echo ""
source "$ENV_FILE"
cd "$AGENT_DIR"
python mobile_agent/nexo_mobile_agent.py
