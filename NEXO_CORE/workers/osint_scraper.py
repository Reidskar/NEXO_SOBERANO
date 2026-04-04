"""
NEXO SOBERANO — Autonomous OSINT Scraper (Phase 12)
====================================================
Background worker that continuously monitors Telegram channels, Twitter/X accounts,
Google Drive, and OneDrive for new OSINT military/geopolitical events.

When a new qualifying event is found:
1. Extracts coordinates and event type via Gemini Vision.
2. Broadcasts a TACTICAL_SIMULATION event via WebSocket.
3. Stores the event in Supabase `osint_events` table.

Sources:
 - Telegram  → Telethon (MTProto API)
 - Twitter/X → Tweepy API v2
 - Drive     → Existing drive_service.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# ─── Telegram channels and Twitter accounts to monitor ───────────────────────
TELEGRAM_CHANNELS = [c.strip() for c in os.getenv("TELEGRAM_CHANNELS", "wfwitness,intelslava,wartranslated,rybar_en").split(",") if c.strip()]
TWITTER_ACCOUNTS = [a.strip() for a in os.getenv("TWITTER_ACCOUNTS", "WarMonitor3,OSINTua,IntelSlava").split(",") if a.strip()]

# ─── Poll intervals ───────────────────────────────────────────────────────────
TELEGRAM_POLL_SECONDS = int(os.getenv("OSINT_TELEGRAM_INTERVAL", "120"))  # 2 min
TWITTER_POLL_SECONDS = int(os.getenv("OSINT_TWITTER_INTERVAL", "300"))   # 5 min
DRIVE_POLL_SECONDS   = int(os.getenv("OSINT_DRIVE_INTERVAL",   "300"))   # 5 min

# ─── Filter: minimum message length to bother analyzing ──────────────────────
MIN_TEXT_LENGTH = 60

# ─── Backend webhook URL (same server) ───────────────────────────────────────
_BASE_URL = os.getenv("NEXO_SUPERVISOR_BASE_URL", "http://127.0.0.1:8000")
_API_KEY  = os.getenv("NEXO_API_KEY", "nexo_dev_key_2025")


class OsintScraper:
    """Autonomous OSINT multi-source monitor."""

    def __init__(self) -> None:
        self._tg_client = None
        self._tw_client = None
        self._last_tg_msg: dict[str, int] = {}   # channel → last message_id seen
        self._last_tw_id: dict[str, str] = {}    # account → last tweet id seen
        self._last_drive_check = 0.0
        self._last_tg_check    = 0.0
        self._last_tw_check    = 0.0
        self._running = False

    # ─────────────────────────────────────────────────────────────────────────
    # SOURCE: TELEGRAM
    # ─────────────────────────────────────────────────────────────────────────
    async def _init_telegram(self) -> bool:
        """Initialize Telethon client. Returns True if successful."""
        api_id   = os.getenv("TELEGRAM_API_ID", "")
        api_hash = os.getenv("TELEGRAM_API_HASH", "")
        session  = os.getenv("TELEGRAM_SESSION_STRING", "")

        if not all([api_id, api_hash, session]):
            logger.info("[OSINT Scraper] Telegram credentials missing — source disabled")
            return False

        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            self._tg_client = TelegramClient(StringSession(session), int(api_id), api_hash)
            await self._tg_client.connect()
            logger.info("[OSINT Scraper] Telegram client connected ✓")
            return True
        except ImportError:
            logger.warning("[OSINT Scraper] telethon not installed — pip install telethon")
            return False
        except Exception as exc:
            logger.warning(f"[OSINT Scraper] Telegram init failed: {exc}")
            return False

    async def _poll_telegram(self) -> list[dict]:
        """Fetch recent messages from each monitored channel."""
        if not self._tg_client:
            return []

        events = []
        try:
            from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
            for channel in TELEGRAM_CHANNELS:
                try:
                    last_id = self._last_tg_msg.get(channel, 0)
                    messages = await self._tg_client.get_messages(channel, limit=5, min_id=last_id)
                    for msg in reversed(messages):
                        if not msg.text or len(msg.text) < MIN_TEXT_LENGTH:
                            continue
                        self._last_tg_msg[channel] = max(self._last_tg_msg.get(channel, 0), msg.id)

                        # Download photo if available
                        image_path = None
                        if msg.media and isinstance(msg.media, MessageMediaPhoto):
                            try:
                                path = f"/tmp/tg_{channel}_{msg.id}.jpg"
                                await self._tg_client.download_media(msg.media, path)
                                image_path = path
                            except Exception:
                                pass

                        events.append({
                            "text": msg.text,
                            "source": f"telegram:{channel}",
                            "image_path": image_path,
                            "media_urls": [],
                        })
                        logger.info(f"[OSINT Telegram] New event from {channel}: {msg.text[:80]}...")
                except Exception as exc:
                    logger.warning(f"[OSINT Telegram] Error reading {channel}: {exc}")
        except Exception as exc:
            logger.error(f"[OSINT Telegram] Poll failed: {exc}")

        return events

    # ─────────────────────────────────────────────────────────────────────────
    # SOURCE: TWITTER / X
    # ─────────────────────────────────────────────────────────────────────────
    def _init_twitter(self) -> bool:
        bearer = os.getenv("TWITTER_BEARER_TOKEN", "")
        if not bearer:
            logger.info("[OSINT Scraper] Twitter credentials missing — source disabled")
            return False
        try:
            import tweepy
            self._tw_client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)
            logger.info("[OSINT Scraper] Twitter client initialized ✓")
            return True
        except ImportError:
            logger.warning("[OSINT Scraper] tweepy not installed — pip install tweepy")
            return False
        except Exception as exc:
            logger.warning(f"[OSINT Scraper] Twitter init failed: {exc}")
            return False

    async def _poll_twitter(self) -> list[dict]:
        if not self._tw_client:
            return []

        events = []
        try:
            import tweepy
            for account in TWITTER_ACCOUNTS:
                try:
                    since_id = self._last_tw_id.get(account)
                    user = self._tw_client.get_user(username=account)
                    if not user.data:
                        continue
                    uid = user.data.id
                    tweets = self._tw_client.get_users_tweets(
                        uid,
                        max_results=5,
                        since_id=since_id,
                        tweet_fields=["id", "text", "created_at"],
                        expansions=["attachments.media_keys"],
                        media_fields=["url", "preview_image_url"],
                    )
                    if not tweets.data:
                        continue
                    for tweet in reversed(tweets.data):
                        self._last_tw_id[account] = str(tweet.id)
                        if len(tweet.text) < MIN_TEXT_LENGTH:
                            continue
                        events.append({
                            "text": tweet.text,
                            "source": f"twitter:{account}",
                            "image_path": None,
                            "media_urls": [],
                        })
                        logger.info(f"[OSINT Twitter] New tweet from @{account}: {tweet.text[:80]}...")
                except tweepy.errors.TweepyException as exc:
                    logger.warning(f"[OSINT Twitter] @{account}: {exc}")
        except Exception as exc:
            logger.error(f"[OSINT Twitter] Poll failed: {exc}")

        return events

    # ─────────────────────────────────────────────────────────────────────────
    # BROADCAST: Emit event via existing /api/webhooks/ingest
    # ─────────────────────────────────────────────────────────────────────────
    async def _broadcast_event(self, event: dict) -> None:
        """POST the extracted simulation event to the backend webhook."""
        payload = {
            "tenant_slug": "demo",
            "type": "TACTICAL_SIMULATION",
            "title": event.get("target") or event.get("event_type", "OSINT Event"),
            "body": event.get("brief", ""),
            "severity": float(event.get("severity", 0.7)),
            # Extended fields for the simulation
            "lat": event.get("lat"),
            "lng": event.get("lng"),
            "event_type": event.get("event_type"),
            "country": event.get("country"),
            "target": event.get("target"),
            "media_urls": event.get("media_urls", []),
            "source": event.get("source", "osint"),
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{_BASE_URL}/api/webhooks/ingest",
                    json=payload,
                    headers={"x-api-key": _API_KEY},
                )
                if resp.status_code == 200:
                    logger.info(f"[OSINT Scraper] Broadcast OK → lat={event.get('lat')}, lng={event.get('lng')}")
                else:
                    logger.warning(f"[OSINT Scraper] Broadcast failed: {resp.status_code} {resp.text[:200]}")
        except Exception as exc:
            logger.error(f"[OSINT Scraper] Broadcast error: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ─────────────────────────────────────────────────────────────────────────
    async def run_cycle(self) -> None:
        """Execute one full scrape cycle across all sources."""
        from NEXO_CORE.services.osint_event_extractor import extract_osint_event

        all_raw: list[dict] = []
        now = time.time()

        if now - self._last_tg_check >= TELEGRAM_POLL_SECONDS:
            all_raw += await self._poll_telegram()
            self._last_tg_check = now

        if now - self._last_tw_check >= TWITTER_POLL_SECONDS:
            all_raw += await self._poll_twitter()
            self._last_tw_check = now

        for raw in all_raw:
            try:
                event = await extract_osint_event(
                    text=raw["text"],
                    image_path=raw.get("image_path"),
                    source=raw.get("source", "osint"),
                    media_urls=raw.get("media_urls", []),
                )
                if event.get("lat") and event.get("lng"):
                    await self._broadcast_event(event)
                else:
                    logger.debug(f"[OSINT Scraper] No coords extracted — skipping broadcast: {raw['text'][:80]}")
            except Exception as exc:
                logger.error(f"[OSINT Scraper] Event processing failed: {exc}")

    async def loop(self) -> None:
        """Long-running background loop."""
        self._running = True
        logger.info("🛰  OSINT Scraper loop started")

        await self._init_telegram()
        self._init_twitter()

        while self._running:
            try:
                await self.run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[OSINT Scraper] Cycle error: {exc}")
            await asyncio.sleep(30)  # Check every 30s; per-source timers govern actual fetching

    def start(self) -> None:
        asyncio.create_task(self.loop())

    async def shutdown(self) -> None:
        self._running = False
        if self._tg_client:
            await self._tg_client.disconnect()


# Singleton
osint_scraper = OsintScraper()
