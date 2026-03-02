"""
Influencer & Partnerships Service: Gestión de influencers y colaboraciones estratégicas
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List
from enum import Enum

class PartnershipStatus(Enum):
    PROSPECT = "prospect"
    NEGOTIATION = "negotiation"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"

class InfluencerService:
    def __init__(self, db_path: str = "influencers.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas de influencers y partnerships."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS influencers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                username TEXT UNIQUE,
                platform TEXT,
                followers INTEGER,
                engagement_rate REAL,
                avg_likes INTEGER,
                avg_comments INTEGER,
                bio TEXT,
                verified INTEGER DEFAULT 0,
                contact_email TEXT,
                contact_phone TEXT,
                website TEXT,
                rate_per_post REAL,
                niche_json TEXT,
                audience_demographics_json TEXT,
                added_at TEXT,
                last_analyzed TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS partnerships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                influencer_id INTEGER,
                partnership_name TEXT,
                status TEXT,
                campaign_type TEXT,
                deliverables_json TEXT,
                compensation REAL,
                currency TEXT,
                start_date TEXT,
                end_date TEXT,
                content_posts INTEGER,
                stories INTEGER,
                reels INTEGER,
                links_expected TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (influencer_id) REFERENCES influencers(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS partnership_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partnership_id INTEGER,
                metric_date TEXT,
                impressions INTEGER,
                engagement INTEGER,
                clicks INTEGER,
                conversions INTEGER,
                sales REAL,
                roi REAL,
                sentiment_score REAL,
                created_at TEXT,
                FOREIGN KEY (partnership_id) REFERENCES partnerships(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS affiliate_programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                affiliate_id TEXT,
                affiliate_name TEXT,
                platform TEXT,
                commission_rate REAL,
                volume_bonus_json TEXT,
                status TEXT,
                total_sales REAL,
                total_commission REAL,
                join_date TEXT,
                last_payout TEXT,
                created_at TEXT
            )
            """)

    def add_influencer(self, name: str, username: str, platform: str,
                      followers: int, engagement_rate: float = 0,
                      contact_email: str = "", rate_per_post: float = 0,
                      niches: List[str] = None) -> Dict:
        """Agregar influencer a base de datos."""
        try:
            niche_json = json.dumps(niches or [])
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO influencers
                (name, username, platform, followers, engagement_rate, contact_email,
                 rate_per_post, niche_json, added_at, last_analyzed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, username, platform, followers, engagement_rate, contact_email,
                     rate_per_post, niche_json, datetime.utcnow().isoformat(),
                     datetime.utcnow().isoformat()))
                
                influencer_id = con.execute(
                    "SELECT id FROM influencers WHERE username=?", (username,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'influencer_id': influencer_id,
                'message': f'✅ Influencer "{name}" agregado'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def search_influencers(self, platform: str = None, niche: str = None,
                          min_followers: int = 0, max_followers: int = None) -> List[Dict]:
        """Buscar influencers por criterios."""
        try:
            query = "SELECT * FROM influencers WHERE followers >= ?"
            params = [min_followers]
            
            if platform:
                query += " AND platform = ?"
                params.append(platform)
            
            if max_followers:
                query += " AND followers <= ?"
                params.append(max_followers)
            
            if niche:
                query += " AND niche_json LIKE ?"
                params.append(f'%"{niche}"%')
            
            query += " ORDER BY followers DESC"
            
            with self._conn() as con:
                results = con.execute(query, params).fetchall()
            
            influencers = []
            for r in results:
                influencers.append({
                    'id': r[0],
                    'name': r[1],
                    'username': r[2],
                    'platform': r[3],
                    'followers': r[4],
                    'engagement_rate': f"{r[5]}%" if r[5] else "N/A",
                    'niches': json.loads(r[10]),
                    'rate_per_post': f"${r[13]}" if r[13] else "Negotiable"
                })
            
            return influencers
        except Exception as e:
            log.info(f"❌ Error searching influencers: {e}")
            return []

    def create_partnership(self, influencer_id: int, partnership_name: str,
                          campaign_type: str = "sponsored_post",
                          deliverables: Dict = None,
                          compensation: float = 0,
                          start_date: str = None,
                          end_date: str = None) -> Dict:
        """Crear partnership con influencer."""
        try:
            deliverables_json = json.dumps(deliverables or {
                'content_posts': 1,
                'stories': 3,
                'reels': 0
            })
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO partnerships
                (influencer_id, partnership_name, status, campaign_type,
                 deliverables_json, compensation, start_date, end_date, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (influencer_id, partnership_name, 'negotiation', campaign_type,
                     deliverables_json, compensation,
                     start_date or datetime.now().isoformat(),
                     end_date or (datetime.now() + timedelta(days=30)).isoformat(),
                     datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                partnership_id = con.execute(
                    "SELECT id FROM partnerships WHERE influencer_id=? ORDER BY id DESC LIMIT 1",
                    (influencer_id,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'partnership_id': partnership_id,
                'message': f'✅ Partnership "{partnership_name}" creado'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_partnership_status(self, partnership_id: int) -> Dict:
        """Obtener estado detallado de partnership."""
        try:
            with self._conn() as con:
                partnership = con.execute(
                    "SELECT * FROM partnerships WHERE id=?", (partnership_id,)
                ).fetchone()
                
                if not partnership:
                    return {'status': 'error', 'message': 'Partnership no encontrado'}
                
                performance = con.execute("""
                    SELECT SUM(impressions), SUM(engagement), SUM(clicks),
                           SUM(conversions), SUM(sales), AVG(roi)
                    FROM partnership_performance
                    WHERE partnership_id=?
                """, (partnership_id,)).fetchone()
            
            total_impressions, total_engagement, total_clicks, total_conversions, total_sales, avg_roi = performance or (0, 0, 0, 0, 0, 0)
            
            return {
                'status': 'success',
                'partnership': {
                    'id': partnership[0],
                    'name': partnership[2],
                    'campaign_type': partnership[4],
                    'status': partnership[3],
                    'compensation': f"${partnership[7]}",
                    'start_date': partnership[8],
                    'end_date': partnership[9]
                },
                'performance': {
                    'impressions': total_impressions or 0,
                    'engagement': total_engagement or 0,
                    'clicks': total_clicks or 0,
                    'conversions': total_conversions or 0,
                    'sales': f"${total_sales or 0:.2f}",
                    'avg_roi': f"{avg_roi or 0:.1f}%" if avg_roi else "N/A"
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def track_partnership_performance(self, partnership_id: int,
                                     impressions: int = 0,
                                     engagement: int = 0,
                                     clicks: int = 0,
                                     conversions: int = 0,
                                     sales: float = 0) -> Dict:
        """Registrar métricas de performance."""
        try:
            with self._conn() as con:
                # Obtener costo del partnership
                partnership = con.execute(
                    "SELECT compensation FROM partnerships WHERE id=?", (partnership_id,)
                ).fetchone()
                
                compensation = partnership[0] if partnership else 0
                roi = ((sales - compensation) / compensation * 100) if compensation > 0 else 0
                
                con.execute("""
                INSERT INTO partnership_performance
                (partnership_id, metric_date, impressions, engagement, clicks,
                 conversions, sales, roi, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (partnership_id, datetime.now().strftime('%Y-%m-%d'),
                     impressions, engagement, clicks, conversions, sales, roi,
                     datetime.utcnow().isoformat()))
            
            return {
                'status': 'success',
                'roi': f"{roi:.1f}%",
                'sales': f"${sales}",
                'message': '✅ Métricas registradas'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_affiliate_program(self, affiliate_name: str, platform: str,
                                commission_rate: float = 0.10) -> Dict:
        """Crear programa de afiliados."""
        try:
            volume_bonus = json.dumps({
                '1000': 0.12,
                '5000': 0.15,
                '10000': 0.20
            })
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO affiliate_programs
                (affiliate_name, platform, commission_rate, volume_bonus_json,
                 status, join_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (affiliate_name, platform, commission_rate, volume_bonus,
                     'active', datetime.now().isoformat(),
                     datetime.utcnow().isoformat()))
                
                affiliate_id = con.execute(
                    "SELECT id FROM affiliate_programs ORDER BY id DESC LIMIT 1"
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'affiliate_id': affiliate_id,
                'message': f'✅ Programa de afiliados creado',
                'commission_structure': {
                    'base_rate': f"{commission_rate * 100}%",
                    'volume_bonuses': json.loads(volume_bonus)
                }
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_influencer_outreach_template(self, influencer_name: str,
                                        campaign_name: str) -> str:
        """Obtener template de email para contactar influencer."""
        return f"""
Subject: Colaboración con {campaign_name}

Hola {influencer_name},

Espero encuentres bien. He seguido tu contenido en [PLATFORM] y me encanta tu enfoque en [NICHE].

Creemos que sería una excelente oportunidad colaborar en [{campaign_name}]. Nuestras audiencias se alinean perfectamente y creo que podríamos crear algo impactante juntos.

Propuesta:
• [DELIVERABLE 1]
• [DELIVERABLE 2]
• [DELIVERABLE 3]

Compensación: $[AMOUNT] + [ADDITIONAL BENEFITS]
Cronograma: [START DATE] - [END DATE]

¿Te gustaría conversar más sobre esto? Estoy disponible para agendar una llamada.

Saludos,
[YOUR NAME]
[YOUR TITLE]
[CONTACT INFO]
        """

    def get_partnership_templates(self) -> List[Dict]:
        """Obtener templates de partnership."""
        return [
            {
                'name': 'Sponsored Post',
                'description': 'Post único patrocinado',
                'deliverables': {
                    'posts': 1,
                    'stories': 3,
                    'reels': 0
                },
                'duration': '7-14 días'
            },
            {
                'name': 'Product Placement',
                'description': 'Integración natural del producto',
                'deliverables': {
                    'posts': 2,
                    'stories': 5,
                    'reels': 1
                },
                'duration': '30 días'
            },
            {
                'name': 'Brand Ambassador',
                'description': 'Ambassadorship de largo plazo',
                'deliverables': {
                    'posts': 4,
                    'stories': 12,
                    'reels': 4
                },
                'duration': '90 días'
            },
            {
                'name': 'Content Creation',
                'description': 'Creación de contenido exclusivo',
                'deliverables': {
                    'posts': 8,
                    'stories': 20,
                    'reels': 12
                },
                'duration': '60 días'
            }
        ]

    def get_influencer_tiers(self) -> Dict:
        """Obtener clasificación de influencers."""
        return {
            'Nano': {
                'followers': '1K-10K',
                'engagement': 'Alta (5-15%)',
                'use_case': 'Nicho específico, comunidades leales',
                'avg_cost': '$200-500'
            },
            'Micro': {
                'followers': '10K-100K',
                'engagement': 'Media-Alta (2-8%)',
                'use_case': 'Especialización, autoridad local',
                'avg_cost': '$500-2K'
            },
            'Mid-Tier': {
                'followers': '100K-1M',
                'engagement': 'Media (1-3%)',
                'use_case': 'Cobertura regional, brand awareness',
                'avg_cost': '$2K-10K'
            },
            'Macro': {
                'followers': '1M-10M',
                'engagement': 'Baja-Media (0.5-2%)',
                'use_case': 'Reach masivo, visibilidad global',
                'avg_cost': '$10K-100K'
            },
            'Celebrity': {
                'followers': '>10M',
                'engagement': 'Baja (0.1-0.5%)',
                'use_case': 'Máxima visibilidad, mainstream',
                'avg_cost': '$100K+'
            }
        }

    def get_partnership_roi_analysis(self, partnership_id: int) -> Dict:
        """Analizar ROI de partnership."""
        try:
            with self._conn() as con:
                partnership = con.execute(
                    "SELECT compensation FROM partnerships WHERE id=?", (partnership_id,)
                ).fetchone()
                
                metrics = con.execute("""
                    SELECT SUM(sales), AVG(roi), SUM(impressions), SUM(conversions)
                    FROM partnership_performance
                    WHERE partnership_id=?
                """, (partnership_id,)).fetchone()
            
            total_sales, avg_roi, impressions, conversions = metrics or (0, 0, 0, 0)
            compensation = partnership[0] if partnership else 0
            
            return {
                'status': 'success',
                'investment': f"${compensation:.2f}",
                'revenue_generated': f"${total_sales or 0:.2f}",
                'net_profit': f"${(total_sales - compensation) if total_sales else -compensation:.2f}",
                'roi_percentage': f"{avg_roi or 0:.1f}%",
                'reach': impressions or 0,
                'conversions': conversions or 0,
                'cost_per_conversion': f"${compensation / conversions:.2f}" if conversions > 0 else "N/A",
                'overall_rating': '⭐⭐⭐⭐' if avg_roi and avg_roi > 200 else '⭐⭐⭐' if avg_roi and avg_roi > 50 else '⭐⭐'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
