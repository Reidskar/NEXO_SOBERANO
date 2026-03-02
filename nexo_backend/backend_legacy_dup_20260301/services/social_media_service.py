"""
Social Media Manager: Gestión de redes sociales y publicaciones
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List

class SocialMediaManager:
    def __init__(self, db_path: str = "social_media.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de redes sociales."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS social_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                account_name TEXT,
                username TEXT,
                access_token TEXT,
                followers_count INTEGER,
                connected_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                platform TEXT,
                content TEXT,
                media_urls_json TEXT,
                hashtags_json TEXT,
                mentions_json TEXT,
                post_type TEXT,
                scheduled_for TEXT,
                published_at TEXT,
                post_id TEXT,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                created_at TEXT,
                FOREIGN KEY (account_id) REFERENCES social_accounts(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS hashtag_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hashtag TEXT UNIQUE,
                platform TEXT,
                usage_count INTEGER,
                reach INTEGER,
                engagement INTEGER,
                trending INTEGER DEFAULT 0,
                last_updated TEXT
            )
            """)

    def connect_social_account(self, platform: str, account_name: str,
                              username: str, access_token: str) -> Dict:
        """Conectar cuenta de red social."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO social_accounts
                (platform, account_name, username, access_token, connected_at)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    platform, account_name, username, access_token,
                    datetime.utcnow().isoformat()
                ))
                
                account_id = con.execute(
                    "SELECT id FROM social_accounts WHERE username=?", (username,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'account_id': account_id,
                'message': f'✅ Cuenta {username} conectada en {platform}'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_post(self, account_id: int, platform: str, content: str,
                   media_urls: list = None, hashtags: list = None,
                   mentions: list = None, post_type: str = 'text',
                   scheduled_for: str = None) -> Dict:
        """Crear post para red social."""
        try:
            media_urls_json = json.dumps(media_urls or [])
            hashtags_json = json.dumps(hashtags or [])
            mentions_json = json.dumps(mentions or [])
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO social_posts
                (account_id, platform, content, media_urls_json, hashtags_json,
                 mentions_json, post_type, scheduled_for, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id, platform, content, media_urls_json,
                    hashtags_json, mentions_json, post_type,
                    scheduled_for, datetime.utcnow().isoformat()
                ))
                
                post_id = con.execute(
                    "SELECT id FROM social_posts WHERE account_id=? AND platform=? ORDER BY id DESC LIMIT 1",
                    (account_id, platform)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'post_id': post_id,
                'message': f'✅ Post creado para {platform}',
                'scheduled_for': scheduled_for or 'Inmediato'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def bulk_create_posts(self, content_calendar: list) -> Dict:
        """Crear múltiples posts desde calendario."""
        created = 0
        errors = []
        
        for item in content_calendar:
            try:
                result = self.create_post(
                    account_id=item.get('account_id'),
                    platform=item.get('platform'),
                    content=item.get('content'),
                    media_urls=item.get('media_urls'),
                    hashtags=item.get('hashtags'),
                    scheduled_for=item.get('scheduled_for')
                )
                if result['status'] == 'success':
                    created += 1
            except Exception as e:
                errors.append(str(e))
        
        return {
            'status': 'success',
            'created': created,
            'errors': errors
        }

    def publish_post(self, post_id: int) -> Dict:
        """Publicar post ahora."""
        try:
            with self._conn() as con:
                con.execute(
                    "UPDATE social_posts SET published_at=? WHERE id=?",
                    (datetime.utcnow().isoformat(), post_id)
                )
            
            return {'status': 'success', 'message': '✅ Post publicado'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_optimal_posting_times(self, platform: str) -> Dict:
        """Obtener horarios óptimos para publicar."""
        optimal_times = {
            'Instagram': {
                'weekdays': ['9:00 AM', '12:00 PM', '6:00 PM', '8:00 PM'],
                'weekends': ['11:00 AM', '3:00 PM', '7:00 PM'],
                'best_day': 'Wednesday',
                'engagement_rate': '5.2%'
            },
            'Twitter': {
                'weekdays': ['8:00 AM', '1:00 PM', '5:00 PM', '9:00 PM'],
                'weekends': ['10:00 AM', '4:00 PM', '8:00 PM'],
                'best_day': 'Thursday',
                'engagement_rate': '3.8%'
            },
            'LinkedIn': {
                'weekdays': ['7:30 AM', '12:00 PM', '5:30 PM'],
                'weekends': ['10:00 AM', '3:00 PM'],
                'best_day': 'Tuesday',
                'engagement_rate': '2.5%'
            },
            'Facebook': {
                'weekdays': ['1:00 PM', '7:00 PM', '8:00 PM'],
                'weekends': ['12:00 PM', '6:00 PM'],
                'best_day': 'Saturday',
                'engagement_rate': '4.1%'
            },
            'TikTok': {
                'weekdays': ['6:00 AM', '10:00 AM', '7:00 PM', '11:00 PM'],
                'weekends': ['10:00 AM', '12:00 PM', '8:00 PM', '10:00 PM'],
                'best_day': 'Friday',
                'engagement_rate': '8.7%'
            }
        }
        
        return optimal_times.get(platform, {
            'weekdays': ['9:00 AM', '12:00 PM', '6:00 PM'],
            'weekends': ['11:00 AM', '3:00 PM', '7:00 PM'],
            'best_day': 'Wednesday',
            'engagement_rate': 'Variable'
        })

    def track_post_engagement(self, post_id: int, likes: int = 0,
                             comments: int = 0, shares: int = 0,
                             views: int = 0) -> Dict:
        """Registrar engagement de post."""
        try:
            total_engagement = likes + comments + shares
            engagement_rate = (total_engagement / max(views, 1)) * 100 if views > 0 else 0
            
            with self._conn() as con:
                con.execute("""
                UPDATE social_posts 
                SET likes=?, comments=?, shares=?, views=?, engagement_rate=?
                WHERE id=?
                """, (likes, comments, shares, views, engagement_rate, post_id))
            
            return {
                'status': 'success',
                'engagement_rate': f"{engagement_rate:.2f}%",
                'total_engagement': total_engagement
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_trending_hashtags(self, platform: str = None) -> list:
        """Obtener hashtags trending."""
        try:
            with self._conn() as con:
                cur = con.cursor()
                
                if platform:
                    cur.execute("""
                        SELECT hashtag, usage_count, engagement, engagement/usage_count as rate
                        FROM hashtag_analytics
                        WHERE platform=? AND trending=1
                        ORDER BY engagement DESC
                        LIMIT 15
                    """, (platform,))
                else:
                    cur.execute("""
                        SELECT hashtag, usage_count, engagement
                        FROM hashtag_analytics
                        WHERE trending=1
                        ORDER BY engagement DESC
                        LIMIT 20
                    """)
                
                results = cur.fetchall()
                return [{'hashtag': r[0], 'usage': r[1], 'engagement': r[2]} for r in results]
        except Exception as e:
            log.info(f"❌ Error getting trending hashtags: {e}")
            return []

    def suggest_hashtags_for_content(self, content: str, platform: str,
                                    count: int = 15) -> list:
        """Sugerir hashtags relevantes para contenido."""
        # Palabras clave extraídas
        words = content.lower().split()
        keywords = [w for w in words if len(w) > 4]
        
        # Hashtags genéricos según platform
        platform_hashtags = {
            'Instagram': [
                '#nexo', '#noticias', '#tecnología', '#análisis', '#tendencias',
                '#digital', '#marketing', '#socialmedia', '#innovation', '#trending'
            ],
            'Twitter': [
                '#News', '#Tech', '#Breaking', '#Analysis', '#Trending',
                '#Business', '#Innovation', '#Digital'
            ],
            'LinkedIn': [
                '#Business', '#Innovation', '#Leadership', '#Technology',
                '#Education', '#Career', '#Professional', '#Future'
            ],
            'Facebook': [
                '#News', '#Community', '#Insights', '#Updates', '#Trending',
                '#Importante', '#Información', '#Popular'
            ],
            'TikTok': [
                '#FYP', '#Trending', '#Viral', '#ForYou', '#Explore',
                '#Fresh', '#New', '#Popular', '#Challenge'
            ]
        }
        
        base_hashtags = platform_hashtags.get(platform, ['#trending', '#viral'])
        
        # Generar hashtags de palabras clave
        keyword_hashtags = [f"#{kw[:20]}" for kw in keywords[:count-len(base_hashtags)]]
        
        return (base_hashtags[:len(base_hashtags)] + keyword_hashtags)[:count]

    def get_social_analytics(self, account_id: int = None) -> Dict:
        """Obtener analíticas de redes sociales."""
        with self._conn() as con:
            cur = con.cursor()
            
            if account_id:
                cur.execute("""
                    SELECT platform, COUNT(*) as total_posts,
                           SUM(likes) as total_likes,
                           SUM(comments) as total_comments,
                           SUM(shares) as total_shares,
                           AVG(engagement_rate) as avg_engagement
                    FROM social_posts
                    WHERE account_id=?
                    GROUP BY platform
                """, (account_id,))
            else:
                cur.execute("""
                    SELECT platform, COUNT(*) as total_posts,
                           SUM(likes) as total_likes,
                           SUM(comments) as total_comments,
                           SUM(shares) as total_shares,
                           AVG(engagement_rate) as avg_engagement
                    FROM social_posts
                    GROUP BY platform
                """)
            
            results = cur.fetchall()
            
            analytics = {}
            for row in results:
                platform, posts, likes, comments, shares, engagement = row
                analytics[platform] = {
                    'total_posts': posts,
                    'total_likes': likes or 0,
                    'total_comments': comments or 0,
                    'total_shares': shares or 0,
                    'avg_engagement': f"{engagement:.2f}%" if engagement else "0%"
                }
            
            return analytics

    def schedule_content_series(self, platform: str, theme: str,
                               ndays: int = 7) -> Dict:
        """Programar serie de contenido."""
        posts = []
        for i in range(ndays):
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            optimal_time = self.get_optimal_posting_times(platform)
            scheduled_for = f"{date} {optimal_time['weekdays'][i % len(optimal_time['weekdays'])]}"
            
            posts.append({
                'date': date,
                'platform': platform,
                'theme': theme,
                'scheduled_for': scheduled_for,
                'status': 'scheduled'
            })
        
        return {
            'status': 'success',
            'series': posts,
            'total_posts': len(posts),
            'theme': theme
        }

    def export_social_calendar(self) -> str:
        """Exportar calendario de redes sociales."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Plataforma', 'Contenido', 'Hashtags', 'Estado', 'Engagement'])
        
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT scheduled_for, platform, content, hashtags_json, 
                       CASE WHEN published_at IS NOT NULL THEN 'Publicado' 
                            ELSE 'Programado' END,
                       engagement_rate
                FROM social_posts
                ORDER BY scheduled_for
            """)
            
            for row in cur.fetchall():
                scheduled, platform, content, hashtags, status, engagement = row
                hashtags_str = ', '.join(json.loads(hashtags)) if hashtags else ''
                writer.writerow([
                    scheduled, platform, content[:50], hashtags_str, status, f"{engagement:.1f}%"
                ])
        
        return output.getvalue()
