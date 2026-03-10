web: uvicorn NEXO_CORE.main:app --host 0.0.0.0 --port $PORT
worker: celery -A backend.worker.celery_app worker --loglevel=info --pool=solo
beat: celery -A backend.worker.celery_app beat --loglevel=info
