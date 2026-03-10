# 🧬 Sistema de Evolución Continua de IA - NEXO

## 📋 Descripción General

El **Sistema de Evolución IA** es un orquestador automático que permite que todas las inteligencias artificiales del ecosistema NEXO evolucionen continuamente en cuatro dimensiones:

1. **Código**: Mejora automática de calidad mediante escaneo y auto-reparación
2. **Sistema**: Optimización del comportamiento y funcionamiento operativo
3. **Visual Web**: Evolución de interfaces y experiencia de usuario
4. **Programación**: Generación de hints y recomendaciones para desarrollo

---

## 🎯 Características Principales

- ✅ **Ciclo de evolución automático** que combina:
  - Análisis de inteligencia autónoma (analytics agregados)
  - Escaneo de código completo (nexo_autosupervisor)
  - Auto-reparación opcional de issues críticos
  - Generación de hints accionables para mejora continua

- 📊 **Monitoreo en tiempo real** vía Control Center
- 🔧 **Integración nativa** con War Room y backend
- 📝 **Persistencia de histórico** en logs JSON

---

## 🚀 Uso

### API Endpoints

#### 1. Ejecutar Ciclo de Evolución

```http
POST /api/ai/evolution-cycle?apply_code_fix=true
Headers:
  X-NEXO-API-KEY: tu_clave_aqui
```

**Parámetros:**
- `apply_code_fix` (bool, default=true): Si aplica auto-reparación durante escaneo

**Respuesta:**
```json
{
  "ok": true,
  "timestamp": "2024-01-15T10:30:45.123Z",
  "duration_seconds": 42.5,
  "data": {
    "mode": "evolution",
    "intelligence_analytics": {...},
    "scan_summary": {
      "files_scanned": 192,
      "critical_issues": 0,
      "high_issues": 63,
      "medium_issues": 128,
      "quality_score": 96.76
    },
    "hints": [
      "Reducir issues altos (63) en tandas priorizadas",
      "Corregir OAuth scopes/consent en integraciones",
      "Ampliar corpus RAG (>20 docs) para QA Bot",
      "Agregar tests unitarios en módulos críticos"
    ]
  }
}
```

#### 2. Consultar Estado de Última Evolución

```http
GET /api/ai/evolution-status
Headers:
  X-NEXO-API-KEY: tu_clave_aqui
```

**Respuesta:**
```json
{
  "ok": true,
  "has_data": true,
  "timestamp": "2024-01-15T10:30:45.123Z",
  "data": {
    "mode": "evolution",
    "quality_score": 96.76,
    "critical_issues": 0,
    "hints": [...]
  }
}
```

---

## 🖥️ Frontend - Control Center

### Ubicación
[http://localhost:8000/control-center](http://localhost:8000/control-center)

### Funcionalidad

1. **Panel "Evolución IA"**:
   - Badge de estado: ✅ ok / ⚠️ warn / ⏸️ idle
   - Modo de operación (evolution/autonomous)
   - Quality Score (0-100)
   - Issues críticos detectados

2. **Botón "Evolución IA (auto)"**:
   - Ejecuta manualmente un ciclo completo
   - Aplica auto-fix de código
   - Muestra resultados vía notificación

3. **Panel "Hints de Evolución"**:
   - Lista de recomendaciones accionables
   - Generadas dinámicamente según estado del sistema
   - Prioriza issues críticos, errores de integración, mejoras UX

4. **Actualización automática**:
   - Cada 10 segundos consulta `/api/ai/evolution-status`
   - Refleja cambios en tiempo real

---

## ⚙️ Configuración y Personalización

### Frecuencia de Evolución

**Recomendaciones:**
- **Manual**: Para desarrollo activo, ejecutar vía botón en Control Center
- **Programado (futuro)**: Configurar cron/scheduler para ejecutar cada 1-6 horas
- **Watch mode**: Activar nexo_autosupervisor en modo watch para escaneo continuo

### Activación de Auto-Fix

```python
# En código backend/routes/agente.py
await intelligence_evolution_cycle(apply_code_fix=True)  # Aplica reparaciones
await intelligence_evolution_cycle(apply_code_fix=False) # Solo escaneo
```

### Persistencia de Logs

- **Última ejecución**: `logs/ai_evolution_last.json`
- **Histórico completo**: `logs/ai_evolution_history.jsonl` (JSON Lines)

---

## 🧠 Arquitectura Interna

### Flujo de Ejecución

```
┌─────────────────────────────────────────────────┐
│ 1. intelligence_evolution_cycle()               │
│    - Genera timestamp                           │
│    - Prepara payload inicial                    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. Analytics Agregados                          │
│    - Consulta /api/ai/status                    │
│    - Obtiene métricas de ai_qa_bot              │
│    - Obtiene snapshot de web_ai_supervisor      │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 3. Escaneo de Código (nexo_autosupervisor)     │
│    - Ejecuta: python nexo_autosupervisor.py     │
│      --scan [--fix si apply_code_fix=true]      │
│    - Timeout: 120 segundos                      │
│    - Captura stdout/stderr                      │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 4. Parseo de Resultados                         │
│    - Extrae métricas del reporte generado       │
│    - Calcula quality_score                      │
│    - Identifica issues críticos/altos           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 5. Generación de Hints                          │
│    - Analiza issues críticos                    │
│    - Detecta errores de integración OAuth       │
│    - Evalúa tamaño de corpus RAG                │
│    - Genera 4-8 recomendaciones priorizadas     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 6. Persistencia                                 │
│    - Guarda logs/ai_evolution_last.json         │
│    - Appends logs/ai_evolution_history.jsonl    │
│    - Retorna payload JSON completo              │
└─────────────────────────────────────────────────┘
```

### Componentes Clave

- **backend/routes/agente.py**:
  - `_run_local_command()`: Ejecutor seguro de comandos Python
  - `_latest_supervisor_scan_summary()`: Parser de reportes del autosupervisor
  - `_build_evolution_hints()`: Motor de generación de hints
  - `intelligence_evolution_cycle()`: Orquestador principal
  - `intelligence_evolution_status()`: Consulta de último estado

- **NEXO_CORE/api/ai.py**:
  - Delegación de endpoints `/api/ai/evolution-*` a `backend.routes.agente`
  - Rate limiting integrado
  - Autenticación vía X-NEXO-API-KEY

- **frontend_public/control_center.html**:
  - UI reactiva con actualización automática
  - Notificaciones de resultados
  - Visualización de hints y métricas

---

## 📈 Métricas y KPIs

### Quality Score (0-100)
- **95-100**: ✅ Excelente - Sistema óptimo
- **85-94**: ✅ ok - Calidad adecuada con mejoras menores
- **70-84**: ⚠️ warn - Requiere atención
- **< 70**: ❌ Crítico - Intervención urgente

### Cálculo:
```python
base = 100
base -= (critical_count * 10)   # -10 por cada crítico
base -= (high_count * 2)        # -2 por cada alto
base -= (medium_count * 0.5)    # -0.5 por cada medio
quality_score = max(0, base)
```

### Categorías de Hints

1. **Código**: Reducción de issues, refactorización, tests
2. **Integración**: OAuth, API keys, permisos, conectores
3. **IA/ML**: Corpus RAG, embeddings, fine-tuning
4. **UX/Frontend**: Responsive, accesibilidad, performance
5. **DevOps**: Despliegue, monitoreo, logging

---

## 🔧 Troubleshooting

### Error: "Endpoint not available on port 8000"
**Causa**: Backend no tiene los nuevos endpoints cargados.
**Solución**: Reiniciar NEXO_CORE:
```bash
# Detener proceso actual
Ctrl+C

# Reiniciar backend
python run_backend.py
# O usar tarea de VS Code:
# 🚀 NEXO: Iniciar Backend
```

### Error: "Unauthorized"
**Causa**: Falta o es incorrecta la API key.
**Solución**: Configurar en headers:
```http
X-NEXO-API-KEY: CAMBIA_ESTA_CLAVE_NEXO
```

### Error: Timeout en evolution-cycle
**Causa**: Escaneo de código toma >120 segundos.
**Solución**: 
1. Reducir archivos escaneados en nexo_autosupervisor.py
2. Aumentar timeout en `_run_local_command(timeout=120)`

### Hints vacíos o genéricos
**Causa**: No se detectan issues críticos o falta contexto.
**Solución**: 
1. Ejecutar escaneo manual: `python nexo_autosupervisor.py --scan`
2. Revisar logs en `reports/nexo_supervisor_*.txt`
3. Verificar que hay datos en analytics del sistema

---

## 🚀 Roadmap

### Fase 1 (Actual) ✅
- [x] Backend de evolución automática
- [x] Frontend de control y monitoreo
- [x] Persistencia de logs
- [x] Generación de hints

### Fase 2 (Próxima)
- [ ] Scheduler automático (cron/APScheduler)
- [ ] Notificaciones Discord cuando quality_score < 85
- [ ] Dashboard de métricas históricas
- [ ] A/B testing de evoluciones (rollback si empeora)

### Fase 3 (Futuro)
- [ ] Integración con GitHub Actions (CI/CD)
- [ ] Auto-aplicación de hints vía IA generativa
- [ ] Análisis de tendencias y predicción de issues
- [ ] Reportes ejecutivos semanales/mensuales

---

## 📚 Referencias

- [nexo_autosupervisor.py](nexo_autosupervisor.py) - Escaneo y auto-reparación
- [backend/routes/agente.py](backend/routes/agente.py) - Lógica de evolución
- [NEXO_CORE/api/ai.py](NEXO_CORE/api/ai.py) - Endpoints nativos
- [frontend_public/control_center.html](frontend_public/control_center.html) - UI de control

---

## 🤝 Contribución

Para añadir nuevos hints o mejorar la generación automática:

1. Editar `_build_evolution_hints()` en [backend/routes/agente.py](backend/routes/agente.py)
2. Añadir condiciones basadas en:
   - `scan_summary` (issues críticos/altos)
   - `analytics` (métricas de IA)
   - Archivos específicos del proyecto
3. Validar ejecutando un ciclo manual
4. Documentar el nuevo hint aquí

---

**Última actualización:** Enero 2024  
**Versión:** 1.0.0  
**Autor:** NEXO AI Team
