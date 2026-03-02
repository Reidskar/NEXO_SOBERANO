"""
Rutas relacionadas con eventos e infraestructura geoespacial.

Incluye un endpoint `/infraestructura` que usa `overpass_service` para convertir
consultas en lenguaje natural en coordenadas OSM, devolviendo el JSON con el
modelo minimalista.

Más adelante podrán agregarse `/eventos` (eventos propios) y `/alertas`.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict

from backend.services.overpass_service import buscar_infraestructura

router = APIRouter(prefix="/eventos", tags=["eventos"])

@router.get("/infraestructura")
async def infraestructura(query: str = Query(..., description="Texto libre describiendo lo que buscas"),
                          west: Optional[float] = None,
                          south: Optional[float] = None,
                          east: Optional[float] = None,
                          north: Optional[float] = None) -> List[Dict]:
    """Busca objetos en OpenStreetMap según la consulta.

    Se puede limitar mediante caja delimitadora opcional (west, south, east, north).
    """
    bbox = None
    if None not in (west, south, east, north):
        bbox = [west, south, east, north]
    try:
        results = buscar_infraestructura(query, bbox=bbox)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar infraestructura: {e}")
