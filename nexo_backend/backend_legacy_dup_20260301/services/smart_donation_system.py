"""
Smart Donation System: Sistema de donaciones inteligente para YouTube
Permite a viewers donar y seleccionar contenido basado en el valor de pantalla
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from enum import Enum

class DonationStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    CONSUMED = "consumed"
    EXPIRED = "expired"

class SmartDonationSystem:
    """Sistema de donaciones inteligente con valoración dinámica de tiempo en pantalla."""
    
    def __init__(self, db_path: str = "smart_donations.db"):
        self.db_path = db_path
        self._init_db()
    
    def _conn(self):
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Crear tablas para sistema de donaciones."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS screen_time_valuations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                timestamp TEXT,
                viewers_count INTEGER,
                price_per_second REAL,
                price_per_minute REAL,
                base_cpm REAL,
                engagement_multiplier REAL,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_id TEXT,
                channel_id TEXT,
                donation_amount REAL,
                currency TEXT,
                screen_time_seconds INTEGER,
                screen_time_value REAL,
                content_type TEXT,
                content_preference_json TEXT,
                status TEXT,
                expires_at TEXT,
                consumed_at TEXT,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS screen_time_redemption (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donation_id INTEGER,
                content_id TEXT,
                content_title TEXT,
                seconds_watched INTEGER,
                timestamp TEXT,
                FOREIGN KEY (donation_id) REFERENCES donations(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS viewer_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                date TEXT,
                total_viewers INTEGER,
                concurrent_viewers INTEGER,
                avg_engagement_score REAL,
                total_donations REAL,
                total_screen_time_sold INTEGER,
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS channel_content_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                content_id TEXT UNIQUE,
                content_title TEXT,
                content_type TEXT,
                duration_seconds INTEGER,
                category TEXT,
                tags_json TEXT,
                min_donation_threshold REAL,
                description TEXT,
                available INTEGER DEFAULT 1,
                created_at TEXT
            )
            """)
    
    def calculate_screen_time_value(self, channel_id: str, viewers_count: int,
                                    engagement_rate: float = 0.85,
                                    cpm_base: float = 5.0) -> Dict:
        """
        Calcular el valor de tiempo en pantalla usando fórmula profesional.
        
        Fórmula:
        - CPM Base (Cost Per Mille): $5-15 típico
        - Engagement Multiplier: 0.5-2.0x
        - Screen Time Value = (Viewers * CPM / 1000) * Engagement
        - Price per second = (Screen Time Value) / 3600
        """
        try:
            # Aplicar multiplier de engagement
            engagement_multiplier = max(0.5, min(2.0, engagement_rate * 2.0))
            
            # Calcular CPM efectivo
            effective_cpm = cpm_base * engagement_multiplier
            
            # Calcular valor por hora (3600 segundos)
            hourly_value = (viewers_count * effective_cpm) / 1000
            
            # Valor por segundo
            price_per_second = hourly_value / 3600
            
            # Valor por minuto (60 segundos)
            price_per_minute = price_per_second * 60
            
            # Guardar valuación en BD
            with self._conn() as con:
                con.execute("""
                INSERT INTO screen_time_valuations
                (channel_id, timestamp, viewers_count, price_per_second,
                 price_per_minute, base_cpm, engagement_multiplier, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (channel_id, datetime.now().strftime('%Y-%m-%d %H:%M:00'),
                     viewers_count, price_per_second, price_per_minute,
                     effective_cpm, engagement_multiplier, datetime.utcnow().isoformat()))
            
            return {
                'status': 'success',
                'viewers_count': viewers_count,
                'engagement_multiplier': round(engagement_multiplier, 2),
                'effective_cpm': round(effective_cpm, 2),
                'price_per_second': round(price_per_second, 4),
                'price_per_minute': round(price_per_minute, 2),
                'price_per_hour': round(hourly_value, 2),
                'example_20_seconds': round(price_per_second * 20, 2),
                'example_1_minute': round(price_per_minute, 2),
                'example_5_minutes': round(price_per_minute * 5, 2),
                'calculation': f"{viewers_count:,} viewers × ${effective_cpm:.2f} CPM ÷ 1000 = ${hourly_value:.2f}/hour"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def process_donation(self, donor_id: str, channel_id: str,
                        donation_amount: float, currency: str = 'USD',
                        content_preferences: List[str] = None) -> Dict:
        """
        Procesar donación y convertirla en tiempo de pantalla comprado.
        El valor se calcula automáticamente en base a la valuación actual.
        """
        try:
            # Obtener valuación más reciente
            with self._conn() as con:
                valuation = con.execute("""
                    SELECT price_per_second FROM screen_time_valuations
                    WHERE channel_id=?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (channel_id,)).fetchone()
            
            if not valuation:
                return {'status': 'error', 'message': 'No valuation data available'}
            
            price_per_second = valuation[0]
            screen_time_seconds = int(donation_amount / price_per_second)
            screen_time_value = screen_time_seconds * price_per_second
            
            # Crear oportunidad de donación
            with self._conn() as con:
                expires_at = (datetime.now() + timedelta(days=30)).isoformat()
                
                con.execute("""
                INSERT INTO donations
                (donor_id, channel_id, donation_amount, currency, screen_time_seconds,
                 screen_time_value, content_preference_json, status, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (donor_id, channel_id, donation_amount, currency,
                     screen_time_seconds, screen_time_value,
                     json.dumps(content_preferences or []), 'active',
                     expires_at, datetime.utcnow().isoformat()))
                
                donation_id = con.execute(
                    "SELECT id FROM donations WHERE donor_id=? ORDER BY id DESC LIMIT 1",
                    (donor_id,)
                ).fetchone()[0]
            
            # Convertir segundos a formato legible
            minutes = screen_time_seconds // 60
            seconds = screen_time_seconds % 60
            
            return {
                'status': 'success',
                'donation_id': donation_id,
                'donation_amount': round(donation_amount, 2),
                'screen_time_purchased': f"{int(screen_time_seconds)}s ({minutes}m {seconds}s)",
                'screen_time_seconds': screen_time_seconds,
                'effective_price_per_second': round(price_per_second, 4),
                'expires_in_days': 30,
                'message': f'✅ Donación procesada: ${donation_amount:.2f} = {screen_time_seconds}s de pantalla',
                'content_preferences': content_preferences or []
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_available_content(self, channel_id: str, donor_id: str = None,
                             content_type: str = None) -> List[Dict]:
        """
        Obtener contenido disponible que el donor puede ver con sus donaciones.
        """
        try:
            with self._conn() as con:
                query = """
                    SELECT id, content_id, content_title, duration_seconds, category,
                           tags_json, min_donation_threshold, description
                    FROM channel_content_catalog
                    WHERE channel_id=? AND available=1
                """
                params = [channel_id]
                
                if content_type:
                    query += " AND content_type=?"
                    params.append(content_type)
                
                query += " ORDER BY duration_seconds ASC"
                
                contents = con.execute(query, params).fetchall()
            
            # Si hay donor, verificar si puede ver cada contenido
            available_content = []
            for content in contents:
                content_dict = {
                    'id': content[0],
                    'content_id': content[1],
                    'title': content[2],
                    'duration_seconds': content[3],
                    'duration_formatted': f"{int(content[3]/60)}m {int(content[3]%60)}s",
                    'category': content[4],
                    'tags': json.loads(content[5]) if content[5] else [],
                    'min_donation_threshold': round(content[6] or 0, 2),
                    'description': content[7]
                }
                
                if donor_id:
                    # Verificar si donor tiene suficiente pantalla comprada
                    donor_screen_time = self._get_donor_available_screen_time(donor_id, channel_id)
                    content_dict['can_watch'] = donor_screen_time >= content[3]
                    content_dict['donor_available_seconds'] = donor_screen_time
                
                available_content.append(content_dict)
            
            return available_content
        except Exception as e:
            log.info(f"❌ Error getting content: {e}")
            return []
    
    def _get_donor_available_screen_time(self, donor_id: str, channel_id: str) -> int:
        """Obtener tiempo de pantalla disponible sin usar del donor."""
        try:
            with self._conn() as con:
                donation = con.execute("""
                    SELECT screen_time_seconds FROM donations
                    WHERE donor_id=? AND channel_id=? AND status='active'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (donor_id, channel_id)).fetchone()
                
                if not donation:
                    return 0
                
                total_purchased = donation[0]
                
                # Restar tiempo ya usado
                used = con.execute("""
                    SELECT SUM(seconds_watched) FROM screen_time_redemption
                    WHERE donation_id IN (
                        SELECT id FROM donations
                        WHERE donor_id=? AND channel_id=?
                    )
                """, (donor_id, channel_id)).fetchone()
                
                used_seconds = used[0] or 0
                
                return max(0, total_purchased - used_seconds)
        except Exception as e:
            return 0
    
    def redeem_screen_time(self, donation_id: int, content_id: str,
                          content_title: str, seconds_watched: int) -> Dict:
        """Registrar visualización de contenido usando tiempo de pantalla comprado."""
        try:
            with self._conn() as con:
                # Verificar que hay suficiente tiempo disponible
                donation = con.execute(
                    "SELECT screen_time_seconds, status FROM donations WHERE id=?",
                    (donation_id,)
                ).fetchone()
                
                if not donation or donation[1] != 'active':
                    return {'status': 'error', 'message': 'Donación no válida o expirada'}
                
                total_screen_time = donation[0]
                
                # Obtener tiempo ya usado
                used = con.execute("""
                    SELECT COALESCE(SUM(seconds_watched), 0) FROM screen_time_redemption
                    WHERE donation_id=?
                """, (donation_id,)).fetchone()[0]
                
                available = total_screen_time - used
                
                if seconds_watched > available:
                    return {
                        'status': 'error',
                        'message': f'Tiempo insuficiente. Disponible: {available}s, Requerido: {seconds_watched}s'
                    }
                
                # Registrar redención
                con.execute("""
                INSERT INTO screen_time_redemption
                (donation_id, content_id, content_title, seconds_watched, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """, (donation_id, content_id, content_title, seconds_watched,
                     datetime.utcnow().isoformat()))
                
                # Actualizar estado si se agotó todo el tiempo
                new_available = available - seconds_watched
                if new_available <= 0:
                    con.execute(
                        "UPDATE donations SET status='consumed', consumed_at=? WHERE id=?",
                        (datetime.utcnow().isoformat(), donation_id)
                    )
            
            return {
                'status': 'success',
                'message': f'✅ Visualización registrada: {seconds_watched}s',
                'remaining_screen_time': available - seconds_watched
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def add_content_to_catalog(self, channel_id: str, content_id: str,
                              title: str, duration_seconds: int,
                              content_type: str = 'video',
                              category: str = 'general',
                              tags: List[str] = None,
                              description: str = '') -> Dict:
        """Agregar contenido al catálogo de un canal."""
        try:
            tags_json = json.dumps(tags or [])
            
            with self._conn() as con:
                con.execute("""
                INSERT INTO channel_content_catalog
                (channel_id, content_id, content_title, content_type, duration_seconds,
                 category, tags_json, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (channel_id, content_id, title, content_type, duration_seconds,
                     category, tags_json, description, datetime.utcnow().isoformat()))
            
            return {
                'status': 'success',
                'message': f'✅ Contenido "{title}" agregado',
                'duration_formatted': f"{int(duration_seconds/60)}m {int(duration_seconds%60)}s"
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_donor_dashboard(self, donor_id: str, channel_id: str = None) -> Dict:
        """Obtener dashboard del donor."""
        try:
            with self._conn() as con:
                if channel_id:
                    donations = con.execute("""
                        SELECT id, channel_id, donation_amount, screen_time_seconds, status, created_at
                        FROM donations
                        WHERE donor_id=? AND channel_id=?
                        ORDER BY created_at DESC
                    """, (donor_id, channel_id)).fetchall()
                else:
                    donations = con.execute("""
                        SELECT id, channel_id, donation_amount, screen_time_seconds, status, created_at
                        FROM donations
                        WHERE donor_id=?
                        ORDER BY created_at DESC
                        LIMIT 10
                    """, (donor_id,)).fetchall()
            
            total_donated = sum(d[2] for d in donations)
            total_screen_time = sum(d[3] for d in donations)
            active_donations = sum(1 for d in donations if d[4] == 'active')
            
            return {
                'status': 'success',
                'donor_id': donor_id,
                'total_donated': round(total_donated, 2),
                'total_screen_time_seconds': total_screen_time,
                'total_screen_time_formatted': f"{int(total_screen_time/60)}m {int(total_screen_time%60)}s",
                'active_donations': active_donations,
                'recent_donations': [
                    {
                        'channel_id': d[1],
                        'amount': round(d[2], 2),
                        'screen_time': d[3],
                        'status': d[4],
                        'date': d[5]
                    }
                    for d in donations
                ]
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_channel_donation_analytics(self, channel_id: str, days: int = 30) -> Dict:
        """Obtener analíticas de donaciones del canal."""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with self._conn() as con:
                # Total de donaciones
                totals = con.execute("""
                    SELECT COUNT(*) as donation_count,
                           SUM(donation_amount) as total_revenue,
                           SUM(screen_time_seconds) as total_screen_time,
                           AVG(donation_amount) as avg_donation
                    FROM donations
                    WHERE channel_id=? AND created_at >= ?
                """, (channel_id, start_date + ' 00:00:00')).fetchone()
                
                # Por estado
                by_status = con.execute("""
                    SELECT status, COUNT(*) as count, SUM(donation_amount) as amount
                    FROM donations
                    WHERE channel_id=? AND created_at >= ?
                    GROUP BY status
                """, (channel_id, start_date + ' 00:00:00')).fetchall()
                
                # Por día
                daily = con.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count, SUM(donation_amount) as amount
                    FROM donations
                    WHERE channel_id=? AND created_at >= ?
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, (channel_id, start_date + ' 00:00:00')).fetchall()
            
            donation_count, total_revenue, total_screen_time, avg_donation = totals
            
            return {
                'status': 'success',
                'period_days': days,
                'total_donations': donation_count or 0,
                'total_revenue': round(total_revenue or 0, 2),
                'average_donation': round(avg_donation or 0, 2),
                'total_screen_time_sold': total_screen_time or 0,
                'by_status': [
                    {'status': s[0], 'count': s[1], 'revenue': round(s[2] or 0, 2)}
                    for s in by_status
                ],
                'daily_breakdown': [
                    {'date': d[0], 'donations': d[1], 'revenue': round(d[2] or 0, 2)}
                    for d in daily
                ]
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_donation_metrics(self, channel_id: str) -> Dict:
        """Obtener métricas clave de donaciones."""
        try:
            metrics = self.calculate_screen_time_value(
                channel_id=channel_id,
                viewers_count=1000,  # default
                engagement_rate=0.85,
                cpm_base=5.0
            )
            
            return metrics
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
