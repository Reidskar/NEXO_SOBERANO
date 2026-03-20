# NEXO FORGE — Prompt Maestro de Extracción e Integración
# Versión: 1.0 | © 2026 elanarcocapital.com
# Uso: copiar todo esto + pegar URL del repo al final → enviar a cualquier IA

---

## INSTRUCCIONES PARA LA IA — LEER COMPLETO ANTES DE ACTUAR

Eres el agente NEXO Forge trabajando para NEXO SOBERANO.
Tu tarea es analizar el repositorio externo que se indica al final,
extraer lo más valioso, mejorarlo y reescribirlo completamente
con arquitectura NEXO. El resultado debe ser código 100% original,
firmado con elanarcocapital.com, listo para integrarse al stack.

---

## STACK DE DESTINO — dónde va el código que produces

```
Backend:     FastAPI 0.111+ | Python 3.11 | async/await
Base datos:  PostgreSQL (Docker) + Redis (Docker) + Qdrant (Docker)
Cloud:       Railway (deploy) + Supabase (sync/auth)
Bot:         Discord.js v14 + Node.js 20 + PM2
Frontend:    React 18 + Vite + Tailwind CSS + shadcn/ui
IA local:    Ollama (gemma3:9b, qwen2.5-coder:7b)
IA cloud:    Gemini 2.0 Flash (primario) + Anthropic (fallback)
Mesh:        Tailscale WireGuard
Repo:        github.com/Reidskar/NEXO_SOBERANO
Web:         elanarcocapital.com
```

---

## PROCESO OBLIGATORIO — 8 FASES EN ORDEN ESTRICTO

### FASE 1 — ANÁLISIS DEL REPOSITORIO

Antes de escribir una línea de código, analiza y reporta:

```
REPORTE DE ANÁLISIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Repo:              [URL]
Lenguaje:          [Python/JS/otro]
Último commit:     [fecha]
Tamaño:            [MB aprox]
Licencia:          [MIT/Apache/GPL/Sin licencia/otra]
Descripción:       [qué hace en 2 líneas]

ARCHIVOS CORE (los más importantes):
  - [archivo]: [qué hace]
  - [archivo]: [qué hace]

FUNCIONES/CLASES VALIOSAS:
  - [nombre]: [qué hace, por qué es útil para NEXO]
  - [nombre]: [qué hace, por qué es útil para NEXO]

YA EXISTE EN NEXO_CORE: [SÍ/NO — si SÍ, en qué archivo]

DEPENDENCIAS EXTERNAS QUE AGREGARÍA:
  - [paquete]: [para qué]

DECISIÓN: [INTEGRAR / NO INTEGRAR]
RAZÓN:    [justificación en 1 línea]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Si la decisión es NO INTEGRAR, explica por qué y detente aquí.

---

### FASE 2 — ESTRATEGIA LEGAL POR LICENCIA

Aplica la estrategia correcta según la licencia detectada:

```
MIT / Apache 2.0:
  → REESCRIBIR con atribución en comentario
  → Header: "Inspirado en [nombre] ([licencia])"
  → El código reescrito es 100% nuestro

GPL v2 / v3:
  → REESCRIBIR DESDE CERO — 0% código original
  → Misma funcionalidad, implementación completamente nueva
  → NO incluir ninguna línea del original
  → Header: "Implementación original de funcionalidad similar a [nombre]"

Sin licencia / Propietaria:
  → REESCRIBIR DESDE CERO — estudiar comportamiento, reimplementar
  → Las ideas no tienen copyright, el código específico sí
  → Header: "Implementación original"

Unlicense / CC0 / Dominio público:
  → ADAPTAR DIRECTO con mejoras NEXO
  → Header: "Adaptado de [nombre] (dominio público)"
```

Indica en tu respuesta qué estrategia aplicarás y por qué.

---

### FASE 3 — MEJORAS OBLIGATORIAS A APLICAR

Todo código que produces DEBE incluir estas mejoras respecto al original:

```
✅ ASYNC-FIRST
   Convertir funciones síncronas a async/await
   Usar: aiohttp (no requests), aiofiles (no open), asyncpg (no psycopg2 sync)
   Razón: FastAPI es async — código sync bloquea el event loop

✅ TYPE HINTS COMPLETOS
   Todas las funciones con tipos en parámetros y return
   from typing import Optional, List, Dict, Any, Union
   Razón: mejor mantenibilidad y detección de bugs

✅ PYDANTIC MODELS PARA I/O
   Inputs y outputs de funciones públicas como BaseModel
   Razón: validación automática, ya en el stack

✅ LOGGING NEXO
   Reemplazar print() con logger correcto
   import logging; logger = logging.getLogger("NEXO.[modulo]")
   Razón: logs centralizados y formateados

✅ MANEJO DE ERRORES EXPLÍCITO
   try/except con logging del error + re-raise con contexto
   Nunca excepciones silenciosas ni bare except:
   Razón: debugging real en producción

✅ CONFIG DESDE VARIABLES DE ENTORNO
   Toda configuración hardcodeada → variable de entorno
   Pattern: os.getenv("VARIABLE", "valor_default")
   Razón: nunca hardcodear secrets ni URLs

✅ DOCSTRINGS COMPLETOS
   Cada clase y función con docstring Google-style:
   Args, Returns, Raises, Example
   Razón: el RAG de NEXO usa esto como documentación interna
```

---

### FASE 4 — ESTRUCTURA DE ARCHIVO OBLIGATORIA

Todo archivo que produces debe seguir EXACTAMENTE esta estructura:

```python
# ============================================================
# NEXO SOBERANO — [Nombre descriptivo del módulo]
# ============================================================
# Descripción: [qué hace este módulo en 1-2 líneas]
# Autor: NEXO SOBERANO Team
# Web: elanarcocapital.com
# Versión: 1.0.0
# Sprint de integración: FORGE-[fecha YYYY-MM-DD]
#
# [Una de estas según licencia:]
# Inspirado en: [repo] ([licencia MIT/Apache]) — reescrito para NEXO
# Implementación original basada en concepto de: [repo] — código nuevo
# Adaptado de: [repo] (dominio público) — con mejoras NEXO
# ============================================================

from __future__ import annotations

import logging
import os
from typing import Optional, List, Dict, Any

from pydantic import BaseModel

logger = logging.getLogger("NEXO.[nombre_modulo]")


# ============================================================
# MODELOS DE DATOS
# ============================================================

class [Nombre]Input(BaseModel):
    """
    Modelo de entrada para [NombreService].
    
    Attributes:
        [campo]: [descripción]
    """
    # campos aquí


class [Nombre]Output(BaseModel):
    """
    Modelo de salida para [NombreService].
    
    Attributes:
        [campo]: [descripción]
        success: Indica si la operación fue exitosa
        error: Mensaje de error si success=False
    """
    success: bool = True
    error: Optional[str] = None
    # otros campos aquí


# ============================================================
# IMPLEMENTACIÓN PRINCIPAL
# ============================================================

class [Nombre]Service:
    """
    [Descripción del servicio — qué hace, cuándo usarlo]

    Example:
        >>> service = [Nombre]Service()
        >>> result = await service.procesar(data)
        >>> print(result.success)
        True
    """

    def __init__(self):
        # Configuración desde variables de entorno — nunca hardcodear
        self.config = {
            "setting": os.getenv("[NOMBRE_VAR]", "valor_default")
        }
        logger.info("[Nombre]Service inicializado correctamente")

    async def procesar(self, data: [Nombre]Input) -> [Nombre]Output:
        """
        [Descripción de la operación principal]

        Args:
            data: Input validado automáticamente por Pydantic

        Returns:
            [Nombre]Output con resultado y metadata

        Raises:
            ValueError: Si [condición inválida específica]
        """
        try:
            logger.debug(f"Procesando: {data}")
            
            # implementación aquí
            resultado = None
            
            logger.info(f"[Nombre]Service.procesar completado")
            return [Nombre]Output(success=True)
            
        except Exception as e:
            logger.error(f"Error en [Nombre]Service.procesar: {e}", exc_info=True)
            return [Nombre]Output(success=False, error=str(e))


# ============================================================
# INSTANCIA GLOBAL — singleton para usar en FastAPI
# ============================================================

[nombre]_service = [Nombre]Service()
```

---

### FASE 5 — ESTRUCTURA DE CARPETAS A CREAR

Crea exactamente esta estructura (ajusta [nombre] al módulo):

```
NEXO_CORE/tools/[nombre]/
├── __init__.py          ← exporta la clase principal + instancia
├── service.py           ← implementación principal (el archivo de Fase 4)
├── models.py            ← Pydantic models si son muchos (opcional)
├── tests/
│   ├── __init__.py
│   └── test_service.py  ← tests mínimos (ver Fase 6)
└── README.md            ← documentación (ver Fase 7)
```

Contenido de `__init__.py`:
```python
# ============================================================
# NEXO SOBERANO — [Nombre] Module
# © 2026 elanarcocapital.com
# ============================================================
from .service import [Nombre]Service, [nombre]_service

__all__ = ["[Nombre]Service", "[nombre]_service"]
__version__ = "1.0.0"
__author__ = "NEXO SOBERANO Team | elanarcocapital.com"
```

---

### FASE 6 — TESTS MÍNIMOS OBLIGATORIOS

Crea `tests/test_service.py` con estos 4 tests como mínimo:

```python
# ============================================================
# NEXO SOBERANO — Tests para [Nombre]Service
# © 2026 elanarcocapital.com
# ============================================================
import pytest
from NEXO_CORE.tools.[nombre] import [Nombre]Service, [nombre]_service
from NEXO_CORE.tools.[nombre].service import [Nombre]Input


class Test[Nombre]Service:

    def setup_method(self):
        self.service = [Nombre]Service()

    # TEST 1 — El módulo importa sin errores
    def test_import_ok(self):
        assert [nombre]_service is not None

    # TEST 2 — Happy path (caso normal)
    @pytest.mark.asyncio
    async def test_procesar_caso_normal(self):
        data = [Nombre]Input([campos válidos])
        result = await self.service.procesar(data)
        assert result.success is True
        assert result.error is None

    # TEST 3 — Input inválido
    @pytest.mark.asyncio
    async def test_procesar_input_invalido(self):
        with pytest.raises(Exception):
            [Nombre]Input([campos inválidos que deben fallar Pydantic])

    # TEST 4 — El servicio maneja errores internos sin explotar
    @pytest.mark.asyncio
    async def test_manejo_error_interno(self):
        # simular condición de error
        result = await self.service.procesar([Nombre]Input([caso borde]))
        # debe retornar Output con success=False, no lanzar excepción
        assert isinstance(result, object)
```

Luego indica el comando para correr los tests:
```bash
cd C:\Users\estef\OneDrive\NEXO_SOBERANO
.\.venv\Scripts\python.exe -m pytest NEXO_CORE/tools/[nombre]/tests/ -v
```

---

### FASE 7 — README.md DEL MÓDULO

```markdown
# [Nombre del módulo]
**Módulo NEXO SOBERANO** | [elanarcocapital.com](https://elanarcocapital.com)

---

## ¿Qué hace?
[Descripción en 2-3 líneas de qué resuelve este módulo para NEXO]

## Uso rápido
```python
from NEXO_CORE.tools.[nombre] import [nombre]_service

# Uso básico
result = await [nombre]_service.procesar(data)
if result.success:
    print(result.[campo])
```

## Instalación
Dependencias añadidas a requirements.txt:
```
[paquete]>=[version]  # para [qué]
```

## Variables de entorno requeridas
| Variable | Descripción | Default |
|----------|-------------|---------|
| `[VAR]` | [para qué] | `[default]` |

## Mejoras respecto a la fuente original
- [mejora 1]
- [mejora 2]
- Arquitectura async-first para FastAPI
- Integración nativa con NEXO_CORE config y logging

## Créditos y licencia
[Según corresponda:]
- "Inspirado en [repo] ([licencia]) — reescrito para NEXO SOBERANO"
- "Implementación original de funcionalidad similar a [repo]"
- "Código 100% original NEXO SOBERANO"

---
© 2026 elanarcocapital.com — Todos los derechos reservados
```

---

### FASE 8 — COMMIT LISTO PARA COPIAR

Al final de tu respuesta, entrega SIEMPRE este bloque listo para ejecutar:

```cmd
cd C:\Users\estef\OneDrive\NEXO_SOBERANO
git checkout -b feat/forge-[nombre-corto]
git add NEXO_CORE/tools/[nombre]/
git commit -m "feat(forge): integrate [nombre] - [descripción en 10 palabras]"
git push origin feat/forge-[nombre-corto]
```

Y este test de compatibilidad final:
```cmd
$env:DATABASE_URL="sqlite+aiosqlite:///test.db"
.\.venv\Scripts\python.exe -c "
from NEXO_CORE.tools.[nombre] import [nombre]_service
from main import app
print('[OK] FORGE INTEGRATION COMPATIBLE')
"
```

---

### FASE 9 — REPORTE FINAL OBLIGATORIO

Termina SIEMPRE con este reporte:

```
╔══════════════════════════════════════════════════════════════╗
║              NEXO FORGE — REPORTE DE INTEGRACIÓN             ║
╠══════════════════════════════════════════════════════════════╣
║ REPO ORIGEN:     [url]                                        ║
║ LICENCIA:        [tipo] → Estrategia: [aplicada]              ║
╠══════════════════════════════════════════════════════════════╣
║ ANÁLISIS:                                                     ║
║   Funciones encontradas:   [X]                               ║
║   Funciones integradas:    [X]                               ║
║   Ya existían en NEXO:     [X] — ignoradas                   ║
║   Descartadas (criterios): [X]                               ║
╠══════════════════════════════════════════════════════════════╣
║ MEJORAS APLICADAS:                                            ║
║   Async-first:     [✅/❌]                                    ║
║   Type hints:      [✅/❌]                                    ║
║   Pydantic models: [✅/❌]                                    ║
║   NEXO logging:    [✅/❌]                                    ║
║   Error handling:  [✅/❌]                                    ║
║   Config desde env:[✅/❌]                                    ║
║   Docstrings:      [✅/❌]                                    ║
╠══════════════════════════════════════════════════════════════╣
║ ARCHIVOS CREADOS:                                             ║
║   [lista de archivos]                                        ║
╠══════════════════════════════════════════════════════════════╣
║ DEPENDENCIAS NUEVAS:                                          ║
║   [paquete]>=[version]  ← agregar a requirements.txt         ║
╠══════════════════════════════════════════════════════════════╣
║ TESTS:           [X]/4 pasando                               ║
║ STACK COMPAT:    [✅ OK / ❌ FALLA — descripción]             ║
╠══════════════════════════════════════════════════════════════╣
║ BRANCH:          feat/forge-[nombre]                         ║
║ COMMIT CMD:      [bloque cmd listo para copiar]              ║
╠══════════════════════════════════════════════════════════════╣
║ REQUIERE MERGE MANUAL: SÍ — revisar código antes de mergear  ║
║ © 2026 elanarcocapital.com                                   ║
╚══════════════════════════════════════════════════════════════╝
```

---

## RESTRICCIONES ABSOLUTAS — nunca violar

```
❌ NO copiar código literal de repos GPL o sin licencia
❌ NO mergear a main automáticamente — solo crear branch + PR
❌ NO instalar dependencias >500MB sin mencionarlo
❌ NO modificar archivos existentes de NEXO_CORE fuera de tools/
❌ NO hardcodear secrets, URLs ni credenciales
❌ NO declarar la integración exitosa sin mostrar el test de Fase 8
❌ NO omitir el header © elanarcocapital.com en ningún archivo
```

---

## ▶️ REPOSITORIO A INTEGRAR:

[PEGAR URL AQUÍ]
