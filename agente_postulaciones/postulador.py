from __future__ import annotations

from typing import Dict
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from scraper import Job


def auto_apply(
    job: Job,
    email: str,
    password: str,
    base_url: str,
    dry_run: bool = True,
    headless: bool = True,
) -> Dict:
    if dry_run:
        return {"ok": True, "status": "dry_run", "job_id": job.id, "apply_url": job.apply_url}

    if not email or not password:
        return {"ok": False, "status": "missing_credentials", "job_id": job.id}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()

            parsed = urlparse((base_url or "").strip())
            safe_base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "https://www.computrabajo.cl"
            page.goto(safe_base_url, wait_until="domcontentloaded", timeout=60000)

            login_candidates = [
                "a[href*='login']",
                "a:has-text('Ingresar')",
                "a:has-text('Iniciar sesión')",
            ]
            for sel in login_candidates:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click()
                    page.wait_for_timeout(500)
                    break

            page.locator("input[type='email'], input[name='email']").first.fill(email)
            page.locator("input[type='password'], input[name='password']").first.fill(password)
            page.locator("button[type='submit'], button:has-text('Ingresar'), button:has-text('Entrar')").first.click()
            page.wait_for_load_state("domcontentloaded")

            page.goto(job.apply_url, wait_until="domcontentloaded", timeout=60000)

            apply_selectors = [
                "button:has-text('Postular')",
                "a:has-text('Postular')",
                "button:has-text('Aplicar')",
            ]
            clicked = False
            for sel in apply_selectors:
                locator = page.locator(sel)
                if locator.count() > 0:
                    locator.first.click()
                    page.wait_for_timeout(800)
                    clicked = True
                    break

            browser.close()
            return {
                "ok": clicked,
                "status": "applied" if clicked else "apply_button_not_found",
                "job_id": job.id,
                "apply_url": job.apply_url,
            }
    except Exception as exc:
        return {"ok": False, "status": "error", "job_id": job.id, "error": str(exc)}
