"""
NEXO Mobile Agent - Xiaomi 14T Pro
Funciones:
- Monitor de salud del sistema (API + Railway + Supabase)
- Detector de alertas en tiempo real via WebSocket
- Sistema de aprendizaje: registra qué consultas hace el usuario
- Monitor de stream (detecta si OBS está activo)
- Notificaciones nativas Android via termux-api
- Auto-reporte cada 5 minutos al backend
"""

import os, time, json, threading, requests, subprocess
import websocket
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.table import Table

# Intentar cargar .env desde la ubicación de Termux o local
env_path = Path.home() / "nexo-agent/config/.env"
if not env_path.exists():
    env_path = Path(".env")
    
load_dotenv(env_path)

NEXO_URL = os.getenv("NEXO_LOCAL_URL", os.getenv("NEXO_RAILWAY_URL"))
API_KEY = os.getenv("NEXO_API_KEY")
AGENT_ID = os.getenv("AGENT_ID", "mobile_agent")
INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))

console = Console()

# --- SISTEMA DE APRENDIZAJE LIGERO ---
class LearningSystem:
    def __init__(self):
        self.log_path = Path.home() / "nexo-agent/cache/interactions.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def record(self, event_type: str, data: dict):
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "agent": AGENT_ID,
            "type": event_type,
            "data": data
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def sync_to_backend(self):
        """Envía interacciones acumuladas al backend periódicamente"""
        while True:
            try:
                if self.log_path.exists():
                    lines = self.log_path.read_text().strip().split("\n")
                    if lines and lines[0]:
                        # Siempre enviamos un latido (heartbeat) si hay datos o simplemente para decir que estamos vivos
                        requests.post(
                            f"{NEXO_URL}/api/webhooks/ingest",
                            json={
                                "tenant_slug": "demo", 
                                "type": "agent_heartbeat",
                                "title": f"Xiaomi check-in: {len(lines)} eventos",
                                "body": "\n".join(lines[-50:]),
                                "severity": 0.1
                            },
                            headers={"X-API-Key": API_KEY},
                            timeout=10
                        )
                        self.log_path.write_text("")
                else:
                    # Latido vacío si no hay logs
                    requests.post(
                        f"{NEXO_URL}/api/webhooks/ingest",
                        json={
                            "tenant_slug": "demo", 
                            "type": "agent_heartbeat",
                            "title": "Xiaomi Pulse",
                            "body": "Agent is alive and monitoring.",
                            "severity": 0.05
                        },
                        headers={"X-API-Key": API_KEY},
                        timeout=10
                    )
            except Exception as e:
                console.print(f"[red]Error en sync: {e}[/red]")
            
            time.sleep(300)  # Sincronizar cada 5 minutos

# --- MONITOR DE SERVICIOS ---
class ServiceMonitor:
    def __init__(self, learner: LearningSystem):
        self.learner = learner
        self.status = {}
    
    def check_api(self) -> dict:
        endpoints = [
            ("health", f"{NEXO_URL}/health"),
            ("dashboard", f"{NEXO_URL}/api/dashboard/health"),
            ("railway", os.getenv("NEXO_RAILWAY_URL", "") + "/health"),
        ]
        results = {}
        for name, url in endpoints:
            if not url or url.startswith("/"):
                continue
            try:
                r = requests.get(url, timeout=5,
                                 headers={"X-API-Key": API_KEY})
                results[name] = "✅" if r.status_code == 200 else f"⚠️ {r.status_code}"
            except Exception as e:
                results[name] = f"❌ offline"
        return results
    
    def check_device(self) -> dict:
        """Métricas del propio Xiaomi via termux-api"""
        metrics = {}
        try:
            bat = subprocess.run(["termux-battery-status"],
                                 capture_output=True, text=True, timeout=3)
            metrics["battery"] = json.loads(bat.stdout).get("percentage", "?")
        except:
            metrics["battery"] = "N/A"
        try:
            wifi = subprocess.run(["termux-wifi-connectioninfo"],
                                  capture_output=True, text=True, timeout=3)
            data = json.loads(wifi.stdout)
            metrics["wifi"] = data.get("ssid", "?")
            metrics["signal"] = data.get("rssi", "?")
        except:
            metrics["wifi"] = "N/A"
        return metrics
    
    def notify(self, title: str, message: str, priority="default"):
        """Notificación nativa Android"""
        try:
            subprocess.run([
                "termux-notification",
                "--title", f"NEXO: {title}",
                "--content", message,
                "--priority", priority,
                "--id", "nexo_monitor"
            ], timeout=3)
        except:
            pass
    
    def run_loop(self):
        last_status = {}
        while True:
            try:
                api_status = self.check_api()
                device = self.check_device()
                
                # Detectar cambios de estado
                for svc, status in api_status.items():
                    if last_status.get(svc) != status:
                        if "❌" in status:
                            self.notify(f"{svc} CAÍDO", 
                                       f"{svc} no responde", "high")
                        elif "✅" in status and "❌" in last_status.get(svc, ""):
                            self.notify(f"{svc} recuperado",
                                       f"{svc} volvió a responder")
                        self.learner.record("status_change", 
                                           {"service": svc, "status": status})
                
                last_status = api_status.copy()
                self.status = {**api_status, **device}
                
            except Exception as e:
                self.learner.record("error", {"msg": str(e)})
            
            time.sleep(INTERVAL)

# --- WEBSOCKET ALERTS ---
class AlertListener:
    def __init__(self, monitor: ServiceMonitor):
        self.monitor = monitor
        ws_url = NEXO_URL.replace("http", "ws") + "/ws/alerts/demo"
        self.ws_url = ws_url
    
    def on_message(self, ws, message):
        try:
            alert = json.loads(message)
            self.monitor.notify(
                alert.get("titulo", "Alerta"),
                alert.get("descripcion", "")[:100],
                "high" if float(alert.get("severidad", 0)) > 0.7 else "default"
            )
        except:
            pass
    
    def start(self):
        def run():
            while True:
                try:
                    ws = websocket.WebSocketApp(
                        self.ws_url,
                        on_message=self.on_message
                    )
                    ws.run_forever(ping_interval=30, ping_timeout=10)
                except:
                    pass
                time.sleep(10)
        threading.Thread(target=run, daemon=True).start()

# --- DASHBOARD TERMINAL ---
def build_table(monitor: ServiceMonitor) -> Table:
    table = Table(title=f"NEXO Agent — {AGENT_ID}",
                  show_header=True, header_style="bold cyan")
    table.add_column("Servicio", style="dim")
    table.add_column("Estado")
    for k, v in monitor.status.items():
        table.add_row(k, str(v))
    return table

# --- MAIN ---
if __name__ == "__main__":
    learner = LearningSystem()
    monitor = ServiceMonitor(learner)
    alerts = AlertListener(monitor)
    
    console.print("[bold green]NEXO Mobile Agent iniciando...[/bold green]")
    
    # Threads paralelos
    threading.Thread(target=monitor.run_loop, daemon=True).start()
    threading.Thread(target=learner.sync_to_backend, daemon=True).start()
    alerts.start()
    
    # Dashboard live en terminal
    with Live(build_table(monitor), refresh_per_second=0.5) as live:
        while True:
            live.update(build_table(monitor))
            time.sleep(2)
