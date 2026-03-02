# Agente de Postulación Inteligente (CV-aware + Multi-dispositivo)

Proyecto listo para VS Code con personalización por CV y coordinación entre dispositivos (`DEVICE_ID` + estado compartido) para evitar duplicar postulaciones.

## Archivos
- `README.md`: guía rápida
- `config.py`: configuración central
- `main.py`: orquestador (cada 4 horas o `--once`)
- `scraper.py`: extracción de ofertas
- `filtro.py`: reglas de sueldo/distancia/keywords
- `evaluador_ia.py`: scoring con Claude (o heurística fallback)
- `postulador.py`: postulación automática con Playwright
- `notificacion.py`: push a Android por ntfy
- `registro.py`: CSV + Google Sheets + seen jobs
- `cv_profile.example.json`: plantilla de perfil CV
- `requirements.txt`: dependencias

## Instalación
Desde `agente_postulaciones`:

```bash
pip install -r requirements.txt
playwright install chromium
```

## Arranque rápido producción
1. Copia y completa variables:

```bash
copy .env.example .env
```

2. Prueba un ciclo:

```bash
python main.py --once
```

### Activar modo real controlado (1 postulación por ciclo)
Con credenciales ya cargadas en `.env`:

```powershell
powershell -ExecutionPolicy Bypass -File enable_live_mode.ps1
python main.py --once
```

3. Registrar tarea cada 4 horas (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File register_task.ps1
```

## Configuración mínima
Define variables de entorno (o exporta en terminal):

- `COMPUTRABAJO_EMAIL`
- `COMPUTRABAJO_PASSWORD`
- `SEARCH_URL`
- `ANTHROPIC_API_KEY` (opcional)
- `NTFY_TOPIC`
- `DEVICE_ID` (importante para multi-dispositivo)
- `CV_PROFILE_FILE` (perfil CV en JSON)
- `STATE_DIR` (opcional, para compartir estado entre equipos)

## Perfil CV (postulaciones acorde a tu experiencia)
1. Crea tu perfil:

```bash
copy cv_profile.example.json cv_profile.json
```

2. Completa `cv_profile.json` con tu experiencia, skills, roles objetivo y exclusiones.

3. Ajusta `.env`:

```dotenv
CV_PROFILE_FILE=cv_profile.json
```

## Uso
Un ciclo:

```bash
python main.py --once
```

Modo continuo (cada 4h):

```bash
python main.py
```

## Multi-dispositivo inteligente
- Cada equipo usa `DEVICE_ID` distinto.
- Si configuras `STATE_DIR` compartido (OneDrive/Drive), el estado queda sincronizado.
- `seen_jobs.json` evita repetir postulaciones del mismo job entre equipos.
- `postulaciones_log.csv` guarda trazabilidad por dispositivo.
- `run_state.json` deja heartbeat/estado del último ciclo.
- `agent_runtime.log` conserva historial operativo del agente.
- `cycle.lock` evita que dos equipos procesen al mismo tiempo.

## Recomendación operativa
Primero corre con `DRY_RUN=true` hasta validar login/selectores de Computrabajo.
Si cambia el HTML del portal, ajusta selectores en `scraper.py` y `postulador.py`.
