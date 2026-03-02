"""
Calendar Service: Integración Google Calendar + Outlook
Auto-crea eventos para noticias importantes y citas del usuario
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from msgraph.core import GraphClient
from azure.identity import ClientSecretCredential

class CalendarService:
    def __init__(self, db_path: str = "calendar.db"):
        self.db_path = db_path
        self.google_calendar = None
        self.outlcook_client = None
        self._init_db()
        self._init_oauth()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Crear tablas para eventos y sincronización."""
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                event_id TEXT UNIQUE,
                title TEXT,
                description TEXT,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                calendar_type TEXT,
                source TEXT,
                sync_status TEXT DEFAULT 'pending',
                created_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS calendar_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE,
                google_token TEXT,
                outlook_token TEXT,
                google_enabled INTEGER DEFAULT 0,
                outlook_enabled INTEGER DEFAULT 0,
                updated_at TEXT
            )
            """)
            
            con.execute("""
            CREATE TABLE IF NOT EXISTS event_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                event_id TEXT,
                reminder_type TEXT,
                send_at TEXT,
                sent_at TEXT,
                status TEXT DEFAULT 'pending'
            )
            """)

    def _init_oauth(self):
        """Inicializar OAuth clients."""
        pass  # Requiere credenciales en variables de entorno

    def request_google_auth(self, user_id: str, redirect_uri: str) -> str:
        """Generar URL para OAuth de Google Calendar."""
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_google.json',
                scopes=SCOPES
            )
            auth_uri = flow.authorization_url(create_session=False)[0]
            
            # Guardar state para validación
            with self._conn() as con:
                con.execute("""
                INSERT INTO calendar_credentials (user_id, google_enabled, updated_at)
                VALUES (?, ?, ?)
                """, (user_id, 0, datetime.utcnow().isoformat()))
            
            return auth_uri
        except Exception as e:
            log.info(f"❌ OAuth Error Google: {e}")
            return None

    def request_outlook_auth(self, user_id: str) -> str:
        """Generar URL para OAuth de Outlook."""
        tenant = os.getenv("AZURE_TENANT_ID")
        client_id = os.getenv("AZURE_CLIENT_ID")
        redirect_uri = os.getenv("AZURE_REDIRECT_URI", "http://localhost:8000/auth/outlook/callback")
        
        auth_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?client_id={client_id}&response_type=code&scope=calendars.readwrite&redirect_uri={redirect_uri}"
        
        return auth_url

    def handle_google_callback(self, user_id: str, authorization_code: str):
        """Procesar callback de Google OAuth."""
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials_google.json',
                scopes=SCOPES
            )
            credentials = flow.run_local_server(port=0)
            
            # Guardar token
            token_json = credentials.to_json()
            with self._conn() as con:
                con.execute("""
                UPDATE calendar_credentials 
                SET google_token=?, google_enabled=1, updated_at=?
                WHERE user_id=?
                """, (token_json, datetime.utcnow().isoformat(), user_id))
            
            return True
        except Exception as e:
            log.info(f"❌ Google callback error: {e}")
            return False

    def create_news_event(self, user_id: str, news: Dict) -> bool:
        """Crear evento en calendario para noticia importante."""
        # Detectar si es noticia importante (breaking, trending, etc)
        if not self._is_important_news(news):
            return False
        
        title = f"📰 {news.get('title', 'Noticia')}"
        description = news.get('summary', news.get('description', ''))
        
        # Detectar hora del evento
        event_time = self._extract_event_time(news)
        if not event_time:
            event_time = datetime.utcnow()
        
        end_time = event_time + timedelta(hours=1)
        
        event_data = {
            'summary': title,
            'description': description,
            'start': {'dateTime': event_time.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'UTC'},
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 60},
                    {'method': 'popup', 'minutes': 15}
                ]
            }
        }
        
        # Sincronizar a calendarios habilitados
        success = False
        
        # Google Calendar
        if self._get_user_calendar_enabled(user_id, 'google'):
            success |= self._create_google_event(user_id, event_data, news)
        
        # Outlook
        if self._get_user_calendar_enabled(user_id, 'outlook'):
            success |= self._create_outlook_event(user_id, event_data, news)
        
        return success

    def _create_google_event(self, user_id: str, event_data: Dict, source_news: Dict) -> bool:
        """Crear evento en Google Calendar."""
        try:
            token_json = self._get_user_token(user_id, 'google')
            if not token_json:
                return False
            
            credentials = Credentials.from_authorized_user_info(json.loads(token_json))
            service = build('calendar', 'v3', credentials=credentials)
            
            event = service.events().insert(
                calendarId='primary',
                body=event_data
            ).execute()
            
            # Guardar referencia
            with self._conn() as con:
                con.execute("""
                INSERT INTO calendar_events 
                (user_id, event_id, title, description, start_time, end_time, calendar_type, source, sync_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    event['id'],
                    event_data['summary'],
                    event_data['description'],
                    event_data['start']['dateTime'],
                    event_data['end']['dateTime'],
                    'google',
                    source_news.get('source', 'nexo'),
                    'synced',
                    datetime.utcnow().isoformat()
                ))
            
            return True
        except Exception as e:
            log.info(f"❌ Google event creation error: {e}")
            return False

    def _create_outlook_event(self, user_id: str, event_data: Dict, source_news: Dict) -> bool:
        """Crear evento en Outlook."""
        try:
            token = self._get_user_token(user_id, 'outlook')
            if not token:
                return False
            
            # Convertir formato de Google a Outlook
            outlook_event = {
                'subject': event_data['summary'],
                'bodyPreview': event_data['description'][:100],
                'start': {
                    'dateTime': event_data['start']['dateTime'],
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': event_data['end']['dateTime'],
                    'timeZone': 'UTC'
                },
                'isReminderOn': True
            }
            
            # Aquí irían las credenciales de Outlook
            # Por ahora es skeleton
            
            return True
        except Exception as e:
            log.info(f"❌ Outlook event creation error: {e}")
            return False

    def _is_important_news(self, news: Dict) -> bool:
        """Determinar si noticia es lo bastante importante para crear evento."""
        importance_signals = [
            news.get('is_breaking'),
            news.get('is_trending'),
            news.get('is_featured'),
            news.get('source') in ['AP', 'Reuters', 'BBC', 'Reuters'],
            news.get('category') in ['Politics', 'Economy', 'Disaster', 'Science']
        ]
        
        return sum(filter(None, importance_signals)) >= 2

    def _extract_event_time(self, news: Dict) -> Optional[datetime]:
        """Extraer tiempo del evento de la noticia."""
        try:
            if 'event_date' in news:
                return datetime.fromisoformat(news['event_date'])
            if 'published_at' in news:
                return datetime.fromisoformat(news['published_at'])
            return None
        except:
            return None

    def _get_user_calendar_enabled(self, user_id: str, calendar_type: str) -> bool:
        """Verificar si usuario tiene calendario habilitado."""
        with self._conn() as con:
            cur = con.cursor()
            field = f'{calendar_type}_enabled'
            cur.execute(f"SELECT {field} FROM calendar_credentials WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            return bool(row and row[0])

    def _get_user_token(self, user_id: str, calendar_type: str) -> Optional[str]:
        """Obtener token de usuario."""
        with self._conn() as con:
            cur = con.cursor()
            field = f'{calendar_type}_token'
            cur.execute(f"SELECT {field} FROM calendar_credentials WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def get_upcoming_events(self, user_id: str, days_ahead: int = 7) -> list:
        """Obtener eventos próximos del usuario."""
        future_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat()
        
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("""
            SELECT * FROM calendar_events 
            WHERE user_id=? AND start_time < ? AND start_time > ?
            ORDER BY start_time
            """, (user_id, future_date, datetime.utcnow().isoformat()))
            return cur.fetchall()

    def set_reminder(self, user_id: str, event_id: str, reminder_type: str, minutes_before: int = 60):
        """Establecer recordatorio para evento."""
        reminder_time = datetime.utcnow() + timedelta(minutes=minutes_before)
        
        with self._conn() as con:
            con.execute("""
            INSERT INTO event_reminders 
            (user_id, event_id, reminder_type, send_at, status)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, event_id, reminder_type, reminder_time.isoformat(), 'pending'))

    def sync_calendars(self, user_id: str) -> Dict:
        """Sincronizar todos los calendarios del usuario."""
        result = {
            'google_synced': 0,
            'outlook_synced': 0,
            'errors': []
        }
        
        # Implementar sincronización bidireccional
        # Por ahora es skeleton
        
        return result
