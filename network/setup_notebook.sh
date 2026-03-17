#!/bin/bash
# Ejecutar en el NOTEBOOK para unirlo al stack El Anarcocapital
# Usage: bash setup_notebook.sh <TAILSCALE_AUTH_KEY>

TAILSCALE_KEY="${1:-}"
PC_IP="192.168.100.22"
PC_TAILSCALE="100.112.238.97"
BACKEND_PORT=8000

echo "=== El Anarcocapital — Setup Notebook ==="

# 1. Tailscale
if ! command -v tailscale &>/dev/null; then
    echo "[1/4] Instalando Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

if [ -n "$TAILSCALE_KEY" ]; then
    sudo tailscale up --authkey="$TAILSCALE_KEY" --hostname="notebook-anarco"
    echo "[OK] Tailscale conectado"
else
    echo "[!] Corre: sudo tailscale up --authkey=TU_KEY --hostname=notebook-anarco"
fi

# 2. SSH server
if command -v apt &>/dev/null; then
    sudo apt install -y openssh-server 2>/dev/null
    sudo systemctl enable ssh && sudo systemctl start ssh
    echo "[OK] SSH habilitado"
fi

# 3. Agregar ruta al backend del PC principal
echo "[2/4] Verificando acceso al backend..."
if curl -s --max-time 3 "http://$PC_TAILSCALE:$BACKEND_PORT/api/health" | grep -q "online"; then
    echo "[OK] Backend El Anarcocapital accesible en http://$PC_TAILSCALE:$BACKEND_PORT"
else
    echo "[!] Backend no accesible — verificar que el PC principal esté corriendo"
fi

# 4. Crear acceso rápido
cat > ~/nexo.sh << 'EOF'
#!/bin/bash
PC="100.112.238.97"
echo "Backend: http://$PC:8000"
echo "API:     http://$PC:8000/api/docs"
echo "Qdrant:  http://$PC:6333/dashboard"
alias nexo-health="curl -s http://$PC:8000/api/health | python3 -m json.tool"
alias nexo-ingest="curl -X POST http://$PC:8000/api/media/ingest-youtube"
EOF
chmod +x ~/nexo.sh
echo "[OK] Acceso rápido en ~/nexo.sh"

echo ""
echo "=== LISTO ==="
echo "Backend: http://$PC_TAILSCALE:$BACKEND_PORT"
echo "Para probar: curl http://$PC_TAILSCALE:$BACKEND_PORT/api/health"
