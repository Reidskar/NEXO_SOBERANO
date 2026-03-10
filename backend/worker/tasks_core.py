from backend.worker.celery_app import celery_app as app
from celery.schedules import crontab
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from NEXO_CORE.core.database import get_db_context, set_tenant_schema
from NEXO_CORE.models.schema import Tenant
from backend.services.supabase_client import get_supabase
from google import genai
from backend.services.worldmonitor_bridge import WorldMonitorBridge

logger = logging.getLogger(__name__)

@app.task(name="tasks.process_email_queue")
def process_email_queue():
    """Procesa la cola de emails pendientes en Supabase."""
    logger.info("Iniciando procesamiento de cola de emails...")
    with get_db_context() as db:
        # Nota: email_queue es global en public
        sql = text("SELECT id, to_email, subject, body FROM public.email_queue WHERE enviado = false LIMIT 10")
        emails = db.execute(sql).fetchall()
        
        for email in emails:
            try:
                # Aquí iría la lógica de envío real (SMTP o API)
                logger.info(f"Enviando email a {email.to_email}...")
                
                # Marcar como enviado
                db.execute(text("UPDATE public.email_queue SET enviado = true, enviado_at = NOW() WHERE id = :id"), {"id": email.id})
                db.commit()
            except Exception as e:
                logger.error(f"Error enviando email {email.id}: {e}")

@app.task(name="tasks.sync_worldmonitor")
def sync_worldmonitor():
    """Sincroniza señales de WorldMonitor y las enruta a los tenants."""
    logger.info("Sincronizando señales de WorldMonitor...")
    bridge = WorldMonitorBridge()
    signals = bridge.fetch_latest_signals()
    
    with get_db_context() as db:
        for signal in signals:
            try:
                tenant_slug = signal.get("tenant_slug", "demo")
                set_tenant_schema(db, tenant_slug)
                db.execute(text("""
                    INSERT INTO alertas (tipo, severidad, titulo, descripcion, fuente, created_at)
                    VALUES (:tipo, :sev, :titulo, :desc, 'worldmonitor', NOW())
                    ON CONFLICT DO NOTHING
                """), {
                    "tipo": signal.get("type", "signal"),
                    "sev": float(signal.get("severity", 0.5)),
                    "titulo": signal.get("title", "WM Signal"),
                    "desc": signal.get("body", ""),
                })
                db.commit()
            except Exception as e:
                logger.error(f"Error procesando señal WM: {e}")

@app.task(name="tasks.send_daily_digest")
def send_daily_digest():
    """Genera y envía el resumen diario de inteligencia por tenant usando Gemini."""
    logger.info("Generando digests diarios con Gemini...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY no configurado para digest")
        return

    client = genai.Client(api_key=api_key)

    with get_db_context() as db:
        tenants = db.query(Tenant).filter_by(active=True).all()
        for tenant in tenants:
            try:
                set_tenant_schema(db, tenant.slug)
                # Consultar alertas últimas 24h
                alertas = db.execute(text(
                    "SELECT titulo, descripcion FROM alertas WHERE created_at > NOW() - INTERVAL '24 hours' LIMIT 20"
                )).fetchall()
                
                if not alertas:
                    continue
                    
                prompt = f"Resume estas {len(alertas)} alertas de inteligencia geopolítica en 3 puntos clave accionables:\n" + \
                         "\n".join([f"- {a.titulo}: {a.descripcion}" for a in alertas])
                
                response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
                digest_text = response.text
                
                # Guardar digest en consultas (como registro histórico)
                db.execute(text("""
                    INSERT INTO consultas (fecha, pregunta, respuesta, modelo) 
                    VALUES (NOW(), 'digest_diario', :r, 'gemini-1.5-flash')
                """), {"r": digest_text})
                db.commit()
                logger.info(f"Digest guardado para {tenant.slug}: {len(digest_text)} chars")
            except Exception as e:
                logger.error(f"Error en digest para {tenant.slug}: {e}")

@app.task(name="tasks.cleanup_old_sessions")
def cleanup_old_sessions():
    """Limpia sesiones expiradas en la base de datos pública."""
    logger.info("Limpiando sesiones expiradas...")
    with get_db_context() as db:
        try:
            sql = text("DELETE FROM public.sessions WHERE expires_at < NOW()")
            result = db.execute(sql)
            db.commit()
            logger.info(f"Sesiones limpiadas: {result.rowcount}")
        except Exception as e:
            logger.error(f"Error cleanup sesiones: {e}")
