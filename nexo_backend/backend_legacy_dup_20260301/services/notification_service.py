"""
Notification Service: Envíos de email inteligentes con preferencias
"""

import sqlite3
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class NotificationService:
    def __init__(self, db_path: str = "notifications.db"):
        self.db_path = db_path
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                type TEXT,
                title TEXT,
                content TEXT,
                category TEXT,
                sent_at TEXT,
                read_at TEXT,
                clicked_at TEXT,
                status TEXT DEFAULT 'pending'
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS email_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_email TEXT,
                subject TEXT,
                html_content TEXT,
                frequency TEXT,
                scheduled_for TEXT,
                sent_at TEXT,
                status TEXT DEFAULT 'pending'
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS news_digest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                digest_date TEXT,
                articles_json TEXT,
                digest_type TEXT,
                status TEXT DEFAULT 'pending'
            )
            """)

    def queue_daily_digest(self, user_id: str, user_email: str, articles: list, 
                          personalization: Dict = None):
        """Encolar digest diario para usuario."""
        digest_html = self._generate_digest_html(articles, personalization)
        
        with self._conn() as con:
            con.execute("""
            INSERT INTO email_queue 
            (user_id, user_email, subject, html_content, frequency, scheduled_for, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                user_email,
                "Nexo: Resumen Diario de Noticias",
                digest_html,
                "daily",
                datetime.utcnow().isoformat(),
                "pending"
            ))

    def _generate_digest_html(self, articles: list, personalization: Dict = None) -> str:
        """Generar HTML del digest personalizado."""
        cognitive_model = personalization or {}
        
        # Adaptar contenido según modelo cognitivo
        summary_length = self._get_summary_length(cognitive_model.get('content_length'))
        
        html = """
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
                    .header { background: #00a8e8; color: white; padding: 20px; text-align: center; }
                    .article { border-left: 4px solid #00a8e8; padding: 15px; margin: 15px 0; }
                    .title { font-size: 1.2em; font-weight: bold; }
                    .summary { color: #666; margin: 10px 0; }
                    .footer { color: #999; font-size: 0.85em; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📰 Nexo - Resumen Diario</h1>
                    <p>{}</p>
                </div>
        """.format(datetime.now().strftime("%d de %B de %Y"))
        
        for article in articles[:10]:  # Top 10
            summary = article.get('summary', '')[:summary_length]
            html += f"""
            <div class="article">
                <div class="title">{article.get('title', 'Sin título')}</div>
                <div class="summary">{summary}</div>
                <a href="{article.get('url', '#')}">Leer más →</a>
            </div>
            """
        
        html += """
            <div class="footer">
                <p>Puedes ajustar tus preferencias en Nexo</p>
                <p><a href="#">Anular suscripción</a></p>
            </div>
            </body>
        </html>
        """
        
        return html

    def _get_summary_length(self, content_length: str) -> int:
        """Determinar longitud de resumen según preferencia."""
        lengths = {
            'short': 100,
            'medium': 250,
            'long': 500,
            'full': 9999
        }
        return lengths.get(content_length, 250)

    def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Enviar email realmente."""
        if not all([self.smtp_user, self.smtp_password]):
            log.info("⚠️ SMTP credenciales no configuradas")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, to_email, msg.as_string())
            
            return True
        except Exception as e:
            log.info(f"❌ Error enviando email: {e}")
            return False

    def send_breaking_news_alert(self, user_id: str, user_email: str, news: Dict):
        """Enviar alerta de breaking news."""
        subject = f"⚠️ BREAKING: {news.get('title')}"
        html = f"""
        <html>
            <body style="font-family: sans-serif;">
                <h2 style="color: #d9534f;">{news.get('title')}</h2>
                <p>{news.get('summary')}</p>
                <a href="{news.get('url')}" style="background: #00a8e8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    Leer noticia completa
                </a>
            </body>
        </html>
        """
        
        result = self.send_email(user_email, subject, html)
        
        if result:
            with self._conn() as con:
                con.execute("""
                INSERT INTO notifications 
                (user_id, type, title, content, category, sent_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    'breaking_news',
                    news.get('title'),
                    news.get('summary'),
                    news.get('category'),
                    datetime.utcnow().isoformat(),
                    'sent'
                ))
        
        return result

    def track_email_open(self, notification_id: int):
        """Registrar apertura de email."""
        with self._conn() as con:
            con.execute(
                "UPDATE notifications SET read_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), notification_id)
            )

    def track_link_click(self, notification_id: int):
        """Registrar click en link."""
        with self._conn() as con:
            con.execute(
                "UPDATE notifications SET clicked_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), notification_id)
            )

    def get_pending_emails(self) -> list:
        """Obtener emails pendientes de enviar."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM email_queue WHERE status='pending' LIMIT 100"
            )
            return cur.fetchall()

    def mark_email_sent(self, email_id: int):
        """Marcar email como enviado."""
        with self._conn() as con:
            con.execute(
                "UPDATE email_queue SET sent_at=?, status='sent' WHERE id=?",
                (datetime.utcnow().isoformat(), email_id)
            )

    def get_user_notification_history(self, user_id: str, limit: int = 50) -> list:
        """Obtener historial de notificaciones del usuario."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT * FROM notifications WHERE user_id=? ORDER BY sent_at DESC LIMIT ?",
                (user_id, limit)
            )
            return cur.fetchall()

    def calculate_engagement_score(self, user_id: str) -> float:
        """Calcular score de engagement (0-100)."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT COUNT(*) as total, COUNT(read_at) as read FROM notifications WHERE user_id=?",
                (user_id,)
            )
            row = cur.fetchone()
            
            if not row or row[0] == 0:
                return 50  # Score por defecto
            
            read_rate = row[1] / row[0]
            cur.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id=? AND clicked_at IS NOT NULL",
                (user_id,)
            )
            click_count = cur.fetchone()[0]
            click_rate = click_count / row[0]
            
            # Score = promedio de read_rate (60%) + click_rate (40%)
            score = int((read_rate * 0.6 + click_rate * 0.4) * 100)
            return min(100, max(0, score))

    def should_reduce_notifications(self, user_id: str) -> bool:
        """Detectar si usuario está saturado."""
        engagement = self.calculate_engagement_score(user_id)
        return engagement < 30  # Si <30%, reducir frecuencia
