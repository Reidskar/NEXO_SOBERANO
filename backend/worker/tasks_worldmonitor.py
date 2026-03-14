"""
backend/worker/tasks_worldmonitor.py
======================================
Tareas Celery para sincronización periódica con WorldMonitor.

Frecuencias recomendadas (balanceando frescura vs costo):
- Señales críticas (surge militar, CII >0.8):  cada 5 min
- Noticias y clusters:                          cada 15 min
- Digest diario con IA:                         1x/día (9 AM)
- Limpieza señales viejas:                      1x/semana
"""

import os
import httpx
import psycopg2
import redis
import json
from datetime import datetime, timezone, timedelta
from psycopg2.extras import RealDictCursor
from celery import shared_task

from backend.services.worldmonitor_bridge import WorldMonitorBridge, SIGNAL_TYPES
from backend.worker.celery_app import celery_app

DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WM_BASE_URL  = os.getenv("WORLDMONITOR_API_URL", "https://worldmonitor.app")


def get_all_active_tenants() -> list[dict]:
    """Obtiene todos los tenants activos con su configuración de WorldMonitor."""
    try:
        with psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, slug, plan, max_tokens_dia
                    FROM tenants
                    WHERE active = TRUE
                """)
                return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        log.info(f"⚠️  Error obteniendo tenants: {e}")
        return []


def get_tenant_wm_config(tenant_slug: str, schema: str) -> dict:
    """
    Obtiene la configuración de WorldMonitor para un tenant.
    Por ahora se guarda en Redis; en producción iría en una tabla de config.
    """
    r = redis.from_url(REDIS_URL, decode_responses=True)
    config_key = f"nexo:wm_config:{tenant_slug}"
    cached = r.get(config_key)
    if cached:
        return json.loads(cached)

    # Configuración por defecto si no hay personalizada
    return {
        "enabled": True,
        "alert_threshold": 0.65,
        "regions_of_interest": [],      # [] = todas las regiones
        "signal_types": list(SIGNAL_TYPES.keys()),
        "digest_enabled": True,
        "realtime_alerts": True,
    }


# ── TAREA: Ingestar señales recientes de WorldMonitor ──────────

@celery_app.task(
    name="tasks.wm.sync_signals",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def sync_worldmonitor_signals(self):
    """
    Sincroniza las últimas señales de WorldMonitor para todos los tenants.
    Corre cada 15 minutos (configurado en celery_app beat_schedule).

    Nota de costo: Esta tarea usa SOLO embeddings locales (sentence-transformers).
    No consume tokens de API de IA. Costo = $0.
    """
    log.info(f"[{datetime.now().isoformat()}] 🌍 Iniciando sync WorldMonitor...")

    tenants = get_all_active_tenants()
    r = redis.from_url(REDIS_URL, decode_responses=True)

    total_ingested = 0

    for tenant in tenants:
        slug   = tenant["slug"]
        schema = f"tenant_{slug.replace('-', '_')}"
        config = get_tenant_wm_config(slug, schema)

        if not config.get("enabled", True):
            continue

        try:
            # Obtener timestamp de última sincronización
            last_sync_key = f"nexo:wm_last_sync:{slug}"
            last_sync = r.get(last_sync_key)
            if not last_sync:
                # Primera vez: últimas 2 horas
                since = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            else:
                since = last_sync

            # Llamar API de WorldMonitor
            # En la práctica, WorldMonitor puede exponer un endpoint
            # /api/signals?since=ISO&severity_min=0.5
            # Por ahora construimos señales simuladas desde su API pública
            signals = fetch_wm_signals(since=since, severity_min=0.4)

            if signals:
                bridge = WorldMonitorBridge(slug)
                result = bridge.ingest_batch(signals)
                total_ingested += result["ingested"]

                # Disparar alertas para señales críticas
                if config.get("realtime_alerts"):
                    critical = [s for s in signals if s.get("severity", 0) >= config["alert_threshold"]]
                    if critical:
                        send_wm_alerts.delay(slug, critical)

            # Actualizar timestamp de última sync
            r.set(last_sync_key, datetime.now(timezone.utc).isoformat())

        except Exception as e:
            log.info(f"⚠️  Error sincronizando tenant {slug}: {e}")
            continue

    log.info(f"✅ WorldMonitor sync completado: {total_ingested} señales ingestionadas")
    return {"total_ingested": total_ingested, "tenants_processed": len(tenants)}


def fetch_wm_signals(since: str, severity_min: float = 0.4) -> list[dict]:
    """
    Obtiene señales de WorldMonitor.

    Opciones de integración con WorldMonitor:
    1. WorldMonitor expone webhook → push a /nexo/worldmonitor/ingest
    2. NEXO hace polling a una API que WorldMonitor comparte
    3. NEXO lee directamente las Edge Functions de WorldMonitor

    Esta función implementa la opción 2 (polling).
    Para la opción 1, el webhook se registra en WorldMonitor y apunta
    a https://tu-nexo.com/nexo/worldmonitor/ingest
    """
    signals = []

    try:
        # Intentar obtener señales del API de WorldMonitor
        # Endpoint hipotético basado en la arquitectura de WorldMonitor
        endpoints = [
            f"{WM_BASE_URL}/api/signals",
            f"{WM_BASE_URL}/api/cii/alerts",
            f"{WM_BASE_URL}/api/military/surges",
        ]

        headers = {}
        wm_key = os.getenv("WORLDMONITOR_API_KEY", "")
        if wm_key:
            headers["X-API-Key"] = wm_key

        for endpoint in endpoints:
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(
                        endpoint,
                        params={"since": since, "severity_min": severity_min},
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        # Normalizar al formato de señal de NEXO
                        raw_signals = data if isinstance(data, list) else data.get("signals", [])
                        for s in raw_signals:
                            normalized = normalize_wm_signal(s)
                            if normalized:
                                signals.append(normalized)
            except Exception:
                continue  # Endpoint no disponible, continuar

    except Exception as e:
        log.info(f"⚠️  Error fetching WorldMonitor signals: {e}")

    return signals


def normalize_wm_signal(raw: dict) -> dict | None:
    """
    Normaliza una señal de WorldMonitor al formato interno de NEXO.
    Maneja los diferentes formatos de CII, geo-convergence, military surge, etc.
    """
    if not raw:
        return None

    # Detectar tipo de señal
    signal_type = "news_cluster"  # default
    if "cii" in raw or "instability" in raw.get("type", "").lower():
        signal_type = "cii_spike"
    elif "convergence" in raw.get("type", "").lower():
        signal_type = "geo_convergence"
    elif "military" in raw.get("type", "").lower() or "surge" in raw.get("type", "").lower():
        signal_type = "military_surge"
    elif "protest" in raw.get("type", "").lower() or "conflict" in raw.get("type", "").lower():
        signal_type = "protest_event"
    elif "ais" in raw.get("type", "").lower() or "maritime" in raw.get("type", "").lower():
        signal_type = "ais_anomaly"
    elif raw.get("type"):
        signal_type = raw["type"]

    return {
        "type": signal_type,
        "severity": float(raw.get("severity") or raw.get("score") or raw.get("cii_score") or 0.5),
        "country": raw.get("country") or raw.get("location", {}).get("country"),
        "region": raw.get("region"),
        "theater": raw.get("theater"),
        "title": raw.get("title") or raw.get("headline") or raw.get("summary", "")[:100],
        "summary": raw.get("summary") or raw.get("description") or raw.get("content", ""),
        "source_articles": raw.get("articles") or raw.get("sources") or [],
        "coordinates": raw.get("coordinates") or raw.get("location"),
        "timestamp": raw.get("timestamp") or raw.get("publishedAt") or datetime.now(timezone.utc).isoformat(),
        "raw_data": raw,
    }


# ── TAREA: Enviar alertas de señales críticas ──────────────────

@celery_app.task(name="tasks.wm.send_alerts", bind=True, max_retries=2)
def send_wm_alerts(self, tenant_slug: str, signals: list[dict]):
    """
    Envía alertas push/email a los usuarios del tenant
    para señales críticas de WorldMonitor.
    Personaliza el contenido según perfil cognitivo de cada usuario.
    """
    if not signals:
        return

    schema = f"tenant_{tenant_slug.replace('-', '_')}"

    try:
        with psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor) as conn:
            with conn.cursor() as cur:
                # Obtener usuarios activos con sus perfiles cognitivos
                cur.execute(f"""
                    SELECT u.id, u.email,
                           cp.vocabulary, cp.content_length,
                           cp.tone, cp.learning_style
                    FROM public.users u
                    LEFT JOIN {schema}.cognitive_profiles cp ON cp.user_id = u.id
                    WHERE u.tenant_id = (
                        SELECT id FROM public.tenants WHERE slug = %s
                    ) AND u.active = TRUE
                """, (tenant_slug,))
                users = cur.fetchall()

        if not users:
            return

        bridge = WorldMonitorBridge(tenant_slug)

        for user in users:
            cognitive = {
                "vocabulary":     user.get("vocabulary", "simple"),
                "content_length": user.get("content_length", "200w"),
                "tone":           user.get("tone", "formal"),
            }

            for signal in signals:
                alert = bridge.build_alert_content(signal, cognitive)

                # Encolar email de alerta
                # (reutiliza el sistema de email_queue de NEXO)
                try:
                    with psycopg2.connect(DATABASE_URL) as conn:
                        with conn.cursor() as cur:
                            cur.execute(f"""
                                INSERT INTO {schema}.email_queue
                                (user_id, status, subject, html_content)
                                VALUES (%s, 'pending', %s, %s)
                            """, (
                                user["id"],
                                alert["subject"],
                                build_alert_html(alert, signal),
                            ))
                        conn.commit()
                except Exception as e:
                    log.info(f"⚠️  Error encolando alerta: {e}")

    except Exception as e:
        log.info(f"⚠️  Error enviando alertas WM: {e}")
        raise self.retry(exc=e)


def build_alert_html(alert: dict, signal: dict) -> str:
    """Genera HTML del email de alerta."""
    articles_html = ""
    for art in signal.get("source_articles", [])[:3]:
        url   = art.get("url", "#")
        title = art.get("title", "Ver fuente")
        articles_html += f'<li><a href="{url}" style="color:#3b82f6">{title}</a></li>'

    coords_html = ""
    if signal.get("coordinates"):
        lat = signal["coordinates"].get("lat", 0)
        lon = signal["coordinates"].get("lon", 0)
        coords_html = f'<p style="color:#9ca3af;font-size:12px">📍 {lat:.2f}°, {lon:.2f}°</p>'

    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#111827;color:#f9fafb;padding:24px;border-radius:12px">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
        <span style="font-size:28px">{alert.get('subject','').split(']')[0].replace('[','').strip() if ']' in alert.get('subject','') else '🔔'}</span>
        <div>
          <span style="background:#ef4444;color:white;padding:2px 10px;border-radius:99px;font-size:12px;font-weight:bold">
            {alert.get('severity','Alerta')}
          </span>
          <span style="background:#1f2937;color:#9ca3af;padding:2px 10px;border-radius:99px;font-size:12px;margin-left:6px">
            {alert.get('type','Evento')}
          </span>
        </div>
      </div>
      <h2 style="font-size:18px;font-weight:bold;color:#f9fafb;margin:0 0 12px 0">
        {signal.get('title','')}
      </h2>
      <p style="color:#d1d5db;line-height:1.6;margin-bottom:16px">
        {alert.get('body','')}
      </p>
      {coords_html}
      {'<ul style="color:#d1d5db;padding-left:20px">' + articles_html + '</ul>' if articles_html else ''}
      <p style="color:#6b7280;font-size:11px;margin-top:20px;border-top:1px solid #374151;padding-top:12px">
        Alerta generada por NEXO SOBERANO · Datos: WorldMonitor · {alert.get('timestamp','')}
      </p>
    </div>
    """


# ── TAREA: Digest diario de inteligencia global ────────────────

@celery_app.task(name="tasks.wm.daily_digest", bind=True)
def generate_daily_intelligence_digest(self):
    """
    Genera un digest diario de inteligencia global para cada tenant.
    Usa IA (Gemini Flash) para sintetizar las señales del día.
    Corre 1x/día a las 9 AM → costo mínimo de IA.
    """
    from backend.services.cost_manager_multitenant import CostManagerMultiTenant

    tenants = get_all_active_tenants()

    for tenant in tenants:
        slug   = tenant["slug"]
        schema = f"tenant_{slug.replace('-', '_')}"
        config = get_tenant_wm_config(slug, schema)

        if not config.get("digest_enabled", True):
            continue

        try:
            cost_mgr = CostManagerMultiTenant(slug)
            if not cost_mgr.puede_operar(tokens_estimados=2000):
                log.info(f"⚠️  Tenant {slug} sin presupuesto para digest")
                continue

            # Obtener señales de las últimas 24h
            bridge = WorldMonitorBridge(slug)
            top_signals = bridge.query_intelligence(
                "eventos críticos alta severidad últimas 24 horas",
                top_k=10,
                filter_severity_min=0.5,
            )

            if not top_signals:
                continue

            # Sintetizar con IA (modelo más barato)
            digest_text = synthesize_digest_with_ai(top_signals, slug, cost_mgr)

            # Enviar a todos los usuarios del tenant
            send_digest_to_users.delay(slug, digest_text, top_signals)

        except Exception as e:
            log.info(f"⚠️  Error generando digest para {slug}: {e}")
            continue


def synthesize_digest_with_ai(signals: list[dict], tenant_slug: str,
                                cost_mgr) -> str:
    """Sintetiza señales en un resumen coherente usando Gemini Flash."""
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        # Sin IA: generar digest textual simple
        return build_text_digest(signals)

    signals_text = "\n".join([
        f"- [{s.get('type','?')}] {s.get('country','Global')}: {s.get('title','')} (severidad: {s.get('severity',0):.1f})"
        for s in signals[:8]
    ])

    prompt = f"""Eres un analista de inteligencia geopolítica. 
Resume en 3-4 párrafos concisos las siguientes señales de inteligencia global del día de hoy.
Identifica patrones, conexiones entre eventos y riesgos emergentes.
Sé objetivo y basado en datos. No especules más allá de los datos.

SEÑALES:
{signals_text}

RESUMEN (en español, tono profesional):"""

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        tokens_used = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 500
        cost_mgr.registrar("gemini-1.5-flash", tokens_used // 2, tokens_used // 2, "wm_digest")
        return response.text
    except Exception as e:
        log.info(f"⚠️  Error en síntesis IA: {e}")
        return build_text_digest(signals)


def build_text_digest(signals: list[dict]) -> str:
    """Digest sin IA: lista estructurada de señales."""
    lines = ["📊 RESUMEN DE INTELIGENCIA GLOBAL\n"]
    for s in signals[:8]:
        nivel = "🔴" if s.get("severity", 0) > 0.7 else "🟡" if s.get("severity", 0) > 0.4 else "🟢"
        lines.append(f"{nivel} {s.get('country','Global')}: {s.get('title','')}")
    return "\n".join(lines)


@celery_app.task(name="tasks.wm.send_digest")
def send_digest_to_users(tenant_slug: str, digest_text: str, signals: list[dict]):
    """Encola el digest diario para todos los usuarios del tenant."""
    schema = f"tenant_{tenant_slug.replace('-', '_')}"

    try:
        with psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM public.users WHERE tenant_id = "
                    "(SELECT id FROM public.tenants WHERE slug = %s) AND active = TRUE",
                    (tenant_slug,)
                )
                users = cur.fetchall()

        for user in users:
            with psycopg2.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        INSERT INTO {schema}.email_queue
                        (user_id, status, subject, html_content)
                        VALUES (%s, 'pending', %s, %s)
                    """, (
                        user["id"],
                        f"🌍 Digest de Inteligencia Global — {datetime.now().strftime('%d/%m/%Y')}",
                        build_digest_html(digest_text, signals),
                    ))
                conn.commit()

    except Exception as e:
        log.info(f"⚠️  Error enviando digest: {e}")


def build_digest_html(digest_text: str, signals: list[dict]) -> str:
    """HTML del digest diario."""
    signals_html = "".join([
        f"""<tr>
          <td style="padding:8px;color:#d1d5db">{s.get('country','Global')}</td>
          <td style="padding:8px;color:#d1d5db">{s.get('title','')[:80]}</td>
          <td style="padding:8px;text-align:center">
            <span style="background:{'#ef4444' if s.get('severity',0)>0.7 else '#f59e0b' if s.get('severity',0)>0.4 else '#10b981'};
                         color:white;padding:2px 8px;border-radius:99px;font-size:11px">
              {s.get('severity',0):.0%}
            </span>
          </td>
        </tr>"""
        for s in signals[:8]
    ])

    return f"""
    <div style="font-family:sans-serif;max-width:700px;margin:0 auto;background:#111827;color:#f9fafb;padding:32px;border-radius:12px">
      <h1 style="font-size:22px;font-weight:bold;margin-bottom:4px">🌍 Digest de Inteligencia Global</h1>
      <p style="color:#6b7280;margin-bottom:24px">{datetime.now().strftime('%A %d de %B, %Y')}</p>

      <div style="background:#1f2937;border-radius:8px;padding:20px;margin-bottom:24px;line-height:1.7;color:#d1d5db">
        {digest_text.replace(chr(10), '<br>')}
      </div>

      <h2 style="font-size:16px;font-weight:bold;margin-bottom:12px">Señales destacadas</h2>
      <table style="width:100%;border-collapse:collapse">
        <thead>
          <tr style="border-bottom:1px solid #374151">
            <th style="padding:8px;text-align:left;color:#9ca3af;font-size:12px">País/Región</th>
            <th style="padding:8px;text-align:left;color:#9ca3af;font-size:12px">Evento</th>
            <th style="padding:8px;text-align:center;color:#9ca3af;font-size:12px">Severidad</th>
          </tr>
        </thead>
        <tbody>{signals_html}</tbody>
      </table>

      <p style="color:#6b7280;font-size:11px;margin-top:24px;border-top:1px solid #374151;padding-top:16px">
        NEXO SOBERANO · Inteligencia global en tiempo real via WorldMonitor
      </p>
    </div>
    """
