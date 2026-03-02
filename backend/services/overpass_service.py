"""
Overpass Service — consulta infraestructura crítica usando la Overpass API (OpenStreetMap).

Proporciona un método simple que recibe una cadena de texto en lenguaje natural y
la convierte en una consulta Overpass básica. Los resultados se devuelven en un
formato JSON minimalista similar al modelo de eventos de WorldMonitor.

Este módulo se utiliza desde `backend/routes/eventos.py`.
"""

import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# mapeo de palabras clave a filtros OSM
_FILTER_KEYWORDS = {
    # el valor corresponde al contenido dentro de los corchetes [] en Overpass
    "bases militares": "military",            # cualquier nodo/way/relation con etiqueta "military"
    "plantas nucleares": "amenity=nuclear_power",
    "data centers": "amenity=data_center",
    "pipelines": "man_made=pipeline",
    "puentes": "bridge=yes",
    "aeropuertos": "aeroway=aerodrome",
    # agrega otras palabras clave según sea necesario
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def _build_query(filter_expr: str, bbox: Optional[List[float]] = None) -> str:
    """Construye una consulta básica de Overpass.

    Si se proporciona un `bbox` debe ser una lista de cuatro floats en el orden
    [south, west, north, east] conforme a la sintaxis de Overpass.
    """
    area = ""
    if bbox and len(bbox) == 4:
        south, west, north, east = bbox
        area = f"({south},{west},{north},{east})"
    return f"""[out:json][timeout:25];
(
  node[{filter_expr}]{area};
  way[{filter_expr}]{area};
  relation[{filter_expr}]{area};
);
out center;
"""


def _parse_overpass_response(data: dict) -> List[Dict]:
    """Convierten la respuesta de Overpass a una lista simple de objetos."""
    results: List[Dict] = []
    for el in data.get("elements", []):
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        results.append({
            "id": str(el.get("id")),
            "type": el.get("type"),
            "lat": lat,
            "lon": lon,
            "tags": el.get("tags", {}),
        })
    return results


def buscar_infraestructura(query: str, bbox: Optional[List[float]] = None) -> List[Dict]:
    """Busca infraestructura en Overpass según texto libre.

    Args:
        query: cadena del usuario (e.g. "bases militares cerca de Taiwán").
        bbox: opcional, [west, south, east, north] para acotar la búsqueda.

    Devuelve una lista con elementos que tienen lat/lon y etiquetas OSM.
    """
    text = query.lower()
    filter_expr = None
    keyword: Optional[str] = None
    for k, v in _FILTER_KEYWORDS.items():
        if k in text:
            keyword = k
            filter_expr = v
            break
    if filter_expr is None:
        logger.warning("No existe filtro OSM para la consulta: %s", query)
        return []

    payload = _build_query(filter_expr, bbox=bbox)
    try:
        resp = requests.post(OVERPASS_URL, data=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = _parse_overpass_response(data)
        # si identificamos palabra clave, anotar categoría
        if keyword:
            for it in items:
                it["category"] = keyword
        return items
    except Exception as e:
        logger.error("Error al consultar Overpass: %s", e)
        return []
