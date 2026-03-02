# 🚀 NEXO SOBERANO - Guía de Ejecución

## Estructura completada
```
NEXO_SOBERANO/
├── core/                    # Motor RAG + Orquestador
├── api/                     # FastAPI Backend
│   ├── main.py             # Aplicación FastAPI
│   └── routes/             # Endpoints
├── services/               # Conectores (Google, Microsoft, etc)
├── frontend/               # React + Tailwind
│   └── src/
│       ├── components/     # Componentes reutilizables
│       ├── pages/          # Páginas principales
│       └── App.jsx         # Componente raíz
└── requirements.txt        # Dependencias Python
```

## ⚡ Paso 1: Backend

```bash
# Terminal 1: Backend Python
cd c:\Users\Admn\Desktop\NEXO_SOBERANO
python -m uvicorn api.main:app --reload --port 8000
```

✅ Verifica: http://localhost:8000/docs

## ⚡ Paso 2: Frontend

```bash
# Terminal 2: Frontend React
cd c:\Users\Admn\Desktop\NEXO_SOBERANO\frontend
npm install
npm run dev
```

✅ Verifica: http://localhost:3000

## 📊 APIs disponibles

- `GET /api/health` → Estado del backend
- `GET /api/status` → Status detallado
- `POST /api/chat` → Enviar pregunta al RAG
- `GET /docs` → Documentación Swagger

## 🔑 Siguientes fases

### Fase 2: Integración Real
- Sistema de indexado automático
- Conexión real a ChromaDB
- Integración Discord bot
- Integración Google Drive API

### Fase 3: Despliegue
- Vercel para frontend
- Cloudflare Tunnel para PC local
- Base de datos centralizada

---

**Estado actual**: Arquitectura modular completa + Backend + Frontend base
**Próximo**: Sistema de RAG con GPU e integración real de conectores
