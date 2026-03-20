import psutil
import json
import requests
from datetime import datetime

metrics = {
    "timestamp": datetime.now().isoformat(),
    "cpu_percent": psutil.cpu_percent(interval=2),
    "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
    "ram_used_gb": round(psutil.virtual_memory().used / 1e9, 2),
    "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 2),
    "ram_percent": psutil.virtual_memory().percent,
    "disk_used_gb": round(psutil.disk_usage('/').used / 1e9, 2),
    "disk_free_gb": round(psutil.disk_usage('/').free / 1e9, 2)
}
print(json.dumps(metrics, indent=2))

COSTOS_MENSUALES_USD = {
    "railway_hosting": {"valor_usd": 5.00},
    "dominio_elanarcocapital": {"valor_usd": 15.00}
}
try:
    usd_clp = requests.get("https://mindicador.cl/api/dolar").json()["serie"][0]["valor"]
    for servicio, datos in COSTOS_MENSUALES_USD.items():
        gasto_diario_clp = (datos["valor_usd"] * usd_clp) / 30
        print(f"Gasto diario {servicio}: ${gasto_diario_clp:.2f} CLP")
except Exception as e:
    print(f"Error calculando costos: {e}")
