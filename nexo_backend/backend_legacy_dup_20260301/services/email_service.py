"""
Email Service: Gestión de emails, newsletters y campañas de email marketing
"""

import sqlite3
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class EmailService:
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587,
                 sender_email: str = "", sender_password: str = "",
                 db_path: str = "email_campaigns.db"):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de email."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS email_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                subject TEXT,
                html_body TEXT,
                plain_text_body TEXT,
                variables_json TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS email_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                template_id INTEGER,
                recipient_list_json TEXT,
                subject TEXT,
                status TEXT,
                scheduled_for TEXT,
                sent_at TEXT,
                total_recipients INTEGER,
                sent_count INTEGER DEFAULT 0,
                opened_count INTEGER DEFAULT 0,
                clicked_count INTEGER DEFAULT 0,
                bounced_count INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (template_id) REFERENCES email_templates(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                recipient_email TEXT,
                status TEXT,
                sent_at TEXT,
                opened_at TEXT,
                clicked_at TEXT,
                bounce_reason TEXT,
                error_message TEXT,
                FOREIGN KEY (campaign_id) REFERENCES email_campaigns(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS email_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                updated_at TEXT
            )
            """)

    def configure_smtp(self, smtp_server: str, smtp_port: int,
                      sender_email: str, sender_password: str) -> Dict:
        """Configurar servidor SMTP."""
        try:
            self.smtp_server = smtp_server
            self.smtp_port = smtp_port
            self.sender_email = sender_email
            self.sender_password = sender_password
            
            # Probar conexión
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.quit()
            
            with self._conn() as con:
                con.execute("DELETE FROM email_settings WHERE key IN ('smtp_server', 'smtp_port', 'sender_email')")
                con.execute("INSERT OR REPLACE INTO email_settings (key, value, updated_at) VALUES (?, ?, ?)",
                           ('smtp_server', smtp_server, datetime.utcnow().isoformat()))
                con.execute("INSERT OR REPLACE INTO email_settings (key, value, updated_at) VALUES (?, ?, ?)",
                           ('smtp_port', str(smtp_port), datetime.utcnow().isoformat()))
                con.execute("INSERT OR REPLACE INTO email_settings (key, value, updated_at) VALUES (?, ?, ?)",
                           ('sender_email', sender_email, datetime.utcnow().isoformat()))
            
            return {'status': 'success', 'message': '✅ SMTP configurado correctamente'}
        except Exception as e:
            return {'status': 'error', 'message': f'❌ Error SMTP: {str(e)}'}

    def create_template(self, name: str, subject: str, html_body: str,
                       plain_text_body: str = "", variables: list = None) -> Dict:
        """Crear plantilla de email."""
        try:
            variables_json = json.dumps(variables or [])
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO email_templates
                (name, subject, html_body, plain_text_body, variables_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, subject, html_body, plain_text_body, variables_json,
                     datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                template_id = con.execute(
                    "SELECT id FROM email_templates WHERE name=?", (name,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'template_id': template_id,
                'message': f'✅ Plantilla "{name}" creada'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_campaign(self, name: str, template_id: int, recipients: List[str],
                       subject: str = None, scheduled_for: str = None) -> Dict:
        """Crear campaña de email."""
        try:
            recipients_json = json.dumps(recipients)
            status = 'scheduled' if scheduled_for else 'draft'
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO email_campaigns
                (name, template_id, recipient_list_json, subject, status,
                 scheduled_for, total_recipients, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, template_id, recipients_json, subject, status,
                     scheduled_for, len(recipients), datetime.utcnow().isoformat()))
                
                campaign_id = con.execute(
                    "SELECT id FROM email_campaigns WHERE name=? ORDER BY id DESC LIMIT 1", (name,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'campaign_id': campaign_id,
                'message': f'✅ Campaña "{name}" creada con {len(recipients)} destinatarios'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def send_email(self, to_email: str, subject: str, html_body: str,
                  plain_text_body: str = "", campaign_id: int = None) -> Dict:
        """Enviar email individual."""
        try:
            if not self.sender_email or not self.sender_password:
                return {'status': 'error', 'message': 'SMTP no configurado'}
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email
            
            part1 = MIMEText(plain_text_body or 'Ver versión HTML', 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()
            
            # Log del envío
            if campaign_id:
                with self._conn() as con:
                    con.execute("""
                    INSERT INTO email_logs
                    (campaign_id, recipient_email, status, sent_at)
                    VALUES (?, ?, ?, ?)
                    """, (campaign_id, to_email, 'sent', datetime.utcnow().isoformat()))
                    
                    con.execute(
                        "UPDATE email_campaigns SET sent_count = sent_count + 1 WHERE id=?",
                        (campaign_id,)
                    )
            
            return {'status': 'success', 'message': f'✅ Email enviado a {to_email}'}
        except Exception as e:
            if campaign_id:
                with self._conn() as con:
                    con.execute("""
                    INSERT INTO email_logs
                    (campaign_id, recipient_email, status, error_message)
                    VALUES (?, ?, ?, ?)
                    """, (campaign_id, to_email, 'failed', str(e)))
            
            return {'status': 'error', 'message': f'❌ Error: {str(e)}'}

    def send_bulk_emails(self, campaign_id: int) -> Dict:
        """Enviar emails en lote."""
        try:
            with self._conn() as con:
                # Obtener campaña
                campaign = con.execute(
                    "SELECT template_id, recipient_list_json, subject FROM email_campaigns WHERE id=?",
                    (campaign_id,)
                ).fetchone()
                
                if not campaign:
                    return {'status': 'error', 'message': 'Campaña no encontrada'}
                
                template_id, recipients_json, subject = campaign
                recipients = json.loads(recipients_json)
                
                # Obtener template
                template = con.execute(
                    "SELECT html_body, plain_text_body FROM email_templates WHERE id=?",
                    (template_id,)
                ).fetchone()
                
                html_body, plain_text = template
                
                # Enviar a todos
                sent_count = 0
                failed_count = 0
                
                for recipient in recipients:
                    result = self.send_email(recipient, subject, html_body, plain_text, campaign_id)
                    if result['status'] == 'success':
                        sent_count += 1
                    else:
                        failed_count += 1
                
                # Actualizar estado de campaña
                con.execute(
                    "UPDATE email_campaigns SET status='sent', sent_at=? WHERE id=?",
                    (datetime.utcnow().isoformat(), campaign_id)
                )
            
            return {
                'status': 'success',
                'sent': sent_count,
                'failed': failed_count,
                'message': f'✅ {sent_count} emails enviados, {failed_count} fallidos'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def schedule_campaign(self, campaign_id: int, send_at: str) -> Dict:
        """Programar envío de campaña."""
        try:
            with self._conn() as con:
                con.execute(
                    "UPDATE email_campaigns SET scheduled_for=?, status='scheduled' WHERE id=?",
                    (send_at, campaign_id)
                )
            
            return {'status': 'success', 'message': f'✅ Campaña programada para {send_at}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def track_email_open(self, email_log_id: int) -> Dict:
        """Registrar apertura de email."""
        try:
            with self._conn() as con:
                con.execute(
                    "UPDATE email_logs SET opened_at=?, status='opened' WHERE id=?",
                    (datetime.utcnow().isoformat(), email_log_id)
                )
                
                # Obtener campaign_id para actualizar stats
                campaign_id = con.execute(
                    "SELECT campaign_id FROM email_logs WHERE id=?", (email_log_id,)
                ).fetchone()[0]
                
                con.execute(
                    "UPDATE email_campaigns SET opened_count = opened_count + 1 WHERE id=?",
                    (campaign_id,)
                )
            
            return {'status': 'success', 'message': '✅ Apertura registrada'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def track_email_click(self, email_log_id: int) -> Dict:
        """Registrar click en email."""
        try:
            with self._conn() as con:
                con.execute(
                    "UPDATE email_logs SET clicked_at=? WHERE id=?",
                    (datetime.utcnow().isoformat(), email_log_id)
                )
                
                campaign_id = con.execute(
                    "SELECT campaign_id FROM email_logs WHERE id=?", (email_log_id,)
                ).fetchone()[0]
                
                con.execute(
                    "UPDATE email_campaigns SET clicked_count = clicked_count + 1 WHERE id=?",
                    (campaign_id,)
                )
            
            return {'status': 'success', 'message': '✅ Click registrado'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_campaign_stats(self, campaign_id: int) -> Dict:
        """Obtener estadísticas de campaña."""
        try:
            with self._conn() as con:
                stats = con.execute("""
                SELECT total_recipients, sent_count, opened_count, clicked_count, bounced_count
                FROM email_campaigns
                WHERE id=?
                """, (campaign_id,)).fetchone()
                
                if not stats:
                    return {'status': 'error', 'message': 'Campaña no encontrada'}
                
                total, sent, opened, clicked, bounced = stats
                
                open_rate = (opened / sent * 100) if sent > 0 else 0
                click_rate = (clicked / opened * 100) if opened > 0 else 0
                bounce_rate = (bounced / total * 100) if total > 0 else 0
                
                return {
                    'status': 'success',
                    'total_recipients': total,
                    'sent': sent,
                    'opened': opened,
                    'clicked': clicked,
                    'bounced': bounced,
                    'open_rate': f"{open_rate:.2f}%",
                    'click_rate': f"{click_rate:.2f}%",
                    'bounce_rate': f"{bounce_rate:.2f}%"
                }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_automations(self) -> List[Dict]:
        """Obtener list de automaciones de email."""
        return [
            {
                'name': 'Bienvenida',
                'trigger': 'Nuevo suscriptor',
                'action': 'Email de bienvenida',
                'tags': ['Newsletter', 'Automática']
            },
            {
                'name': 'Abandono de carrito',
                'trigger': 'Carrito >30min sin completar',
                'action': 'Recordatorio con descuento',
                'tags': ['E-commerce', 'Automática']
            },
            {
                'name': 'Re-engagement',
                'trigger': 'Sin abrir emails 30 días',
                'action': 'Email especial de reactivación',
                'tags': ['Retención', 'Automática']
            },
            {
                'name': 'Cumpleaños',
                'trigger': 'Día de cumpleaños',
                'action': 'Email personalizado + oferta',
                'tags': ['Personalización', 'Automática']
            }
        ]

    def export_campaign_report(self, campaign_id: int) -> str:
        """Exportar reporte de campaña en CSV."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Email', 'Estado', 'Enviado', 'Abierto', 'Clicked', 'Motivo Bounce'])
        
        try:
            with self._conn() as con:
                cur = con.cursor()
                cur.execute("""
                    SELECT recipient_email, status, sent_at, opened_at, clicked_at, bounce_reason
                    FROM email_logs
                    WHERE campaign_id=?
                    ORDER BY sent_at DESC
                """, (campaign_id,))
                
                for row in cur.fetchall():
                    email, status, sent, opened, clicked, bounce = row
                    writer.writerow([
                        email,
                        status,
                        sent[:10] if sent else '',
                        'Sí' if opened else 'No',
                        'Sí' if clicked else 'No',
                        bounce or ''
                    ])
        except Exception as e:
            log.info(f"❌ Error exporting campaign report: {e}")
        
        return output.getvalue()

    def create_newsletter_template(self, organization_name: str) -> Dict:
        """Crear plantilla de newsletter profesional."""
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
              <!-- Header -->
              <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">{organization_name} Newsletter</h1>
                <p style="margin: 10px 0 0; font-size: 14px; opacity: 0.9;">Contenido exclusivo cada semana</p>
              </div>
              
              <!-- Content -->
              <div style="padding: 30px;">
                <h2>{{TITLE}}</h2>
                <p style="color: #666; line-height: 1.6;">{{CONTENT}}</p>
                
                <!-- Articles -->
                <div style="margin-top: 20px;">
                  {{ARTICLES}}
                </div>
                
                <!-- CTA Button -->
                <div style="text-align: center; margin-top: 30px;">
                  <a href="{{CTA_URL}}" style="background-color: #667eea; color: white; padding: 12px 30px; border-radius: 5px; text-decoration: none; font-weight: bold;">
                    Leer Más →
                  </a>
                </div>
              </div>
              
              <!-- Footer -->
              <div style="background-color: #f9f9f9; padding: 20px; text-align: center; border-top: 1px solid #eee; font-size: 12px; color: #999;">
                <p>© 2026 {organization_name}. Derechos reservados.</p>
                <p><a href="{{UNSUBSCRIBE_URL}}" style="color: #667eea; text-decoration: none;">Desuscribirse</a></p>
              </div>
            </div>
          </body>
        </html>
        """
        
        return self.create_template(
            name=f"{organization_name}_Newsletter",
            subject=f"{{TITLE}} - {organization_name}",
            html_body=html_body,
            variables=['TITLE', 'CONTENT', 'ARTICLES', 'CTA_URL', 'UNSUBSCRIBE_URL']
        )
