# Prompt — Vibe Prospecting + Refuerzo Comercial

Actúa como arquitecto de growth + data quality.

Diseña integración de Vibe Prospecting para:

1. Buscar perfiles objetivo (ONGs, medios, think tanks, sponsors).
2. Validar calidad de lead (email/domain/title/fit score).
3. Persistir en Google Sheet + Drive + JSON local.
4. Generar primer outreach con compliance básico.

## Requisitos técnicos

- Deduplicación por `email`, `linkedin_url`, `company_domain`.
- Score 0-100 con umbrales de acción.
- Auditoría por lote (`batch_id`, fecha, operador, fuentes).
- Guardrails de seguridad y privacidad.

## Entregables

A) Esquema de datos
B) Flujo por etapas
C) Plantilla de outreach
D) Reglas de exclusión
E) KPI semanales
