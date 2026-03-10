# 💰 GUÍA DE COSTOS OPERACIONALES - NEXO SOBERANO

## 📊 Resumen Ejecutivo

Sistema NEXO registra y analiza **todos los costos operacionales** automáticamente:

- **APIs de IA**: Gemini, Claude (Anthropic), OpenAI/Copilot, Grok (xAI)
- **Servicios externos**: Google Drive, Microsoft Graph, X/Twitter, Discord
- **Tracking en tiempo real** con alertas de presupuesto excedido
- **Reportes detallados** disponibles en War Room y API

---

## 🤖 COSTOS DE APIs DE IA

### 1. Google Gemini (Recomendado para mayor parte del trabajo)

#### Free Tier
- **gemini-2.5-flash-lite**: ✨ **GRATIS** hasta 1.5M tokens/día
- **gemini-1.5-flash**: ✨ **GRATIS** hasta 1.5M tokens/día
- Perfecto para clasificación, RAG, embeddings básicos

#### Paid Tier (cuando excedes free tier)
| Modelo | Input (por 1M tokens) | Output (por 1M tokens) | Uso recomendado |
|--------|----------------------|------------------------|-----------------|
| gemini-1.5-flash | $0.075 | $0.30 | Clasificación rápida, RAG básico |
| gemini-1.5-pro | $1.25 | $5.00 | Análisis profundo, FODA complejo |
| gemini-2.5-pro | $2.50 | $10.00 | Máxima calidad, razonamiento avanzado |
| embeddings | $0.00125 | - | Vectorización (fallback si local falla) |

**💡 Tip**: NEXO usa `all-MiniLM-L6-v2` local **gratis** por defecto para embeddings. Gemini embeddings solo como fallback.

### 2. Anthropic Claude (Mejor razonamiento)

| Modelo | Input (por 1M tokens) | Output (por 1M tokens) | Uso en NEXO |
|--------|----------------------|------------------------|-------------|
| claude-3-5-sonnet-20241022 | $3.00 | $15.00 | Decisor FODA, análisis estratégico |
| claude-haiku-4-5-20251001 | $0.80 | $4.00 | Análisis rápido, clasificación |
| claude-3-opus | $15.00 | $75.00 | ⚠️ MUY CARO, no habilitado por defecto |

**Uso actual**: Decisor principal en análisis FODA cuando `decisor_final=claude`.

### 3. OpenAI / Copilot

| Modelo | Input (por 1M tokens) | Output (por 1M tokens) | Uso en NEXO |
|--------|----------------------|------------------------|-------------|
| gpt-4.1-mini | $0.15 | $0.60 | Fallback general cuando otros fallan |
| gpt-4-turbo | $10.00 | $30.00 | ⚠️ Caro, no recomendado |
| gpt-4o | $2.50 | $10.00 | Análisis cuando se requiere |
| gpt-3.5-turbo | $0.50 | $1.50 | Legacy, no usado |

**Uso actual**: Backup en routing multi-IA. También usado en `agente_postulaciones` para scoring de trabajos.

### 4. xAI Grok (Beta)

| Modelo | Input (por 1M tokens) | Output (por 1M tokens) | Uso en NEXO |
|--------|----------------------|------------------------|-------------|
| grok-beta | ~$2.00 | ~$6.00 | Consultas especiales, integración X/Twitter |
| grok-2 | ~$2.00 | ~$6.00 | Similar a grok-beta |

**Uso actual**: 
- Endpoint `/agente/grok/consult` para consultas directas
- Fallback en routing multi-IA
- Integración con X/Twitter para análisis de menciones

---

## 🌐 COSTOS DE SERVICIOS EXTERNOS

### Google Services

#### Google Drive API
- **Tier**: Gratis hasta 1M queries/día por usuario
- **Quota reset**: Diario
- **Costo adicional**: $0 (incluido en cuenta Google gratuita)
- **Uso en NEXO**: Sincronización automática, clasificación de archivos

#### Google Photos API
- **Tier**: Gratis hasta 10K requests/día
- **Costo adicional**: $0
- **Uso en NEXO**: Backup de capturas, análisis de imágenes

### Microsoft Services

#### Microsoft Graph API (OneDrive)
- **Tier**: Gratis con cuenta Microsoft 365
- **Quota**: 100K requests/día
- **Costo adicional**: $0 (incluido en Microsoft 365 personal/business)
- **Uso en NEXO**: Sincronización OneDrive, clasificación automática

### X/Twitter API

#### Free Tier
- **Read**: 0 tweets/mes (prácticamente inútil)
- **Write**: 0 tweets/mes

#### Basic Tier
- **Costo mensual**: $100 USD
- **Read**: 10,000 tweets/mes
- **Write**: 3,000 tweets/mes
- **Uso en NEXO**: Publicación automática, monitoreo de menciones, análisis con Grok

⚠️ **Importante**: API v2 de X es de pago obligatorio para uso productivo.

### Discord Bot

#### Discord Webhooks
- **Costo**: $0 (gratis)
- **Rate limits**: 30 messages/min, 2K messages/día por webhook
- **Uso en NEXO**: Notificaciones de stream, alertas operacionales

---

## 📈 ESTIMACIÓN DE COSTOS MENSUALES

### Escenario 1: **Uso Ligero** (Free tier principalmente)
```
Gemini Free Tier (1.5M tokens/día):     $0
Claude (5K tokens/día):                 ~$0.15/día = $4.50/mes
OpenAI/Copilot (fallback mínimo):       ~$0.50/mes
Grok (consultas ocasionales):           ~$1/mes
Google Drive/Photos API:                $0
Microsoft Graph:                        $0
Discord Webhooks:                       $0
X/Twitter API Basic:                    $100/mes (opcional)

TOTAL (sin X): ~$6/mes
TOTAL (con X): ~$106/mes
```

### Escenario 2: **Uso Moderado**
```
Gemini (algunos días excede free tier):  ~$10/mes
Claude (decisor FODA frecuente):         ~$15/mes
OpenAI/Copilot (backup activo):          ~$5/mes
Grok (consultas regulares):              ~$3/mes
Servicios externos:                      $0
X/Twitter API Basic:                     $100/mes (opcional)

TOTAL (sin X): ~$33/mes
TOTAL (con X): ~$133/mes
```

### Escenario 3: **Uso Intensivo** (RAG masivo, FODA diario)
```
Gemini Pro (análisis profundo diario):   ~$50/mes
Claude (decisor principal + revisiones): ~$40/mes
OpenAI/Copilot (backup frecuente):       ~$15/mes
Grok (integración X activa):             ~$10/mes
X/Twitter API Basic:                     $100/mes
Google Workspace (si se requiere más quota): $6/mes (opcional)

TOTAL: ~$221/mes
```

---

## 🎯 RECOMENDACIONES PARA MINIMIZAR COSTOS

### 1. Mantén Gemini Free Tier
```python
# En backend/config.py
MAX_TOKENS_DIA = 900_000  # Default: 900K tokens/día

# Sistema automáticamente detiene cuando excede
if not cost_mgr.puede_operar():
    raise HTTPException(429, "Presupuesto diario Gemini excedido")
```

### 2. Usa Local Embeddings (Gratis)
```python
# Backend usa sentence-transformers local por defecto
EMBED_LOCAL = "all-MiniLM-L6-v2"  # $0 costo

# Gemini embeddings solo como fallback
EMBED_GEMINI = "models/embedding-001"  # $0.00125 por 1M tokens
```

### 3. Prioriza Multi-Provider Routing Inteligente
```python
# En backend/services/rag_service.py
# Orden de fallback (de más barato a más caro):
provider_map = {
    "auto": ["gemini", "grok", "openai", "anthropic"],  # Gemini primero
}
```

### 4. Configura Alertas de Costo
```python
# Sistema genera warnings automáticos:
if gemini_cost > 1.0 and period == "today":
    warnings.append("⚠️ Gemini cost today: $X.XX. Switch to flash-lite.")
```

### 5. Monitorea Dashboard
- **War Room Panel**: Costos en tiempo real
- **API Endpoint**: `GET /api/agente/costs/report?period=today`
- **Budget Status**: `GET /api/agente/costs/budget`

---

## 🔧 CONFIGURACIÓN DE APIs

### Variables de Entorno (.env)

```bash
# ═══ APIs DE IA ═══
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
XAI_API_KEY=xai-...

# ═══ MODELOS (optimizar por costo) ═══
GEMINI_MODEL_FLASH=gemini-2.5-flash-lite  # Free tier
GEMINI_MODEL_PRO=gemini-1.5-pro           # Paid pero barato
CLAUDE_MODEL=claude-3-5-sonnet-20241022   # Balanceado
OPENAI_MODEL=gpt-4.1-mini                 # Más barato de OpenAI
XAI_MODEL=grok-beta

# ═══ PRESUPUESTOS ═══
MAX_TOKENS_DIA=900000  # Limit diario Gemini

# ═══ SERVICIOS EXTERNOS ═══
GOOGLE_DRIVE_ENABLED=true
MICROSOFT_GRAPH_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## 📊 ENDPOINTS DE COSTOS

### 1. Reporte Completo
```http
GET /api/agente/costs/report?period=today
```

**Response**:
```json
{
  "period": "today",
  "date_range": {"start": "2025-01-01", "end": "2025-01-01T15:30:00"},
  "ai_providers": {
    "gemini": {
      "calls": 150,
      "tokens_in": 45000,
      "tokens_out": 12000,
      "total_tokens": 57000,
      "cost_usd": 0.0
    },
    "anthropic": {
      "calls": 5,
      "tokens_in": 3000,
      "tokens_out": 1500,
      "total_tokens": 4500,
      "cost_usd": 0.0315
    }
  },
  "external_services": {
    "google_drive_api": {"operations": 20, "cost_usd": 0.0},
    "x_twitter_api": {"operations": 0, "cost_usd": 3.33}
  },
  "total_cost_usd": 3.36,
  "total_ai_cost_usd": 0.03,
  "total_services_cost_usd": 3.33,
  "warnings": [
    "⚠️ X/Twitter API Basic prorrateado: $100/mes = $3.33/día"
  ]
}
```

### 2. Resumen Diario (últimos 7 días)
```http
GET /api/agente/costs/daily-summary?days=7
```

### 3. Estado de Presupuesto
```http
GET /api/agente/costs/budget
```

**Response**:
```json
{
  "gemini_tokens_today": 125000,
  "gemini_free_tier_limit": 900000,
  "gemini_remaining": 775000,
  "gemini_usage_percent": 13.9,
  "can_operate": true,
  "date": "2025-01-01"
}
```

---

## 🛡️ SOBERANÍA DE DATOS Y PRIVACIDAD

### ¿Qué datos se envían a APIs externas?

#### Google Gemini (cuando se usa)
- ✅ Chunks de texto (400 caracteres) para clasificación
- ✅ Preguntas de usuario + contexto RAG (top 5 chunks)
- ✅ PDFs escaneados para OCR (solo si no se puede leer localmente)
- ❌ **NUNCA**: Archivos completos, credenciales, datos sensibles

#### Anthropic Claude
- ✅ Prompts de análisis FODA
- ✅ Contexto RAG cuando es decisor final
- ❌ **NUNCA**: Documentos completos

#### OpenAI/Copilot
- ✅ Solo como fallback en routing multi-IA
- ✅ Prompts de RAG cuando otros providers fallan

#### xAI Grok
- ✅ Consultas específicas vía endpoint `/grok/consult`
- ✅ Análisis de menciones de X/Twitter

### ¿Qué se procesa 100% localmente?

- ✅ **Embeddings**: `all-MiniLM-L6-v2` (CPU/GPU local)
- ✅ **ChromaDB**: Base vectorial on-premise
- ✅ **SQLite**: Metadatos y costos
- ✅ **Procesamiento de archivos**: PyMuPDF, Pillow, python-docx
- ✅ **OBS control**: WebSocket local

---

## 📌 REFERENCIAS DE PRICING OFICIAL

- **Google Gemini**: https://ai.google.dev/pricing
- **Anthropic Claude**: https://www.anthropic.com/pricing
- **OpenAI**: https://openai.com/pricing
- **xAI Grok**: https://x.ai/api (pricing en beta)
- **Google Drive API**: https://developers.google.com/drive/api/guides/limits
- **Microsoft Graph**: https://learn.microsoft.com/en-us/graph/throttling
- **X/Twitter API**: https://developer.twitter.com/en/products/twitter-api

---

## 🚀 PRÓXIMOS PASOS

1. **Revisar costos actuales**:
   ```bash
   curl http://localhost:8000/api/agente/costs/report?period=week
   ```

2. **Monitorear War Room**: Panel de costos en tiempo real

3. **Ajustar presupuestos** en `backend/config.py` según necesidad

4. **Optimizar routing**: Priorizar providers más baratos en `rag_service.py`

5. **Configurar alertas**: Discord/email cuando costos excedan umbrales

---

**Última actualización**: 2025-01-28  
**Versión NEXO**: 2.0.0  
**Autor**: Sistema IA NEXO
