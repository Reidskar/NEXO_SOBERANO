---
name: security-review
description: Auditoría de seguridad completa — Gemma 4 + bandit + ruff. Ejecutar antes de cada merge.
allowed_tools: ["Bash", "Read", "Grep", "Glob"]
---

# /security-review

Motor: **Gemma 4 local ($0)** + bandit + ruff.

## Ejecutar

```bash
# Auditoría de archivos staged (pre-commit)
python scripts/nexo_manager.py security

# Auditoría de archivo específico
python scripts/nexo_manager.py security --file backend/routes/nuevo_endpoint.py
```

## Qué verifica Gemma 4
- Prompt injection (inputs usuario → LLM sin sanitizar)
- Endpoints sin `_require_key()` en mutaciones
- OSINT results devueltos crudos (sin pasar por Gemma 4 análisis)
- AI calls que bypasan `ai_router.py` (van directo a cloud)
- Command injection (`shell=True` con input usuario)
- SQL injection (queries con f-strings)
- Secretos hardcodeados
- SSRF (requests a URLs de usuario sin validar)
- Deserialización insegura (pickle, yaml.load sin SafeLoader)

## Criterio de aprobación
Sin issues CRÍTICO o ALTO → merge permitido.
