import subprocess
import json
from datetime import datetime
import os

ADB = r"C:\Users\Admn\Downloads\scrcpy-win64-v3.3.4\scrcpy-win64-v3.3.4\adb.exe"

def adb(cmd):
    try:
        r = subprocess.run([ADB, "shell"] + cmd.split(),
                          capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return f"ERROR: {e}"

props = {
    "sim1_state":      adb("getprop gsm.sim.state"),
    "sim2_state":      adb("getprop gsm.sim.state.2"),
    "sim1_operator":   adb("getprop gsm.operator.alpha"),
    "sim2_operator":   adb("getprop gsm.operator.alpha.2"),
    "sim1_numeric":    adb("getprop gsm.operator.numeric"),
    "sim2_numeric":    adb("getprop gsm.operator.numeric.2"),
    "network_type":    adb("getprop gsm.network.type"),
    "airplane_mode":   adb("settings get global airplane_mode_on"),
    "mobile_data_1":   adb("settings get global mobile_data"),
    "mobile_data_2":   adb("settings get global mobile_data2"),
    "preferred_net":   adb("settings get global preferred_network_mode"),
    "preferred_net2":  adb("settings get global preferred_network_mode1"),
    "data_roaming":    adb("settings get global data_roaming"),
    "wifi_state":      adb("settings get global wifi_on"),
}

# APN actual
apn_raw = adb("content query --uri content://telephony/carriers/preferapn")
props["apn_actual"] = apn_raw

# Señal
signal = adb("dumpsys telephony.registry")
for line in signal.split("\n"):
    if any(k in line for k in ["SignalStrength","ServiceState","DataState","NetworkType"]):
        props.setdefault("signal_info", []).append(line.strip())

reporte = {
    "timestamp": datetime.now().isoformat(),
    "dispositivo": adb("getprop ro.product.model"),
    "android": adb("getprop ro.build.version.release"),
    "diagnostico": props,
    "problemas_detectados": [],
    "soluciones": []
}

# Análisis automático
if "LOADED" in props["sim1_state"] and not props["sim1_operator"]:
    reporte["problemas_detectados"].append("SIM1 Movistar: detectada pero sin operador registrado")
    reporte["soluciones"].append("Aplicar APN Movistar Chile manualmente")

if props["preferred_net"] not in ["9","20","22"]:
    reporte["problemas_detectados"].append(f"Modo de red incorrecto: {props['preferred_net']}")
    reporte["soluciones"].append("Cambiar a modo LTE/3G/2G automático (valor 9)")

if props["airplane_mode"] == "1":
    reporte["problemas_detectados"].append("Modo avión ACTIVO")
    reporte["soluciones"].append("Desactivar modo avión")

if props["mobile_data_1"] == "0":
    reporte["problemas_detectados"].append("Datos móviles SIM1 desactivados")
    reporte["soluciones"].append("Activar datos móviles")

os.makedirs("logs", exist_ok=True)
with open("logs/diagnostico_sim.json", "w", encoding="utf-8") as f:
    json.dump(reporte, f, indent=2, ensure_ascii=False)

log.info(json.dumps(reporte, indent=2, ensure_ascii=False))
