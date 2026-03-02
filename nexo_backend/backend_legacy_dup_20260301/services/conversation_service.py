"""
Conversation Service: manejo de contexto, memoria y flujo conversacional.
Cada usuario tiene su historial y contexto progresivo.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

class ConversationService:
    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        self.contexts = defaultdict(dict)  # contexto en memoria por usuario
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                timestamp TEXT,
                role TEXT,
                content TEXT,
                model TEXT,
                intent TEXT
            )
            """)
            con.execute("""
            CREATE TABLE IF NOT EXISTS context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE,
                last_topic TEXT,
                preferences TEXT,
                memory TEXT,
                updated_at TEXT
            )
            """)

    def get_conversation(self, user_id: str, limit: int = 10) -> List[dict]:
        """Obtiene últimos N mensajes del usuario."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT timestamp, role, content, model FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cur.fetchall()
        return [
            {"timestamp": r[0], "role": r[1], "content": r[2], "model": r[3]}
            for r in reversed(rows)
        ]

    def add_message(
        self,
        user_id: str,
        role: str,
        content: str,
        model: str = "auto",
        intent: str = "chat"
    ):
        """Almacena un mensaje en el historial."""
        with self._conn() as con:
            con.execute(
                "INSERT INTO messages (user_id, timestamp, role, content, model, intent) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, datetime.utcnow().isoformat(), role, content, model, intent)
            )

    def get_context(self, user_id: str) -> Dict:
        """Recupera contexto del usuario."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT last_topic, preferences, memory FROM context WHERE user_id=?",
                (user_id,)
            )
            row = cur.fetchone()
        
        if row:
            return {
                "last_topic": row[0],
                "preferences": row[1],
                "memory": row[2]
            }
        return {}

    def update_context(self, user_id: str, topic: str = None, memory: str = None):
        """Actualiza contexto del usuario (progresivo)."""
        with self._conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO context (user_id, last_topic, memory, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, topic or "", memory or "", datetime.utcnow().isoformat())
            )

    def build_messages_for_model(self, user_id: str, limit: int = 5) -> List[dict]:
        """Construye lista de mensajes para enviar al modelo (FIFO)."""
        conv = self.get_conversation(user_id, limit=limit)
        messages = []
        for msg in conv:
            messages.append({"role": msg["role"], "content": msg["content"]})
        return messages

    def get_user_preference(self, user_id: str, key: str) -> Optional[str]:
        """Lee preferencia guardada del usuario (canal favorito, modelo, etc.)"""
        ctx = self.get_context(user_id)
        if ctx and ctx.get("preferences"):
            import json
            try:
                prefs = json.loads(ctx["preferences"])
                return prefs.get(key)
            except:
                pass
        return None

    def set_user_preference(self, user_id: str, key: str, value: str):
        """Guarda preferencia del usuario."""
        ctx = self.get_context(user_id)
        import json
        prefs = {}
        if ctx and ctx.get("preferences"):
            try:
                prefs = json.loads(ctx["preferences"])
            except:
                pass
        prefs[key] = value
        self.update_context(user_id, memory=json.dumps(prefs))

    def get_summary(self, user_id: str) -> str:
        """Resumen del contexto del usuario para prompt del modelo."""
        ctx = self.get_context(user_id)
        conv = self.get_conversation(user_id, limit=3)
        
        summary = f"Usuario: {user_id}\n"
        if ctx.get("last_topic"):
            summary += f"Tema actual: {ctx['last_topic']}\n"
        summary += f"Últimos mensajes: {len(conv)}\n"
        
        return summary
