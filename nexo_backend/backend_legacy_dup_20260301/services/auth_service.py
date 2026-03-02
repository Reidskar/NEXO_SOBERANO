"""
Authentication Service: JWT-based auth para toda la aplicación.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sqlite3
import jwt
import hashlib
import secrets

class AuthService:
    def __init__(self, secret_key: Optional[str] = None, db_path: str = "auth.db"):
        self.secret_key = secret_key or os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
        self.db_path = db_path
        self.algorithm = "HS256"
        self.token_expiry = 24  # horas
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT,
                last_login TEXT
            )
            """)
            con.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                key TEXT UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """)

    def hash_password(self, password: str) -> str:
        """Hashear contraseña con PBKDF2."""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${pwd_hash.hex()}"

    def verify_password(self, password: str, hash_str: str) -> bool:
        """Verificar contraseña hasheada."""
        try:
            salt, pwd_hash = hash_str.split("$")
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return new_hash.hex() == pwd_hash
        except:
            return False

    def create_user(self, username: str, email: str, password: str, role: str = "user") -> Dict[str, Any]:
        """Crear nuevo usuario."""
        pwd_hash = self.hash_password(password)
        try:
            with self._conn() as con:
                con.execute(
                    "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                    (username, email, pwd_hash, role, datetime.utcnow().isoformat())
                )
            return {"status": "created", "username": username}
        except sqlite3.IntegrityError as e:
            return {"error": str(e)}

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Autenticar usuario y devolver JWT token."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT id, password_hash FROM users WHERE username=? AND is_active=1", (username,))
            user = cur.fetchone()

        if not user or not self.verify_password(password, user[1]):
            return None

        # Actualizar último login
        with self._conn() as con:
            con.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.utcnow().isoformat(), user[0]))

        # Generar token
        payload = {
            "sub": user[0],
            "username": username,
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificar JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def generate_api_key(self, user_id: int, name: str) -> str:
        """Generar clave de API para usuario."""
        key = f"nxo_{secrets.token_urlsafe(32)}"
        with self._conn() as con:
            con.execute(
                "INSERT INTO api_keys (user_id, name, key, created_at) VALUES (?, ?, ?, ?)",
                (user_id, name, key, datetime.utcnow().isoformat())
            )
        return key

    def verify_api_key(self, key: str) -> Optional[int]:
        """Verificar API key y devolver user_id."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT user_id FROM api_keys WHERE key=? AND is_active=1", (key,))
            result = cur.fetchone()
        return result[0] if result else None

    def list_users(self, limit: int = 100) -> list:
        """Listar usuarios (solo admin)."""
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT id, username, email, role, created_at FROM users LIMIT ?", (limit,))
            return cur.fetchall()

    def deactivate_user(self, user_id: int):
        """Desactivar usuario."""
        with self._conn() as con:
            con.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
