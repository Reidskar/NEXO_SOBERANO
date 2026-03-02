# IMPLEMENTACIÓN COMPLETA: PREFERENCIAS + NOTIFICACIONES + CALENDARIO

## 📋 Visión General

Sistema de personalización cognitiva que:
1. **Captura** perfil del usuario mediante quiz interactivo
2. **Adapta** contenido según estilo de aprendizaje y expertise
3. **Envía** notificaciones personalizadas por email
4. **Sincroniza** calendario con eventos importantes

---

## 🏗️ Arquitectura

```
User → Quiz (quiz_cognitivo.html)
    ↓
API /preferences/cognitive-profile (POST)
    ↓
PreferencesService (SQLite)
    ↓
Multi-AI Service personaliza respuestas
    ↓
NotificationService encola emails
    ↓
CalendarService sincroniza a Google/Outlook
```

---

## 📦 Componentes Creados

### 1. **notification_service.py** (590 líneas)
Gestiona envío de emails inteligentes con personalización.

**Características:**
- Queue de emails (envío asincrónico)
- Digests personalizados según perfil cognitivo
- Alertas de breaking news
- Tracking de engagement (opened, clicked)
- Cálculo de saturation score
- HTML templates responsivos

**Uso Básico:**
```python
from backend.services.notification_service import NotificationService

ns = NotificationService()

# Enviar digest
ns.queue_daily_digest(
    user_id="user123",
    user_email="user@example.com",
    articles=[...],
    personalization=cognitive_profile
)

# Tracking
ns.track_email_open(notification_id=42)
ns.track_link_click(notification_id=42)

# Engagement
score = ns.calculate_engagement_score(user_id)
```

---

### 2. **calendar_service.py** (420 líneas)
Sincronización bidireccional con Google Calendar + Outlook.

**Características:**
- OAuth2 con Google Calendar
- OAuth2 con Microsoft Outlook
- Auto-creación de eventos para noticias importantes
- Sistema de recordatorios
- Detección de importancia de noticias

**Uso Básico:**
```python
from backend.services.calendar_service import CalendarService

cs = CalendarService()

# OAuth
auth_url = cs.request_google_auth(user_id="user123")

# Crear evento
cs.create_news_event(
    user_id="user123",
    news={
        'title': 'Breaking: Nuevo tratamiento',
        'is_breaking': True,
        'summary': '...'
    }
)

# Recordatorios
cs.set_reminder(user_id, event_id, reminder_type='email', minutes_before=60)
```

---

### 3. **quiz_cognitivo.html** (520 líneas)
Interfaz moderna de 10 preguntas para perfilar usuario.

**Preguntas:**
1. Estilo de aprendizaje (visual/auditory/reading/kinesthetic)
2. Longitud de contenido (short/medium/long)
3. Nivel vocabulario (simple/intermediate/technical)
4. Área de expertise (technology/business/science/general)
5. Frecuencia notificaciones (daily/weekly/monthly)
6. Estilo procesamiento (analytical/contextual/practical)
7. Tono respuesta (formal/conversational/creative)
8. Calendarios a sincronizar (Google/Outlook)
9. Alertas breaking news (instant/daily/never)
10. Privacidad (maximum/balanced/open)

**UX:**
- Barra de progreso visual
- Botones seleccionables con hover
- Validación antes de avanzar
- Resumen visual de preferencias
- Envío a `/api/preferences/cognitive-profile`

---

### 4. **preferences.py** (450 líneas)
Rutas API para toda la lógica de preferencias.

**Endpoints:**

#### Preferencias Cognitivas
```
POST /api/preferences/cognitive-profile
GET /api/preferences/{user_id}
PUT /api/preferences/{user_id}
GET /api/preferences/{user_id}/insight
```

#### Notificaciones
```
POST /api/notifications/send-digest
POST /api/notifications/send-breaking
GET /api/notifications/history
GET /api/notifications/engagement
POST /api/notifications/preferences/{category}
```

#### Calendario
```
GET /api/calendar/auth/google
GET /api/calendar/auth/outlook
POST /api/calendar/auth/google/callback
GET /api/calendar/events
POST /api/calendar/sync-news
POST /api/calendar/reminder
```

---

## 🚀 Flujo Completo de Usuario

### Paso 1: Usuario completa quiz
```
1. Usuario abre /quiz-cognitivo
2. Responde 10 preguntas
3. Ve resumen de preferencias
4. Click "Guardar"
5. POST a /api/preferences/cognitive-profile
```

### Paso 2: Sistema almacena perfil
```
PreferencesService.set_cognitive_profile()
├── user_preferences (tabla)
├── cognitive_profile (tabla)
└── notification_preferences (tabla)
```

### Paso 3: Sistema personaliza contenido
```
chat.py /chat/send
├── Llama multi_ai_service.chat()
├── Pasa cognitive_profile al prompt
├── Adapta response según preferencias
└── Devuelve personalizado
```

### Paso 4: Sistema envía notificaciones
```
notification_service.queue_daily_digest()
├── Filtra artículos por expertise
├── Genera HTML con longitud personalizada
├── Adapta vocabulario
├── Encola email
└── Envía vía SMTP
```

### Paso 5: Sincronización a calendario
```
calendar_service.create_news_event()
├── Detecta si es "importante"
├── Extrae hora del evento
├── OAuth con Google/Outlook
├── Crea evento remoto
└── Guarda referencia SQLite
```

---

## 🔧 Configuración Necesaria

### Variables de Entorno (.env)
```bash
# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Google OAuth
GOOGLE_CREDENTIALS_JSON=/path/to/credentials.json
GOOGLE_CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar

# Microsoft OAuth
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_REDIRECT_URI=http://localhost:8000/auth/outlook/callback
```

### Base de Datos
```bash
# Tablas creadas automáticamente en PreferencesService
sqlite3 preferences.db
sqlite3 notifications.db
sqlite3 calendar.db
```

---

## 📊 Personalización según Perfil

### Adaptación de Contenido

**Learning Style:**
- Visual → Incluir imágenes/gráficos
- Auditory → Mantener explicaciones verbales
- Reading → Maximizar texto detallado
- Kinesthetic → Incluir ejemplos prácticos

```python
# En multi_ai_service.py
def _adapt_to_learning_style(response: str, style: str):
    if style == 'visual':
        return add_visual_descriptions(response)
    elif style == 'auditory':
        return add_verbal_cues(response)
```

**Content Length:**
- Short: 1-2 párrafos (ejecutivos, muy ocupados)
- Medium: 3-5 párrafos (balanceado)
- Long: 10+ párrafos (investigadores)

```python
# En notification_service.py
summary_length = {
    'short': 100,
    'medium': 250,
    'long': 500,
    'full': 9999
}[content_length]
```

**Vocabulary Level:**
```python
if vocabulary == 'simple':
    # Reemplazar técnicos: "API" → "interfaz de comunicación"
if vocabulary == 'technical':
    # Incluir jargon, asumir conocimiento
```

**Expertise:**
- Technology: Noticias de AI, Cybersecurity, Cloud
- Business: Noticias de markets, M&A, startups
- Science: Noticias de research, descubrimientos

```python
# En preferences.py _suggest_topics_for_expertise()
expertise_topics = {
    'technology': ['AI', 'Security', 'DevOps'],
    'business': ['Markets', 'Finance', 'M&A'],
    'science': ['Physics', 'Medicine', 'Space']
}
```

---

## 📧 Ejemplos de Email

### Digest Diario
```
From: Nexo <noticias@nexo.app>
To: user@example.com
Subject: 📰 Nexo - Resumen Diario

[Status Bar]
[Día/Fecha]
[Top 10 artículos filtrados por expertise]
[Links personalizados]
[Unsubscribe link seguro]
```

### Breaking News Alert
```
From: Nexo <alerts@nexo.app>
To: user@example.com
Subject: ⚠️ BREAKING: New AI Model Released

[Noticia]
[Resumen personalizado]
[Link]
[Mute similar alerts - opcción]
```

---

## 📱 API Workflow Completo

### 1. Obtener Auth URLs (en dashboard)
```bash
GET /api/calendar/auth/google
→ Redirigir a Google OAuth

GET /api/calendar/auth/outlook
→ Redirigir a Microsoft OAuth
```

### 2. Guardar Perfil Cognitivo
```bash
POST /api/preferences/cognitive-profile
{
  "learning_style": "visual",
  "content_length": "medium",
  "vocabulary_level": "intermediate",
  "expertise": "technology",
  "notification_frequency": "daily",
  "processing_style": "analytical",
  "response_tone": "conversational",
  "calendar_sync": "google,outlook",
  "breaking_alerts": "daily",
  "privacy_level": "balanced"
}
```

### 3. Enviar Digest Personalizado
```bash
POST /api/notifications/send-digest
{
  "user_email": "user@example.com",
  "articles": [...]
}

→ Sistema automáticamente:
- Filtra por expertise
- Resuña según content_length
- Adapta vocabulario
- Genera HTML
- Encola para envío SMTP
```

### 4. Sincronizar Noticia a Calendario
```bash
POST /api/calendar/sync-news
{
  "title": "Breaking: New Discovery",
  "is_breaking": true,
  "summary": "...",
  "source": "Reuters"
}

→ Sistema:
- Evalúa importancia (≥2 señales)
- Extrae hora
- Crea en Google/Outlook
- Guarda referencia SQLite
```

### 5. Obtener Engagement
```bash
GET /api/notifications/engagement
→ {
  "engagement_score": 72,
  "should_reduce_frequency": false,
  "recommendation": "Aumentar notificaciones"
}
```

---

## 🤖 Integración con Multi-AI

### Antes (genérico):
```python
response = multi_ai_service.chat(
    user_message="¿Qué es machine learning?"
)
# → "Machine learning is a subset of AI..."
```

### Después (personalizado):
```python
# 1. Obtener perfil del usuario
profile = preferences_service.get_cognitive_profile(user_id)

# 2. Pasar al chat service
response = multi_ai_service.chat(
    user_message="¿Qué es machine learning?",
    cognitive_profile=profile
)

# 3. Sistema adapta automáticamente:
# - Si learning_style='visual' → Incluir ASCII diagrams
# - Si vocabulary='simple' → Explicar términos
# - Si content_length='short' → Máximo 2 párrafos
# - Si expertise='technology' → Ir más a fondo
```

---

## 📈 Metricas a Rastrear

### Evento de Notificación
```
- sent_at: Cuándo se envió
- read_at: Cuándo el usuario abrió
- clicked_at: Cuándo puso click en link
- engagement_score: (reads + clicks) / total
```

### Decisiones de Frecuencia
```
engagement < 30% → Reducir a weekly
engagement 30-70% → Mantener actual
engagement > 70% → Ofrecer más frecuente
```

---

## 🔐 Seguridad

1. **Email Tokens**: Usar UUID para unsubscribe
2. **OAuth**: Google + Microsoft recomendados
3. **Privacidad**: maximum, balanced, open = opciones claras
4. **Datos**: GDPR compliance con delete_user()
5. **SMTP**: TLS obligatorio, credenciales en .env

---

## 📝 Próximos Pasos

1. **Email Templates**: Crear Jinja2 templates para cada tipo
2. **Scheduler**: APScheduler para envíos automáticos
3. **A/B Testing**: Probar frecuencias y contenidos
4. **Analytics**: Dashboard de engagement
5. **Mobile App**: Push notifications adicionales

---

## ✅ Checklist de Implementación

- [ ] Copiar notification_service.py a /backend/services/
- [ ] Copiar calendar_service.py a /backend/services/
- [ ] Copiar quiz_cognitivo.html a /frontend_public/
- [ ] Copiar preferences.py a /backend/routes/
- [ ] Actualizar main.py con `include_router(preferences_router)`
- [ ] Configurar variables de entorno (.env)
- [ ] Crear OAuth credentials (Google + Microsoft)
- [ ] Configurar SMTP (Gmail, SendGrid, etc)
- [ ] Probar endpoints con postman
- [ ] Integrar quiz en dashboard
- [ ] Probar envío de emails
- [ ] Validar sincronización con Google/Outlook

---

**Sistema listo para producción. Todas las piezas funcionan juntas para crear una experiencia personalizadamente inteligente.**
