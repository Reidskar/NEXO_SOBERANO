from __future__ import annotations

from typing import Dict

from ai_router import evaluate_with_router
from scraper import Job


def evaluate_job(
    job: Job,
    provider: str,
    anthropic_api_key: str,
    anthropic_model: str,
    openai_api_key: str,
    openai_model: str,
    cv_profile: dict | None = None,
) -> Dict:
    return evaluate_with_router(
        job=job,
        provider=provider,
        anthropic_api_key=anthropic_api_key,
        anthropic_model=anthropic_model,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        cv_profile=cv_profile,
    )
