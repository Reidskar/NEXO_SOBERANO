import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from sqlalchemy.future import select
from core.database import SessionLocal, Document
from core.config import settings

logger = logging.getLogger(__name__)

class NewsletterWorker:
    def __init__(self):
        # NOTA: Configurar variables reales en entorno de produccion
        self.smtp_host = "smtp.gmail.com"
        self.smtp_port = 587
        self.smtp_user = "tu_correo@gmail.com"
        self.smtp_pass = "tu_password_app"

    async def generate_and_send(self):
        logger.info("Generando Newsletter diario...")
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        async with SessionLocal() as session:
            stmt = select(Document).where(Document.created_at >= yesterday).order_by(Document.impact_level.desc()).limit(3)
            result = await session.execute(stmt)
            top_docs = result.scalars().all()
            
        if not top_docs:
            logger.info("No hay documentos suficientes para el newsletter.")
            return

        html_content = "<h2>🔥 Boletín de Inteligencia NEXO SOBERANO</h2>\n"
        for i, doc in enumerate(top_docs, 1):
            html_content += f"<h3>#{i} - {doc.title} (Impacto: {doc.impact_level}/10)</h3>\n"
            html_content += f"<p><b>País:</b> {doc.country} | <b>Categoría:</b> {doc.category}</p>\n"
            html_content += f"<p><b>Resumen:</b> {doc.summary}</p>\n"
            if doc.drive_url:
                html_content += f"<p><a href='{doc.drive_url}'>Leer Documento Completo</a></p>\n"
            html_content += "<hr>\n"

        # Guardar copia local HTML
        filename = f"newsletter_{datetime.utcnow().strftime('%Y%m%d')}.html"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Reporte HTML guardado localmente en {filename}")
        except Exception as e:
            logger.warning(f"No se pudo guardar copia local de reporte: {e}")

        # Enviar email
        try:
            msg = EmailMessage()
            msg.set_content("Abre el correo en un cliente que soporte HTML.")
            msg.add_alternative(html_content, subtype='html')
            msg['Subject'] = f"Reporte Diario de Inteligencia - {datetime.utcnow().strftime('%Y-%m-%d')}"
            msg['From'] = self.smtp_user
            msg['To'] = "suscriptores@nexosoberano.com"
            
            # TODO: Activar el envio real
            # with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
            #     s.starttls()
            #     s.login(self.smtp_user, self.smtp_pass)
            #     s.send_message(msg)
            
            logger.info("Newsletter generado exitosamente (Simulado).")
        except Exception as e:
            logger.error(f"Error enviando newsletter: {e}")

newsletter_worker = NewsletterWorker()
