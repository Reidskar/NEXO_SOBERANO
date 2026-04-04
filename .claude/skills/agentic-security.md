---
name: agentic-security
description: Activate when building AI agent pipelines, MCP integrations, tool execution, or any code where external content reaches the AI context. Covers prompt injection defense for NEXO's AI router and OSINT pipelines.
origin: affaan-m/everything-claude-code (the-security-guide.md)
---

# Agentic Security — NEXO SOBERANO

## Threat Model (2025-2026 CVEs)

- **CVE-2025-59536** (CVSS 8.7): Code executed before trust confirmation
- **CVE-2026-21852**: API key leakage via env var manipulation
- Snyk analysis: 36% of public skills contain prompt injection (1,467 malicious payloads)

## Primary Attack Vectors en NEXO

| Vector | Dónde aplica en NEXO |
|---|---|
| Email/PDF con prompts ocultos | `x_monitor.py` procesando tweets |
| GitHub PR/diff comments | CI/CD hooks |
| MCP server tool poisoning | `.mcp.json` servers |
| Memoria persistente cross-session | Qdrant + `/api/knowledge/*` |
| Hidden Unicode en inputs | BigBrother OSINT results |
| Documentación externa envenenada | Context7 MCP fetches |

## Defense Layers (Obligatorias)

### 1. Separación de Identidad
- Nunca usar credenciales personales para agentes (Railway, GitHub Actions)
- Cuentas de servicio separadas para operaciones sensibles

### 2. Aislamiento
- BigBrother corre en su propio proceso/container
- Ollama en Torre separada de la red pública
- OSINT results procesados localmente (Gemma 4) antes de cualquier salida

### 3. Mínima Agencia
- BigBrother endpoints: siempre API key auth
- Comandos de globo: siempre x-api-key header
- Shell commands en scripts: nunca con input de usuario directo

### 4. Sanitización (especialmente para OSINT)
```python
# ✗ WRONG: OSINT result directo al AI
prompt = f"Analiza: {raw_osint_result}"

# ✓ CORRECT: Sanitizar primero
import unicodedata
clean = unicodedata.normalize('NFKC', str(raw_osint_result))
clean = clean[:8000]  # limit context window
prompt = f"Analiza el siguiente resultado OSINT:\n\n{clean}"
```

### 5. Observabilidad
- Todos los tool calls de AI logueados en `logs/`
- Rate limits registrados con usuario/IP
- Audit trail de llamadas OSINT (quién buscó qué)

### 6. Kill Switches
```python
# supervisor_osint.py tiene --once para verificación puntual
# Si Ollama no responde en 180s → timeout y fallback cloud
# NEXO_MAX_TOKENS_DIA = hard limit → bloquea procesos excedentes
```

## Principio Fundamental
> "Nunca dejar que la capa de conveniencia supere la capa de aislamiento"

No exponer resultados crudos de OSINT, BigBrother, o AI sin filtrar por Gemma 4 local primero.
