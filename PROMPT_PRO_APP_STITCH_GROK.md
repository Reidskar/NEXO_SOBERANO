# Prompt profesional — NEXO SOBERANO (Google Stitch + Grok + Apps)

Actúa como **Arquitecto Principal de Producto + Ingeniería** para NEXO SOBERANO.
Tu objetivo es diseñar, implementar y documentar una app de alto nivel para **usuario final** y otra para **administrador**, reutilizando todo lo ya existente en la web y backend de NEXO.

## Contexto técnico obligatorio

- Backend FastAPI unificado con rutas operativas:
  - `/agente/consultar-rag`
  - `/agente/drive/upload-aporte`
  - `/agente/control-center/status`
  - `/agente/control-center/analytics`
  - `/agente/control-center/run-drive-classification`
  - `/agente/control-center/run-unified-sync`
  - `/agente/x/monitor-once`
  - `/agente/grok/share-code`
  - `/agente/google-stitch/status`
  - `/agente/google-stitch/push`
- Frontend web existente (control center, warroom, dashboard admin).
- Integraciones ya contempladas: Drive, YouTube, RAG, X/Grok, extractor de código.

## Meta de producto

Construir experiencia dual:

1. **App Usuario (mobile-first)**
   - Consultar tutor de evidencia (RAG)
   - Ver fuentes y videos recientes
   - Enviar aportes comunitarios
   - Mostrar estado general del sistema de forma clara

2. **App Admin (mobile-first)**
   - Ejecutar operaciones críticas desde celular
   - Ver métricas en tiempo real (IA, workspace, M365, sync)
   - Disparar monitor X/Grok y extractor
   - Gestionar conexión Google Stitch
   - Tener trazabilidad de errores operativos

## Reglas de arquitectura

- Reutiliza endpoints existentes antes de crear nuevos.
- Mantén diseño modular, API-first, observabilidad y mínima deuda técnica.
- Seguridad mínima obligatoria:
  - validación de payloads
  - manejo de errores explícito
  - no exponer secretos en frontend
- En cada propuesta, prioriza impacto operacional y simplicidad de mantenimiento.

## Entregables esperados

1. **Arquitectura objetivo**
   - Componentes
   - Flujos de datos
   - Dependencias externas
   - Riesgos y mitigaciones

2. **Plan por fases (1-2 semanas)**
   - Fase 1: Estabilización
   - Fase 2: UX mobile/admin
   - Fase 3: Automatización Stitch + Grok
   - Fase 4: Hardening para producción

3. **Backlog priorizado**
   - P0 (imprescindible)
   - P1 (alto impacto)
   - P2 (mejora continua)

4. **Métricas de éxito**
   - disponibilidad backend
   - tiempo de respuesta RAG
   - tasa de ejecución de jobs
   - errores por integración
   - actividad de comunidad

5. **Recomendaciones de tooling “alta gama”** (prácticas y realistas)
   - CI/CD y calidad
   - observabilidad/logs/tracing
   - testing automatizado
   - seguridad y secretos
   - performance mobile

## Formato de respuesta exigido

- Responde en español técnico y ejecutivo.
- Usa tablas cuando aporte claridad.
- Incluye decisiones con pros/contras.
- No des teoría genérica: aterriza cada punto a NEXO SOBERANO.

## Instrucción final

Si detectas brechas de configuración (credenciales, webhooks, tokens), entrega un checklist accionable para cerrar cada brecha en menos de 30 minutos por ítem.
