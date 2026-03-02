"""
Marketing Engine: Campañas de marketing digital, social media, SEO
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter

class MarketingEngine:
    def __init__(self, db_path: str = "marketing.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de marketing."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS email_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                subject TEXT,
                content_html TEXT,
                target_audience TEXT,
                recipients_count INTEGER,
                sent_at TEXT,
                opened_count INTEGER,
                clicked_count INTEGER,
                conversion_count INTEGER,
                status TEXT DEFAULT 'draft',
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS social_media_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                content TEXT,
                image_url TEXT,
                hashtags_json TEXT,
                scheduled_for TEXT,
                published_at TEXT,
                likes INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS seo_optimization (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id TEXT,
                page_title TEXT,
                page_url TEXT,
                keywords_json TEXT,
                meta_description TEXT,
                h1_tags_json TEXT,
                content_length INTEGER,
                internal_links INTEGER,
                external_links INTEGER,
                page_speed REAL,
                mobile_friendly INTEGER,
                seo_score INTEGER,
                created_at TEXT,
                updated_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS content_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                content_type TEXT,
                platforms_json TEXT,
                topic TEXT,
                keywords_json TEXT,
                target_audience TEXT,
                status TEXT DEFAULT 'planned',
                published_count INTEGER DEFAULT 0,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS marketing_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric TEXT,
                value REAL,
                period TEXT,
                channel TEXT,
                created_at TEXT
            )
            """)

    def create_email_campaign(self, name: str, subject: str, content_html: str,
                            target_audience: str = 'all') -> Dict:
        """Crear campaña de email marketing."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO email_campaigns
                (name, subject, content_html, target_audience, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    name, subject, content_html, target_audience,
                    'draft', datetime.utcnow().isoformat()
                ))
                
                campaign_id = con.execute(
                    "SELECT id FROM email_campaigns WHERE name=? ORDER BY id DESC LIMIT 1",
                    (name,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'campaign_id': campaign_id,
                'message': f'✅ Campaña "{name}" creada'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def schedule_social_post(self, platform: str, content: str, 
                            image_url: str = None, hashtags: list = None,
                            scheduled_for: str = None) -> Dict:
        """Programar post en redes sociales."""
        try:
            hashtags_json = json.dumps(hashtags or [])
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO social_media_posts
                (platform, content, image_url, hashtags_json, scheduled_for, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    platform, content, image_url, hashtags_json,
                    scheduled_for, datetime.utcnow().isoformat()
                ))
                
                post_id = con.execute(
                    "SELECT id FROM social_media_posts WHERE platform=? AND content=? ORDER BY id DESC LIMIT 1",
                    (platform, content)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'post_id': post_id,
                'message': f'✅ Post programado en {platform}',
                'scheduled_for': scheduled_for
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def generate_social_media_calendar(self, days_ahead: int = 30) -> Dict:
        """Generar calendario de contenido para redes sociales."""
        platforms = ['Instagram', 'Twitter', 'LinkedIn', 'Facebook', 'TikTok']
        content_types = ['Noticia', 'Tutorial', 'Análisis', 'Encuesta', 'Video', 'Infografía']
        
        calendar = []
        
        for i in range(days_ahead):
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Seleccionar plataforma y tipo de contenido
            platform = platforms[i % len(platforms)]
            content_type = content_types[i % len(content_types)]
            
            calendar.append({
                'date': date,
                'platform': platform,
                'content_type': content_type,
                'topic': f'Contenido {content_type.lower()} - Día {i+1}',
                'status': 'planned'
            })
        
        return {
            'status': 'success',
            'calendar': calendar,
            'total_posts': len(calendar)
        }

    def optimize_for_seo(self, page_id: str, page_title: str, page_url: str,
                        content: str, keywords: list) -> Dict:
        """Analizar y optimizar página para SEO."""
        try:
            # Calcular métricas
            content_length = len(content.split())
            h1_tags = [tag for tag in content.split() if '<h1>' in tag or '</h1>' in tag]
            
            # Calcular score SEO (0-100)
            seo_score = self._calculate_seo_score(
                page_title=page_title,
                content_length=content_length,
                keywords=keywords,
                h1_tags_count=len(h1_tags),
                url=page_url
            )
            
            keywords_json = json.dumps(keywords)
            h1_tags_json = json.dumps(h1_tags)
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO seo_optimization
                (page_id, page_title, page_url, keywords_json, content_length, 
                 h1_tags_json, seo_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    page_id, page_title, page_url, keywords_json,
                    content_length, h1_tags_json, seo_score,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
            
            recommendations = self._get_seo_recommendations(seo_score)
            
            return {
                'status': 'success',
                'seo_score': seo_score,
                'recommendations': recommendations,
                'keywords': keywords,
                'content_length': content_length
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _calculate_seo_score(self, page_title: str, content_length: int,
                           keywords: list, h1_tags_count: int, url: str) -> int:
        """Calcular score SEO."""
        score = 0
        
        # Título (max 20 puntos)
        if 30 <= len(page_title) <= 60:
            score += 20
        elif len(page_title) > 0:
            score += 10
        
        # Longitud de contenido (max 20 puntos)
        if content_length >= 300:
            score += 20
        elif content_length >= 150:
            score += 15
        
        # Keywords (max 20 puntos)
        if len(keywords) >= 5:
            score += 20
        elif len(keywords) >= 3:
            score += 15
        elif len(keywords) > 0:
            score += 10
        
        # H1 tags (max 15 puntos)
        if h1_tags_count >= 1:
            score += 15
        
        # URL structure (max 15 puntos)
        if url.count('/') >= 2:
            score += 15
        
        # Mobile friendly (max 10 puntos)
        score += 10
        
        return min(100, score)

    def _get_seo_recommendations(self, seo_score: int) -> list:
        """Obtener recomendaciones según score SEO."""
        recommendations = []
        
        if seo_score < 40:
            recommendations.extend([
                '❌ Mejorar título (30-60 caracteres)',
                '❌ Agregar más contenido (mínimo 300 palabras)',
                '❌ Revisar keywords principales',
                '❌ Añadir meta description'
            ])
        elif seo_score < 70:
            recommendations.extend([
                '⚠️ Título podría mejorarse',
                '⚠️ Agregar más contenido detallado',
                '⚠️ Incluir más keywords relacionadas',
                '⚠️ Mejorar estructura de headers (H1, H2, H3)'
            ])
        else:
            recommendations.extend([
                '✅ SEO muy bueno',
                '💡 Considerar agregar más contenido visual',
                '💡 Incluir enlaces internos estratégicos',
                '💡 Optimizar meta description'
            ])
        
        return recommendations

    def generate_hashtags(self, content: str, count: int = 10) -> list:
        """Generar hashtags relevantes para contenido."""
        # Keywords extraídas del contenido
        words = content.lower().split()
        
        # Filtrar palabras relevantes (>4 caracteres, no es stopword)
        stopwords = {'que', 'para', 'una', 'este', 'este', 'sido', 'otros', 'como'}
        keywords = [w for w in words if len(w) > 4 and w not in stopwords]
        
        # Contar frecuencia
        keyword_freq = Counter(keywords)
        top_keywords = [k for k, v in keyword_freq.most_common(count)]
        
        # Convertir a hashtags
        hashtags = [f"#{kw}" for kw in top_keywords]
        
        return hashtags

    def generate_meta_tags(self, title: str, description: str, keywords: list) -> Dict:
        """Generar meta tags para SEO."""
        return {
            'meta_title': title[:60],  # Max 60 chars
            'meta_description': description[:160],  # Max 160 chars
            'meta_keywords': ', '.join(keywords[:10]),
            'og_title': title,
            'og_description': description,
            'og_type': 'website',
            'twitter_card': 'summary_large_image',
            'twitter_title': title,
            'twitter_description': description[:280]
        }

    def get_marketing_dashboard(self) -> Dict:
        """Obtener dashboard de marketing."""
        with self._conn() as con:
            cur = con.cursor()
            
            # Email campaigns
            cur.execute("""
                SELECT COUNT(*), 
                       SUM(opened_count), 
                       SUM(clicked_count),
                       SUM(conversion_count)
                FROM email_campaigns
                WHERE status='sent'
            """)
            email_stats = cur.fetchone()
            
            # Social media posts
            cur.execute("""
                SELECT COUNT(*), 
                       SUM(likes), 
                       SUM(shares),
                       SUM(impressions)
                FROM social_media_posts
                WHERE published_at IS NOT NULL
            """)
            social_stats = cur.fetchone()
            
            # Top performing posts
            cur.execute("""
                SELECT platform, content, likes, shares, impressions
                FROM social_media_posts
                WHERE published_at IS NOT NULL
                ORDER BY (likes + shares + impressions) DESC
                LIMIT 5
            """)
            top_posts = cur.fetchall()
            
            return {
                'email_campaigns': {
                    'total': email_stats[0] or 0,
                    'opens': email_stats[1] or 0,
                    'clicks': email_stats[2] or 0,
                    'conversions': email_stats[3] or 0
                },
                'social_media': {
                    'total_posts': social_stats[0] or 0,
                    'total_likes': social_stats[1] or 0,
                    'total_shares': social_stats[2] or 0,
                    'total_impressions': social_stats[3] or 0
                },
                'top_performing_posts': [
                    {
                        'platform': row[0],
                        'content': row[1][:100],
                        'engagement': row[2] + row[3]
                    } for row in top_posts
                ]
            }

    def track_campaign_metrics(self, campaign_id: int, metric_type: str,
                              value: float, channel: str = 'email') -> bool:
        """Registrar métrica de campaña."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO marketing_analytics
                (metric, value, channel, period, created_at)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    metric_type, value, channel,
                    datetime.now().strftime('%Y-%m-%d'),
                    datetime.utcnow().isoformat()
                ))
            return True
        except Exception as e:
            log.info(f"❌ Error tracking metric: {e}")
            return False

    def get_growth_strategy(self) -> Dict:
        """Obtener estrategia de crecimiento recomendada."""
        return {
            'title': '🚀 Estrategia de Crecimiento Digital',
            'channels': [
                {
                    'channel': 'Email Marketing',
                    'tactics': [
                        'Segmentación por intereses',
                        'A/B testing de subject lines',
                        'Personalización de contenido',
                        'Automatización de secuencias'
                    ],
                    'expected_roi': '300-400%'
                },
                {
                    'channel': 'Social Media',
                    'tactics': [
                        'Contenido diario consistente',
                        'Engagement con comunidad',
                        'Hashtag strategy optimizada',
                        'Partnerships con influencers'
                    ],
                    'expected_roi': '200-300%'
                },
                {
                    'channel': 'SEO',
                    'tactics': [
                        'Keyword research profesional',
                        'Content optimization',
                        'Link building estratégico',
                        'Technical SEO improvements'
                    ],
                    'expected_roi': '400-500%'
                },
                {
                    'channel': 'Paid Ads',
                    'tactics': [
                        'Google Ads campaigns',
                        'Facebook/Instagram Ads',
                        'Retargeting campaigns',
                        'Conversion tracking'
                    ],
                    'expected_roi': '250-350%'
                },
                {
                    'channel': 'Content Marketing',
                    'tactics': [
                        'Blog posts optimizados',
                        'Video marketing',
                        'Infografías',
                        'Guías y whitepapers'
                    ],
                    'expected_roi': '350-450%'
                }
            ],
            'quarterly_goals': {
                'Q1': 'Establecer base de audiencia',
                'Q2': 'Optimizar conversión',
                'Q3': 'Expandir canales',
                'Q4': 'Consolidar crecimiento'
            }
        }
