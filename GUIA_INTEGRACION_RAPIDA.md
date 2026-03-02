# ⚡ GUÍA RÁPIDA DE INTEGRACIÓN (30 MINUTOS)

## Objetivo
Integrar completamente el sistema de personalización cognitiva + notificaciones + calendario en Nexo Soberano.

---

## ✅ STEP 1: Verify Files Created (2 min)

```bash
# Services
✓ nexo_backend/backend/services/notification_service.py
✓ nexo_backend/backend/services/calendar_service.py
✓ nexo_backend/backend/services/preferences_service.py (ya existía)

# Routes
✓ nexo_backend/backend/routes/preferences.py

# Workers
✓ nexo_backend/workers/email_dispatcher.py

# Frontend
✓ frontend_public/quiz_cognitivo.html
✓ frontend_public/admin_dashboard_v2.html

# Config
✓ nexo_backend/main.py (actualizado)
✓ requirements.txt (actualizado)
✓ .env.example (actualizado)

# Docs
✓ IMPLEMENTACION_PERSONALIZACION.md
✓ SISTEMA_PERSONALIZACION_COMPLETO.md
✓ GUIA_INTEGRACION_RAPIDA.md (este archivo)
```

---

## ✅ STEP 2: Install Dependencies (3 min)

```bash
cd /path/to/NEXO_SOBERANO
pip install -r requirements.txt

# Verify installations
python -c "from apscheduler.schedulers.background import BackgroundScheduler; print('✓ APScheduler OK')"
python -c "from google.oauth2.credentials import Credentials; print('✓ Google OAuth OK')"
python -c "from msgraph.core import GraphClient; print('✓ Microsoft Graph OK')"
```

---

## ✅ STEP 3: Configure Environment (5 min)

```bash
# Copy example config
cp .env.example .env

# Edit .env with your credentials
nano .env

# Critical variables to set:
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza-...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
JWT_SECRET=your-secret-key
```

### Para Gmail SMTP:
1. Habilitar 2FA en tu cuenta Gmail
2. Generar "App Password" en https://myaccount.google.com/apppasswords
3. Usar ese password en SMTP_PASSWORD

### Para Google Calendar OAuth:
1. Ir a https://console.cloud.google.com
2. Crear proyecto "Nexo"
3. Habilitar "Google Calendar API"
4. Crear OAuth 2.0 credentials (Desktop app)
5. Descargar JSON → guardar como `credentials_google.json`
6. Actualizar GOOGLE_CREDENTIALS_JSON en .env

### Para Microsoft Outlook OAuth:
1. Ir a https://portal.azure.com
2. Crear app registration
3. Copiar Tenant ID, Client ID, Client Secret
4. Habilitar "Calendars.ReadWrite" scope
5. Actualizar variables en .env

---

## ✅ STEP 4: Database Initialization (2 min)

```bash
# Los servicios crean tablas automáticamente on first run
# Pero puedes pre-crear si prefieres:

python -c "
from backend.services.preferences_service import PreferencesService
from backend.services.notification_service import NotificationService
from backend.services.calendar_service import CalendarService

ps = PreferencesService()
ns = NotificationService()
cs = CalendarService()

print('✓ Databases initialized')
"
```

---

## ✅ STEP 5: Start Backend (3 min)

```bash
cd nexo_backend

# Terminal 1: Backend FastAPI
python main.py
# Debe mostrar: "Uvicorn running on http://127.0.0.1:8000"
# Verificar: curl http://localhost:8000/health
```

---

## ✅ STEP 6: Start Email Dispatcher (2 min)

```bash
# Terminal 2: Email Worker
cd nexo_backend
python workers/email_dispatcher.py
# Debe mostrar: "✅ Email Dispatcher iniciado"
# Se ejecutará cada 5 min procesando la queue
```

---

## ✅ STEP 7: Test Endpoints (5 min)

### A. Test Preferences API
```bash
# 1. Crear usuario (autenticación primero)
AUTH_TOKEN=$(curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test123!"}' \
  | jq -r '.token')

# 2. Guardar perfil cognitivo
curl -X POST http://localhost:8000/api/preferences/cognitive-profile \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "learning_style": "visual",
    "content_length": "medium",
    "vocabulary_level": "intermediate",
    "expertise": "technology",
    "notification_frequency": "daily",
    "processing_style": "analytical",
    "response_tone": "conversational",
    "breaking_alerts": "daily",
    "privacy_level": "balanced"
  }'

# Response: {"status": "success", "message": "Perfil cognitivo guardado"}
```

### B. Test Notification API
```bash
curl -X POST http://localhost:8000/api/notifications/send-digest \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "test@example.com",
    "articles": [
      {
        "title": "AI Model Released",
        "summary": "OpenAI releases GPT-5",
        "url": "https://example.com"
      }
    ]
  }'

# Response: {"status": "queued", "message": "Digest encolado para envío"}
```

### C. Test Calendar API
```bash
# Obtener auth URL
curl http://localhost:8000/api/calendar/auth/google \
  -H "Authorization: Bearer $AUTH_TOKEN"

# Response: {"auth_url": "https://accounts.google.com/o/oauth2/auth?..."}
```

### D. Test Dispatcher Admin
```bash
curl http://localhost:8000/admin/dispatcher/stats

# Response: {
#   "queue": {"pending": 0, "sent": 1, "failed": 0},
#   "engagement": {"opened": 0, "total": 1, "open_rate": "0.0%"},
#   "running": true
# }
```

---

## ✅ STEP 8: Access Web Interfaces (2 min)

### Quiz de Preferencias
```
http://localhost:8000/quiz-cognitivo
```
- Usuario responde 10 preguntas
- Sistema guarda perfil
- Redirige a dashboard

### Admin Dashboard
```
http://localhost:8000/admin-dashboard-v2
```
- Ver estadísticas de emails
- Monitor dispatcher
- Ver usuarios y engagement
- Gestionar configuración

---

## ✅ STEP 9: Integration Check (3 min)

```bash
# Verificar que todo funciona junto

# 1. Health check
curl http://localhost:8000/health/full

# 2. Ver stats del dispatcher
curl http://localhost:8000/admin/dispatcher/stats

# 3. Verificar que preferences se guardó
AUTH_TOKEN="your-token-here"
curl http://localhost:8000/api/preferences/$USER_ID \
  -H "Authorization: Bearer $AUTH_TOKEN"

# 4. Check logs
tail -f /var/log/nexo/app.log
```

---

## ✅ STEP 10: Production Setup (Optional)

### Para usar en producción:

```bash
# 1. Crear servicio systemd para dispatcher
sudo nano /etc/systemd/system/nexo-dispatcher.service

[Unit]
Description=Nexo Email Dispatcher
After=network.target

[Service]
Type=simple
User=nexo
WorkingDirectory=/opt/nexo
ExecStart=/usr/bin/python3 workers/email_dispatcher.py
Restart=always

[Install]
WantedBy=multi-user.target

# 2. Habilitar servicio
sudo systemctl daemon-reload
sudo systemctl enable nexo-dispatcher
sudo systemctl start nexo-dispatcher

# 3. Verificar
sudo systemctl status nexo-dispatcher
```

---

## 🔧 TROUBLESHOOTING RÁPIDO

### ❌ Error: "SMTP authentication failed"
```bash
# Verificar credenciales en .env
# Para Gmail: Habilitar "Less secure apps" o usar App Password
# Probar con: telnet smtp.gmail.com 587
```

### ❌ Error: "Google OAuth credentials not found"
```bash
# Descargar credentials.json desde Google Cloud Console
# Guardar en directorio especificado en GOOGLE_CREDENTIALS_JSON
```

### ❌ Error: "Database is locked"
```bash
# SQLite issue - reiniciar backend y dispatcher
# pkill -f "uvicorn|email_dispatcher"
# python main.py
```

### ❌ Emails no se envían
```bash
# Verificar que dispatcher está corriendo
curl http://localhost:8000/admin/dispatcher/stats

# Si no está corriendo:
python workers/email_dispatcher.py

# Forzar procesamiento inmediato:
curl -X POST http://localhost:8000/admin/dispatcher/process-now
```

### ❌ Quiz no guarda preferencias
```bash
# Verificar token JWT válido
# Revisar headers en browser: Authorization: Bearer <token>
# Check API response: curl -v (ver status code)
```

---

## 📚 ARCHIVOS CLAVE

| Archivo | Propósito | Status |
|---------|-----------|--------|
| `notification_service.py` | Envío de emails | ✅ PRONTO |
| `calendar_service.py` | Sync Google/Outlook | ✅ LISTO |
| `email_dispatcher.py` | Worker background | ✅ LISTO |
| `preferences.py` | Rutas API | ✅ LISTO |
| `quiz_cognitivo.html` | Quiz UI | ✅ LISTO |
| `admin_dashboard_v2.html` | Admin UI | ✅ LISTO |
| `.env.example` | Config template | ✅ LISTO |
| `main.py` | FastAPI entry | ✅ ACTUALIZADO |
| `requirements.txt` | Dependencies | ✅ ACTUALIZADO |

---

## 🎯 FLUJO DE USUARIO COMPLETO

```
1. Usuario abre http://localhost:8000/quiz-cognitivo
   ↓
2. Completa 10 preguntas en 2 minutos
   ↓
3. Click "Guardar" → POST /api/preferences/cognitive-profile
   ↓
4. Sistema almacena perfil en SQLite
   ↓
5. Usuario recibe noticias personalizadas
   ↓
6. Sistema automáticamente:
   - Filtra por expertise
   - Adapta longitud de contenido
   - Personaliza vocabulario
   - Envía por email
   - Sincróniza a Google Calendar
   ↓
7. Dispatcher procesa queue cada 5 min
   ↓
8. Admin monitorea todo en dashboard
```

---

## ✨ QUÉ OBTIENES

✅ Sistema de preferencias cognitivas  
✅ Personalización inteligente de contenido  
✅ Email marketing automatizado  
✅ Sincronización con calendario (Google + Outlook)  
✅ Tracking de engagement  
✅ Admin dashboard en tiempo real  
✅ Production-ready architecture  

---

## ⏱️ TIMELINE TOTAL

- Step 1 (Verify): 2 min
- Step 2 (Install): 3 min
- Step 3 (Config): 5 min
- Step 4 (Database): 2 min
- Step 5 (Backend): 3 min
- Step 6 (Dispatcher): 2 min
- Step 7 (Test): 5 min
- Step 8 (Demo): 2 min
- Step 9 (Check): 3 min
- Step 10 (Prod): Optional

**TOTAL: ~27 minutos hasta producción ▶️**

---

## 📞 NEXT STEPS

✓ Sistema implementado  
→ Próximo: Integración con news feeds / RSS  
→ Próximo: A/B testing de frecuencias  
→ Próximo: Mobile push notifications  

---

**¡Listo para usar!**

**Nexo Soberano - Personal Intelligence Platform** 🧠
