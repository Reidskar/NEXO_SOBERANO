# 🚀 NEXO SOBERANO - GUÍA DE OPERACIÓN COMPLETA

Sistema omnicanal inteligente con Copilot (OpenAI) + Gemini (Google) integrados.

---

## 📋 PRE-REQUISITOS

### 1. Claves de API

**OpenAI / Copilot:**
- Ve a https://platform.openai.com/api/keys
- Genera una clave
- Guarda en variable de entorno: `OPENAI_API_KEY`

**Google Gemini:**
- Ve a https://makersuite.google.com/app/apikeys
- Genera una clave
- Guarda en variable de entorno: `GEMINI_API_KEY`

**Telegram (opcional):**
- Habla con @BotFather en Telegram
- Crea un bot
- Guarda el token en `TELEGRAM_TOKEN`

### 2. Configuración de variables de entorno

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "sk-xxxxx"
$env:GEMINI_API_KEY = "AIza-xxxxx"
$env:TELEGRAM_TOKEN = "123456:ABC-xyz"
```

**Windows (cmd, persistente):**
```
setx OPENAI_API_KEY "sk-xxxxx"
setx GEMINI_API_KEY "AIza-xxxxx"
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-xxxxx"
export GEMINI_API_KEY="AIza-xxxxx"
```

---

## 🚀 CÓMO EJECUTAR

### Paso 1: Instalar dependencias

```bash
cd nexo_backend
pip install -r requirements.txt
```

### Paso 2: Iniciar backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verás algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Paso 3: Servir frontend chat

En otra terminal (desde obs_control o nexo_backend):

```bash
cd ../obs_control
python -m http.server 8080
```

### Paso 4: Acceder al chat

Abre en tu navegador:
```
http://localhost:8080/chat.html
```

---

## 💬 CÓMO USAR EL CHAT

### Interface

- **Izquierda**: Panel de control (modelos, canales, acciones)
- **Centro**: Chat conversacional
- **Abajo**: Input para escribir

### Elegir modelo

Botones arriba en sidebar:
- `Copilot`: OpenAI (más potente)
- `Gemini`: Google (más rápido)
- `Auto`: selecciona automáticamente el mejor

### Enviar por canales omnicanal

1. Selecciona un canal (Telegram, WhatsApp, Facebook, Instagram)
2. El chat comprenderá automáticamente que quieres enviar algo
3. La IA analizará tu intención y enviará por el canal correcto

**Ejemplos de intención:**

- "Mándalo por Telegram" → intención: `send_telegram`
- "Publica en Instagram" → intención: `send_instagram`
- "Guarda esto en el diario" → intención: `guardar_diario`
- "¿Qué hay en el diario?" → intención: `leer_diario`

### Historial y contexto

El sistema **recuerda la conversación** automáticamente:
- Última tema de conversación
- Preferencia de modelo elegida
- Historial de últimos 20 mensajes
- Análisis cognitivo de cada entrada (intent, entities, sentimiento)

El diario se guarda en SQLite y es accesible sin perder nada.

---

## 📊 ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────┐
│   CHAT INTERFACE (chat.html)                │
│   - Sidebar: modelos, canales, acciones    │
│   - Chat area: historial conversacional    │
│   - Input: enviar mensajes                 │
└────────────┬────────────────────────────────┘
             │ REST API / WebSocket
             ▼
┌─────────────────────────────────────────────┐
│   BACKEND FASTAPI (main.py)                 │
├─────────────────────────────────────────────┤
│  /chat/send         → envía msg a IA        │
│  /chat/history      → lee historial         │
│  /chat/context      → contexto del usuario  │
│  /chat/ws           → WebSocket tiempo real │
│  /omni/send         → envía por canal       │
│  /omni/webhook      → recibe de Telegram... │
│  /agente/consultar  → consultas RAG         │
└────────────┬────────────────────────────────┘
             │
    ┌────────┴────────┬──────────────┐
    ▼                 ▼              ▼
┌─────────────────────────────────────────────┐
│   SERVICIOS DE IA                           │
├─────────────────────────────────────────────┤
│  MultiAIService                             │
│  - chat_openai()    → Copilot              │
│  - chat_gemini()    → Gemini               │
│  - analyze()        → análisis cognitivo    │
│                                             │
│  ConversationService                        │
│  - get_conversation() → historial          │
│  - add_message()      → guarda             │
│  - get_context()      → contexto           │
│                                             │
│  OmniChannelManager                         │
│  - receive()        → recibe de canales    │
│  - send()           → envía a canales      │
└─────────────────────────────────────────────┘
    │
    ├─── SQLite (conversations.db)
    ├─── SQLite (diary.db)
    └─── Telegram Bot, Facebook API, etc.
```

---

## 📱 INTEGRACIÓN OMNICANAL

### Telegram

1. Crea un bot con @BotFather
2. Pega el token en `TELEGRAM_TOKEN`
3. El sistema empieza a escuchar automáticamente

Los mensajes que recibas en Telegram:
1. Se pasan a la IA
2. Se archivan en el diario
3. La IA responde automáticamente por el mismo canal

### WhatsApp / Facebook / Instagram

Estos requieren configuración de webhooks. Para cada uno:

1. Crea una app en Meta/Twilio
2. Configura el webhook URL: `http://tu-ip:8000/omni/webhook/{channel}`
3. El sistema recibirá los datos

*Los adaptadores están listos en `omni_service.py`, solo falta completar los detalles API de cada plataforma.*

---

## 🧠 CAPACIDADES COGNITIVAS

### Análisis automático

Cada mensaje es analizado para extraer:
- **intent**: qué quiere hacer (chat, enviar, guardar, consultar)
- **entidades**: qué se menciona (usuario, canal, tema)
- **sentimiento**: positivo/neutral/negativo
- **acción**: qué hacer siguiente

### Contexto progresivo

El sistema mantiene:
- Tema actual de conversación
- Decisiones previas del usuario
- Preferencias (modelo favorito, canal preferido)
- Historial accesible para referencia

### Memoria multi-usuario

Cada usuario tiene:
- Chat history separado
- Contexto único
- Preferencias personales
- Diario privado

---

## 🔌 INTEGRACIÓN CON OBS (StreamHub)

Si quieres usar el sistema con OBS Studio para transmisión:

1. Abre `panel.html` en tablet (no el chat.html)
2. Controla escenas, overlays, macros desde panel táctico
3. El chat.html está diseñado para funcionar paralelo

---

## 🔐 SEGURIDAD (IMPORTANTE)

- **Nunca** compartas las claves de API públicamente
- **Nunca** guardes credenciales en código
- Usa variables de entorno
- En producción: implementa autenticación JWT
- Protege los webhooks con HMAC verification

---

## 🐛 TROUBLESHOOTING

### Error: "sin llaves de API"

```python
# Si no aparecen las llaves, verificar:
import os
print(os.getenv("OPENAI_API_KEY"))  # debe mostrar algo
```

### Error: "conexión rechazada a localhost:8000"

- Verificar que uvicorn está corriendo
- Verificar puerto 8000 no está bloqueado
- En Windows Firewall, permitir Python

### Error: "WebSocket no conecta"

- Usar REST API en lugar de WebSocket al principio
- `/chat/send` funciona siempre

### Telegram no recibe mensajes

- Verificar token correcto
- Verificar bot está en un grupo/chat
- Revisar logs del backend

---

## 📈 PRÓXIMOS PASOS

1. **Guardar conversaciones en JSON/CSV**
2. **Dashboard de analytics** (tokens gastados, intenciones más comunes)
3. **Integración con más IAs** (Claude, Llama, etc.)
4. **Automatización**: programar envíos a canales
5. **Voz**: chat por audio con Whisper + TTS
6. **Web pública**: exponer el chat en tu sitio

---

## 📚 RECURSOS

- OpenAI API: https://platform.openai.com/docs
- Google Gemini: https://ai.google.dev
- FastAPI: https://fastapi.tiangolo.com
- python-telegram-bot: https://python-telegram-bot.readthedocs.io

---

## ✅ CHECKLIST DE SETUP

- [ ] Claves de API generadas
- [ ] Variables de entorno configuradas
- [ ] `pip install -r requirements.txt` completado
- [ ] Backend ejecutándose en puerto 8000
- [ ] Frontend servidor en puerto 8080
- [ ] `chat.html` abierto en navegador
- [ ] Primer mensaje enviado ✓
- [ ] Modelo elegido (Copilot/Gemini)
- [ ] Diario guardado y legible
- [ ] Canal Telegram funcionando (si aplica)

**¡Listo para usar!** 🚀
