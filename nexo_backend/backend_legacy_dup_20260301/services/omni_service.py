import threading
import sqlite3
from datetime import datetime
from typing import Callable, Dict, Any, Optional
import requests
import json

class MessageDiary:
    def __init__(self, db_path="diary.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._conn() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                channel TEXT,
                sender TEXT,
                message TEXT
            )
            """)

    def add(self, channel: str, sender: str, message: str):
        with self._conn() as con:
            con.execute(
                "INSERT INTO entries (timestamp, channel, sender, message) VALUES (?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), channel, sender, message)
            )

    def get_all(self):
        with self._conn() as con:
            cur = con.cursor()
            cur.execute("SELECT timestamp, channel, sender, message FROM entries ORDER BY id DESC")
            return cur.fetchall()

class OmniChannelManager:
    def __init__(self, ai_callback: Callable[[str, str], str]):
        self.ai_callback = ai_callback
        self.handlers: Dict[str, Dict[str, Any]] = {}
        self.diary = MessageDiary()

    def register_channel(self, name: str, send_func: Callable[[str, str], None]):
        self.handlers[name] = {"send": send_func}

    def receive(self, channel: str, sender: str, text: str):
        # guardar en diario
        self.diary.add(channel, sender, text)
        # pedir respuesta a la IA central
        response = self.ai_callback(channel, text)
        # registrar respuesta también
        self.diary.add(channel, "IA", response)
        # enviar de vuelta por el canal origen
        if channel in self.handlers:
            self.handlers[channel]["send"](sender, response)

# --- adaptadores mínimos ---

class TelegramAdapter:
    def __init__(self, token: str, manager: OmniChannelManager):
        from telegram import Update
        from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

        self.manager = manager
        self.updater = Updater(token=token, use_context=True)
        dp = self.updater.dispatcher
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self._on_message))

    def _on_message(self, update: 'Update', context: 'CallbackContext'):
        chat_id = update.effective_chat.id
        text = update.message.text
        sender = update.effective_user.username or str(chat_id)
        self.manager.receive("telegram", sender, text)

    def start(self):
        threading.Thread(target=self.updater.start_polling, daemon=True).start()

    def send(self, to: str, text: str):
        # to is chat_id as string
        self.updater.bot.send_message(chat_id=int(to), text=text)

# Placeholder: implement WhatsApp/Facebook/Instagram using respective APIs
class WhatsAppAdapter:
    def __init__(self, api_url: str, token: str, manager: OmniChannelManager):
        self.api_url = api_url
        self.token = token
        self.manager = manager

    def send(self, to, text):
        # ejemplo genérico HTTP
        requests.post(f"{self.api_url}/message", json={"to": to, "text": text}, headers={"Authorization": f"Bearer {self.token}"})

class FBAdapter:
    def __init__(self, page_token: str, manager: OmniChannelManager):
        self.token = page_token
        self.manager = manager

    def send(self, id, text):
        requests.post(
            "https://graph.facebook.com/v11.0/me/messages",
            params={"access_token": self.token},
            json={"recipient": {"id": id}, "message": {"text": text}}
        )

# la lógica para recibir webhooks se implementaría en rutas separadas
