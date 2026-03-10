import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

_raw_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if _raw_url.startswith("rediss://"):
    BROKER_URL = _raw_url + "?ssl_cert_reqs=CERT_NONE"
    SSL_OPTS = {"ssl_cert_reqs": None}
else:
    BROKER_URL = _raw_url
    SSL_OPTS = {}

celery_app = Celery("nexo")
celery_app.conf.update(
    broker_url=BROKER_URL,
    result_backend=BROKER_URL,
    broker_use_ssl=SSL_OPTS or None,
    redis_backend_use_ssl=SSL_OPTS or None,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Santiago",
    enable_utc=True,
    include=["backend.worker.tasks_core"],
    beat_schedule={
        "email-queue": {"task": "tasks.process_email_queue", "schedule": 300.0},
        "worldmonitor-sync": {"task": "tasks.sync_worldmonitor", "schedule": 900.0},
        "daily-digest": {"task": "tasks.send_daily_digest", "schedule": crontab(hour=9, minute=0)},
        "cleanup-sessions": {"task": "tasks.cleanup_old_sessions", "schedule": crontab(hour=3, minute=0)},
    }
)
