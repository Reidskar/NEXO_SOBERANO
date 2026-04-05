"""
backend/routes/phone_setup.py
Ruta /phone/setup.sh — configuración completa del agente NEXO para Termux.

Funcionalidades incluidas:
  - Heartbeat cada 30s con métricas del dispositivo
  - Polling de comandos cada 10s (bidireccional)
  - Comandos ejecutables: notify, location, screenshot, exec, ping,
    volume, torch, vibrate, open_url, alarm
  - Termux:Boot auto-inicio al encender el teléfono
  - Wake lock para prevenir que Android mate el proceso
  - Notificación persistente en barra de notificaciones con estado
  - Reconexión automática si el backend no responde
  - CLI interactiva: nexo "pregunta" → responde con IA
"""
import os
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["phone"])


def _cfg():
    tower_ip     = os.getenv("NEXO_TOWER_IP", "192.168.100.22")
    railway      = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
    backend_rw   = f"https://{railway}" if railway else ""
    api_key      = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
    return tower_ip, backend_rw, api_key


@router.get("/phone/setup.sh", response_class=PlainTextResponse, include_in_schema=False)
async def phone_setup_sh():
    tower_ip, backend_rw, api_key = _cfg()

    return f'''#!/data/data/com.termux/files/usr/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  NEXO SOBERANO — Configuración completa del agente Termux   ║
# ╚══════════════════════════════════════════════════════════════╝
# Uso: curl http://{tower_ip}:8000/phone/setup.sh | bash
# Nota: PIDFILE siempre en $HOME — nunca en /tmp/ (no existe en Termux)
set -e

AGENT_DIR="$HOME/nexo_agent"
LOG_DIR="$AGENT_DIR/logs"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  NEXO SOBERANO — Phone Agent Setup                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Paquetes Termux ──────────────────────────────────────────────────────
echo "[1/7] Instalando paquetes Termux..."
pkg install -y python python-pip curl termux-api 2>/dev/null || true

# ── 2. Dependencias Python ──────────────────────────────────────────────────
echo "[2/7] Instalando dependencias Python..."
pip install --quiet requests psutil 2>/dev/null || pip install requests psutil

# ── 3. Estructura de directorios ────────────────────────────────────────────
echo "[3/7] Creando estructura..."
mkdir -p "$AGENT_DIR" "$LOG_DIR" "$HOME/.termux/boot"

# ── 4. Agente principal ─────────────────────────────────────────────────────
echo "[4/7] Escribiendo agente principal..."
cat > "$AGENT_DIR/nexo_mobile_agent.py" << \'PYEOF\'
#!/usr/bin/env python3
"""
NEXO SOBERANO — Phone Agent completo para Termux
Bidireccional: reporta métricas + recibe y ejecuta comandos
"""
import json, logging, os, subprocess, sys, time, uuid
from datetime import datetime, timezone
import requests, psutil

# ─── Paths (todo en $HOME, nunca /tmp) ──────────────────────────────────────
_BASE    = os.path.join(os.path.expanduser("~"), "nexo_agent")
_LOGFILE = os.path.join(_BASE, "logs", "agent.log")
_PIDFILE = os.path.join(_BASE, "nexo_agent.pid")

os.makedirs(os.path.join(_BASE, "logs"), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(_LOGFILE)],
)
logger = logging.getLogger("NEXO_PHONE")

# ─── Configuración desde .env ────────────────────────────────────────────────
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
    os.getenv("NEXO_BACKEND",           "http://192.168.100.22:8000"),
    os.getenv("NEXO_BACKEND_TAILSCALE", ""),
    os.getenv("NEXO_BACKEND_RAILWAY",   ""),
] if b]
AGENT_ID      = os.getenv("NEXO_AGENT_ID", "phone-agent-01")
POLL_INTERVAL = int(os.getenv("NEXO_POLL", "30"))
CMD_INTERVAL  = int(os.getenv("NEXO_CMD_POLL", "10"))
API_KEY       = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")
NOTIFY_ICON   = "phone"

_HEADERS = {{"X-API-Key": API_KEY, "Content-Type": "application/json"}}

# ─── Backend auto-detección ─────────────────────────────────────────────────
def get_backend():
    for url in BACKENDS:
        try:
            if requests.get(f"{{url}}/health", timeout=3).status_code < 500:
                return url
        except Exception:
            pass
    return BACKENDS[0]

BACKEND = get_backend()

# ─── Métricas ────────────────────────────────────────────────────────────────
def get_metrics() -> dict:
    m = {{
        "agent_id":  AGENT_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tipo":      "phone",
        "backend":   BACKEND,
    }}
    try:
        m["cpu_pct"] = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        m["ram_pct"]      = mem.percent
        m["ram_total_mb"] = round(mem.total / 1e6, 1)
    except Exception as e:
        m["psutil_error"] = str(e)
    for cmd, key in [("termux-battery-status", "bat"), ("termux-wifi-connectioninfo", "wifi")]:
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

# ─── Ejecutor de comandos ────────────────────────────────────────────────────
def _run_cmd(args: list, **kw) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=10, **kw)
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return str(e)

def _notify(title: str, content: str, ongoing: bool = False):
    args = ["termux-notification",
            "--title", title,
            "--content", content,
            "--id", "99",
            "--icon", NOTIFY_ICON]
    if ongoing:
        args.append("--ongoing")
    try:
        subprocess.run(args, timeout=5)
    except Exception:
        pass

def execute_command(cmd: dict):
    ctype   = cmd.get("type", "")
    payload = cmd.get("payload", {{}})
    logger.info(f"Ejecutando comando: {{ctype}}")

    if ctype == "notify":
        _notify(
            payload.get("title", "NEXO"),
            payload.get("content", ""),
        )

    elif ctype == "ping":
        # Reportar que está vivo
        requests.post(
            f"{{BACKEND}}/api/mobile/heartbeat",
            json={{**get_metrics(), "ping_response": True, "cmd_id": cmd.get("id")}},
            headers=_HEADERS, timeout=8,
        )

    elif ctype == "location":
        out = _run_cmd(["termux-location", "-p", "gps", "-r", "once"])
        try:
            loc = json.loads(out)
            requests.post(
                f"{{BACKEND}}/api/webhooks/ingest",
                json={{
                    "tenant_slug": "globe",
                    "type":  "phone_location",
                    "title": f"{{AGENT_ID}} — ubicación GPS",
                    "body":  json.dumps({{"lat": loc.get("latitude"), "lng": loc.get("longitude"),
                                         "accuracy": loc.get("accuracy"), "alt": loc.get("altitude")}}),
                    "severity": 0.3,
                }},
                headers=_HEADERS, timeout=8,
            )
        except Exception as e:
            logger.warning(f"location: {{e}}")

    elif ctype == "screenshot":
        out_path = os.path.join(_BASE, "screenshot.png")
        _run_cmd(["termux-screenshot", "-f", out_path])
        _notify("NEXO Screenshot", f"Guardado en {{out_path}}")

    elif ctype == "volume":
        # payload: {{"stream": "music", "volume": 5}}
        stream = payload.get("stream", "music")
        vol    = payload.get("volume", 5)
        _run_cmd(["termux-volume", stream, str(vol)])

    elif ctype == "torch":
        # payload: {{"on": true/false}}
        state = "on" if payload.get("on", True) else "off"
        _run_cmd(["termux-torch", state])

    elif ctype == "vibrate":
        duration = str(payload.get("duration_ms", 500))
        _run_cmd(["termux-vibrate", "-d", duration, "-f"])

    elif ctype == "open_url":
        url = payload.get("url", "")
        if url:
            _run_cmd(["termux-open-url", url])

    elif ctype == "alarm":
        hour   = payload.get("hour", 7)
        minute = payload.get("minute", 0)
        msg    = payload.get("message", "NEXO Alarm")
        _run_cmd(["termux-alarm", "-h", str(hour), "-m", str(minute), "-n", msg])

    elif ctype == "exec":
        # Ejecuta un comando shell — solo si la API key es correcta
        shell_cmd = payload.get("command", "")
        if shell_cmd:
            out = _run_cmd(["bash", "-c", shell_cmd])
            logger.info(f"exec output: {{out[:200]}}")
            _notify("NEXO exec", out[:100])

    elif ctype == "set_backend":
        global BACKEND
        BACKEND = payload.get("url", BACKEND)
        logger.info(f"Backend actualizado a: {{BACKEND}}")

    else:
        logger.warning(f"Comando desconocido: {{ctype}}")

# ─── Notificación de estado persistente ─────────────────────────────────────
def update_status_notification(metrics: dict):
    bat  = metrics.get("bateria_pct", "?")
    cpu  = metrics.get("cpu_pct",     "?")
    wifi = metrics.get("wifi_ssid",   "?")
    _notify(
        "◎ NEXO SOBERANO — Agente activo",
        f"BAT {bat}%  CPU {cpu}%  WiFi {wifi}",
        ongoing=True,
    )

# ─── Loop principal ──────────────────────────────────────────────────────────
def main():
    global BACKEND
    # Escribir PID
    with open(_PIDFILE, "w") as f:
        f.write(str(os.getpid()))

    logger.info(f"NEXO Phone Agent v2 — PID {{os.getpid()}}")
    logger.info(f"Backend: {{BACKEND}}")
    logger.info(f"Agent ID: {{AGENT_ID}}")
    logger.info(f"Heartbeat: {{POLL_INTERVAL}}s  Comandos: {{CMD_INTERVAL}}s")

    _notify("◎ NEXO SOBERANO", "Agente de teléfono iniciado", ongoing=True)

    errors = 0
    last_heartbeat = 0
    last_cmd_poll  = 0

    while True:
        now = time.time()

        # ── Heartbeat (cada POLL_INTERVAL) ──────────────────────────────────
        if now - last_heartbeat >= POLL_INTERVAL:
            try:
                metrics = get_metrics()
                r = requests.post(
                    f"{{BACKEND}}/api/mobile/heartbeat",
                    json=metrics, headers=_HEADERS, timeout=10,
                )
                if r.status_code == 200:
                    data = r.json()
                    errors = 0
                    last_heartbeat = now
                    update_status_notification(metrics)
                    # Ejecutar comandos que vengan en la respuesta del heartbeat
                    for cmd in data.get("commands", []):
                        try:
                            execute_command(cmd)
                        except Exception as e:
                            logger.error(f"Error ejecutando {{cmd.get('type')}}: {{e}}")
                    logger.info(
                        f"HB OK  CPU:{{metrics.get('cpu_pct')}}%"
                        f"  BAT:{{metrics.get('bateria_pct')}}%"
                        f"  WiFi:{{metrics.get('wifi_ssid')}}"
                    )
                else:
                    logger.warning(f"HB HTTP {{r.status_code}}")
                    errors += 1
            except Exception as e:
                logger.error(f"HB error: {{e}}")
                errors += 1
                if errors >= 5:
                    logger.warning("Re-detectando backend...")
                    BACKEND = get_backend()
                    errors = 0

        # ── Polling de comandos (cada CMD_INTERVAL) ──────────────────────────
        if now - last_cmd_poll >= CMD_INTERVAL:
            try:
                r = requests.get(
                    f"{{BACKEND}}/api/mobile/commands/{{AGENT_ID}}",
                    headers=_HEADERS, timeout=6,
                )
                if r.status_code == 200:
                    for cmd in r.json().get("commands", []):
                        try:
                            execute_command(cmd)
                        except Exception as e:
                            logger.error(f"Cmd error: {{e}}")
                last_cmd_poll = now
            except Exception:
                pass  # silencioso — el heartbeat ya maneja errores

        time.sleep(2)

if __name__ == "__main__":
    main()
\'PYEOF\'
chmod +x "$AGENT_DIR/nexo_mobile_agent.py"

# ── 5. Scripts de control ────────────────────────────────────────────────────
echo "[5/7] Creando scripts de control..."

cat > "$AGENT_DIR/start.sh" << \'SHEOF\'
#!/data/data/com.termux/files/usr/bin/bash
AGENT_DIR="$HOME/nexo_agent"
PIDFILE="$AGENT_DIR/nexo_agent.pid"
LOGFILE="$AGENT_DIR/logs/agent.log"
mkdir -p "$AGENT_DIR/logs"

# Matar proceso anterior
[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; rm -f "$PIDFILE"

# Wake lock: evita que Android duerma el proceso
termux-wake-lock 2>/dev/null || true

echo "[NEXO] Iniciando agente..."
nohup python "$AGENT_DIR/nexo_mobile_agent.py" >> "$LOGFILE" 2>&1 &
echo $! > "$PIDFILE"
echo "[NEXO] Corriendo — PID: $(cat "$PIDFILE")"
echo "[NEXO] Logs: tail -f $LOGFILE"
\'SHEOF\'
chmod +x "$AGENT_DIR/start.sh"

cat > "$AGENT_DIR/stop.sh" << \'SHEOF\'
#!/data/data/com.termux/files/usr/bin/bash
PIDFILE="$HOME/nexo_agent/nexo_agent.pid"
termux-wake-unlock 2>/dev/null || true
[ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null && rm -f "$PIDFILE" \
    && termux-notification-remove 99 2>/dev/null \
    && echo "[NEXO] Agente detenido." \
    || echo "[NEXO] No estaba corriendo."
\'SHEOF\'
chmod +x "$AGENT_DIR/stop.sh"

cat > "$AGENT_DIR/status.sh" << \'SHEOF\'
#!/data/data/com.termux/files/usr/bin/bash
PIDFILE="$HOME/nexo_agent/nexo_agent.pid"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "[NEXO] ✅ Corriendo — PID: $(cat "$PIDFILE")"
    tail -5 "$HOME/nexo_agent/logs/agent.log"
else
    echo "[NEXO] ❌ No está corriendo"
fi
\'SHEOF\'
chmod +x "$AGENT_DIR/status.sh"

# CLI interactiva: nexo "pregunta al agente IA"
cat > "$AGENT_DIR/nexo" << \'SHEOF\'
#!/data/data/com.termux/files/usr/bin/bash
source "$HOME/nexo_agent/.env" 2>/dev/null
BACKEND="${{NEXO_BACKEND:-http://192.168.100.22:8000}}"
QUERY="${{1:-status}}"
echo "[NEXO] Preguntando al agente: $QUERY"
curl -s -X POST "$BACKEND/api/agente/" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: ${{NEXO_API_KEY:-nexo_dev_key_2025}}" \
     -d "{{\\"query\\":\\"$QUERY\\"}}" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get(\'respuesta\',d))" 2>/dev/null || echo "Backend no disponible"
\'SHEOF\'
chmod +x "$AGENT_DIR/nexo"
# Acceso global
ln -sf "$AGENT_DIR/nexo" "$HOME/.local/bin/nexo" 2>/dev/null || \
    ln -sf "$AGENT_DIR/nexo" "/data/data/com.termux/files/usr/bin/nexo" 2>/dev/null || true

# ── 6. Auto-inicio en boot (Termux:Boot) ────────────────────────────────────
echo "[6/7] Configurando auto-inicio en boot..."
cat > "$HOME/.termux/boot/nexo-agent.sh" << \'SHEOF\'
#!/data/data/com.termux/files/usr/bin/bash
# Auto-inicia el agente NEXO cuando el teléfono enciende
# Requiere la app Termux:Boot instalada desde F-Droid
sleep 15   # esperar red
termux-wake-lock
bash "$HOME/nexo_agent/start.sh"
\'SHEOF\'
chmod +x "$HOME/.termux/boot/nexo-agent.sh"

# ── 7. Archivo .env ─────────────────────────────────────────────────────────
echo "[7/7] Configurando .env..."
if [ ! -f "$AGENT_DIR/.env" ]; then
    cat > "$AGENT_DIR/.env" << \'ENVEOF\'
# ─── NEXO Phone Agent — Configuración ───────────────────────────────────────
# Backend local (Torre en la misma red WiFi)
NEXO_BACKEND=http://{tower_ip}:8000

# Backend Tailscale (si usas VPN Tailscale para acceso remoto)
NEXO_BACKEND_TAILSCALE=

# Backend Railway (producción)
NEXO_BACKEND_RAILWAY={backend_rw}

# Identificador único de este dispositivo
NEXO_AGENT_ID=phone-agent-01

# Intervalo de heartbeat en segundos (métricas → torre)
NEXO_POLL=30

# Intervalo de polling de comandos en segundos (torre → phone)
NEXO_CMD_POLL=10

# API Key (debe coincidir con NEXO_API_KEY en la torre)
NEXO_API_KEY={api_key}
\'ENVEOF\'
    echo "  ✓ .env creado"
else
    echo "  ✓ .env ya existe (no se sobreescribe)"
fi

# ── Resumen ──────────────────────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  ✅ NEXO Phone Agent configurado correctamente            ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  Iniciar:  bash ~/nexo_agent/start.sh                    ║"
echo "║  Detener:  bash ~/nexo_agent/stop.sh                     ║"
echo "║  Estado:   bash ~/nexo_agent/status.sh                   ║"
echo "║  Logs:     tail -f ~/nexo_agent/logs/agent.log           ║"
echo "║  CLI IA:   nexo \\"pregunta al agente\\"                    ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  Config:   nano ~/nexo_agent/.env                        ║"
echo "║  Auto-boot:instala Termux:Boot desde F-Droid             ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  Comandos desde la Torre:                                ║"
echo "║  POST /api/mobile/command/phone-agent-01                 ║"
echo "║  {{\"type\":\"notify\",\"payload\":{{\"title\":\"T\",\"content\":\"C\"}}}}  ║"
echo "║  Tipos: notify | ping | location | screenshot |          ║"
echo "║         volume | torch | vibrate | open_url | exec       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "→ Iniciando agente ahora..."
bash "$AGENT_DIR/start.sh"
'''

