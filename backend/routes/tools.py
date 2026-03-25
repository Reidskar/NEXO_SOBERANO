# ============================================================
# NEXO SOBERANO — Tools API Router
# © 2026 elanarcocapital.com
# ============================================================
from __future__ import annotations
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/tools", tags=["tools"])

@router.get("/domain-scan")
async def scan_domain(domain: str = "elanarcocapital.com"):
    """Escaneo de inteligencia de dominio para nexo-sentinel."""
    try:
        from NEXO_CORE.tools.domain_intel import domain_intel_service
    except ImportError:
        raise HTTPException(503, "domain_intel no disponible en este entorno")
    result = await domain_intel_service.scan(domain)
    return {
        "domain":        result.domain,
        "timestamp":     result.scan_timestamp,
        "ssl_valid":     result.ssl_info.get("valid"),
        "ssl_days_left": result.ssl_info.get("days_until_expiry"),
        "dns_resolved":  result.dns_records.get("resolved"),
        "ips":           result.dns_records.get("ips", []),
        "alerts":        result.alerts,
        "alert_count":   len(result.alerts),
        "success":       result.success
    }
