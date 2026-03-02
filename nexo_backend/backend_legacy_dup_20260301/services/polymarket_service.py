"""
Polymarket Integration: Integración con mercados de predicción para análisis de mercado
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from enum import Enum

class MarketStatus(Enum):
    OPEN = "open"
    TRADING = "trading"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"

class PolymarketService:
    """Integración con predicciones de mercado tipo Polymarket."""
    
    def __init__(self, db_path: str = "polymarket.db"):
        self.db_path = db_path
        self._init_db()
    
    def _conn(self):
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Crear tablas para mercados de predicción."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS prediction_markets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_name TEXT UNIQUE,
                description TEXT,
                category TEXT,
                outcome_yes_text TEXT,
                outcome_no_text TEXT,
                resolution_source TEXT,
                liquidity_pool REAL,
                yes_price REAL DEFAULT 0.5,
                no_price REAL DEFAULT 0.5,
                volume_24h REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_at TEXT,
                resolution_date TEXT,
                resolved_at TEXT,
                winning_outcome TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS market_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id INTEGER,
                user_id TEXT,
                position_type TEXT,
                amount_invested REAL,
                shares_owned REAL,
                entry_price REAL,
                current_value REAL,
                pnl REAL,
                profit_percentage REAL,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (market_id) REFERENCES prediction_markets(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS market_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id INTEGER,
                user_id TEXT,
                trade_type TEXT,
                position_type TEXT,
                shares TEXT,
                price REAL,
                amount REAL,
                executed_at TEXT,
                FOREIGN KEY (market_id) REFERENCES prediction_markets(id)
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS market_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id INTEGER,
                date TEXT,
                open_interest REAL,
                volume REAL,
                yes_price REAL,
                no_price REAL,
                probability_yes REAL,
                probability_no REAL,
                created_at TEXT,
                FOREIGN KEY (market_id) REFERENCES prediction_markets(id)
            )
            """)
    
    def create_market(self, market_name: str, description: str,
                     category: str = "general",
                     outcome_yes: str = "Yes",
                     outcome_no: str = "No",
                     resolution_source: str = "manual",
                     initial_liquidity: float = 1000.0) -> Dict:
        """Crear nuevo mercado de predicción."""
        try:
            with self._conn() as con:
                con.execute("""
                INSERT INTO prediction_markets
                (market_name, description, category, outcome_yes_text, outcome_no_text,
                 resolution_source, liquidity_pool, yes_price, no_price, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (market_name, description, category, outcome_yes, outcome_no,
                     resolution_source, initial_liquidity, 0.5, 0.5, 'open',
                     datetime.utcnow().isoformat()))
                
                market_id = con.execute(
                    "SELECT id FROM prediction_markets WHERE market_name=?", (market_name,)
                ).fetchone()[0]
            
            return {
                'status': 'success',
                'market_id': market_id,
                'message': f'✅ Mercado "{market_name}" creado',
                'initial_probability': {'yes': 0.5, 'no': 0.5}
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def place_bet(self, market_id: int, user_id: str, position_type: str,
                 amount: float) -> Dict:
        """Colocar apuesta en un mercado."""
        try:
            with self._conn() as con:
                market = con.execute(
                    "SELECT yes_price, no_price, liquidity_pool FROM prediction_markets WHERE id=?",
                    (market_id,)
                ).fetchone()
                
                yes_price, no_price, liquidity = market
                
                # Calcular precio y shares
                if position_type.lower() == 'yes':
                    price = yes_price
                    new_price = self._calculate_new_price(amount, liquidity, position_type)
                else:
                    price = no_price
                    new_price = self._calculate_new_price(amount, liquidity, position_type)
                
                shares = amount / price if price > 0 else 0
                
                # Registrar posición
                con.execute("""
                INSERT INTO market_positions
                (market_id, user_id, position_type, amount_invested, shares_owned,
                 entry_price, current_value, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (market_id, user_id, position_type, amount, shares, price, amount,
                     datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                # Registrar trade
                con.execute("""
                INSERT INTO market_trades
                (market_id, user_id, trade_type, position_type, shares, price, amount, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (market_id, user_id, 'buy', position_type, str(shares), price, amount,
                     datetime.utcnow().isoformat()))
                
                # Actualizar precios
                if position_type.lower() == 'yes':
                    con.execute(
                        "UPDATE prediction_markets SET yes_price=?, volume_24h = volume_24h + ? WHERE id=?",
                        (new_price, amount, market_id)
                    )
                else:
                    con.execute(
                        "UPDATE prediction_markets SET no_price=?, volume_24h = volume_24h + ? WHERE id=?",
                        (new_price, amount, market_id)
                    )
            
            return {
                'status': 'success',
                'shares': round(shares, 4),
                'price': round(price, 4),
                'message': f'✅ Apuesta colocada: {shares:.4f} shares @ ${price:.4f}'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_new_price(self, amount: float, liquidity: float,
                            position_type: str) -> float:
        """Calcular nuevo precio CFMM (Constant Function Market Maker)."""
        # Fórmula simplificada de AMM
        # Precio basado en: amount / (liquidity + amount)
        buy_pressure = amount / (liquidity + amount)
        
        if position_type.lower() == 'yes':
            # Si se compra YES, el precio sube
            new_price = min(0.99, 0.5 + buy_pressure * 0.3)
        else:
            # Si se compra NO, el precio de NO sube (YES baja)
            new_price = max(0.01, 0.5 - buy_pressure * 0.3)
        
        return new_price
    
    def get_market_probability(self, market_id: int) -> Dict:
        """Obtener probabilidades implícitas del mercado."""
        try:
            with self._conn() as con:
                market = con.execute(
                    "SELECT yes_price, no_price, outcome_yes_text, outcome_no_text FROM prediction_markets WHERE id=?",
                    (market_id,)
                ).fetchone()
                
                yes_price, no_price, yes_text, no_text = market
                
                # Normalizar probabilidades
                total = yes_price + no_price
                prob_yes = yes_price / total if total > 0 else 0.5
                prob_no = no_price / total if total > 0 else 0.5
            
            return {
                'status': 'success',
                'probability_yes': round(prob_yes * 100, 2),
                'probability_no': round(prob_no * 100, 2),
                'implied_outcome_yes': f"{yes_text}: {prob_yes*100:.1f}%",
                'implied_outcome_no': f"{no_text}: {prob_no*100:.1f}%",
                'confidence': 'high' if abs(prob_yes - prob_no) > 0.2 else 'medium' if abs(prob_yes - prob_no) > 0.1 else 'low'
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def resolve_market(self, market_id: int, winning_outcome: str,
                      payout_ratio: float = 1.0) -> Dict:
        """Resolver un mercado después de su fecha de resolución."""
        try:
            with self._conn() as con:
                # Actualizar mercado
                con.execute(
                    "UPDATE prediction_markets SET status=?, resolved_at=?, winning_outcome=? WHERE id=?",
                    ('resolved', datetime.utcnow().isoformat(), winning_outcome, market_id)
                )
                
                # Calcular payouts
                positions = con.execute(
                    "SELECT user_id, position_type, amount_invested FROM market_positions WHERE market_id=?",
                    (market_id,)
                ).fetchall()
                
                total_payout = 0
                winners = []
                
                for user_id, position_type, amount in positions:
                    if position_type.lower() == winning_outcome.lower():
                        payout = amount * payout_ratio
                        total_payout += payout
                        winners.append({
                            'user_id': user_id,
                            'payout': payout,
                            'profit': payout - amount
                        })
            
            return {
                'status': 'success',
                'market_resolved': True,
                'winning_outcome': winning_outcome,
                'winners_count': len(winners),
                'total_payout': round(total_payout, 2),
                'top_winners': winners[:5]
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_market_analytics(self, market_id: int, days: int = 7) -> Dict:
        """Obtener analíticas del mercado."""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            with self._conn() as con:
                analytics = con.execute("""
                    SELECT date, open_interest, volume, yes_price, probability_yes
                    FROM market_analytics
                    WHERE market_id=? AND date >= ?
                    ORDER BY date
                """, (market_id, start_date)).fetchall()
                
                market = con.execute(
                    "SELECT volume_24h, yes_price FROM prediction_markets WHERE id=?",
                    (market_id,)
                ).fetchone()
            
            volume_24h, current_yes_price = market or (0, 0.5)
            
            chart_data = [
                {
                    'date': row[0],
                    'open_interest': row[1] or 0,
                    'volume': row[2] or 0,
                    'yes_price': row[3] or 0.5,
                    'probability': row[4] or 50
                }
                for row in analytics
            ]
            
            return {
                'status': 'success',
                'market_id': market_id,
                'days': days,
                'current_volume_24h': round(volume_24h, 2),
                'current_yes_price': round(current_yes_price, 4),
                'analytics': chart_data
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_prediction_markets_for_content(self, content_id: str) -> List[Dict]:
        """Obtener mercados de predicción específicos para contenido."""
        return [
            {
                'market_name': f'Will {content_id} reach 1M views?',
                'category': 'content_performance',
                'resolution_date': (datetime.now() + timedelta(days=30)).isoformat(),
                'current_probability_yes': 45,
                'volume_24h': 1250
            },
            {
                'market_name': f'Will {content_id} get >100K likes?',
                'category': 'engagement',
                'resolution_date': (datetime.now() + timedelta(days=14)).isoformat(),
                'current_probability_yes': 62,
                'volume_24h': 890
            },
            {
                'market_name': f'Will {content_id} trending in 24h?',
                'category': 'virality',
                'resolution_date': (datetime.now() + timedelta(hours=24)).isoformat(),
                'current_probability_yes': 28,
                'volume_24h': 2340
            }
        ]
    
    def get_market_insights(self, market_id: int) -> Dict:
        """Obtener insights profesionales del mercado."""
        try:
            with self._conn() as con:
                market = con.execute(
                    "SELECT market_name, description, yes_price, no_price, volume_24h FROM prediction_markets WHERE id=?",
                    (market_id,)
                ).fetchone()
                
                trades = con.execute(
                    "SELECT COUNT(*) as trade_count, SUM(amount) as total_volume FROM market_trades WHERE market_id=?",
                    (market_id,)
                ).fetchone()
            
            name, desc, yes_price, no_price, vol24 = market
            trade_count, total_vol = trades
            
            # Calcular volatilidad
            volatility = abs(yes_price - 0.5) * 100  # Simple volatility metric
            
            # Calcular momentum
            momentum = "bullish" if yes_price > 0.55 else "bearish" if yes_price < 0.45 else "neutral"
            
            return {
                'status': 'success',
                'market_name': name,
                'description': desc,
                'current_probability_yes': round(yes_price * 100, 2),
                'current_probability_no': round(no_price * 100, 2),
                'volatility_score': round(volatility, 2),
                'momentum': momentum,
                'trading_activity': '🔥 High' if vol24 > 5000 else '🔶 Medium' if vol24 > 1000 else '❄️ Low',
                'total_trades': trade_count or 0,
                'total_volume': round(total_vol or 0, 2),
                'recommendation': self._get_recommendation(yes_price, volatility)
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _get_recommendation(self, yes_price: float, volatility: float) -> str:
        """Generar recomendación basada en análisis."""
        if yes_price > 0.7:
            return "📈 Strong YES - High probability de ocurrencia"
        elif yes_price > 0.6:
            return "✅ Likely YES - Probabilidad favorable"
        elif yes_price > 0.55:
            return "🔶 Slight YES - Ligeramente favorable"
        elif yes_price > 0.45:
            return "⚖️ No consensus - Mercado indeciso"
        elif yes_price > 0.4:
            return "🔶 Slight NO - Ligeramente desfavorable"
        elif yes_price > 0.3:
            return "❌ Unlikely NO - Probabilidad baja"
        else:
            return "📉 Strong NO - Muy baja probabilidad"
    
    def export_market_data(self, market_id: int) -> str:
        """Exportar datos del mercado en JSON."""
        try:
            with self._conn() as con:
                market = con.execute(
                    "SELECT * FROM prediction_markets WHERE id=?", (market_id,)
                ).fetchone()
                
                if not market:
                    return "{}"
                
                export_data = {
                    'market_id': market[0],
                    'name': market[1],
                    'description': market[2],
                    'category': market[3],
                    'yes_text': market[4],
                    'no_text': market[5],
                    'current_yes_price': market[8],
                    'current_no_price': market[9],
                    'volume_24h': market[10],
                    'status': market[11],
                    'created_at': market[12],
                    'resolution_date': market[13]
                }
                
                return json.dumps(export_data, indent=2)
        except Exception as e:
            return json.dumps({'error': str(e)})
    
    def get_market_leaderboard(self, market_id: int, limit: int = 10) -> List[Dict]:
        """Obtener top traders en un mercado."""
        try:
            with self._conn() as con:
                top_traders = con.execute("""
                    SELECT user_id, position_type, SUM(amount_invested) as total_invested,
                           MAX(profit_percentage) as max_profit
                    FROM market_positions
                    WHERE market_id=?
                    GROUP BY user_id
                    ORDER BY max_profit DESC
                    LIMIT ?
                """, (market_id, limit)).fetchall()
            
            leaderboard = []
            for i, (user_id, position, invested, profit) in enumerate(top_traders, 1):
                leaderboard.append({
                    'rank': i,
                    'user_id': user_id,
                    'position': position,
                    'invested': round(invested, 2),
                    'profit_percentage': f"{profit or 0:.1f}%"
                })
            
            return leaderboard
        except Exception as e:
            log.info(f"❌ Error getting leaderboard: {e}")
            return []
