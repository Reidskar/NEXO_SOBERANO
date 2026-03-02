"""
Subscription Service: Sistema de suscripción a la revista + envío automático
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4
import hashlib

class SubscriptionService:
    def __init__(self, db_path: str = "subscriptions.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de suscripción."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                name TEXT,
                subscription_type TEXT,
                subscribed_at TEXT,
                unsubscribe_token TEXT UNIQUE,
                active INTEGER DEFAULT 1,
                frequency TEXT DEFAULT 'weekly',
                topics_json TEXT,
                last_sent_issue INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS newsletter_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_number INTEGER UNIQUE,
                title TEXT,
                content_html TEXT,
                published_at TEXT,
                articles_count INTEGER,
                tags_json TEXT,
                featured_image TEXT,
                status TEXT DEFAULT 'draft'
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS subscription_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_id INTEGER,
                event_type TEXT,
                issue_number INTEGER,
                sent_at TEXT,
                opened_at TEXT,
                clicked_at TEXT,
                unsubscribed_at TEXT,
                FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS subscription_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_id INTEGER UNIQUE,
                frequency TEXT,
                day_of_week TEXT,
                time_of_day TEXT,
                preferred_topics TEXT,
                language TEXT DEFAULT 'es',
                FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
            )
            """)

    def subscribe(self, email: str, name: str = "Usuario", 
                 frequency: str = "weekly", topics: list = None) -> Dict:
        """Crear nueva suscripción."""
        try:
            unsubscribe_token = str(uuid4())
            topics_json = json.dumps(topics or ['noticias', 'análisis', 'tecnología'])
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO subscribers 
                (email, name, subscription_type, subscribed_at, unsubscribe_token, 
                 frequency, topics_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    email,
                    name,
                    'newsletter',
                    datetime.utcnow().isoformat(),
                    unsubscribe_token,
                    frequency,
                    topics_json,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
                
                subscriber_id = con.execute(
                    "SELECT id FROM subscribers WHERE email=?", (email,)
                ).fetchone()[0]
                
                # Crear preferencias
                con.execute("""
                INSERT INTO subscription_preferences
                (subscriber_id, frequency, day_of_week, time_of_day, preferred_topics)
                VALUES (?, ?, ?, ?, ?)
                """, (subscriber_id, frequency, 'monday', '09:00', json.dumps(topics or [])))
            
            return {
                'status': 'success',
                'message': f'✅ Suscripción exitosa para {email}',
                'subscriber_id': subscriber_id,
                'unsubscribe_token': unsubscribe_token
            }
        except sqlite3.IntegrityError:
            return {
                'status': 'error',
                'message': '❌ Este email ya está suscrito',
                'code': 'ALREADY_SUBSCRIBED'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def unsubscribe(self, unsubscribe_token: str) -> Dict:
        """Darse de baja de suscripción."""
        try:
            with self._conn() as con:
                cur = con.cursor()
                cur.execute(
                    "SELECT id FROM subscribers WHERE unsubscribe_token=?",
                    (unsubscribe_token,)
                )
                subscriber = cur.fetchone()
                
                if not subscriber:
                    return {
                        'status': 'error',
                        'message': '❌ Token inválido'
                    }
                
                con.execute(
                    "UPDATE subscribers SET active=0, updated_at=? WHERE id=?",
                    (datetime.utcnow().isoformat(), subscriber[0])
                )
                
                con.execute(
                    "INSERT INTO subscription_events (subscriber_id, event_type, unsubscribed_at) VALUES (?, ?, ?)",
                    (subscriber[0], 'unsubscribed', datetime.utcnow().isoformat())
                )
            
            return {
                'status': 'success',
                'message': '✅ Te has dado de baja correctamente'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_active_subscribers(self) -> list:
        """Obtener todos los suscriptores activos."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT id, email, name, frequency, topics_json FROM subscribers WHERE active=1"
            )
            return cur.fetchall()

    def get_subscribers_for_frequency(self, frequency: str) -> list:
        """Obtener suscriptores por frecuencia (daily, weekly, monthly)."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT s.id, s.email, s.name, s.topics_json, p.time_of_day
                FROM subscribers s
                JOIN subscription_preferences p ON s.id = p.subscriber_id
                WHERE s.active=1 AND p.frequency=?
            """, (frequency,))
            return cur.fetchall()

    def publish_issue(self, issue_number: int, title: str, content_html: str,
                     articles_count: int, tags: list = None) -> Dict:
        """Publicar nueva edición de la revista."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO newsletter_issues
                (issue_number, title, content_html, published_at, articles_count, tags_json, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    issue_number,
                    title,
                    content_html,
                    datetime.utcnow().isoformat(),
                    articles_count,
                    json.dumps(tags or []),
                    'published'
                ))
            
            return {
                'status': 'success',
                'message': f'✅ Edición {issue_number} publicada',
                'issue_number': issue_number
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def queue_issue_for_subscribers(self, issue_number: int) -> Dict:
        """Encolar edición para envío a suscriptores."""
        try:
            with self._conn() as con:
                # Obtener edición
                cur = con.cursor()
                cur.execute(
                    "SELECT id, title, content_html FROM newsletter_issues WHERE issue_number=?",
                    (issue_number,)
                )
                issue = cur.fetchone()
                
                if not issue:
                    return {'status': 'error', 'message': 'Edición no encontrada'}
                
                # Obtener suscriptores activos
                cur.execute(
                    "SELECT id, email FROM subscribers WHERE active=1"
                )
                subscribers = cur.fetchall()
                
                # Registrar envío para cada suscriptor
                for sub_id, email in subscribers:
                    con.execute("""
                    INSERT INTO subscription_events
                    (subscriber_id, event_type, issue_number, sent_at)
                    VALUES (?, ?, ?, ?)
                    """, (
                        sub_id,
                        'sent',
                        issue_number,
                        datetime.utcnow().isoformat()
                    ))
                    
                    # Actualizar last_sent_issue
                    con.execute(
                        "UPDATE subscribers SET last_sent_issue=? WHERE id=?",
                        (issue_number, sub_id)
                    )
            
            return {
                'status': 'success',
                'message': f'✅ Edición {issue_number} encolada para {len(subscribers)} suscriptores',
                'total_subscribers': len(subscribers)
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_subscription_stats(self) -> Dict:
        """Obtener estadísticas de suscripción."""
        with self._conn() as con:
            cur = con.cursor()
            
            # Total
            cur.execute("SELECT COUNT(*) FROM subscribers WHERE active=1")
            total = cur.fetchone()[0]
            
            # Por frecuencia
            cur.execute("""
                SELECT frequency, COUNT(*) as count 
                FROM subscription_preferences 
                GROUP BY frequency
            """)
            by_frequency = dict(cur.fetchall())
            
            # Tópicos populares
            cur.execute("SELECT topics_json FROM subscribers WHERE active=1")
            topics_list = []
            for row in cur.fetchall():
                topics_list.extend(json.loads(row[0]))
            
            from collections import Counter
            topics_count = dict(Counter(topics_list))
            
            return {
                'total_subscribers': total,
                'by_frequency': by_frequency,
                'popular_topics': sorted(
                    topics_count.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]
            }

    def track_email_event(self, issue_number: int, subscriber_id: int, 
                         event_type: str) -> bool:
        """Rastrear evento de email (open, click, etc)."""
        try:
            with self._conn() as con:
                if event_type == 'opened':
                    con.execute(
                        """UPDATE subscription_events 
                           SET opened_at=? 
                           WHERE subscriber_id=? AND issue_number=? AND opened_at IS NULL""",
                        (datetime.utcnow().isoformat(), subscriber_id, issue_number)
                    )
                elif event_type == 'clicked':
                    con.execute(
                        """UPDATE subscription_events 
                           SET clicked_at=? 
                           WHERE subscriber_id=? AND issue_number=? AND clicked_at IS NULL""",
                        (datetime.utcnow().isoformat(), subscriber_id, issue_number)
                    )
            return True
        except Exception as e:
            log.info(f"❌ Error tracking event: {e}")
            return False

    def get_newsletter_analytics(self) -> Dict:
        """Obtener analíticas del newsletter."""
        with self._conn() as con:
            cur = con.cursor()
            
            # Total enviados
            cur.execute("SELECT COUNT(*) FROM subscription_events WHERE event_type='sent'")
            total_sent = cur.fetchone()[0]
            
            # Total abiertos
            cur.execute("SELECT COUNT(*) FROM subscription_events WHERE opened_at IS NOT NULL")
            total_opened = cur.fetchone()[0]
            
            # Total clicks
            cur.execute("SELECT COUNT(*) FROM subscription_events WHERE clicked_at IS NOT NULL")
            total_clicked = cur.fetchone()[0]
            
            # Tasas
            open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
            click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
            
            # Por edición
            cur.execute("""
                SELECT issue_number, COUNT(*) as sent, 
                       SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                       SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked
                FROM subscription_events
                WHERE event_type='sent'
                GROUP BY issue_number
                ORDER BY issue_number DESC
                LIMIT 10
            """)
            by_issue = cur.fetchall()
            
            return {
                'total_sent': total_sent,
                'total_opened': total_opened,
                'total_clicked': total_clicked,
                'open_rate': f"{open_rate:.1f}%",
                'click_rate': f"{click_rate:.1f}%",
                'by_issue': by_issue
            }

    def export_subscribers_csv(self) -> str:
        """Exportar suscriptores a CSV."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Email', 'Nombre', 'Frecuencia', 'Tópicos', 'Suscrito'])
        
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT s.email, s.name, p.frequency, s.topics_json, s.subscribed_at
                FROM subscribers s
                LEFT JOIN subscription_preferences p ON s.id = p.subscriber_id
                WHERE s.active=1
            """)
            
            for row in cur.fetchall():
                email, name, freq, topics, subscribed = row
                topics_str = ', '.join(json.loads(topics)) if topics else ''
                writer.writerow([email, name, freq, topics_str, subscribed])
        
        return output.getvalue()

    def import_subscribers_csv(self, csv_content: str) -> Dict:
        """Importar suscriptores desde CSV."""
        import csv
        from io import StringIO
        
        reader = csv.DictReader(StringIO(csv_content))
        imported = 0
        errors = []
        
        for row in reader:
            try:
                result = self.subscribe(
                    email=row['Email'],
                    name=row.get('Nombre', 'Usuario'),
                    frequency=row.get('Frecuencia', 'weekly'),
                    topics=row.get('Tópicos', '').split(', ') if row.get('Tópicos') else []
                )
                if result['status'] == 'success':
                    imported += 1
            except Exception as e:
                errors.append(f"Error en {row.get('Email', 'unknown')}: {str(e)}")
        
        return {
            'status': 'success',
            'imported': imported,
            'errors': errors
        }
