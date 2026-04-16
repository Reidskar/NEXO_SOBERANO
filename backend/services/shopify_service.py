"""
backend/services/shopify_service.py
Integración NEXO ↔ Shopify Admin API

Casos de uso:
  1. Venta de sitios web y apps (productos digitales)
  2. Dropshipping (productos físicos — fulfillment automático)
  3. Generación de capital — monitoreo de ventas + reporting

Variables .env necesarias:
  SHOPIFY_SHOP_DOMAIN   = tu-tienda.myshopify.com
  SHOPIFY_ACCESS_TOKEN  = shpat_xxxxx  (Admin API token)
  SHOPIFY_WEBHOOK_SECRET = xxx         (para validar webhooks)
"""
from __future__ import annotations

import os
import hmac
import hashlib
import logging
import json
from typing import Optional
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# ── Configuración ──────────────────────────────────────────────────────────────
SHOP_DOMAIN    = os.getenv("SHOPIFY_SHOP_DOMAIN", "")     # siku.myshopify.com
API_KEY        = os.getenv("SHOPIFY_API_KEY", "")
ACCESS_TOKEN   = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

API_VERSION = "2024-10"
BASE_URL    = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}"

HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}


# ── Cliente HTTP ───────────────────────────────────────────────────────────────

def _get(path: str, params: dict = None) -> dict:
    if not SHOP_DOMAIN or not ACCESS_TOKEN:
        raise RuntimeError("SHOPIFY_SHOP_DOMAIN y SHOPIFY_ACCESS_TOKEN no configurados en .env")
    r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(path: str, data: dict) -> dict:
    if not SHOP_DOMAIN or not ACCESS_TOKEN:
        raise RuntimeError("SHOPIFY_SHOP_DOMAIN y SHOPIFY_ACCESS_TOKEN no configurados en .env")
    r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=data, timeout=15)
    r.raise_for_status()
    return r.json()


def _put(path: str, data: dict) -> dict:
    r = requests.put(f"{BASE_URL}{path}", headers=HEADERS, json=data, timeout=15)
    r.raise_for_status()
    return r.json()


# ── Productos ──────────────────────────────────────────────────────────────────

def listar_productos(limit: int = 50) -> list:
    """Lista los productos de la tienda Shopify."""
    data = _get("/products.json", params={"limit": limit})
    return data.get("products", [])


def crear_producto_digital(
    titulo: str,
    descripcion: str,
    precio: float,
    url_entrega: str = "",
    imagenes: list[str] = None,
    tags: list[str] = None,
) -> dict:
    """
    Crea un producto digital (sitio web, app, template).
    La entrega se gestiona vía url_entrega (metafield o nota en orden).
    """
    product_data = {
        "product": {
            "title": titulo,
            "body_html": descripcion,
            "vendor": "El Anarcocapital",
            "product_type": "Digital",
            "tags": ", ".join(tags or ["digital", "nexo"]),
            "variants": [
                {
                    "price": str(precio),
                    "requires_shipping": False,
                    "taxable": True,
                    "inventory_management": None,
                    "inventory_policy": "continue",
                }
            ],
        }
    }
    if imagenes:
        product_data["product"]["images"] = [{"src": src} for src in imagenes]

    result = _post("/products.json", product_data)
    product = result.get("product", {})

    # Guardar URL de entrega como metafield
    if url_entrega and product.get("id"):
        _post(f"/products/{product['id']}/metafields.json", {
            "metafield": {
                "namespace": "nexo",
                "key": "download_url",
                "value": url_entrega,
                "type": "url",
            }
        })

    logger.info(f"[SHOPIFY] Producto digital creado: {titulo} (id={product.get('id')})")
    return product


def crear_producto_dropshipping(
    titulo: str,
    descripcion: str,
    precio_venta: float,
    precio_costo: float,
    proveedor: str = "AliExpress",
    sku_proveedor: str = "",
    imagenes: list[str] = None,
    tags: list[str] = None,
) -> dict:
    """
    Crea un producto de dropshipping con info del proveedor en metafields.
    """
    product_data = {
        "product": {
            "title": titulo,
            "body_html": descripcion,
            "vendor": proveedor,
            "product_type": "Dropshipping",
            "tags": ", ".join(tags or ["dropshipping"]),
            "variants": [
                {
                    "price": str(precio_venta),
                    "compare_at_price": str(round(precio_venta * 1.2, 2)),
                    "cost": str(precio_costo),
                    "requires_shipping": True,
                    "taxable": True,
                    "sku": sku_proveedor,
                }
            ],
        }
    }
    if imagenes:
        product_data["product"]["images"] = [{"src": src} for src in imagenes]

    result = _post("/products.json", product_data)
    product = result.get("product", {})

    # Metafield con info de proveedor
    if product.get("id"):
        _post(f"/products/{product['id']}/metafields.json", {
            "metafield": {
                "namespace": "dropshipping",
                "key": "supplier_info",
                "value": json.dumps({
                    "proveedor": proveedor,
                    "sku": sku_proveedor,
                    "costo": precio_costo,
                }),
                "type": "json",
            }
        })

    logger.info(f"[SHOPIFY] Producto dropshipping creado: {titulo} (proveedor={proveedor})")
    return product


# ── Órdenes ────────────────────────────────────────────────────────────────────

def listar_ordenes(status: str = "any", limit: int = 50) -> list:
    """Lista órdenes. status: 'open' | 'closed' | 'cancelled' | 'any'"""
    data = _get("/orders.json", params={"status": status, "limit": limit})
    return data.get("orders", [])


def obtener_orden(order_id: int) -> dict:
    data = _get(f"/orders/{order_id}.json")
    return data.get("order", {})


def resumen_ventas(dias: int = 30) -> dict:
    """Resumen de ventas de los últimos N días."""
    from datetime import timedelta, timezone
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    ordenes = _get("/orders.json", params={
        "status": "any",
        "created_at_min": desde,
        "limit": 250,
        "fields": "id,total_price,financial_status,fulfillment_status,created_at,line_items",
    }).get("orders", [])

    total_ventas   = 0.0
    total_ordenes  = len(ordenes)
    digital_count  = 0
    drop_count     = 0

    for o in ordenes:
        if o.get("financial_status") == "paid":
            total_ventas += float(o.get("total_price", 0))
        for item in o.get("line_items", []):
            if not item.get("requires_shipping"):
                digital_count += 1
            else:
                drop_count += 1

    return {
        "periodo_dias": dias,
        "total_ordenes": total_ordenes,
        "total_ventas_usd": round(total_ventas, 2),
        "items_digitales": digital_count,
        "items_dropshipping": drop_count,
        "promedio_orden": round(total_ventas / max(total_ordenes, 1), 2),
    }


# ── Webhooks ───────────────────────────────────────────────────────────────────

def verificar_webhook(body: bytes, signature_header: str) -> bool:
    """Valida la firma HMAC de un webhook de Shopify."""
    if not WEBHOOK_SECRET:
        logger.warning("[SHOPIFY] SHOPIFY_WEBHOOK_SECRET no configurado — saltando verificación")
        return True
    digest = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).digest()
    import base64
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature_header)


def procesar_orden_nueva(payload: dict) -> dict:
    """
    Lógica de fulfillment automático al recibir una orden nueva.
    - Digital: envía email con link de descarga
    - Dropshipping: notifica para routing manual/automático
    """
    order_id    = payload.get("id")
    email       = payload.get("email", "")
    total       = payload.get("total_price", "0")
    line_items  = payload.get("line_items", [])

    acciones = []
    for item in line_items:
        requires_shipping = item.get("requires_shipping", True)
        product_id        = item.get("product_id")
        title             = item.get("title", "?")

        if not requires_shipping:
            # Producto digital — buscar URL de entrega
            acciones.append({
                "tipo": "digital",
                "producto": title,
                "accion": "enviar_link_descarga",
                "email": email,
                "product_id": product_id,
            })
            logger.info(f"[SHOPIFY] Orden digital #{order_id}: {title} → {email}")
        else:
            # Dropshipping — notificar
            acciones.append({
                "tipo": "dropshipping",
                "producto": title,
                "accion": "notificar_fulfillment",
                "product_id": product_id,
            })
            logger.info(f"[SHOPIFY] Orden dropshipping #{order_id}: {title}")

    return {
        "order_id": order_id,
        "email": email,
        "total": total,
        "acciones": acciones,
    }


# ── Instancia global ───────────────────────────────────────────────────────────

class ShopifyService:
    """Wrapper con estado para uso desde otros módulos."""

    @property
    def configured(self) -> bool:
        return bool(SHOP_DOMAIN and ACCESS_TOKEN)

    def listar_productos(self, **kw):   return listar_productos(**kw)
    def listar_ordenes(self, **kw):     return listar_ordenes(**kw)
    def resumen_ventas(self, **kw):     return resumen_ventas(**kw)
    def crear_digital(self, **kw):      return crear_producto_digital(**kw)
    def crear_dropshipping(self, **kw): return crear_producto_dropshipping(**kw)


shopify_service = ShopifyService()
