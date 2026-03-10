# Copia el agente al teléfono via ADB
adb push scripts/setup_termux_agent.sh /sdcard/setup_termux.sh
adb push scripts/nexo_mobile_agent.py /sdcard/nexo_agent.py
# Nota: La ruta de destino final en Termux depende del usuario, pero adb shell puede mover archivos si tiene permisos.
# Intentamos mover a la carpeta de datos de Termux via ADB shell
adb shell "cp /sdcard/setup_termux.sh /data/data/com.termux/files/home/setup_termux.sh"
adb shell "mkdir -p /data/data/com.termux/files/home/nexo-agent"
adb shell "cp /sdcard/nexo_agent.py /data/data/com.termux/files/home/nexo-agent/nexo_agent.py"
Write-Host "Archivos copiados al telefono"
Write-Host "Abre Termux y ejecuta: bash ~/setup_termux.sh"
