"""Integración con X (Twitter) y xAI (Grok placeholder/API beta)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests


def _require_tweepy():
    try:
        import tweepy  # type: ignore
        return tweepy
    except Exception as exc:
        raise RuntimeError(
            "tweepy no está disponible. Instala dependencia con: pip install tweepy"
        ) from exc


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key, default) or "").strip()


def _build_x_client():
    tweepy = _require_tweepy()
    api_key = _env("X_API_KEY")
    api_secret = _env("X_API_SECRET")
    access_token = _env("X_ACCESS_TOKEN")
    access_secret = _env("X_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        raise RuntimeError("Faltan credenciales X: X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_SECRET")

    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )


def _build_oauth1_api():
    tweepy = _require_tweepy()
    api_key = _env("X_API_KEY")
    api_secret = _env("X_API_SECRET")
    access_token = _env("X_ACCESS_TOKEN")
    access_secret = _env("X_ACCESS_SECRET")

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    return tweepy.API(auth)


def post_to_x(text: str, media_path: Optional[str] = None, in_reply_to: Optional[str] = None) -> Dict:
    """Publica un post en X; soporta media local opcional."""
    text = (text or "").strip()
    if not text:
        raise ValueError("El texto no puede estar vacío")

    client = _build_x_client()
    media_ids = None

    if media_path:
        api = _build_oauth1_api()
        media = api.media_upload(filename=media_path)
        media_ids = [media.media_id_string]

    response = client.create_tweet(
        text=text[:280],
        media_ids=media_ids,
        in_reply_to_tweet_id=in_reply_to,
    )
    tweet_id = (response.data or {}).get("id")
    username = _env("X_USERNAME", "i")

    return {
        "ok": bool(tweet_id),
        "tweet_id": tweet_id,
        "url": f"https://x.com/{username}/status/{tweet_id}" if tweet_id else None,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "text": text[:280],
    }


def search_x_recent(query: str, limit: int = 10, since_id: Optional[str] = None) -> Dict:
    """Busca posts recientes por query usando X API v2."""
    q = (query or "").strip()
    if not q:
        raise ValueError("query requerido")

    limit = max(1, min(int(limit), 50))
    client = _build_x_client()

    result = client.search_recent_tweets(
        query=q,
        max_results=limit,
        since_id=str(since_id) if since_id else None,
        tweet_fields=["created_at", "author_id", "conversation_id", "lang", "public_metrics"],
    )

    rows: List[Dict] = []
    for tw in (result.data or []):
        rows.append(
            {
                "id": str(tw.id),
                "text": tw.text,
                "author_id": str(getattr(tw, "author_id", "") or ""),
                "conversation_id": str(getattr(tw, "conversation_id", "") or ""),
                "lang": getattr(tw, "lang", None),
                "created_at": getattr(tw, "created_at", None).isoformat() if getattr(tw, "created_at", None) else None,
                "public_metrics": getattr(tw, "public_metrics", None),
            }
        )

    newest_id = rows[0]["id"] if rows else since_id
    return {
        "ok": True,
        "count": len(rows),
        "query": q,
        "since_id": since_id,
        "newest_id": newest_id,
        "tweets": rows,
    }


def fetch_mentions(limit: int = 10, since_id: Optional[str] = None, username: Optional[str] = None) -> Dict:
    """Obtiene menciones recientes al usuario configurado en X."""
    client = _build_x_client()
    user = username or _env("X_BOT_USERNAME") or _env("X_USERNAME")
    if not user:
        raise RuntimeError("Define X_BOT_USERNAME o X_USERNAME en variables de entorno")

    user_resp = client.get_user(username=user)
    user_data = user_resp.data
    if not user_data:
        raise RuntimeError(f"No fue posible resolver el usuario @{user}")

    params = {
        "id": user_data.id,
        "max_results": max(5, min(int(limit), 100)),
        "tweet_fields": ["created_at", "author_id", "conversation_id", "lang", "public_metrics"],
    }
    if since_id:
        params["since_id"] = str(since_id)

    mentions = client.get_users_mentions(**params)
    rows: List[Dict] = []
    for tw in (mentions.data or []):
        rows.append(
            {
                "id": str(tw.id),
                "text": tw.text,
                "author_id": str(getattr(tw, "author_id", "") or ""),
                "conversation_id": str(getattr(tw, "conversation_id", "") or ""),
                "lang": getattr(tw, "lang", None),
                "created_at": getattr(tw, "created_at", None).isoformat() if getattr(tw, "created_at", None) else None,
                "public_metrics": getattr(tw, "public_metrics", None),
            }
        )

    newest_id = rows[0]["id"] if rows else since_id
    return {
        "ok": True,
        "username": user,
        "user_id": str(user_data.id),
        "count": len(rows),
        "since_id": since_id,
        "newest_id": newest_id,
        "mentions": rows,
    }


def ask_grok(question: str, model: str = "grok-beta") -> Dict:
    """Consulta xAI API si está disponible; fallback controlado si no hay clave."""
    q = (question or "").strip()
    if not q:
        raise ValueError("question requerido")

    api_key = _env("XAI_API_KEY")
    if not api_key:
        return {
            "ok": False,
            "status": "no_api_key",
            "message": "XAI_API_KEY no configurada. Usa monitoreo en X como fallback.",
            "answer": None,
        }

    base_url = _env("XAI_API_URL", "https://api.x.ai/v1/chat/completions")

    try:
        response = requests.post(
            base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": q}],
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        answer = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content"))
        return {
            "ok": bool(answer),
            "status": "ok" if answer else "empty_response",
            "answer": answer,
            "raw": payload,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "request_error",
            "message": str(exc),
            "answer": None,
        }


def ask_grok_via_x(question: str, context: str = "") -> Dict:
    """Fallback de validación Grok vía mención pública en X cuando no hay API xAI estable."""
    q = (question or "").strip()
    if not q:
        raise ValueError("question requerido")

    context_snippet = (context or "").strip()
    text = (
        f"@grok {q[:200]}\n"
        f"Contexto NEXO: {context_snippet[:100]}...\n"
        "#NexoSoberano"
    )
    result = post_to_x(text=text)
    result["mode"] = "x_mention"
    return result
