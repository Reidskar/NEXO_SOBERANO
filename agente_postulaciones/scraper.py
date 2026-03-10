from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    salary_text: str
    distance_text: str
    detail_url: str
    apply_url: str

    def to_dict(self) -> dict:
        return asdict(self)


def _text(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def fetch_jobs(search_url: str, base_url: str, timeout: int = 20) -> List[Job]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }
    resp = requests.get(search_url, timeout=timeout, headers=headers)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("article, .box_offer, .js_row_offer, .bRS")
    if not cards:
        cards = soup.select("[data-link], [class*='offer'], [class*='job']")
    results: List[Job] = []

    for idx, card in enumerate(cards, start=1):
        title_node = card.select_one("h2 a, .js-o-link, a[data-link], a")
        company_node = card.select_one(".fc_aux, .it-blank, .company")
        location_node = card.select_one(".fc_aux-2, .location")
        salary_node = card.select_one(".salary, .tag.base, .w_100")
        dist_node = card.select_one(".distance, .fc_aux-3")

        detail_href = title_node.get("href", "") if title_node else ""
        detail_url = urljoin(base_url, str(detail_href) if detail_href else "")
        apply_url = detail_url

        stable_seed = (detail_url or f"{_text(title_node)}|{_text(company_node)}|{idx}").strip().lower()
        stable_id = hashlib.sha1(stable_seed.encode("utf-8", errors="ignore")).hexdigest()[:16]
        job = Job(
            id=f"job-{stable_id}",
            title=_text(title_node),
            company=_text(company_node),
            location=_text(location_node),
            salary_text=_text(salary_node),
            distance_text=_text(dist_node),
            detail_url=detail_url,
            apply_url=apply_url,
        )
        if job.title and job.detail_url:
            results.append(job)

    unique = {j.detail_url: j for j in results}
    return list(unique.values())
