"""
backend/routes/shopify.py
API endpoints Shopify para NEXO — marketplace, dropshipping, ventas.
"""
from __future__ import annotations

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

from backend.services.shopify_service import shopify_service, verificar_webhook, procesar_orden_nueva

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/shopify", tags=["shopify"])


# ── Modelos ───────────────────────────────────────────────────────────────────

class ProductoDigitalRequest(BaseModel):
    titulo: str
    descripcion: str
    precio: float
    url_entrega: Optional[str] = ""
    imagenes: Optional[List[str]] = []
    tags: Optional[List[str]] = ["digital", "nexo"]


class ProductoDropshippingRequest(BaseModel):
    titulo: str
    descripcion: str
    precio_venta: float
    precio_costo: float
    proveedor: Optional[str] = "AliExpress"
    sku_proveedor: Optional[str] = ""
    imagenes: Optional[List[str]] = []
    tags: Optional[List[str]] = ["dropshipping"]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
def shopify_status():
    """Verifica configuración Shopify."""
    return {
        "configured": shopify_service.configured,
        "shop": __import__("os").getenv("SHOPIFY_SHOP_DOMAIN", "no configurado"),
    }


@router.get("/productos")
def listar_productos(limit: int = 50):
    """Lista todos los productos de la tienda."""
    try:
        productos = shopify_service.listar_productos(limit=limit)
        return {"ok": True, "total": len(productos), "productos": productos}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/productos/digital")
def crear_producto_digital(body: ProductoDigitalRequest):
    """Crea un producto digital (web, app, template)."""
    try:
        producto = shopify_service.crear_digital(
            titulo=body.titulo,
            descripcion=body.descripcion,
            precio=body.precio,
            url_entrega=body.url_entrega,
            imagenes=body.imagenes,
            tags=body.tags,
        )
        return {"ok": True, "producto": producto}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/productos/dropshipping")
def crear_producto_dropshipping(body: ProductoDropshippingRequest):
    """Crea un producto de dropshipping."""
    try:
        producto = shopify_service.crear_dropshipping(
            titulo=body.titulo,
            descripcion=body.descripcion,
            precio_venta=body.precio_venta,
            precio_costo=body.precio_costo,
            proveedor=body.proveedor,
            sku_proveedor=body.sku_proveedor,
            imagenes=body.imagenes,
            tags=body.tags,
        )
        return {"ok": True, "producto": producto}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/ordenes")
def listar_ordenes(status: str = "any", limit: int = 50):
    """Lista órdenes. status: open | closed | cancelled | any"""
    try:
        ordenes = shopify_service.listar_ordenes(status=status, limit=limit)
        return {"ok": True, "total": len(ordenes), "ordenes": ordenes}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/ventas/resumen")
def resumen_ventas(dias: int = 30):
    """Resumen de ventas de los últimos N días."""
    try:
        return {"ok": True, **shopify_service.resumen_ventas(dias=dias)}
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Webhooks Shopify ──────────────────────────────────────────────────────────

@router.post("/webhook/orden-nueva")
async def webhook_orden_nueva(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
):
    """
    Shopify llama aquí cuando llega una nueva orden.
    Configura en Shopify Admin → Settings → Notifications → Webhooks:
      Topic: orders/create
      URL: https://tu-dominio.com/api/shopify/webhook/orden-nueva
    """
    body = await request.body()

    if x_shopify_hmac_sha256:
        if not verificar_webhook(body, x_shopify_hmac_sha256):
            raise HTTPException(401, "Firma HMAC inválida")

    import json
    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(400, "Payload inválido")

    resultado = procesar_orden_nueva(payload)
    logger.info(f"[SHOPIFY WEBHOOK] Orden nueva procesada: {resultado}")

    # Notificar a Discord si hay órdenes
    try:
        from NEXO_CORE.services.discord_manager import discord_manager
        total = payload.get("total_price", "?")
        email = payload.get("email", "?")
        await discord_manager.send(
            f"🛍️ **Nueva venta Shopify** — ${total} USD — {email}\n"
            f"Orden #{payload.get('order_number', '?')} | {len(payload.get('line_items', []))} item(s)"
        )
    except Exception:
        pass

    return {"ok": True, "procesado": resultado}
