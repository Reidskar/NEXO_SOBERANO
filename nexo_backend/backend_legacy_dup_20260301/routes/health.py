"""
Health Check y Monitoreo del Sistema
"""

from fastapi import APIRouter
from datetime import datetime
import psutil
import sqlite3
import os

router = APIRouter(prefix="/health", tags=["Health"])

def get_system_stats():
    """Obtener estadísticas del sistema."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
    }

def get_database_stats():
    """Estadísticas de BD."""
    try:
        db_path = "/app/data/nexo.db"
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            
            con = sqlite3.connect(db_path)
            cur = con.cursor()
            cur.execute("SELECT COUNT(*) FROM messages")
            msg_count = cur.fetchone()[0]
            con.close()
            
            return {
                "size_mb": round(size_mb, 2),
                "message_count": msg_count,
                "status": "healthy"
            }
    except Exception as e:
        return {"error": str(e), "status": "unhealthy"}
    return {"status": "no_data"}

@router.get("/")
def health_check():
    """Health check básico."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0"
    }

@router.get("/full")
def full_health_check():
    """Health check completo con sistema."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "system": get_system_stats(),
        "database": get_database_stats(),
        "version": "2.0"
    }

@router.get("/metrics")
def metrics():
    """Métricas para Prometheus."""
    stats = get_system_stats()
    db_stats = get_database_stats()
    
    metrics_text = f"""# HELP cpu_usage CPU usage percentage
# TYPE cpu_usage gauge
cpu_usage {stats['cpu_percent']}

# HELP memory_usage Memory usage percentage
# TYPE memory_usage gauge
memory_usage {stats['memory_percent']}

# HELP disk_usage Disk usage percentage
# TYPE disk_usage gauge
disk_usage {stats['disk_percent']}

# HELP db_size Database size in MB
# TYPE db_size gauge
db_size {db_stats.get('size_mb', 0)}

# HELP messages_total Total messages in database
# TYPE messages_total counter
messages_total {db_stats.get('message_count', 0)}
"""
    
    return metrics_text
