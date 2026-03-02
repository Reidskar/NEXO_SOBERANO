from __future__ import annotations

import json
import importlib
from typing import Dict

from scraper import Job


def evaluate_with_router(
    job: Job,
    provider: str,
    anthropic_api_key: str,
    anthropic_model: str,
    openai_api_key: str,
    openai_model: str,
    cv_profile: dict | None = None,
) -> Dict:
    provider = (provider or "auto").lower().strip()

    if provider in {"auto", "anthropic"} and anthropic_api_key:
        result = _eval_anthropic(job, anthropic_api_key, anthropic_model, cv_profile=cv_profile)
        if result.get("ok"):
            return result

    if provider in {"auto", "openai"} and openai_api_key:
        result = _eval_openai(job, openai_api_key, openai_model, cv_profile=cv_profile)
        if result.get("ok"):
            return result

    heuristic = _heuristic(job, cv_profile=cv_profile)
    heuristic["source"] = "heuristic"
    heuristic["ok"] = True
    return heuristic


def _prompt_payload(job: Job) -> str:
    payload = {
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "salary": job.salary_text,
        "distance": job.distance_text,
        "url": job.detail_url,
    }
    return json.dumps(payload, ensure_ascii=False)


def _normalize(data: Dict, source: str) -> Dict:
    score = int(data.get("score", 1))
    return {
        "ok": True,
        "score": max(1, min(10, score)),
        "reason": str(data.get("reason", ""))[:1200],
        "risk_flags": data.get("risk_flags", []),
        "source": source,
    }


def _eval_anthropic(job: Job, api_key: str, model: str, cv_profile: dict | None = None) -> Dict:
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        cv_json = json.dumps(cv_profile or {}, ensure_ascii=False)
        msg = client.messages.create(
            model=model,
            max_tokens=300,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Evalúa esta oferta laboral respecto al perfil CV entregado. "
                        "Responde SOLO JSON con: score(1-10), reason, risk_flags(array). "
                        f"CV: {cv_json}. Oferta: {_prompt_payload(job)}"
                    ),
                }
            ],
        )
        text_parts = []
        for block in msg.content:
            block_text = getattr(block, "text", None)
            if isinstance(block_text, str) and block_text.strip():
                text_parts.append(block_text.strip())
        text = "\n".join(text_parts).strip()
        if not text:
            raise ValueError("Claude no devolvió bloque de texto parseable")
        data = json.loads(text)
        return _normalize(data, "claude")
    except Exception as exc:
        return {"ok": False, "error": str(exc), "source": "claude"}


def _eval_openai(job: Job, api_key: str, model: str, cv_profile: dict | None = None) -> Dict:
    try:
        openai_mod = importlib.import_module("openai")
        OpenAI = getattr(openai_mod, "OpenAI")

        client = OpenAI(api_key=api_key)
        cv_json = json.dumps(cv_profile or {}, ensure_ascii=False)
        completion = client.chat.completions.create(
            model=model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "Eres un evaluador de empleos. Devuelve JSON estricto.",
                },
                {
                    "role": "user",
                    "content": (
                        "Evalúa esta oferta laboral según el CV entregado. "
                        "Responde JSON con: score(1-10), reason, risk_flags(array). "
                        f"CV: {cv_json}. Oferta: {_prompt_payload(job)}"
                    ),
                },
            ],
        )
        text = completion.choices[0].message.content.strip()
        data = json.loads(text)
        return _normalize(data, "openai")
    except Exception as exc:
        return {"ok": False, "error": str(exc), "source": "openai"}


def _heuristic(job: Job, cv_profile: dict | None = None) -> Dict:
    text = f"{job.title} {job.company} {job.location}".lower()
    profile = cv_profile or {}
    score = 5
    if any(k in text for k in ["python", "backend", "datos", "ia", "ai"]):
        score += 2
    if any(k in text for k in ["senior", "sr", "engineer"]):
        score += 1
    if any(k in text for k in ["remoto", "remote", "híbrido", "hibrido"]):
        score += 1

    skills_must = [str(x).lower() for x in profile.get("skills_must", []) if str(x).strip()]
    skills_bonus = [str(x).lower() for x in profile.get("skills_bonus", []) if str(x).strip()]
    exclude_keywords = [str(x).lower() for x in profile.get("exclude_keywords", []) if str(x).strip()]

    if skills_must:
        hits = sum(1 for token in skills_must if token in text)
        score += min(2, hits)
    if skills_bonus:
        bonus_hits = sum(1 for token in skills_bonus if token in text)
        score += min(2, bonus_hits)
    if exclude_keywords and any(token in text for token in exclude_keywords):
        score -= 3

    return {
        "score": max(1, min(10, score)),
        "reason": "Heurística local por palabras clave, modalidad y ajuste con perfil CV.",
        "risk_flags": [],
    }
