import json
import subprocess
import os

# Obtener IP Tailscale de la Torre
try:
    result = subprocess.run(["tailscale", "ip", "-4"],
                           capture_output=True, text=True, check=True)
    torre_ip = result.stdout.strip()
except Exception as e:
    log.info(f"Error obteniendo IP de Tailscale: {e}")
    torre_ip = "100.104.152.43" # Fallback a IP conocida

mesh = {
    "devices": {
        "torre": {
            "nombre": "PC Torre",
            "rol": "servidor_central",
            "ip_local": "192.168.100.22",
            "ip_tailscale": torre_ip,
            "servicios": ["fastapi:8000", "docker", "ollama:11434"]
        },
        "xiaomi": {
            "nombre": "Xiaomi 14T Pro",
            "rol": "agente_movil",
            "ip_tailscale": "100.112.23.72",
            "servicios": ["termux", "nexo_mobile_agent"]
        },
        "dell": {
            "nombre": "Dell Latitude",
            "rol": "consola_portatil",
            "ip_tailscale": "pendiente",
            "servicios": ["moonlight", "kde_connect"]
        }
    },
    "nexo_backend": f"http://{torre_ip}:8000",
    "verificacion": {
        "torre_health": f"http://{torre_ip}:8000/api/health",
        "xiaomi_heartbeat": "http://100.112.23.72:8765/heartbeat"
    }
}

os.makedirs("config", exist_ok=True)
with open("config/mesh_devices.json", "w", encoding="utf-8") as f:
    json.dump(mesh, f, indent=2, ensure_ascii=False)

log.info(json.dumps(mesh, indent=2, ensure_ascii=False))
