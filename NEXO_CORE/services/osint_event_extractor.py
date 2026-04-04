"""
NEXO SOBERANO — OSINT Event Extractor (Phase 12)
================================================
Uses Gemini Vision to parse raw OSINT content (text + image) from
Telegram / Twitter / Drive into a structured tactical simulation event.
"""
from __future__ import annotations

import json
import logging
import re
import os
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── DMS coordinate regex ────────────────────────────────────────────────────
_DMS_RE = re.compile(
    r"""(\d{1,3})[°º]\s*(\d{1,2})['′]\s*(\d{1,2}(?:\.\d+)?)["″]?\s*([NS])"""
    r"""\s*[,;\s]+\s*"""
    r"""(\d{1,3})[°º]\s*(\d{1,2})['′]\s*(\d{1,2}(?:\.\d+)?)["″]?\s*([EW])""",
    re.IGNORECASE,
)

# ─── DD coordinate regex (e.g. 24.0637, 47.546) ──────────────────────────────
_DD_RE = re.compile(
    r"""(-?\d{1,3}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})"""
)


def _dms_to_dd(deg: str, min: str, sec: str, hemi: str) -> float:
    dd = float(deg) + float(min) / 60 + float(sec) / 3600
    if hemi.upper() in ("S", "W"):
        dd = -dd
    return round(dd, 6)


def extract_coords_from_text(text: str) -> Optional[tuple[float, float]]:
    """Fast local DMS / DD coordinate extraction — no API calls."""
    m = _DMS_RE.search(text)
    if m:
        lat = _dms_to_dd(m.group(1), m.group(2), m.group(3), m.group(4))
        lng = _dms_to_dd(m.group(5), m.group(6), m.group(7), m.group(8))
        return lat, lng
    m2 = _DD_RE.search(text)
    if m2:
        return float(m2.group(1)), float(m2.group(2))
    return None


_EVENT_KEYWORDS = {
    "strike": ["explosion", "struck", "bombed", "missile", "attack", "hit", "destroy", "airstrike",
               "impacto", "ataque", "misil", "derribado", "explosión", "bombardeo"],
    "naval_movement": ["fleet", "carrier", "warship", "destroyer", "flotilla", "naval", "barco", "flota"],
    "deployment": ["troops", "deploy", "convoy", "logistics", "armored", "tanker", "soldiers",
                   "tropas", "despliegue", "convoy", "logística"],
    "diplomatic": ["sanctions", "meeting", "treaty", "agreement", "summit", "talks",
                   "sanciones", "acuerdo", "cumbre", "reunión", "negociación"],
}


def classify_event_type(text: str) -> str:
    text_lower = text.lower()
    scores: dict[str, int] = {k: 0 for k in _EVENT_KEYWORDS}
    for event_type, keywords in _EVENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[event_type] += 1
    return max(scores, key=lambda k: scores[k]) if any(scores.values()) else "strike"


async def extract_osint_event(
    text: str,
    image_path: Optional[str] = None,
    source: str = "manual",
    media_urls: Optional[list[str]] = None,
) -> dict:
    """
    Main extraction pipeline.
    1. Try fast local coordinate extraction.
    2. If no coords found (or image present), call Gemini Vision.
    3. Return a standardized tactical simulation event dict.
    """
    result: dict = {
        "lat": None,
        "lng": None,
        "event_type": classify_event_type(text),
        "country": None,
        "target": None,
        "brief": text[:300].strip(),
        "severity": 0.7,
        "source": source,
        "media_urls": media_urls or [],
        "raw_text": text,
    }

    # ── Step 1: Fast local extraction ────────────────────────────────────────
    coords = extract_coords_from_text(text)
    if coords:
        result["lat"], result["lng"] = coords
        logger.info(f"[OSINT Extractor] Coords from text: {coords}")

    # ── Step 2: Gemini Vision (if missing coords or has image) ───────────────
    if result["lat"] is None or image_path:
        try:
            result = await _gemini_extract(text, image_path, result)
        except Exception as exc:
            logger.warning(f"[OSINT Extractor] Gemini extraction failed: {exc}")

    return result


async def _gemini_extract(text: str, image_path: Optional[str], base: dict) -> dict:
    """Call Gemini 1.5 Pro Vision to extract structured event data."""
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("[OSINT Extractor] No GEMINI_API_KEY — skipping Gemini extraction")
        return base

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""Analyze this OSINT military/geopolitical report and extract tactical data.

TEXT: {text[:2000]}

Return ONLY a JSON object with these exact keys (no markdown, no explanation):
{{
  "lat": <decimal latitude or null>,
  "lng": <decimal longitude or null>,
  "event_type": "<strike|naval_movement|deployment|diplomatic>",
  "country": "<country name or null>",
  "target": "<name of military target/location or null>",
  "brief": "<one tactical sentence summary in Spanish>",
  "severity": <float 0.0-1.0 where 1.0=extreme>
}}

Rules:
- If DMS coordinates found (e.g. 24°03'49"N 47°32'45"E), convert to decimal.
- If place names mentioned (e.g. 'Prince Sultan Air Base'), estimate coordinates.
- event_type must be one of: strike, naval_movement, deployment, diplomatic
- brief must be in Spanish, concise, military tone.
"""

    parts = [prompt]

    # Add image if provided
    if image_path and Path(image_path).exists():
        import PIL.Image
        try:
            img = PIL.Image.open(image_path)
            parts.append(img)
        except Exception as e:
            logger.warning(f"[OSINT Extractor] Could not open image: {e}")

    response = model.generate_content(parts)
    raw = response.text.strip()

    # Strip markdown code blocks if present
    if raw.startswith("```"):
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    try:
        extracted = json.loads(raw)
        # Merge into base, only overwrite non-None values
        for key in ["lat", "lng", "event_type", "country", "target", "brief", "severity"]:
            val = extracted.get(key)
            if val is not None:
                base[key] = val
        logger.info(f"[OSINT Extractor] Gemini extracted: lat={base['lat']}, lng={base['lng']}, type={base['event_type']}")
    except json.JSONDecodeError as e:
        logger.error(f"[OSINT Extractor] Failed to parse Gemini JSON: {e}\nRaw: {raw[:500]}")

    return base
