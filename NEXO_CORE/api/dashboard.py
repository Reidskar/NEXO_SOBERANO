from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from NEXO_CORE.core.database import get_db, set_tenant_schema
from NEXO_CORE.models.schema import Tenant
from typing import Dict, Any
import httpx
import redis
import os
from dotenv import load_dotenv
from backend.services.supabase_client import get_supabase

# Carga explícita de variables para las métricas
load_dotenv()

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
async def get_stats(tenant_slug: str, db: Session = Depends(get_db)):
    """Métricas principales del tenant."""
    set_tenant_schema(db, tenant_slug)
    # Forzar schema explícito para queries directas
    db.execute(text(f"SET search_path TO tenant_{tenant_slug}, public"))
    
    # Simulación de métricas (se integrarían con queries reales)
    stats = {
        "tokens_usados_hoy": db.execute(text("SELECT COALESCE(SUM(tokens_in + tokens_out), 0) FROM costos_api WHERE fecha = CURRENT_DATE")).scalar(),
        "alertas_activas": db.execute(text("SELECT COUNT(*) FROM alertas WHERE procesada = false")).scalar(),
        "documentos_total": db.execute(text("SELECT COUNT(*) FROM evidencia")).scalar()
    }
    return stats

@router.get("/health")
async def get_health(db: Session = Depends(get_db)):
    """Estado de salud detallado de servicios externos."""
    health = {
        "supabase": "error",
        "redis": "error",
        "qdrant": "error",
        "database": "error"
    }
    
    # Check Database (Postgres)
    try:
        db.execute(text("SELECT 1"))
        health["database"] = "operative"
    except: pass

    # Check Supabase API
    try:
        sb = get_supabase()
        # Simple test query to public schema
        sb.table("tenants").select("count", count="exact").limit(1).execute()
        health["supabase"] = "connected"
    except: pass

    # Check Qdrant
    try:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{qdrant_url}/healthz", timeout=2.0)
            if resp.status_code == 200:
                health["qdrant"] = "operative"
    except: pass

    # Check Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, socket_timeout=2.0)
        if r.ping():
            health["redis"] = "operative"
    except: pass

    return health

@router.get("/tenants")
async def list_tenants(db: Session = Depends(get_db)):
    """Lista todos los tenants activos."""
    tenants = db.query(Tenant).all()
    return [{"slug": t.slug, "name": t.name, "plan": t.plan, "active": t.active} for t in tenants]

@router.get("/token-history")
async def token_history(tenant_slug: str, days: int = 1, db: Session = Depends(get_db)):
    """Retorna el historial de consumo de tokens agrupado por hora."""
    set_tenant_schema(db, tenant_slug)
    # Forzar schema explícito
    schema = f"tenant_{tenant_slug.replace('-', '_')}"
    db.execute(text(f"SET search_path TO {schema}, public"))
    
    rows = db.execute(text("""
        SELECT DATE_TRUNC('hour', created_at) as hora,
               SUM(tokens_in + tokens_out) as total
        FROM costos_api 
        WHERE created_at > NOW() - INTERVAL '1 day' * :days
        GROUP BY hora ORDER BY hora
    """), {"days": days}).fetchall()
    
    return {
        "labels": [r.hora.strftime("%H:%M") if hasattr(r.hora, 'strftime') else str(r.hora) for r in rows],
        "values": [r.total for r in rows]
    }
