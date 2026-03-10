#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   NEXO SOBERANO — AGENTE RRSS v1.0                                         ║
║   Agente autónomo para redes sociales: X/Twitter, Instagram, Facebook,     ║
║   Telegram y Discord.  Lee credenciales desde variables de entorno (.env)  ║
╚══════════════════════════════════════════════════════════════════════════════╝

MODO DE USO:
    python agente_rrss.py --status              # Estado de conexiones
    python agente_rrss.py --post "Mensaje"      # Publicar en todas las redes
    python agente_rrss.py --post "Msg" --red x  # Publicar solo en X/Twitter
    python agente_rrss.py --watch               # Monitoreo continuo (métricas)
    python agente_rrss.py --test                # Probar credenciales
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ─── Setup logging ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("nexo.agente_rrss")

# ─── Cargar .env si existe ────────────────────────────────────────────────────

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT_DIR / ".env"


def _load_env() -> None:
    if not _ENV_FILE.exists():
        return
    for line in _ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env()


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


HTTP_TIMEOUT_SECONDS = float(_env("NEXO_RRSS_TIMEOUT_SECONDS", "10") or "10")
HTTP_RETRY_ATTEMPTS = int(_env("NEXO_RRSS_RETRY_ATTEMPTS", "3") or "3")
HTTP_RETRY_BACKOFF_SECONDS = float(_env("NEXO_RRSS_RETRY_BACKOFF_SECONDS", "1.5") or "1.5")


def _with_retries(action_name: str, func):
    last_exc = None
    for attempt in range(1, max(1, HTTP_RETRY_ATTEMPTS) + 1):
        try:
            return func()
        except Exception as exc:
            last_exc = exc
            if attempt >= max(1, HTTP_RETRY_ATTEMPTS):
                break
            sleep_s = HTTP_RETRY_BACKOFF_SECONDS * attempt
            log.warning("%s falló (intento %d/%d): %s. Reintentando en %.1fs...",
                        action_name, attempt, HTTP_RETRY_ATTEMPTS, exc, sleep_s)
            time.sleep(sleep_s)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"{action_name} falló sin excepción capturada")


# ─── Modelos de datos ─────────────────────────────────────────────────────────

@dataclass
class PublicacionResult:
    red: str
    exito: bool
    mensaje: str = ""
    post_id: str = ""
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EstadoConexion:
    red: str
    conectada: bool
    usuario: str = ""
    detalle: str = ""


# ─── Conectores por red social ────────────────────────────────────────────────

class ConectorX:
    """Conector para X / Twitter usando Tweepy."""

    NAME = "x"

    def _client(self):
        try:
            import tweepy  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Instala tweepy: pip install tweepy") from exc

        api_key = _env("X_API_KEY")
        api_secret = _env("X_API_SECRET")
        access_token = _env("X_ACCESS_TOKEN")
        access_secret = _env("X_ACCESS_SECRET")

        if not all([api_key, api_secret, access_token, access_secret]):
            raise RuntimeError(
                "Faltan credenciales X: X_API_KEY, X_API_SECRET, "
                "X_ACCESS_TOKEN, X_ACCESS_SECRET"
            )

        return tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
        )

    def estado(self) -> EstadoConexion:
        try:
            client = self._client()
            me = _with_retries("X.get_me", lambda: client.get_me())
            me_data = getattr(me, "data", None)
            user = getattr(me_data, "username", "desconocido") if me_data else "desconocido"
            return EstadoConexion(red=self.NAME, conectada=True, usuario=f"@{user}")
        except Exception as exc:
            return EstadoConexion(red=self.NAME, conectada=False, detalle=str(exc))

    def publicar(self, texto: str) -> PublicacionResult:
        try:
            client = self._client()
            resp = _with_retries("X.create_tweet", lambda: client.create_tweet(text=texto[:280]))
            resp_data = getattr(resp, "data", None)
            if isinstance(resp_data, dict):
                post_id = str(resp_data.get("id", ""))
            else:
                post_id = str(getattr(resp_data, "id", "") or "")
            return PublicacionResult(red=self.NAME, exito=True, mensaje=texto, post_id=post_id)
        except Exception as exc:
            return PublicacionResult(red=self.NAME, exito=False, error=str(exc))


class ConectorTelegram:
    """Conector para Telegram usando la API de bots (requests)."""

    NAME = "telegram"

    def _token(self) -> str:
        token = _env("TELEGRAM_BOT_TOKEN") or _env("TELEGRAM_TOKEN")
        if not token:
            raise RuntimeError("Falta TELEGRAM_BOT_TOKEN en .env")
        return token

    def _chat_id(self) -> str:
        chat_id = _env("TELEGRAM_CHAT_ID")
        if not chat_id:
            raise RuntimeError("Falta TELEGRAM_CHAT_ID en .env")
        return chat_id

    def _api(self, method: str, **kwargs) -> dict:
        import urllib.request
        import json

        url = f"https://api.telegram.org/bot{self._token()}/{method}"
        data = json.dumps(kwargs).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
        )
        def _call():
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as r:
                return json.loads(r.read().decode())
        return _with_retries(f"Telegram.{method}", _call)

    def estado(self) -> EstadoConexion:
        try:
            resp = self._api("getMe")
            username = resp.get("result", {}).get("username", "bot")
            return EstadoConexion(red=self.NAME, conectada=True, usuario=f"@{username}")
        except Exception as exc:
            return EstadoConexion(red=self.NAME, conectada=False, detalle=str(exc))

    def publicar(self, texto: str) -> PublicacionResult:
        try:
            resp = self._api("sendMessage", chat_id=self._chat_id(), text=texto)
            msg_id = str(resp.get("result", {}).get("message_id", ""))
            return PublicacionResult(red=self.NAME, exito=True, mensaje=texto, post_id=msg_id)
        except Exception as exc:
            return PublicacionResult(red=self.NAME, exito=False, error=str(exc))


class ConectorDiscord:
    """Conector para Discord usando webhooks."""

    NAME = "discord"

    def _webhook_url(self) -> str:
        url = _env("DISCORD_WEBHOOK_URL")
        if not url:
            raise RuntimeError("Falta DISCORD_WEBHOOK_URL en .env")
        return url

    def _send(self, payload: dict) -> dict:
        import json
        import urllib.request

        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            self._webhook_url(), data=data,
            headers={"Content-Type": "application/json"},
        )
        def _call():
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        return _with_retries("Discord.webhook_send", _call)

    def estado(self) -> EstadoConexion:
        try:
            import json
            import urllib.request

            def _call():
                with urllib.request.urlopen(self._webhook_url(), timeout=HTTP_TIMEOUT_SECONDS) as r:
                    return json.loads(r.read().decode())

            data = _with_retries("Discord.webhook_status", _call)
            name = data.get("name", "webhook")
            return EstadoConexion(red=self.NAME, conectada=True, usuario=name)
        except Exception as exc:
            return EstadoConexion(red=self.NAME, conectada=False, detalle=str(exc))

    def publicar(self, texto: str) -> PublicacionResult:
        try:
            self._send({"content": texto})
            return PublicacionResult(red=self.NAME, exito=True, mensaje=texto)
        except Exception as exc:
            return PublicacionResult(red=self.NAME, exito=False, error=str(exc))


class ConectorFacebook:
    """Conector para Facebook Page usando Graph API."""

    NAME = "facebook"

    def _page_token(self) -> str:
        token = _env("FACEBOOK_PAGE_TOKEN")
        if not token:
            raise RuntimeError("Falta FACEBOOK_PAGE_TOKEN en .env")
        return token

    def _page_id(self) -> str:
        return _env("FACEBOOK_PAGE_ID", "me")

    def _graph(self, endpoint: str, params: dict) -> dict:
        import json
        import urllib.parse
        import urllib.request

        url = f"https://graph.facebook.com/v19.0/{endpoint}"
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=data)
        def _call():
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as r:
                return json.loads(r.read().decode())
        return _with_retries(f"Facebook.{endpoint}", _call)

    def estado(self) -> EstadoConexion:
        try:
            resp = self._graph(self._page_id(), {"fields": "name", "access_token": self._page_token()})
            return EstadoConexion(red=self.NAME, conectada=True, usuario=resp.get("name", "página"))
        except Exception as exc:
            return EstadoConexion(red=self.NAME, conectada=False, detalle=str(exc))

    def publicar(self, texto: str) -> PublicacionResult:
        try:
            resp = self._graph(
                f"{self._page_id()}/feed",
                {"message": texto, "access_token": self._page_token()},
            )
            post_id = resp.get("id", "")
            return PublicacionResult(red=self.NAME, exito=True, mensaje=texto, post_id=str(post_id))
        except Exception as exc:
            return PublicacionResult(red=self.NAME, exito=False, error=str(exc))


class ConectorInstagram:
    """Conector para Instagram Business usando Graph API."""

    NAME = "instagram"

    def _token(self) -> str:
        token = _env("INSTAGRAM_ACCESS_TOKEN")
        if not token:
            raise RuntimeError("Falta INSTAGRAM_ACCESS_TOKEN en .env")
        return token

    def _account_id(self) -> str:
        aid = _env("INSTAGRAM_BUSINESS_ACCOUNT_ID")
        if not aid:
            raise RuntimeError("Falta INSTAGRAM_BUSINESS_ACCOUNT_ID en .env")
        return aid

    def _graph(self, endpoint: str, params: dict) -> dict:
        import json
        import urllib.parse
        import urllib.request

        url = f"https://graph.facebook.com/v19.0/{endpoint}"
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=data)
        def _call():
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as r:
                return json.loads(r.read().decode())
        return _with_retries(f"Instagram.{endpoint}", _call)

    def estado(self) -> EstadoConexion:
        try:
            resp = self._graph(
                self._account_id(),
                {"fields": "username", "access_token": self._token()},
            )
            return EstadoConexion(
                red=self.NAME, conectada=True,
                usuario=resp.get("username", self._account_id()),
            )
        except Exception as exc:
            return EstadoConexion(red=self.NAME, conectada=False, detalle=str(exc))

    def publicar(self, texto: str, image_url: Optional[str] = None) -> PublicacionResult:
        """Publica en Instagram. Si no hay image_url solo registra (IG exige imagen)."""
        if not image_url:
            return PublicacionResult(
                red=self.NAME, exito=False,
                error="Instagram requiere image_url para publicar. Usa --imagen <URL>",
            )
        try:
            # 1. Crear contenedor
            container = self._graph(
                f"{self._account_id()}/media",
                {"image_url": image_url, "caption": texto, "access_token": self._token()},
            )
            cid = container.get("id")
            if not cid:
                return PublicacionResult(red=self.NAME, exito=False, error="No se obtuvo container_id")

            # 2. Publicar
            result = self._graph(
                f"{self._account_id()}/media_publish",
                {"creation_id": cid, "access_token": self._token()},
            )
            return PublicacionResult(
                red=self.NAME, exito=True, mensaje=texto, post_id=str(result.get("id", "")),
            )
        except Exception as exc:
            return PublicacionResult(red=self.NAME, exito=False, error=str(exc))


# ─── Agente RRSS ─────────────────────────────────────────────────────────────

_CONECTORES_DISPONIBLES = {
    "x": ConectorX,
    "telegram": ConectorTelegram,
    "discord": ConectorDiscord,
    "facebook": ConectorFacebook,
    "instagram": ConectorInstagram,
}


class AgenteRRSS:
    """
    Agente autónomo que gestiona la presencia en redes sociales.
    - Conecta y verifica estado de cada plataforma configurada
    - Publica mensajes en una o todas las redes
    - Modo watch: monitorea métricas periódicamente
    """

    def __init__(self, redes: Optional[List[str]] = None):
        nombres = redes or list(_CONECTORES_DISPONIBLES.keys())
        self.conectores = {n: _CONECTORES_DISPONIBLES[n]() for n in nombres if n in _CONECTORES_DISPONIBLES}
        log.info("🌐 AgenteRRSS iniciado — redes: %s", ", ".join(self.conectores))

    def estado(self) -> List[EstadoConexion]:
        """Verifica el estado de conexión de cada red."""
        resultados = []
        for nombre, conector in self.conectores.items():
            estado = conector.estado()
            icon = "✅" if estado.conectada else "❌"
            detalle = estado.usuario or estado.detalle or ""
            log.info("  %s %-12s %s", icon, nombre, detalle)
            resultados.append(estado)
        return resultados

    def publicar(
        self,
        texto: str,
        red: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> List[PublicacionResult]:
        """Publica texto en una o todas las redes configuradas."""
        objetivos = {red: self.conectores[red]} if red and red in self.conectores else self.conectores
        if not objetivos:
            log.warning("Red '%s' no disponible. Redes configuradas: %s", red, list(self.conectores))
            return []

        resultados: List[PublicacionResult] = []
        for nombre, conector in objetivos.items():
            if nombre == "instagram" and isinstance(conector, ConectorInstagram):
                res = conector.publicar(texto, image_url=image_url)
            else:
                res = conector.publicar(texto)

            icon = "✅" if res.exito else "❌"
            info = res.post_id or res.error or ""
            log.info("  %s %-12s %s", icon, nombre, info)
            resultados.append(res)

        exitosos = sum(1 for r in resultados if r.exito)
        log.info("📣 %d/%d redes publicaron correctamente.", exitosos, len(resultados))
        return resultados

    def watch(self, interval: int = 300) -> None:
        """Monitoreo continuo: verifica estado de conexiones periódicamente."""
        log.info("👁  Modo WATCH RRSS activo — intervalo: %ds", interval)
        log.info("   [Ctrl+C para detener]")
        try:
            while True:
                log.info("\n🔄 Verificando conexiones RRSS — %s", datetime.now(timezone.utc).isoformat())
                self.estado()
                time.sleep(interval)
        except KeyboardInterrupt:
            log.info("⏹  Watch RRSS detenido por el usuario")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NEXO SOBERANO — Agente RRSS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--status", action="store_true", help="Verificar estado de conexiones")
    parser.add_argument("--post", metavar="TEXTO", help="Publicar mensaje")
    parser.add_argument("--red", metavar="RED", help="Red destino: x|telegram|discord|facebook|instagram")
    parser.add_argument("--imagen", metavar="URL", help="URL de imagen (requerido para Instagram)")
    parser.add_argument("--watch", action="store_true", help="Monitoreo continuo")
    parser.add_argument("--test", action="store_true", help="Probar credenciales (alias de --status)")
    parser.add_argument("--interval", type=int, default=300, help="Intervalo watch en segundos")
    parser.add_argument("--redes", nargs="+", help="Redes a usar (por defecto: todas)")
    args = parser.parse_args()

    agente = AgenteRRSS(redes=args.redes)

    if args.status or args.test:
        log.info("🔍 Estado de conexiones RRSS:")
        agente.estado()
    elif args.post:
        log.info("📢 Publicando: %s", args.post[:60])
        agente.publicar(args.post, red=args.red, image_url=args.imagen)
    elif args.watch:
        agente.watch(interval=args.interval)
    else:
        log.info("Estado de conexiones RRSS:")
        agente.estado()


if __name__ == "__main__":
    main()
