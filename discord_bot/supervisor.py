import os
import re
import time
import asyncio
import logging
from collections import defaultdict, deque
from typing import Deque, Dict
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

LOG_CHANNEL_NAME = "logs-torre"  # canal donde se reportan incidentes
MUTED_ROLE_NAME = "Muted"

# Ajustables
SPAM_WINDOW_SECONDS = 10        # ventana para contar mensajes
SPAM_THRESHOLD = 8              # si supera este número en la ventana -> acción
DUP_LINK_THRESHOLD = 3          # enlaces repetidos por usuario para considerar spam
TEMP_MUTE_SECONDS = 300         # 5 minutos

# Lista base de palabras NSFW rápida (amplíala) — sensible: moderar según tus reglas
NSFW_KEYWORDS = {
    "porn",
    "xxx",
    "nude",
    "porno",
    "sexo",
    # añade más según tus necesidades
}

URL_RE = re.compile(r"https?://\S+")

logger = logging.getLogger("supervisor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)


class Supervisor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # user_id -> deque[timestamps]
        self.user_messages: Dict[int, Deque[float]] = defaultdict(lambda: deque())
        # user_id -> dict[url -> count]
        self.user_links: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # simple in-memory punishments scheduled tasks
        self._unmute_tasks: Dict[int, asyncio.Task] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"Supervisor activo como {self.bot.user}. Intents: {self.bot.intents}")
        # optional: confirm logs channel exists
        _ = self._get_log_channel()

    def _get_log_channel(self) -> discord.TextChannel | None:
        for guild in self.bot.guilds:
            for ch in guild.text_channels:
                if ch.name == LOG_CHANNEL_NAME:
                    return ch
        return None

    async def _ensure_muted_role(self, guild: discord.Guild) -> discord.Role:
        role = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
        if role:
            return role
        # create role with very restricted perms
        perms = discord.Permissions(send_messages=False, speak=False)
        role = await guild.create_role(name=MUTED_ROLE_NAME, permissions=perms, reason="Role creado por Supervisor")
        # attempt to set channel overrides to prevent sending messages (best-effort)
        for ch in guild.text_channels:
            try:
                await ch.set_permissions(role, send_messages=False)
            except Exception:
                pass
        return role

    async def _log_incident(self, guild: discord.Guild, user: discord.User, action: str, reason: str, message: discord.Message | None = None):
        ch = self._get_log_channel()
        text = f"[{guild.name}] {user} ({user.id}) -> {action}: {reason}"
        if message:
            text += f"\nMessage: {message.content[:200]}"
            text += f"\nLink: {message.jump_url}"
        if ch:
            try:
                await ch.send(text)
            except Exception:
                logger.exception("No se pudo enviar el log al canal.")
        else:
            logger.info("Log channel not found. Incident: %s", text)

    def _is_nsfw_content(self, content: str) -> bool:
        if not content:
            return False
        content_low = content.lower()
        for kw in NSFW_KEYWORDS:
            if kw in content_low:
                return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ignore bots and webhooks
        if message.author.bot:
            return

        # allow commands to be processed by other cogs/bot
        await self.bot.process_commands(message)

        user_id = message.author.id
        now = time.time()

        # --- SPAM frequency detection ---
        dq = self.user_messages[user_id]
        dq.append(now)
        # remove timestamps outside window
        while dq and dq[0] < now - SPAM_WINDOW_SECONDS:
            dq.popleft()

        if len(dq) >= SPAM_THRESHOLD:
            # spam: delete and mute temporarily
            try:
                await message.delete()
            except Exception:
                pass
            reason = f"Spam: {len(dq)} msgs en {SPAM_WINDOW_SECONDS}s"
            await self._handle_punishment(message.guild, message.author, reason, message)
            return

        # --- Duplicate link detection ---
        urls = URL_RE.findall(message.content or "")
        if message.attachments:
            # attachments can also count as suspicious
            # register as pseudo-url per filename
            for a in message.attachments:
                urls.append(a.filename)

        if urls:
            link_counts = self.user_links[user_id]
            flagged = False
            for u in urls:
                link_counts[u] += 1
                if link_counts[u] >= DUP_LINK_THRESHOLD:
                    flagged = True
            # keep link counts bounded and time-decay them (simple)
            # schedule cleanup: remove oldest entries occasionally
            if flagged:
                try:
                    await message.delete()
                except Exception:
                    pass
                reason = "Links repetidos detectados"
                await self._handle_punishment(message.guild, message.author, reason, message)
                return

        # --- NSFW keyword detection (very basic) ---
        if self._is_nsfw_content(message.content):
            try:
                await message.delete()
            except Exception:
                pass
            reason = "Contenido NSFW detectado (palabra clave)"
            await self._handle_punishment(message.guild, message.author, reason, message)
            return

    async def _handle_punishment(self, guild: discord.Guild, member: discord.Member, reason: str, message: discord.Message | None):
        # warn user with DM (best effort)
        try:
            await member.send(f"Tu mensaje ha sido moderado en '{guild.name}'. Motivo: {reason}")
        except Exception:
            pass

        # log incident
        await self._log_incident(guild, member, "ModerationAction", reason, message)

        # try to mute member temporarily
        try:
            role = await self._ensure_muted_role(guild)
            await member.add_roles(role, reason="Muted by Supervisor: " + reason)
            # schedule unmute
            if member.id in self._unmute_tasks:
                self._unmute_tasks[member.id].cancel()
            task = asyncio.create_task(self._schedule_unmute(guild, member, role, TEMP_MUTE_SECONDS))
            self._unmute_tasks[member.id] = task
        except Exception:
            logger.exception("No se pudo mutear al usuario.")

    async def _schedule_unmute(self, guild: discord.Guild, member: discord.Member, role: discord.Role, delay: int):
        try:
            await asyncio.sleep(delay)
            await member.remove_roles(role, reason="Auto-unmute by Supervisor")
            await self._log_incident(guild, member, "Unmute", f"Auto unmute after {delay}s")
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Error unmute task")
        finally:
            self._unmute_tasks.pop(member.id, None)


def setup(bot: commands.Bot):
    bot.add_cog(Supervisor(bot))
