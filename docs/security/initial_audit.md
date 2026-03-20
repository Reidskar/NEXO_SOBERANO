# NEXO SOBERANO — Auditoría de Seguridad Inicial
Ejecutada por: nexo-sentinel v1.0
Fecha: 2026-03-20

## Estado inicial del stack
### 1. Escaneo de secrets en código
Se ejecutó un escaneo recursivo en archivos `*.py` buscando los patrones `api_key=`, `token=`, y prefijos conocidos (`AIza`, `sk-`, `AAAA`).
**Resultado:** CERO (0) secrets vulnerados detectados en texto plano. Las ocurrencias detectadas corresponden estrictamente a:
- Llamadas correctas a través de variables de entorno (ej: `os.getenv("GEMINI_API_KEY")`, `_env("X_API_KEY")`).
- Archivos de configuración template como `deploy.py` conteniendo placeholders de muestra (`sk-your-key-here`, `AIza-your-key-here`).
- Reglas Regex del propio stack de logger de NEXO_CORE diseñadas para REDACTAR (censurar) las llaves automáticamente, no llaves vivas.

### 2. Verificación de puertos en docker-compose
Se analizó el mapeo de puertos en `docker-compose.yml`.
**Resultado:** Los siguientes puertos están bajo el formato **"X:X"** y se encuentran expuestos públicamente al host (0.0.0.0):
- `8000:8000` (Backend FastAPI)
- `8080:3000` (Frontend)
- `80:80`, `443:443` (Nginx)

*Nota del Sentinel:* Exponer los puertos de Nginx (80/443) es correcto. Sin embargo, Backend y Frontend deberían estar referenciados como `127.0.0.1:X:X` para impedir su acceso externo ajeno a través de sus puertos base, forzando todo tráfico a fluir obligatoriamente por Nginx/Cloudflare o el Tailscale VPN Localhost.

## Pendientes críticos
- [ ] Agregar SecurityHeadersMiddleware a main.py
- [ ] Activar rate limiting con slowapi
- [ ] Desactivar /docs y /redoc en producción
- [ ] Verificar RLS en Supabase
- [ ] Verificar TLS en elanarcocapital.com
- [ ] Instalar fail2ban en Torre (Sprint 2.7)
- [ ] Ejecutar npm audit en discord_bot/

## Vulnerabilidades Dependabot conocidas
- 11 vulnerabilidades detectadas en dependencias externas del repo vinculadas en la plataforma de GitHub (6 high, 2 moderate, 3 low).
