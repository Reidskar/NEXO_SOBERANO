---
name: discord-bot-ia-orchestrator
category: workflow
summary: "Coordinación y programación avanzada de bots de Discord conectados a IA, cerebro central y apps externas."
description: |
  SKILL — Orquestar, programar y optimizar bots de Discord con IA, conectores, y cerebro central, siguiendo los mejores patrones de ingeniería conversacional y automatización. El bot debe:
  - Usar el token correcto y registrar comandos tras cada reinicio.
  - Validar intents en el portal de Discord (Presence, Server Members, Message Content).
  - Conectarse al backend (FastAPI) y responder a comandos.
  - Integrar apps y conectores agregados por el usuario.
  - Mantener conversación fluida y natural, usando arquetipos definidos.
  - Reportar cada paso en formato NEXO REPORTE.
  - Diagnosticar y corregir errores de conexión, intents, comandos, y backend.
workflow:
  steps:
    - Validar token y .env único (sin duplicados)
    - Registrar comandos con register_commands.js tras cada reinicio
    - Verificar y activar intents en Discord portal
    - Confirmar conexión backend y respuesta a comandos
    - Integrar apps/conectores nuevos
    - Usar arquetipos para conversación natural
    - Reportar cada acción y error en formato NEXO REPORTE
  decision_points:
    - ¿Token válido y único?
    - ¿Comandos registrados correctamente?
    - ¿Intents activados?
    - ¿Backend responde?
    - ¿Conectores integrados?
    - ¿Conversación fluida?
completion_criteria:
  - Bot responde a comandos en Discord
  - Comandos registrados sin error
  - Intents activados en portal
  - Backend responde a consultas
  - Apps/conectores accesibles
  - Conversación fluida y natural
  - NEXO REPORTE evidencia cada paso
assets:
  - scripts/register_commands.js
  - templates/.env
  - checklists/discord-intents.md
  - arquetipos/conversacion.md
examples:
  - "Coordina el bot de Discord con IA y apps, reporta cada paso en NEXO REPORTE."
  - "Diagnostica por qué el bot no responde a comandos y corrige, usando el workflow."
  - "Integra un nuevo conector y valida conversación fluida con arquetipos."
---

# Discord Bot IA Orchestrator Skill

Este skill permite coordinar, programar y optimizar bots de Discord conectados a IA, cerebro central y apps externas, siguiendo los mejores patrones conversacionales y de automatización. Incluye validación de token, intents, comandos, backend, conectores y arquetipos, reportando todo en formato NEXO REPORTE.

## Ejemplo de uso
- "Coordina el bot de Discord con IA y apps, reporta cada paso en NEXO REPORTE."
- "Diagnostica por qué el bot no responde a comandos y corrige, usando el workflow."
- "Integra un nuevo conector y valida conversación fluida con arquetipos."

## Personalización sugerida
- Añadir checklists para onboarding de nuevos conectores
- Incluir templates de arquetipos conversacionales
- Automatizar validación de intents y registro de comandos

