# ============================================================
# NEXO SOBERANO — Drive + Photos Intelligence Bridge v1.0
# © 2026 elanarcocapital.com
#
# Conecta evidencia clasificada del Drive y Google Photos
# con el OmniGlobe. La IA entiende el contexto visual y
# lo convierte en eventos georreferenciados en el globo.
#
# Flujo:
#   Drive/Photos → Gemma 4 clasifica → extrae contexto geo
#   → evento en OmniGlobe con evidencia vinculada
# ============================================================
from __future__ import annotations
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("NEXO.drive_intel")

ROOT = Path(__file__).resolve().parents[2]

# Carpetas del Drive que contienen evidencia clasificada
DRIVE_INTEL_FOLDERS = os.getenv("DRIVE_INTEL_FOLDERS", "NEXO_INTEL,EVIDENCIAS,OSINT_CLASSIFIED").split(",")
PHOTOS_CONTEXT_DIR  = ROOT / "logs" / "context_cache" / "photos_intel"
PHOTOS_CONTEXT_DIR.mkdir(parents=True, exist_ok=True)

# Coordenadas por palabras clave en nombres de archivos/descripciones
GEO_KEYWORDS = {
    "ucrania":   (48.3, 31.1), "ukraine":  (48.3, 31.1),
    "rusia":     (55.7, 37.6), "russia":   (55.7, 37.6),
    "israel":    (31.7, 35.2), "gaza":     (31.5, 34.4),
    "taiwan":    (23.5, 121.0),"china":    (35.8, 104.1),
    "iran":      (32.4, 53.6), "siria":    (34.8, 38.9),
    "syria":     (34.8, 38.9), "yemen":    (15.5, 48.5),
    "sahel":     (14.0, 2.0),  "mali":     (17.5, -4.0),
    "venezuela": (6.4, -66.5), "colombia": (4.6, -74.1),
    "mexico":    (23.6, -102.5),"brasil":  (-14.2, -51.9),
    "pakistan":  (30.4, 69.3), "india":    (20.6, 78.9),
    "corea":     (37.5, 127.0),"korea":    (37.5, 127.0),
    "taiwan_strait": (24.0, 119.5),
}

# Tipos de evidencia y su severidad
EVIDENCE_TYPES = {
    "militar":    {"severity": 0.8, "color": "#ef4444", "icon": "🔴"},
    "conflicto":  {"severity": 0.7, "color": "#f97316", "icon": "🟠"},
    "economico":  {"severity": 0.5, "color": "#eab308", "icon": "🟡"},
    "politico":   {"severity": 0.5, "color": "#6366f1", "icon": "🔵"},
    "tecnologico":{"severity": 0.4, "color": "#22c55e", "icon": "🟢"},
    "humanitario":{"severity": 0.6, "color": "#ec4899", "icon": "🩷"},
    "ambiental":  {"severity": 0.4, "color": "#10b981", "icon": "🌿"},
    "general":    {"severity": 0.4, "color": "#94a3b8", "icon": "⚪"},
}


class DriveIntelBridge:
    """
    Clasifica evidencia de Drive/Photos con Gemma 4 y la mapea al globo.
    La IA entiende el contexto de cada archivo y extrae:
    - Región geográfica
    - Tipo de evento
    - Nivel de relevancia
    """

    def __init__(self):
        self._ai = None
        self._classified_cache: dict[str, dict] = {}

    @property
    def ai(self):
        if self._ai is None:
            from NEXO_CORE.services.ollama_service import ollama_service
            self._ai = ollama_service
        return self._ai

    # ── CLASIFICACIÓN CON GEMMA 4 ─────────────────────────────────────────────

    async def clasificar_archivo(
        self,
        nombre: str,
        descripcion: str = "",
        contenido_preview: str = "",
    ) -> dict:
        """
        Gemma 4 clasifica un archivo de Drive/Photos y extrae contexto geopolítico.
        Retorna: {lat, lng, tipo, severidad, label, relevante: bool}
        Costo: $0.
        """
        cache_key = nombre[:50]
        if cache_key in self._classified_cache:
            return self._classified_cache[cache_key]

        system = (
            "Eres un analista de inteligencia geopolítica. "
            "Analiza el nombre/descripción del archivo y extrae:\n"
            "1. País o región geográfica principal\n"
            "2. Tipo de evento: militar/conflicto/economico/politico/tecnologico/humanitario/ambiental/general\n"
            "3. Relevancia: ¿Es inteligencia accionable? (true/false)\n\n"
            "Responde SOLO JSON:\n"
            '{"region": "nombre", "lat": 0.0, "lng": 0.0, "tipo": "...", "severidad": 0.0-1.0, "relevante": true/false, "label": "titulo corto"}'
        )
        texto = f"Archivo: {nombre}\n"
        if descripcion:
            texto += f"Descripción: {descripcion}\n"
        if contenido_preview:
            texto += f"Preview: {contenido_preview[:200]}\n"

        result = {"lat": 0, "lng": 0, "tipo": "general", "severidad": 0.3, "relevante": False, "label": nombre[:40]}

        # Primero: búsqueda de keywords en nombre/descripción
        texto_lower = (nombre + " " + descripcion).lower()
        for keyword, coords in GEO_KEYWORDS.items():
            if keyword in texto_lower:
                result["lat"], result["lng"] = coords
                result["relevante"] = True
                break

        # Luego: Gemma 4 para clasificación semántica
        resp = await self.ai.consultar(prompt=texto, modelo="fast", system=system, temperature=0.0, max_tokens=120)
        if resp.success:
            try:
                m = re.search(r'\{.*\}', resp.text, re.DOTALL)
                if m:
                    parsed = json.loads(m.group())
                    result.update({k: v for k, v in parsed.items() if k in result})
            except Exception:
                pass

        self._classified_cache[cache_key] = result
        return result

    async def procesar_drive_reciente(self, limite: int = 20) -> list[dict]:
        """
        Procesa archivos recientes del Drive y genera eventos para el globo.
        """
        eventos_globo = []
        try:
            from services.connectors.google_connector import list_recent_files_detailed
            archivos = list_recent_files_detailed(max_results=limite)
        except Exception as e:
            logger.warning(f"Drive connector no disponible: {e}")
            # Fallback: buscar en directorio local de documentos
            archivos = self._scan_local_docs()

        for archivo in archivos:
            nombre = archivo.get("name", "") or archivo.get("title", "")
            descripcion = archivo.get("description", "") or ""
            if not nombre:
                continue

            clasificacion = await self.clasificar_archivo(nombre, descripcion)
            if not clasificacion.get("relevante"):
                continue

            tipo_conf = EVIDENCE_TYPES.get(clasificacion.get("tipo", "general"), EVIDENCE_TYPES["general"])
            evento = {
                "id":       f"drive_{hash(nombre) & 0xFFFF}",
                "type":     "add_event",
                "lat":      clasificacion["lat"],
                "lng":      clasificacion["lng"],
                "label":    clasificacion.get("label", nombre[:40]),
                "severity": clasificacion.get("severidad", tipo_conf["severity"]),
                "radius":   0.07,
                "color":    tipo_conf["color"],
                "layer":    "events",
                "source":   "drive_intel",
                "ts":       datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "tipo":     clasificacion.get("tipo"),
                    "archivo":  nombre,
                    "drive_id": archivo.get("id", ""),
                    "region":   clasificacion.get("region", ""),
                },
            }
            eventos_globo.append(evento)

        logger.info(f"Drive intel: {len(eventos_globo)}/{len(archivos)} archivos relevantes mapeados")
        return eventos_globo

    async def procesar_fotos_contexto(self) -> list[dict]:
        """
        Lee el estado de Google Photos (ai_context_tracker) y mapea imágenes
        con contexto geográfico detectado por Gemma 4.
        """
        try:
            context_file = ROOT / "logs" / "ai_context" / "google_photos_last.json"
            if not context_file.exists():
                return []
            data = json.loads(context_file.read_text(encoding="utf-8"))
            fotos = data.get("fotos_recientes", data.get("items", []))[:30]
        except Exception:
            return []

        eventos = []
        for foto in fotos:
            nombre = foto.get("filename", foto.get("name", ""))
            desc   = foto.get("description", foto.get("alt", ""))
            meta   = foto.get("mediaMetadata", {})
            # Extraer EXIF si está disponible
            lat = meta.get("photo", {}).get("latitude") or foto.get("lat")
            lng = meta.get("photo", {}).get("longitude") or foto.get("lng")

            if lat and lng:
                # Tiene coordenadas EXIF — clasificar con Gemma 4
                clasificacion = await self.clasificar_archivo(nombre, desc)
                if clasificacion.get("relevante"):
                    tipo_conf = EVIDENCE_TYPES.get(clasificacion.get("tipo", "general"), EVIDENCE_TYPES["general"])
                    eventos.append({
                        "id":      f"photo_{hash(nombre) & 0xFFFF}",
                        "type":    "add_event",
                        "lat":     float(lat),
                        "lng":     float(lng),
                        "label":   clasificacion.get("label", nombre[:40]),
                        "severity":clasificacion.get("severidad", 0.4),
                        "radius":  0.05,
                        "color":   tipo_conf["color"],
                        "layer":   "events",
                        "source":  "google_photos",
                        "ts":      datetime.now(timezone.utc).isoformat(),
                        "metadata":{"foto": nombre, "tipo": clasificacion.get("tipo")},
                    })

        logger.info(f"Photos intel: {len(eventos)} fotos geolocalizadas mapeadas")
        return eventos

    def _scan_local_docs(self) -> list[dict]:
        """Fallback: escanear directorio local de documentos."""
        docs = []
        for d in [ROOT / "documentos", ROOT / "data", ROOT / "intel"]:
            if d.exists():
                for f in list(d.glob("**/*"))[:50]:
                    if f.is_file():
                        docs.append({"name": f.name, "path": str(f)})
        return docs


# Instancia global
drive_intel_bridge = DriveIntelBridge()
