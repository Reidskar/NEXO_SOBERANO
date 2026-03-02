$ErrorActionPreference = 'Stop'

$projectDir = 'C:\Users\Admn\Desktop\NEXO_SOBERANO\agente_postulaciones'
$pythonExe = 'C:\Users\Admn\Desktop\NEXO_SOBERANO\.venv\Scripts\python.exe'
$taskName = 'NEXO_Agente_Postulaciones_4h'

if (!(Test-Path $pythonExe)) {
  throw "No existe Python esperado: $pythonExe"
}

$action = New-ScheduledTaskAction -Execute $pythonExe -Argument 'main.py --once' -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Agente inteligente de postulaciones cada 4 horas' -Force
Write-Output "Task registrada: $taskName"
