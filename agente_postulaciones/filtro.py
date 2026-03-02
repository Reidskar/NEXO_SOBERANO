from __future__ import annotations

import re
from typing import Iterable, List

from scraper import Job


def _parse_salary_clp(text: str) -> int:
    if not text:
        return 0
    numbers = re.findall(r"\d[\d\.,]*", text.replace(" ", ""))
    if not numbers:
        return 0
    raw = numbers[0].replace(".", "").replace(",", "")
    return int(raw) if raw.isdigit() else 0


def _parse_distance_km(text: str) -> float:
    if not text:
        return 0.0
    match = re.search(r"(\d+[\.,]?\d*)\s*km", text.lower())
    if not match:
        return 0.0
    return float(match.group(1).replace(",", "."))


def apply_rules(
    jobs: Iterable[Job],
    min_salary_clp: int,
    max_distance_km: int,
    keywords_required: List[str],
    cv_profile: dict | None = None,
) -> List[Job]:
    profile = cv_profile or {}
    exclude_keywords = [str(x).lower() for x in profile.get("exclude_keywords", []) if str(x).strip()]
    roles_preferred = [str(x).lower() for x in profile.get("roles_preferred", []) if str(x).strip()]
    skills_must = [str(x).lower() for x in profile.get("skills_must", []) if str(x).strip()]
    profile_salary_min = int(profile.get("salary_min_clp", 0) or 0)

    effective_min_salary = max(int(min_salary_clp), profile_salary_min)
    effective_keywords = [x for x in keywords_required]
    for token in roles_preferred + skills_must:
        if token and token not in [k.lower() for k in effective_keywords]:
            effective_keywords.append(token)

    out: List[Job] = []
    for job in jobs:
        title_blob = f"{job.title} {job.company} {job.location} {job.salary_text} {job.distance_text}".lower()
        if exclude_keywords and any(k in title_blob for k in exclude_keywords):
            continue
        if effective_keywords and not any(k.lower() in title_blob for k in effective_keywords):
            continue
        salary = _parse_salary_clp(job.salary_text)
        if salary and salary < effective_min_salary:
            continue
        distance = _parse_distance_km(job.distance_text)
        if distance and distance > max_distance_km:
            continue
        out.append(job)
    return out
