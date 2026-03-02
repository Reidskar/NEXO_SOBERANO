"""
Email Dispatcher: Procesa queue de emails y envía automáticamente
Se ejecuta como worker background o scheduled task
"""

import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailDispatcher:
    def __init__(self, db_path: str = "notifications.db"):
        self.db_path = db_path
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.scheduler = BackgroundScheduler()
        self.running = False

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def start(self):
        """Iniciar despachador de emails."""
        if self.running:
            logger.warning("Dispatcher ya está corriendo")
            return

        logger.info("✅ Iniciando Email Dispatcher")
        
        # Ejecutar cada 5 minutos
        self.scheduler.add_job(
            self.process_queue,
            CronTrigger(minute="*/5"),
            id="email_dispatcher",
            name="Procesar queue de emails",
            replace_existing=True
        )
        
        # Enviar resumen diario a las 9am
        self.scheduler.add_job(
            self.send_daily_digests,
            CronTrigger(hour=9, minute=0),
            id="daily_digest",
            name="Enviar digests diarios",
            replace_existing=True
        )
        
        # Limpiar histórico de emails viejos cada domingo
        self.scheduler.add_job(
            self.cleanup_old_emails,
            CronTrigger(day_of_week="sun", hour=0, minute=0),
            id="cleanup_emails",
            name="Limpiar histórico",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.running = True
        logger.info("📧 Email Dispatcher iniciado")

    def stop(self):
        """Detener despachador."""
        if self.running:
            self.scheduler.shutdown()
            self.running = False
            logger.info("⏹️ Email Dispatcher detenido")

    def process_queue(self):
        """Procesar emails pendientes de envío."""
        try:
            with self._conn() as con:
                cur = con.cursor()
                cur.execute(
                    "SELECT id, user_id, user_email, subject, html_content FROM email_queue WHERE status='pending' LIMIT 50"
                )
                emails = cur.fetchall()
            
            if not emails:
                return

            logger.info(f"📤 Procesando {len(emails)} emails...")
            
            for email_id, user_id, user_email, subject, html_content in emails:
                try:
                    if self._send_email(user_email, subject, html_content):
                        self._mark_sent(email_id)
                        logger.info(f"✅ Email {email_id} enviado a {user_email}")
                    else:
                        logger.warning(f"❌ Error enviando email {email_id}")
                except Exception as e:
                    logger.error(f"❌ Error enviando email {email_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error procesando queue: {e}")

    def send_daily_digests(self):
        """Enviar digests diarios a usuarios que lo prefieren."""
        try:
            with self._conn() as con:
                cur = con.cursor()
                # Usuarios con frecuencia daily
                cur.execute("""
                SELECT DISTINCT up.user_id, u.email
                FROM user_preferences up
                JOIN users u ON up.user_id = u.id
                WHERE up.notification_frequency = 'daily'
                """)
                users = cur.fetchall()
            
            logger.info(f"📋 Preparando digests para {len(users)} usuarios...")
            
            for user_id, email in users:
                # TODO: Obtener artículos del día, personalizar, enviar
                pass
                
        except Exception as e:
            logger.error(f"❌ Error enviando digests: {e}")

    def cleanup_old_emails(self):
        """Limpiar histórico de emails 90 días atrás."""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=90)).isoformat()
            
            with self._conn() as con:
                cur = con.cursor()
                cur.execute(
                    "DELETE FROM notifications WHERE sent_at < ? AND status='sent'",
                    (cutoff_date,)
                )
                deleted = cur.rowcount
            
            logger.info(f"🗑️ Eliminados {deleted} emails antigüos")
        except Exception as e:
            logger.error(f"❌ Error limpiando: {e}")

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Enviar email realmente."""
        if not all([self.smtp_user, self.smtp_password]):
            logger.warning("⚠️ SMTP credenciales no configuradas")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            
            # Plain text fallback
            text = f"Nexo Notification: {subject}"
            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, to_email, msg.as_string())
            
            logger.debug(f"📬 Email enviado a {to_email}")
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ Error SMTP: Credenciales inválidas")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ Error SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
            return False

    def _mark_sent(self, email_id: int):
        """Marcar email como enviado."""
        with self._conn() as con:
            con.execute(
                "UPDATE email_queue SET sent_at=?, status='sent' WHERE id=?",
                (datetime.utcnow().isoformat(), email_id)
            )

    def get_stats(self) -> dict:
        """Obtener estadísticas de envío."""
        with self._conn() as con:
            cur = con.cursor()
            
            cur.execute("SELECT COUNT(*) FROM email_queue WHERE status='pending'")
            pending = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM email_queue WHERE status='sent'")
            sent = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM email_queue WHERE status='failed'")
            failed = cur.fetchone()[0]
            
            cur.execute("""
            SELECT COUNT(*) FROM notifications 
            WHERE read_at IS NOT NULL
            """)
            opened = cur.fetchone()[0]
            
            total_notif = cur.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
            open_rate = (opened / total_notif * 100) if total_notif > 0 else 0
        
        return {
            'queue': {
                'pending': pending,
                'sent': sent,
                'failed': failed
            },
            'engagement': {
                'opened': opened,
                'total': total_notif,
                'open_rate': f"{open_rate:.1f}%"
            }
        }

# Crear instancia global
dispatcher = EmailDispatcher()

# Rutas para FastAPI
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["email-dispatcher"])

@router.post("/dispatcher/start")
async def start_dispatcher():
    """Iniciar el despachador de emails."""
    dispatcher.start()
    return {'status': 'started', 'message': 'Email dispatcher iniciado'}

@router.post("/dispatcher/stop")
async def stop_dispatcher():
    """Detener el despachador."""
    dispatcher.stop()
    return {'status': 'stopped', 'message': 'Email dispatcher detenido'}

@router.get("/dispatcher/stats")
async def get_dispatcher_stats():
    """Obtener estadísticas del despachador."""
    stats = dispatcher.get_stats()
    stats['running'] = dispatcher.running
    return stats

@router.post("/dispatcher/process-now")
async def process_now():
    """Procesar queue ahora (sin esperar al schedule)."""
    dispatcher.process_queue()
    return {'status': 'processed', 'message': 'Queue procesada'}

if __name__ == "__main__":
    # Usar como worker independiente
    dispatcher.start()
    
    try:
        logger.info("🚀 Email Dispatcher corriendo...")
        while True:
            asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("⏹️ Deteniendo...")
        dispatcher.stop()
