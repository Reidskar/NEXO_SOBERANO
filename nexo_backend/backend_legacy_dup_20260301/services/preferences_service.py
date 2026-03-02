"""
User Preferences Service: Almacena preferencias cognitivas y UI del usuario.
Modelo mental del usuario para personalización.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional

class UserPreferencesService:
    def __init__(self, db_path: str = "preferences.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE,
                
                -- Nivel cognitivo
                cognitive_level TEXT DEFAULT 'intermediate',
                learning_style TEXT DEFAULT 'balanced',
                vocabulary_level TEXT DEFAULT 'standard',
                
                -- Preferencias de notificación
                email_frequency TEXT DEFAULT 'daily',
                notification_enabled BOOLEAN DEFAULT 1,
                quiet_hours_start TEXT DEFAULT '22:00',
                quiet_hours_end TEXT DEFAULT '08:00',
                
                -- Tópicos de interés
                topics_json TEXT,
                
                -- Presentación
                content_length TEXT DEFAULT 'medium',
                presentation_style TEXT DEFAULT 'balanced',
                language TEXT DEFAULT 'es',
                theme TEXT DEFAULT 'dark',
                
                -- Personalización avanzada
                prefer_examples BOOLEAN DEFAULT 1,
                prefer_data BOOLEAN DEFAULT 1,
                prefer_narrative BOOLEAN DEFAULT 1,
                
                -- Tracking
                created_at TEXT,
                updated_at TEXT,
                engagement_score INTEGER DEFAULT 50
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE,
                
                -- Quiz responses
                visual_learner_score REAL DEFAULT 0.5,
                auditory_learner_score REAL DEFAULT 0.5,
                kinesthetic_learner_score REAL DEFAULT 0.5,
                
                -- Processing style
                linear_thinker_score REAL DEFAULT 0.5,
                holistic_thinker_score REAL DEFAULT 0.5,
                
                -- Info preferences
                detail_oriented_score REAL DEFAULT 0.5,
                big_picture_score REAL DEFAULT 0.5,
                
                -- Reading habits
                avg_reading_time_seconds INTEGER DEFAULT 0,
                articles_per_day_avg REAL DEFAULT 0,
                preferred_length TEXT DEFAULT 'medium',
                
                -- Political balance
                left_wing_exposure REAL DEFAULT 0.5,
                right_wing_exposure REAL DEFAULT 0.5,
                
                -- Expertise levels (JSON)
                expertise_json TEXT,
                
                -- Last assessment
                last_assessment TEXT,
                
                updated_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE,
                
                -- Email settings
                daily_digest BOOLEAN DEFAULT 1,
                weekly_digest BOOLEAN DEFAULT 1,
                monthly_digest BOOLEAN DEFAULT 0,
                breaking_news_alerts BOOLEAN DEFAULT 1,
                
                -- Category subscriptions
                politics BOOLEAN DEFAULT 1,
                economy BOOLEAN DEFAULT 1,
                technology BOOLEAN DEFAULT 1,
                science BOOLEAN DEFAULT 1,
                health BOOLEAN DEFAULT 1,
                sports BOOLEAN DEFAULT 0,
                entertainment BOOLEAN DEFAULT 0,
                
                -- Custom categories (JSON)
                custom_categories_json TEXT,
                
                -- Frequency per category
                frequency_json TEXT DEFAULT '{"politics": "daily", "economy": "daily"}',
                
                unsubscribe_token TEXT UNIQUE,
                created_at TEXT,
                updated_at TEXT
            )
            """)

    def get_or_create_preferences(self, user_id: str) -> Dict[str, Any]:
        """Obtener preferencias o crear por defecto."""
        prefs = self.get_preferences(user_id)
        if not prefs:
            self.create_default_preferences(user_id)
            prefs = self.get_preferences(user_id)
        return prefs

    def get_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtener preferencias del usuario."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM user_preferences WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            cols = [desc[0] for desc in cur.description]
            result = dict(zip(cols, row))
            
            # Parse JSON fields
            if result.get('topics_json'):
                result['topics'] = json.loads(result['topics_json'])
            
            return result

    def create_default_preferences(self, user_id: str):
        """Crear preferencias por defecto."""
        with self._conn() as con:
            con.execute("""
            INSERT INTO user_preferences 
            (user_id, cognitive_level, learning_style, topics_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                'intermediate',
                'balanced',
                json.dumps(['política', 'tecnología', 'economía']),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ))
            
            con.execute("""
            INSERT INTO cognitive_profile (user_id, updated_at)
            VALUES (?, ?)
            """, (user_id, datetime.utcnow().isoformat()))
            
            con.execute("""
            INSERT INTO notification_preferences (user_id, created_at, updated_at, unsubscribe_token)
            VALUES (?, ?, ?, ?)
            """, (
                user_id,
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                f"unsub_{user_id}_{datetime.utcnow().timestamp()}"
            ))

    def update_preferences(self, user_id: str, **kwargs) -> bool:
        """Actualizar preferencias."""
        set_clause = ", ".join([f"{k}=?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        query = f"UPDATE user_preferences SET {set_clause}, updated_at=? WHERE user_id=?"
        values.insert(len(values) - 1, datetime.utcnow().isoformat())
        
        with self._conn() as con:
            con.execute(query, values)
        
        return True

    def update_cognitive_profile(self, user_id: str, **scores):
        """Actualizar perfil cognitivo con scores."""
        updates = {k: v for k, v in scores.items() if k.endswith('_score')}
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        set_clause = ", ".join([f"{k}=?" for k in updates.keys()])
        values = list(updates.values()) + [user_id]
        query = f"UPDATE cognitive_profile SET {set_clause} WHERE user_id=?"
        
        with self._conn() as con:
            con.execute(query, values)
        
        return True

    def get_cognitive_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtener perfil cognitivo completo."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM cognitive_profile WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            cols = [desc[0] for desc in cur.description]
            result = dict(zip(cols, row))
            
            if result.get('expertise_json'):
                result['expertise'] = json.loads(result['expertise_json'])
            
            return result

    def set_topics(self, user_id: str, topics: list):
        """Actualizar tópicos de interés."""
        with self._conn() as con:
            con.execute(
                "UPDATE user_preferences SET topics_json=?, updated_at=? WHERE user_id=?",
                (json.dumps(topics), datetime.utcnow().isoformat(), user_id)
            )

    def get_notification_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Obtener preferencias de notificación."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM notification_preferences WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            cols = [desc[0] for desc in cur.description]
            result = dict(zip(cols, row))
            
            if result.get('frequency_json'):
                result['frequency'] = json.loads(result['frequency_json'])
            if result.get('custom_categories_json'):
                result['custom_categories'] = json.loads(result['custom_categories_json'])
            
            return result

    def update_notification_frequency(self, user_id: str, category: str, frequency: str):
        """Actualizar frecuencia para categoría específica."""
        prefs = self.get_notification_preferences(user_id)
        frequency_dict = json.loads(prefs['frequency_json']) if prefs else {}
        frequency_dict[category] = frequency
        
        with self._conn() as con:
            con.execute(
                "UPDATE notification_preferences SET frequency_json=?, updated_at=? WHERE user_id=?",
                (json.dumps(frequency_dict), datetime.utcnow().isoformat(), user_id)
            )

    def get_user_cognitive_model(self, user_id: str) -> Dict[str, Any]:
        """Obtener modelo mental completo para personalización."""
        prefs = self.get_preferences(user_id)
        cognitive = self.get_cognitive_profile(user_id)
        
        return {
            "learning_style": prefs.get('learning_style'),
            "cognitive_level": prefs.get('cognitive_level'),
            "vocabulary_level": prefs.get('vocabulary_level'),
            "content_length": prefs.get('content_length'),
            "presentation_style": prefs.get('presentation_style'),
            "prefer_examples": prefs.get('prefer_examples'),
            "prefer_data": prefs.get('prefer_data'),
            "visual_score": cognitive.get('visual_learner_score') if cognitive else 0.3,
            "detail_score": cognitive.get('detail_oriented_score') if cognitive else 0.5,
            "big_picture_score": cognitive.get('big_picture_score') if cognitive else 0.5,
            "engagement_score": prefs.get('engagement_score')
        }
