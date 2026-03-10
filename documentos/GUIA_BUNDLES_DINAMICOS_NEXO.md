# Guía rápida: Bundles dinámicos de skills

## Objetivo
Cargar y activar skills por contexto de negocio usando catálogo JSON único, para que NEXO seleccione capacidades según escenario (engineering, marketing, research, operations).

## 1) Generar catálogo masivo
Ejecuta:

```powershell
.\.venv\Scripts\python.exe scripts\catalog_antigravity_skills.py --source . --output logs\antigravity_skills_catalog.json --min-confidence 0.35
```

Salida esperada: `logs/antigravity_skills_catalog.json`

## 2) Bundles recomendados por contexto
- **Engineering**: debugging, arquitectura limpia, backend, devops.
- **Marketing**: prospección, outreach, SEO, copy.
- **Research**: geopolítica, análisis económico, RAG, NotebookLM.
- **Operations**: automatización, orquestación Make/n8n, conectores.

## 3) Activación por contexto (patrón)
1. Detectar contexto desde señal de entrada (Drive/tag/canal/comando).
2. Filtrar catálogo por `bundle`.
3. Construir prompt/router solo con skills del bundle activo.
4. Ejecutar con Claude/Gemini y persistir resultado en War Room + reporte.

## 4) Auditoría de terceros (mínima obligatoria)
Antes de activar skills externas:
- Verificar fuente y hash del archivo.
- Revisar comandos sugeridos y bloquear shell peligrosa.
- Exigir score de confianza mínimo (`min-confidence`).
- Registrar trazabilidad (`source_file`, `generated_at`, bundle aplicado).

## 5) Siguiente paso recomendado
Conectar este catálogo al selector del backend para que `provider=auto` mantenga Claude/Gemini y elija skills por bundle en tiempo real.
