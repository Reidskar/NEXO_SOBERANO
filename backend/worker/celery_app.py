"""
backend/worker/celery_app.py
==============================
Reemplaza APScheduler (que corría in-process y se perdía al reiniciar).
Celery corre en contenedor separado, es independiente del API.

Tareas programadas:
- Cada 5 min:   procesar cola de emails pendientes
- Cada 15 min:  sync señales WorldMonitor
- 9:00 AM:      enviar digests diarios (por tenant)
- Domingos 0h:  limpiar datos viejos (> 90 días)
"""

import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "nexo_soberano",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "backend.worker.tasks_email",
        "backend.worker.tasks_cleanup",
        "backend.worker.tasks_worldmonitor",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Santiago",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    result_expires=3600,

    beat_schedule={
        # Email: cada 5 minutos
        "procesar-email-queue": {
            "task": "tasks.email.procesar_cola",
            "schedule": 300.0,
        },
        # WorldMonitor: señales cada 15 minutos
        "sync-worldmonitor-signals": {
            "task": "tasks.wm.sync_signals",
            "schedule": 900.0,   # 15 min
        },
        # Digest diario con IA: 9 AM Santiago
        "digest-diario-inteligencia": {
            "task": "tasks.wm.daily_digest",
            "schedule": crontab(hour=9, minute=0),
        },
        # Limpieza semanal: domingo 00:00
        "limpieza-semanal": {
            "task": "tasks.cleanup.limpiar_datos_viejos",
            "schedule": crontab(hour=0, minute=0, day_of_week=0),
        },
    }
)
