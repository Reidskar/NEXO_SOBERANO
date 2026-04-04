# Plan de Acción Operativo y de Calidad — NEXO (2026-03-06)

## 1) Sondeo ejecutivo (estado actual)

### Calidad de código
- Escaneo supervisor: **200 archivos analizados** (truncado por límite), **score 96.59/100**.
- Hallazgos: **1 crítico**, 65 altos, 65 medios, 82 bajos.
- Riesgo crítico identificado en:
  - `AI-INTELLIGENCE-SYSTEM/scripts/run_mass_video_system.py` línea ~175
  - Código `SV007`: posible SQL injection por uso de f-string.

### Estabilidad de backend
- Test principal de backend: **PASS (1/1)** en `test_backend.py`.
- Esto confirma que la base responde, pero no reemplaza pruebas de seguridad/carga.

### Productividad e integración
- `credential_api_autopilot_last.json`: **productivity_score 77.5**.
- Auto-fixes aplicados: sincronización de bridge key, webhook alert y seguimiento personal por Discord.
- Pendiente humano: `OPENAI_API_KEY` y `XAI_API_KEY` (resiliencia IA actual 2/4).

### Innovación y modernización
- `innovation_scout_last.json`: **innovation_score 62.0**.
- 20 paquetes desactualizados detectados.
- Integraciones útiles faltantes: `apify-client`, `pandas`, `plotly`, `python-docx`.

---

## 2) Riesgos priorizados

## P0 (Crítico)
1. **Seguridad**: posible SQL injection (`SV007`) en `run_mass_video_system.py`.
2. **Cobertura incompleta de escaneo**: análisis truncado (200/203); existe riesgo oculto en los 3 no escaneados.

## P1 (Alto impacto)
1. **Resiliencia IA incompleta**: faltan `OPENAI_API_KEY` y `XAI_API_KEY`.
2. **XSS potencial en frontend** (`HT005`/`innerHTML`) en múltiples archivos HTML.

## P2 (Importante)
1. Dependencias desactualizadas (seguridad/compatibilidad).
2. Integraciones analíticas faltantes (Apify + data stack).
3. Manejo de excepciones demasiado amplio (`ST001`/`ST002`) en varias rutas/scripts.

---

## 3) Plan de acción profesional (ejecución por fases)

### Fase 0 — 24h (contención y seguridad)
**Objetivo:** eliminar riesgo crítico y asegurar continuidad.

1. Corregir `SV007` en `run_mass_video_system.py`:
   - Reemplazar SQL dinámico por query parametrizada.
   - Validar entradas con allowlist/typing.
2. Volver a ejecutar escaneo completo sin truncamiento:
   - Ajustar `NEXO_SUPERVISOR_MAX_FILES` para cubrir 100%.
3. Re-ejecutar pruebas backend + smoke de rutas clave.

**KPI de salida Fase 0**
- `critical = 0`
- `scan_truncated = false`
- tests backend verdes

### Fase 1 — 48h (resiliencia y operación)
**Objetivo:** subir confiabilidad operativa y velocidad de respuesta.

1. Cargar `OPENAI_API_KEY` y `XAI_API_KEY`.
2. Ejecutar `POST /agente/autopilot/credentials` y verificar:
   - `ai_ready_count = 4`
   - `approvals_required = 0` (credenciales IA)
3. Confirmar estado en Discord y loop de alertas.

**KPI de salida Fase 1**
- `ai_ready_count = 4/4`
- `productivity_score >= 88`

### Fase 2 — 7 días (hardening frontend + deuda técnica)
**Objetivo:** profesionalizar UX segura y reducir fragilidad.

1. Reducir `HT005` (innerHTML) en paneles críticos:
   - priorizar `admin_dashboard.html` y war rooms.
   - usar sanitización/DOM seguro.
2. Reducir `ST001/ST002` y `CX001` en módulos más usados.
3. Definir política de excepciones (errores específicos por capa).

**KPI de salida Fase 2**
- `high` -30%
- `HT005` -60%
- `ST001/ST002` -40%

### Fase 3 — 14 días (optimización extrema)
**Objetivo:** aumentar rendimiento y toma de decisiones.

1. Ejecutar ventana controlada de upgrades (paquetes desactualizados).
2. Instalar stack analítico:
   - `pandas`, `plotly`, `python-docx`, `apify-client`.
3. Activar rutina semanal automática:
   - escaneo + innovation scout + reporte de acción por Discord.

**KPI de salida Fase 3**
- `innovation_score >= 80`
- tiempo de diagnóstico semanal < 15 min
- 1 reporte ejecutivo automático/semana

---

## 4) Cadencia de gestión recomendada

### Diario (15 min)
- Ver `credential_api_autopilot_last.json`
- Ver `innovation_scout_last.json`
- Confirmar bloqueadores en Discord

### Semanal (60 min)
- Revisión de métricas de calidad y deuda
- Priorización de 3 fixes de mayor impacto
- Validación de backlog seguridad/operación

### Mensual
- Upgrade controlado de dependencias
- Revisión de arquitectura y costo/valor de integraciones

---

## 5) Próximo sprint sugerido (concreto)
1. Fix `SV007` (P0)
2. Completar `OPENAI_API_KEY` + `XAI_API_KEY` (P1)
3. Reducir `HT005` en 2 archivos principales (P1)
4. Habilitar escaneo completo no truncado (P0/P1)

---

## 6) Entregables de control
- `reports/supervisor/scan_*.json`
- `logs/credential_api_autopilot_last.json`
- `logs/innovation_scout_last.json`
- `reports/PLAN_ACCION_OPERATIVO_2026-03-06.md`
