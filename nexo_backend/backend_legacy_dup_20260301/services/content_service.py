"""
Content Management Service: Gestión centralizada de contenido y editorial
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List
from enum import Enum

class ContentStatus(Enum):
    IDEA = "idea"
    OUTLINE = "outline"
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ContentType(Enum):
    BLOG = "blog"
    VIDEO = "video"
    PODCAST = "podcast"
    INFOGRAPHIC = "infographic"
    WHITEPAPER = "whitepaper"
    CASE_STUDY = "case_study"
    WEBINAR = "webinar"
    EBOOK = "ebook"

class ContentService:
    def __init__(self, db_path: str = "content.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de gestión de contenido."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS content_pieces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                slug TEXT UNIQUE,
                content_type TEXT,
                status TEXT,
                markup_content TEXT,
                plain_text_content TEXT,
                estimated_reading_time INTEGER,
                author TEXT,
                created_at TEXT,
                updated_at TEXT,
                published_at TEXT,
                scheduled_for TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS content_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                keywords_json TEXT,
                tags_json TEXT,
                meta_description TEXT,
                thumbnail_url TEXT,
                featured_image_url TEXT,
                seo_score INTEGER,
                target_audience TEXT,
                content_category TEXT,
                FOREIGN KEY (content_id) REFERENCES content_pieces(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS content_distribution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                platform TEXT,
                platform_url TEXT,
                published_at TEXT,
                views INTEGER DEFAULT 0,
                engagement INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                status TEXT,
                FOREIGN KEY (content_id) REFERENCES content_pieces(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS editorial_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                publish_date TEXT,
                time_zone TEXT,
                distribution_channels_json TEXT,
                promotion_strategy TEXT,
                status TEXT,
                created_at TEXT,
                FOREIGN KEY (content_id) REFERENCES content_pieces(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS content_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER,
                date TEXT,
                views INTEGER,
                unique_visitors INTEGER,
                average_time_on_page REAL,
                bounce_rate REAL,
                conversions INTEGER,
                revenue REAL,
                created_at TEXT,
                FOREIGN KEY (content_id) REFERENCES content_pieces(id)
            )
            """)

    def create_content(self, title: str, content_type: str,
                      markup_content: str = "",
                      author: str = "system",
                      target_audience: str = "",
                      keywords: List[str] = None) -> Dict:
        """Crear nueva pieza de contenido."""
        try:
            slug = title.lower().replace(' ', '-')[:50]
            
            # Calcular tiempo de lectura (aprox 200 palabras/minuto)
            word_count = len(markup_content.split())
            reading_time = max(1, word_count // 200)
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO content_pieces
                (title, slug, content_type, status, markup_content,
                 plain_text_content, estimated_reading_time, author, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (title, slug, content_type, 'draft', markup_content,
                     markup_content, reading_time, author,
                     datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                content_id = con.execute(
                    "SELECT id FROM content_pieces WHERE slug=?", (slug,)
                ).fetchone()[0]
                
                # Insertar metadata
                keywords_json = json.dumps(keywords or [])
                con.execute("""
                INSERT INTO content_metadata
                (content_id, keywords_json, target_audience)
                VALUES (?, ?, ?)
                """, (content_id, keywords_json, target_audience))
            
            return {
                'status': 'success',
                'content_id': content_id,
                'message': f'✅ Contenido "{title}" creado',
                'reading_time': f"{reading_time} min"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def update_content_status(self, content_id: int, new_status: str) -> Dict:
        """Actualizar estado de contenido."""
        try:
            with self._conn() as con:
                con.execute(
                    "UPDATE content_pieces SET status=?, updated_at=? WHERE id=?",
                    (new_status, datetime.utcnow().isoformat(), content_id)
                )
            
            status_messages = {
                'draft': '📝 Borrador',
                'review': '👀 En revisión',
                'approved': '✅ Aprobado',
                'scheduled': '📅 Programado',
                'published': '🚀 Publicado'
            }
            
            return {
                'status': 'success',
                'new_status': status_messages.get(new_status, new_status)
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def schedule_content(self, content_id: int, publish_date: str,
                        distribution_channels: List[str] = None) -> Dict:
        """Programar publicación de contenido."""
        try:
            distribution_json = json.dumps(distribution_channels or ['blog', 'email', 'social'])
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO editorial_calendar
                (content_id, publish_date, distribution_channels_json, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (content_id, publish_date, distribution_json, 'scheduled',
                     datetime.utcnow().isoformat()))
                
                con.execute(
                    "UPDATE content_pieces SET status=?, scheduled_for=? WHERE id=?",
                    ('scheduled', publish_date, content_id)
                )
            
            return {
                'status': 'success',
                'message': f'✅ Contenido programado para {publish_date}',
                'channels': distribution_channels
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def publish_content(self, content_id: int) -> Dict:
        """Publicar contenido ahora."""
        try:
            with self._conn() as con:
                content = con.execute(
                    "SELECT title, slug FROM content_pieces WHERE id=?", (content_id,)
                ).fetchone()
                
                con.execute(
                    "UPDATE content_pieces SET status=?, published_at=? WHERE id=?",
                    ('published', datetime.utcnow().isoformat(), content_id)
                )
                
                # Registrar en distribution channels
                channels = ['website', 'email', 'social']
                for channel in channels:
                    con.execute("""
                    INSERT INTO content_distribution
                    (content_id, platform, status)
                    VALUES (?, ?, ?)
                    """, (content_id, channel, 'published'))
            
            return {
                'status': 'success',
                'message': f'✅ Contenido "{content[0]}" publicado',
                'url': f"/blog/{content[1]}"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_editorial_calendar(self, days_ahead: int = 30) -> Dict:
        """Obtener calendario editorial."""
        try:
            start_date = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            
            with self._conn() as con:
                calendar = con.execute("""
                    SELECT ec.publish_date, cp.title, cp.content_type, cp.status,
                           ec.distribution_channels_json
                    FROM editorial_calendar ec
                    JOIN content_pieces cp ON ec.content_id = cp.id
                    WHERE ec.publish_date BETWEEN ? AND ?
                    ORDER BY ec.publish_date
                """, (start_date, end_date)).fetchall()
            
            grouped = {}
            for row in calendar:
                date = row[0]
                if date not in grouped:
                    grouped[date] = []
                
                grouped[date].append({
                    'title': row[1],
                    'type': row[2],
                    'status': row[3],
                    'channels': json.loads(row[4])
                })
            
            return {
                'status': 'success',
                'calendar': grouped,
                'total_items': sum(len(v) for v in grouped.values())
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def track_content_performance(self, content_id: int,
                                 views: int = 0,
                                 unique_visitors: int = 0,
                                 avg_time_on_page: float = 0,
                                 bounce_rate: float = 0) -> Dict:
        """Registrar análisis de contenido."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO content_analytics
                (content_id, date, views, unique_visitors, average_time_on_page,
                 bounce_rate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (content_id, datetime.now().strftime('%Y-%m-%d'),
                     views, unique_visitors, avg_time_on_page, bounce_rate,
                     datetime.utcnow().isoformat()))
            
            return {
                'status': 'success',
                'message': '✅ Análisis registrado',
                'metrics': {
                    'views': views,
                    'bounce_rate': f"{bounce_rate:.1f}%",
                    'avg_time_page': f"{avg_time_on_page:.1f}s"
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_content_performance_report(self, content_id: int) -> Dict:
        """Obtener reporte de desempeño de contenido."""
        try:
            with self._conn() as con:
                content = con.execute(
                    "SELECT title, published_at FROM content_pieces WHERE id=?",
                    (content_id,)
                ).fetchone()
                
                analytics = con.execute("""
                    SELECT SUM(views), SUM(unique_visitors), AVG(average_time_on_page),
                           AVG(bounce_rate), SUM(conversions), SUM(revenue)
                    FROM content_analytics
                    WHERE content_id=?
                """, (content_id,)).fetchone()
            
            total_views, unique, avg_time, avg_bounce, conversions, revenue = analytics or (0, 0, 0, 0, 0, 0)
            
            return {
                'status': 'success',
                'content': content[0] if content else 'N/A',
                'published': content[1] if content else 'N/A',
                'performance': {
                    'views': total_views or 0,
                    'unique_visitors': unique or 0,
                    'avg_time_on_page': f"{avg_time or 0:.1f}s",
                    'bounce_rate': f"{avg_bounce or 0:.1f}%",
                    'conversions': conversions or 0,
                    'revenue': f"${revenue or 0:.2f}"
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_content_ideas(self) -> List[Dict]:
        """Obtener ideas de contenido sugeridas."""
        return [
            {
                'title': 'Tendencias de IA 2025',
                'type': 'Blog',
                'channel': 'Todos',
                'seo_opportunity': 'Alto',
                'estimated_traffic': '+500 views'
            },
            {
                'title': 'Introducción a Marketing Digital',
                'type': 'Guía',
                'channel': 'Email + Social',
                'seo_opportunity': 'Muy Alto',
                'estimated_traffic': '+1.2K views'
            },
            {
                'title': 'Case Study: Resultados de Campaña',
                'type': 'Case Study',
                'channel': 'LinkedIn + Blog',
                'seo_opportunity': 'Medio',
                'estimated_traffic': '+300 views'
            },
            {
                'title': 'Video: Top 5 Tips de Email Marketing',
                'type': 'Video',
                'channel': 'YouTube + TikTok',
                'seo_opportunity': 'Alto',
                'estimated_traffic': '+800 views'
            }
        ]

    def get_content_calendar_template(self) -> Dict:
        """Obtener template de calendario de contenido."""
        today = datetime.now()
        
        return {
            'status': 'success',
            'week_template': [
                {
                    'day': 'Monday',
                    'content_type': 'Blog Post',
                    'channels': ['Blog', 'Email'],
                    'time': '9:00 AM'
                },
                {
                    'day': 'Wednesday',
                    'content_type': 'Video',
                    'channels': ['YouTube', 'TikTok'],
                    'time': '2:00 PM'
                },
                {
                    'day': 'Thursday',
                    'content_type': 'Infografía',
                    'channels': ['Twitter', 'LinkedIn'],
                    'time': '10:00 AM'
                },
                {
                    'day': 'Friday',
                    'content_type': 'Case Study',
                    'channels': ['LinkedIn', 'Email'],
                    'time': '3:00 PM'
                },
                {
                    'day': 'Saturday',
                    'content_type': 'Reel',
                    'channels': ['Instagram', 'TikTok'],
                    'time': '7:00 PM'
                }
            ]
        }

    def suggest_content_repurposing(self, original_content_id: int) -> Dict:
        """Sugerir maneras de reutilizar contenido."""
        return {
            'status': 'success',
            'original': 'Blog Post',
            'repurposing_opportunities': [
                {
                    'format': 'Infographic',
                    'platform': 'Instagram, Pinterest',
                    'effort': 'Media',
                    'potential_reach': '+2K views'
                },
                {
                    'format': 'Video Summary',
                    'platform': 'YouTube, TikTok',
                    'effort': 'Alta',
                    'potential_reach': '+5K views'
                },
                {
                    'format': 'Email Series',
                    'platform': 'Email',
                    'effort': 'Baja',
                    'potential_reach': '+3K opens'
                },
                {
                    'format': 'Podcast',
                    'platform': 'Spotify, Apple Podcasts',
                    'effort': 'Alta',
                    'potential_reach': '+1.5K listeners'
                },
                {
                    'format': 'Twitter Thread',
                    'platform': 'Twitter, LinkedIn',
                    'effort': 'Baja',
                    'potential_reach': '+800 impressions'
                }
            ]
        }

    def get_seo_content_recommendations(self) -> List[Dict]:
        """Obtener recomendaciones de SEO para contenido."""
        return [
            {
                'title': 'Optimizar meta descriptions',
                'impact': '+15% CTR',
                'effort': 'Baja',
                'priority': 'Alta'
            },
            {
                'title': 'Agregar schema markup',
                'impact': '+25% rich snippets',
                'effort': 'Media',
                'priority': 'Media'
            },
            {
                'title': 'Crear internal linking strategy',
                'impact': '+30% session duration',
                'effort': 'Media',
                'priority': 'Alta'
            },
            {
                'title': 'Optimizar velocidad de página',
                'impact': '+20% ranking',
                'effort': 'Alta',
                'priority': 'Alta'
            },
            {
                'title': 'Actualizar contenido antiguo',
                'impact': '+40% traffic',
                'effort': 'Variable',
                'priority': 'Media'
            }
        ]
