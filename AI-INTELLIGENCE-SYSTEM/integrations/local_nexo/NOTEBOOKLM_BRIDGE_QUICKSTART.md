# NotebookLM Bridge — Quickstart Local

## 1) Arrancar servicio

```powershell
.\.venv\Scripts\python.exe AI-INTELLIGENCE-SYSTEM\scripts\notebooklm_bridge_api.py
```

Servicio: `http://127.0.0.1:8011`

## 2) Probar salud

```powershell
Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:8011/health' -Method GET
```

## 3) Crear libreta (dry-run)

```powershell
$h=@{'X-NEXO-API-KEY'='NEXO_LOCAL_2026_OK';'Content-Type'='application/json'}
Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:8011/notebooks/create' -Method POST -Headers $h -Body '{"name":"NEXO-Geopolitica","description":"Base de investigación"}'
```

## 4) Sincronizar carpeta Drive (dry-run)

```powershell
$h=@{'X-NEXO-API-KEY'='NEXO_LOCAL_2026_OK';'Content-Type'='application/json'}
Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:8011/drive/sync-folder' -Method POST -Headers $h -Body '{"folder_id":"TU_FOLDER_ID","notebook_id":"nb_demo","max_files":50}'
```

## 5) Generar resumen con guardrails

```powershell
$h=@{'X-NEXO-API-KEY'='NEXO_LOCAL_2026_OK';'Content-Type'='application/json'}
Invoke-RestMethod -UseBasicParsing -Uri 'http://127.0.0.1:8011/summaries/generate' -Method POST -Headers $h -Body '{"notebook_id":"nb_demo","objective":"Riesgo logístico en Medio Oriente","strict_evidence":true}'
```

## Nota

Este bridge está en modo `dry-run` por defecto para validar contratos y seguridad.
Cuando conectes `notebooklm-py/Playwright`, mantén la interfaz y solo cambia el adaptador interno.
