#!/data/data/com.termux/files/usr/bin/bash
# NEXO SOBERANO — Auto-start al encender el dispositivo
source ~/.bashrc
sleep 15  # Esperar que WiFi conecte
cd ~
nohup python3 ~/nexo_mobile_agent.py >> /sdcard/nexo_mobile.log 2>&1 &
echo "[NEXO BOOT] Agente iniciado: $(date)" >> /sdcard/nexo_boot.log
