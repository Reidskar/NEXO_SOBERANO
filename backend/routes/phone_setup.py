"""
backend/routes/phone_setup.py
Ruta /phone/setup.sh — script de configuración para Termux (Android).

Uso en Termux:
    curl http://<TORRE_IP>:8000/phone/setup.sh | bash
"""
import os
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["phone"])


def _build_setup_script() -> str:
    tower_ip = os.getenv("NEXO_TOWER_IP", "192.168.100.22")
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    backend_railway = f"https://{railway_domain}" if railway_domain else ""
    api_key = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")

    return f'''#!/data/data/com.termux/files/usr/bin/bash
# ╔══════════════════════════════════════════════════════╗
# ║  NEXO SOBERANO — Phone Agent Setup para Termux      ║
# ╚══════════════════════════════════════════════════════╝
# NOTA: PIDFILE y LOGS siempre en $HOME/nexo_agent/ — nunca en /tmp/
set -e

AGENT_DIR="$HOME/nexo_agent"
LOG_DIR="$AGENT_DIR/logs"
PIDFILE="$AGENT_DIR/nexo_agent.pid"

echo "[1/6] Verificando Termux..."
pkg install -y python python-pip curl 2>/dev/null || true

echo "[2/6] Instalando dependencias Python..."
pip install --quiet requests psutil 2>/dev/null || pip install requests psutil

echo "[3/6] Creando estructura de archivos..."
mkdir -p "$AGENT_DIR" "$LOG_DIR"

echo "[4/6] Escribiendo agente principal..."
cat > "$AGENT_DIR/nexo_mobile_agent.py" << \'PYEOF\'
#!/usr/bin/env python3
"""NEXO SOBERANO — Phone Agent para Termux"""
import os, time, json, logging, subprocess
from datetime import datetime, timezone
import requests, psutil

_BASE = os.path.join(os.path.expanduser("~"), "nexo_agent")
_LOG  = os.path.join(_BASE, "logs", "agent.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(_LOG)],
)
logger = logging.getLogger("NEXO_PHONE")

def _load_env():
    p = os.path.join(_BASE, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

BACKENDS = [b for b in [
    os.getenv("NEXO_BACKEND",          "http://192.168.100.22:8000"),
    os.getenv("NEXO_BACKEND_TAILSCALE",""),
    os.getenv("NEXO_BACKEND_RAILWAY",  ""),
] if b]
AGENT_ID      = os.getenv("NEXO_AGENT_ID", "phone-agent-01")
POLL_INTERVAL = int(os.getenv("NEXO_POLL", "30"))
API_KEY       = os.getenv("NEXO_API_KEY",  "nexo_dev_key_2025")

def get_backend():
    for url in BACKENDS:
        try:
            if requests.get(f"{{url}}/health", timeout=3).status_code < 500:
                return url
        except Exception:
            pass
    return BACKENDS[0]

def get_metrics():
    m = {{"agent_id": AGENT_ID,
         "timestamp": datetime.now(timezone.utc).isoformat(),
         "tipo": "phone"}}
    try:
        m["cpu_pct"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        m["ram_pct"] = mem.percent
        m["ram_total_mb"] = round(mem.total / 1e6, 1)
    except Exception as e:
        m["psutil_error"] = str(e)
    for cmd, key in [("termux-battery-status","bat"),("termux-wifi-connectioninfo","wifi")]:
        try:
            r = subprocess.run([cmd], capture_output=True, text=True, timeout=4)
            if r.returncode == 0:
                d = json.loads(r.stdout)
                if key == "bat":
                    m["bateria_pct"]    = d.get("percentage", -1)
                    m["bateria_estado"] = d.get("status", "unknown")
                    m["cargando"]       = d.get("plugged", False)
                else:
                    m["wifi_ssid"] = d.get("ssid", "unknown")
                    m["wifi_rssi"] = d.get("rssi", 0)
        except Exception:
            pass
    return m

def main():
    backend = get_backend()
    logger.info(f"NEXO Phone Agent arriba — backend: {{backend}}")
    errors = 0
    while True:
        try:
            metrics = get_metrics()
            r = requests.post(
                f"{{backend}}/api/mobile/heartbeat",
                json=metrics,
                headers={{"X-API-Key": API_KEY}},
                timeout=10,
            )
            if r.status_code == 200:
                logger.info(f"Heartbeat OK CPU:{{metrics.get(\'cpu_pct\')}}% BAT:{{metrics.get(\'bateria_pct\')}}%")
                errors = 0
            else:
                logger.warning(f"HTTP {{r.status_code}}: {{r.text[:80]}}")
                errors += 1
        except Exception as e:
            logger.error(f"Error: {{e}}")
            errors += 1
        if errors >= 10:
            logger.critical("10 errores consecutivos — re-detectando backend...")
            backend = get_backend()
            errors = 0
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
\'PYEOF\'
chmod +x "$AGENT_DIR/nexo_mobile_agent.py"

echo "[5/6] Configurando scripts de control..."

cat > "$AGENT_DIR/start.sh" << \'SHEOF\'
#!/data/data/com.termux/files/usr/bin/bash
# start.sh — NEXO Phone Agent
# NOTA: PIDFILE en $HOME/nexo_agent/ (Termux no puede escribir en /tmp/)
AGENT_DIR="$HOME/nexo_agent"
PIDFILE="$AGENT_DIR/nexo_agent.pid"
LOGFILE="$AGENT_DIR/logs/agent.log"

echo "[NEXO Phone] Iniciando agente..."

if [ -f "$PIDFILE" ]; then
    OLD="$(cat "$PIDFILE")"
    kill "$OLD" 2>/dev/null || true
    rm -f "$PIDFILE"
fi

mkdir -p "$AGENT_DIR/logs"
nohup python "$AGENT_DIR/nexo_mobile_agent.py" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "[NEXO Phone] PID: $(cat "$PIDFILE") — logs en $LOGFILE"
\'SHEOF\'
chmod +x "$AGENT_DIR/start.sh"

cat > "$AGENT_DIR/stop.sh" << \'SHEOF\'
#!/data/data/com.termux/files/usr/bin/bash
PIDFILE="$HOME/nexo_agent/nexo_agent.pid"
[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null && rm -f "$PIDFILE" && echo "[NEXO] Detenido." || echo "No estaba corriendo."
\'SHEOF\'
chmod +x "$AGENT_DIR/stop.sh"

echo "[6/6] Creando .env del agente..."
if [ ! -f "$AGENT_DIR/.env" ]; then
    cat > "$AGENT_DIR/.env" << \'ENVEOF\'
NEXO_BACKEND=http://{tower_ip}:8000
NEXO_BACKEND_RAILWAY={backend_railway}
NEXO_AGENT_ID=phone-agent-01
NEXO_POLL=30
NEXO_API_KEY={api_key}
GEMINI_API_KEY=
\'ENVEOF\'
    echo "  .env creado — edita con: nano $AGENT_DIR/.env"
else
    echo "  .env ya existe, no se sobreescribe"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  NEXO Phone Agent configurado            ║"
echo "║                                          ║"
echo "║  Iniciar:  bash ~/nexo_agent/start.sh   ║"
echo "║  Detener:  bash ~/nexo_agent/stop.sh    ║"
echo "║  Logs:     tail -f ~/nexo_agent/logs/agent.log"
echo "║  Config:   nano ~/nexo_agent/.env        ║"
echo "╚══════════════════════════════════════════╝"
'''


@router.get("/phone/setup.sh", response_class=PlainTextResponse, include_in_schema=False)
async def phone_setup_sh():
    """
    Devuelve el script bash de configuración del agente móvil para Termux.
    Uso: curl http://<TORRE_IP>:8000/phone/setup.sh | bash
    """
    return _build_setup_script()
