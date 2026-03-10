import os

script_content = r'''# setup_autostart.ps1
$scriptPath = "C:\Users\Admn\Desktop\NEXO_SOBERANO\scripts\start_local_server.ps1"
$taskName = "NexoLocalServer"
Write-Host "Configurando inicio automatico..."
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File \"$scriptPath\""
$trigger = New-ScheduledTaskTrigger -AtLogon
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force
Write-Host "Tarea programada registrada."
'''

ps1_path = os.path.join("scripts", "install_autostart.ps1")
with open(ps1_path, "w", encoding="utf-8") as f:
    f.write(script_content)

print(f"Script generado en {ps1_path}")
