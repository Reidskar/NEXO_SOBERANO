# NEXO SOBERANO

This repository contains the core initialization scripts for the NEXO Soberano system.

## Setup

1. **Configure Python environment** (a virtual environment will be created automatically when you open the workspace):
   ```powershell
   # this happens automatically when you use VS Code python extension, or run any Python command
   python -m venv .venv
   ```

2. **Install dependencies**:
   ```powershell
   C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe -m pip install -r requirements.txt
   ```

3. **Start the system**:
   - Run one of these commands from the workspace root:
     ```powershell
     python nexo_soberano.py
     # or
     python asistente_nexo.py  # wrapper around nexo_soberano
     ```
   - If you use the configured virtual environment, you can invoke it directly:
     ```powershell
     C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe nexo_soberano.py
     ```

4. **Run the API bridge (FastAPI server)**:
   - Make sure dependencies are installed (`fastapi`, `uvicorn`, `pydantic`)
   - Start the server from the workspace root with:
     ```powershell
     uvicorn api_puente:app --reload
     ```
   - Visit `http://127.0.0.1:8000/docs` in your browser to interact with the endpoints.

The scripts will create the `NEXO_SOBERANO` directory structure, initialize the SQLite vault `boveda.db`, and populate the bitacora logs (MD, JSON and DOCX).

## Créditos OSS (integraciones referenciadas)

NEXO SOBERANO integra ideas/herramientas del ecosistema open source con adaptación propia para operación unificada.

- WebOSINT — https://github.com/C3n7ral051nt4g3ncy/WebOSINT
- SN0INT — https://github.com/kpcyrd/sn0int
- GeoSentinel — https://github.com/h9zdev/GeoSentinel
- Sightline — https://github.com/ni5arga/sightline
- WorldMonitor — https://github.com/koala73/worldmonitor
- Intercept — https://github.com/smittix/intercept
- Ground Station — https://github.com/sgoudelis/ground-station
- TVScreener — https://github.com/deepentropy/tvscreener

Uso en NEXO: estas referencias se emplean como base de capacidades OSINT y monitoreo; el flujo de decisiones, correlación, analítica y UI operativa se ejecuta en la arquitectura propia de NEXO.

## Go-live rápido (hoy)

1. Copia variables desde `.env.example` a `.env` y completa mínimo:
  - `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`
  - `GOOGLE_STITCH_WEBHOOK_URL`
  - `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `ADMIN_EMAIL`
  - `NEXO_PUBLIC_BASE_URL`

2. Ejecuta backend:
  ```powershell
  C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
  ```

3. Ejecuta validación integral y genera reporte:
  ```powershell
  C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe scripts/validate_go_live.py --base-url http://127.0.0.1:8000
  ```

4. (Opcional) incluir pruebas con envío email y Grok share:
  ```powershell
  C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe scripts/validate_go_live.py --base-url http://127.0.0.1:8000 --include-email --include-grok-share
  ```

5. Ejecutar monitor X manual (one-shot):
  ```powershell
  C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe scripts/run_x_monitor.py --once --limit 20
  ```

6. Programar monitor X cada 15 min:
  ```powershell
  C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe scripts/install_x_monitor_task.py --interval-minutes 15 --limit 20
  ```
  Para modo servicio (sin sesión abierta), ejecutar como Administrador:
  ```powershell
  C:/Users/Admn/Desktop/NEXO_SOBERANO/.venv/Scripts/python.exe scripts/install_x_monitor_task.py --interval-minutes 15 --limit 20 --as-system
  ```

El reporte consolidado queda en `logs/go_live_validation_last.json`.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'docx'`**
  Run `pip install python-docx` or `pip install -r requirements.txt`.

- If you ever want to reset the environment, delete the `.venv` directory and re-run step 1.
