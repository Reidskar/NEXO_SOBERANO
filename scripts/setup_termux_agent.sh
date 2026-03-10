#!/data/data/com.termux/files/usr/bin/bash
# NEXO SOBERANO - Agente Móvil v1.0
# Xiaomi 14T Pro Setup Script

echo "=== NEXO Mobile Agent Setup ==="

# Actualizar paquetes base (mínimos, sin bloat)
pkg update -y && pkg upgrade -y

# Instalar solo lo esencial
pkg install -y python git curl wget nano openssh termux-api

# Instalar termux-api app (para acceso a sensores, notificaciones, etc.)
# El usuario debe instalar com.termux.api desde F-Droid

# Python ligero — sin torch, sin modelos pesados
pip install --quiet \
  requests \
  httpx \
  schedule \
  psutil \
  websocket-client \
  python-dotenv \
  rich \
  watchdog

# Crear estructura de directorios
mkdir -p ~/nexo-agent/{logs,cache,config,monitors}

# Crear archivo de configuración
cat > ~/nexo-agent/config/.env << 'EOF'
NEXO_LOCAL_URL=http://192.168.100.22:8000
NEXO_RAILWAY_URL=https://nexo-soberano.up.railway.app
NEXO_API_KEY=nexo_dev_key_2025
TENANT_SLUG=demo
AGENT_ID=xiaomi_14t_pro
CHECK_INTERVAL=30
EOF

echo "✅ Dependencias instaladas"
